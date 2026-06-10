"""Single-agent orchestrator (PRD §9).

`run_turn(conversation_id, user_message, payload)` drives one turn of the guided
ordering workflow. This unit is intentionally free of FastAPI imports so it can
become a single LangGraph node later. The LLM, session store, and all backend
services are injected behind interfaces.

The workflow transitions, UI payloads, and all transactional data (quote, cart,
order) are deterministic. Only the conversational reply text comes from the LLM,
and it is grounded on FACTS passed per turn (PRD: the LLM never invents prices,
quote IDs, or order numbers).
"""
from __future__ import annotations

import os
from pathlib import Path

from .. import tools
from ..formatting import format_eur
from ..mapping import accepted_lines, map_product, map_products
from ..models import MappingStatus, OrderInfo, ParsedItem, SessionState, TurnResult, WorkflowStep
from ..parsing import extract_quantity, first_product_token, parse_typed_products
from ..services.interfaces import (
    CartService,
    CatalogService,
    OrderService,
    PricingService,
    QuoteService,
)
from ..session import InMemorySessionStore, SessionStore
from .llm import Intent, LLMClient, MockLLMClient, RealLLMClient

# Sliding-window memory: messages handed to the LLM per turn, and the cap kept in the session.
MAX_HISTORY_MESSAGES = 16  # ~8 exchanges of context for the LLM
MAX_STORED_MESSAGES = 40   # bound the session transcript to keep memory flat

# UI control actions: handled deterministically, no LLM call, kept out of the transcript.
_CONTROL_INTENTS = {Intent.UPDATE_CART, Intent.REMOVE_CART, Intent.SHOW_CART}

_STUBS = {
    Intent.STUB_CERTIFICATES: ("Certificates", "Requesting product certificates is coming soon."),
    Intent.STUB_SUPPORT: ("Support", "Technical support is coming soon."),
    Intent.STUB_ORDER_STATUS: ("Order status", "Order status tracking is coming soon."),
    Intent.STUB_PRICE_AVAILABILITY: (
        "Price & Availability",
        "Price & availability lookup is coming soon.",
    ),
}


class Orchestrator:
    def __init__(
        self,
        *,
        llm: LLMClient,
        sessions: SessionStore,
        catalog: CatalogService,
        pricing: PricingService,
        quotes: QuoteService,
        carts: CartService,
        orders: OrderService,
    ) -> None:
        self._llm = llm
        self._sessions = sessions
        self._catalog = catalog
        self._pricing = pricing
        self._quotes = quotes
        self._carts = carts
        self._orders = orders
        self._po_counter = 0  # sequential prefill: SCHAMA0001, SCHAMA0002, ...

    def _next_po_number(self) -> str:
        self._po_counter += 1
        return f"SCHAMA{self._po_counter:04d}"

    def create_conversation(self) -> str:
        return self._sessions.create().conversation_id

    def get_state(self, conversation_id: str) -> SessionState | None:
        return self._sessions.get(conversation_id)

    def get_quote(self, quote_id: str):
        return self._quotes.get_quote(quote_id)

    def run_turn(
        self,
        conversation_id: str,
        user_message: str,
        payload: dict | None = None,
    ) -> TurnResult:
        state = self._sessions.get(conversation_id) or self._sessions.create(conversation_id)
        intent = self._llm.decide(user_message, state.step)
        # _reply() reads state.transcript (prior turns only) as LLM history; append after.
        result = self._handle(intent, state, user_message, payload or {})
        if intent not in _CONTROL_INTENTS:
            state.transcript.append({"role": "user", "text": user_message})
            state.transcript.append({"role": "assistant", "text": result.text})
            if len(state.transcript) > MAX_STORED_MESSAGES:
                state.transcript = state.transcript[-MAX_STORED_MESSAGES:]
        self._sessions.save(state)
        return result

    def _handle(
        self, intent: Intent, state: SessionState, message: str, payload: dict
    ) -> TurnResult:
        if intent in _STUBS:
            title, msg = _STUBS[intent]
            return self._reply(
                state, "stub", message, [tools.stub_payload(title, msg)], {"title": title, "message": msg}
            )

        handlers = {
            Intent.BUY_PRODUCTS: self._buy_products,
            Intent.SUBMIT_PRODUCTS: self._submit_products,
            Intent.REQUEST_QUOTE: self._request_quote,
            Intent.DECLINE_MAPPINGS: self._decline,
            Intent.PROCEED: self._proceed,
            Intent.PLACE_ORDER: self._place_order,
            Intent.PRODUCT_DETAILS: self._product_details,
            Intent.ORDER_DETAILS: self._order_details,
            Intent.ADD_TO_CART: self._add_to_cart,
            Intent.CHANGE_QTY: self._change_quantity,
            Intent.UPDATE_CART: self._update_cart,
            Intent.REMOVE_CART: self._remove_cart,
            Intent.SHOW_CART: self._show_cart,
        }
        handler = handlers.get(intent)
        if handler is None:
            return self._reply(state, "unknown", message, [], {})
        return handler(state, message, payload)

    # --- intent handlers -------------------------------------------------

    def _buy_products(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        self._reset_order(state)
        state.step = WorkflowStep.AWAITING_PRODUCTS
        return self._reply(
            state, "buy_products", message,
            [tools.upload_widget_payload(), tools.type_prompt_payload()],
        )

    def _submit_products(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        # Typing products after a completed order starts a fresh one.
        if state.step == WorkflowStep.CONFIRMED:
            self._reset_order(state)

        items = parse_typed_products(message)
        valid = [i for i in items if i.valid]
        if not items:
            return self._reply(state, "empty_list", message, [tools.type_prompt_payload()])
        if not valid:
            return self._reply(state, "invalid_qty", message, [tools.type_prompt_payload()])

        results = map_products(valid, self._catalog)

        # Add-to-existing-order mode: a cart/quote already exists -> add accepted items straight in.
        if state.step in (WorkflowStep.QUOTE_READY, WorkflowStep.CART_REVIEW):
            accepted = accepted_lines(results)
            if not accepted:
                return self._reply(state, "added_none", message, [tools.mapping_table_payload(results)])
            cart = self._merge_into_cart(state, accepted)
            state.mapping_results = state.mapping_results + results
            return self._reply(
                state, "added_items", message,
                [tools.cart_payload(cart)],
                {
                    "item_count": cart.item_count,
                    "total_display": format_eur(cart.total),
                    "added": [{"sku": sku, "qty": qty} for sku, qty in accepted],
                },
            )

        # Initial review mode: accumulate items typed before the quote.
        if state.step == WorkflowStep.AWAITING_MAPPING_REVIEW and state.mapping_results:
            state.mapping_results = state.mapping_results + results
            state.parsed_items = state.parsed_items + valid
        else:
            state.mapping_results = results
            state.parsed_items = valid
        state.step = WorkflowStep.AWAITING_MAPPING_REVIEW

        return self._reply(
            state, "mapping_ready", message,
            [tools.mapping_table_payload(state.mapping_results)],
            self._mapping_facts(state.mapping_results),
        )

    def _product_details(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        token = first_product_token(message)
        result = map_product(ParsedItem(raw=token or message, qty=1), self._catalog)
        entry = self._catalog.get(result.matched_sku) if result.matched_sku else None
        if entry is None:
            return self._reply(state, "product_details_missing", message, [])
        # The input isn't itself a Schaeffler product (it resolved via cross-reference/fuzzy):
        # name the Schaeffler equivalent and ask before showing its details.
        if result.status is MappingStatus.MAPPED:
            return self._reply(
                state, "product_equivalent", message,
                [tools.equivalent_prompt_payload(result.raw, entry)],
                {"raw": result.raw, "sku": entry.schaeffler_sku, "description": entry.description},
            )
        return self._reply(
            state, "product_details", message,
            [tools.product_details_payload(entry)],
            {"sku": entry.schaeffler_sku, "in_stock": entry.availability.in_stock},
        )

    def _order_details(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        if not state.order_id:
            return self._reply(state, "unknown", message, [])
        po = state.order_info.purchase_order_number if state.order_info else None
        return self._reply(
            state, "order_recap", message, [], {"order_id": state.order_id, "po": po}
        )

    def _add_to_cart(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        sku = payload.get("sku")
        qty = self._as_qty(payload.get("qty"), default=1)
        entry = self._catalog.get(sku) if sku else None
        if entry is None:
            return self._reply(state, "product_details_missing", message, [])
        # Already in the cart: confirm before adding again, and let the user pick a quantity.
        if not payload.get("confirm_add"):
            existing = next(
                (i for i in self._carts.get_cart(state.conversation_id).items
                 if i.sku == entry.schaeffler_sku),
                None,
            )
            if existing is not None:
                return self._reply(
                    state, "already_in_cart", message,
                    [tools.already_in_cart_payload(entry, existing.qty)],
                    {"sku": entry.schaeffler_sku, "current_qty": existing.qty},
                )
        cart = self._merge_into_cart(state, [(entry.schaeffler_sku, qty)])
        return self._reply(
            state, "added_items", message,
            [tools.cart_payload(cart)],
            {
                "item_count": cart.item_count,
                "total_display": format_eur(cart.total),
                "added": [{"sku": entry.schaeffler_sku, "qty": qty}],
            },
        )

    def _change_quantity(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        """Apply a free-text quantity change to a cart line (e.g. "make it 20", "add 20 more").

        Resolves the target SKU from a typed product code, or the sole cart line when there's
        only one. "add"/"more" adds to the current quantity; otherwise the quantity is set.
        """
        cart = self._carts.get_cart(state.conversation_id)
        if not cart.items:
            return self._reply(state, "cart_empty", message, [tools.cart_payload(cart)])

        qty = extract_quantity(message)
        if qty is None:
            return self._reply(state, "qty_unclear", message, [tools.cart_payload(cart)])

        token = first_product_token(message)
        sku = map_product(ParsedItem(raw=token, qty=1), self._catalog).matched_sku if token else None
        if sku is None or not any(i.sku == sku for i in cart.items):
            if len(cart.items) == 1:
                sku = cart.items[0].sku
            else:
                return self._reply(
                    state, "which_item", message, [tools.cart_payload(cart)],
                    {"items": [i.sku for i in cart.items]},
                )

        norm = message.lower()
        if any(w in norm for w in ("add", "more", "another", "additional", "extra")) and qty > 0:
            cart = self._carts.add_to_cart(state.conversation_id, [(sku, qty)])
        else:
            cart = self._carts.update_cart_item(state.conversation_id, sku, qty)

        item = next((i for i in cart.items if i.sku == sku), None)
        return self._reply(
            state, "qty_updated", message, [tools.cart_payload(cart)],
            {
                "sku": sku,
                "qty": item.qty if item else 0,
                "item_count": cart.item_count,
                "total_display": format_eur(cart.total),
            },
        )

    def _update_cart(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        sku = payload.get("sku")
        qty = self._as_qty(payload.get("qty"), default=0)
        if sku:
            self._carts.update_cart_item(state.conversation_id, sku, qty)
        return self._cart_control(state)

    def _remove_cart(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        sku = payload.get("sku")
        if sku:
            self._carts.remove_cart_item(state.conversation_id, sku)
        return self._cart_control(state)

    def _show_cart(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        return self._cart_control(state)

    def _request_quote(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        if state.step != WorkflowStep.AWAITING_MAPPING_REVIEW:
            return self._reply(state, "request_quote_too_early", message, [])
        lines = accepted_lines(state.mapping_results)
        if not lines:
            return self._reply(
                state, "no_mapping", message, [tools.mapping_table_payload(state.mapping_results)]
            )
        quote = self._quotes.create_quote(lines)
        state.quote_id = quote.quote_id
        state.step = WorkflowStep.QUOTE_READY
        return self._reply(
            state, "quote_ready", message,
            [tools.quote_card_payload(quote)],
            {"quote_id": quote.quote_id, "total_display": format_eur(quote.total), "line_count": len(quote.lines)},
        )

    def _decline(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        state.parsed_items = []
        state.mapping_results = []
        state.step = WorkflowStep.AWAITING_PRODUCTS
        return self._reply(state, "decline", message, [tools.type_prompt_payload()])

    def _proceed(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        if state.step == WorkflowStep.QUOTE_READY:
            cart = self._carts.add_to_cart(
                state.conversation_id, accepted_lines(state.mapping_results)
            )
            state.step = WorkflowStep.CART_REVIEW
            return self._reply(
                state, "cart", message,
                [tools.cart_payload(cart)],
                {"item_count": cart.item_count, "total_display": format_eur(cart.total)},
            )

        if state.step == WorkflowStep.CART_REVIEW:
            state.step = WorkflowStep.CHECKOUT
            # Prefill the PO number once per order (stable if the form re-renders).
            if not state.po_prefill:
                state.po_prefill = self._next_po_number()
            return self._reply(
                state, "checkout", message, [tools.checkout_form_payload(state.po_prefill)]
            )

        return self._reply(state, "proceed_nothing", message, [])

    def _place_order(self, state: SessionState, message: str, payload: dict) -> TurnResult:
        if state.step != WorkflowStep.CHECKOUT:
            return self._reply(state, "place_order_too_early", message, [])

        po_number = (payload.get("purchase_order_number") or "").strip()
        if not po_number:
            return self._reply(state, "need_po", message, [tools.checkout_form_payload(state.po_prefill)])

        order_info = OrderInfo(
            purchase_order_number=po_number,
            order_type=payload.get("order_type"),
            comment=payload.get("comment"),
        )
        cart = self._carts.get_cart(state.conversation_id)
        order = self._orders.create_order(cart, order_info)
        state.order_info = order_info
        state.order_id = order.order_id
        state.step = WorkflowStep.CONFIRMED
        return self._reply(
            state, "confirmed", message,
            [tools.confirmation_payload(order)],
            {"order_id": order.order_id},
        )

    # --- helpers ---------------------------------------------------------

    def _reset_order(self, state: SessionState) -> None:
        """Clear the working order state and empty the cart (for a fresh order)."""
        state.parsed_items = []
        state.mapping_results = []
        state.quote_id = None
        state.order_info = None
        state.order_id = None
        state.po_prefill = None  # next order gets a fresh PO number
        self._carts.clear_cart(state.conversation_id)

    def _cart_control(self, state: SessionState) -> TurnResult:
        """Deterministic cart view/edit response — no LLM call (kept out of transcript)."""
        cart = self._carts.get_cart(state.conversation_id)
        if cart.item_count and state.step not in (WorkflowStep.CART_REVIEW, WorkflowStep.CHECKOUT):
            state.step = WorkflowStep.CART_REVIEW
        text = "" if cart.item_count else "Your cart is empty."
        return TurnResult(text=text, ui=[tools.cart_payload(cart)], step=state.step)

    def _merge_into_cart(self, state: SessionState, lines: list[tuple[str, int]]):
        """Add lines to the cart, seeding from the active quote if the cart isn't built yet."""
        if state.step == WorkflowStep.QUOTE_READY:
            self._carts.add_to_cart(state.conversation_id, accepted_lines(state.mapping_results))
        cart = self._carts.add_to_cart(state.conversation_id, lines)
        state.step = WorkflowStep.CART_REVIEW
        return cart

    @staticmethod
    def _as_qty(value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _mapping_facts(results) -> dict:
        recognized = sum(1 for r in results if r.status.value == "matched")
        mapped = sum(1 for r in results if r.status.value == "mapped")
        no_eq = sum(1 for r in results if r.matched_sku is None)
        items = [
            {"input": r.raw, "schaeffler_sku": r.matched_sku, "status": r.status.value}
            for r in results
        ]
        return {"recognized": recognized, "mapped": mapped, "no_eq": no_eq, "items": items}

    def _reply(
        self, state: SessionState, kind: str, message: str, ui: list[dict], facts: dict | None = None
    ) -> TurnResult:
        history = state.transcript[-MAX_HISTORY_MESSAGES:]
        text = self._llm.generate_reply(
            kind=kind,
            user_message=message,
            step=state.step.value,
            facts=facts or {},
            history=history,
        )
        return TurnResult(text=text, ui=ui, step=state.step)


def _default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "catalog.json"


def build_default_orchestrator(
    catalog_path: str | Path | None = None, llm: LLMClient | None = None
) -> Orchestrator:
    """Wire the orchestrator with all-mock services.

    Uses RealLLMClient when ANTHROPIC_API_KEY is set (conversational replies via Claude),
    otherwise MockLLMClient so the app still runs offline. Pass `llm` to override.
    """
    from ..services.mock import (
        MockCartService,
        MockCatalogService,
        MockOrderService,
        MockPricingService,
        MockQuoteService,
    )

    catalog = MockCatalogService(catalog_path or _default_catalog_path())
    pricing = MockPricingService(catalog)
    if llm is None:
        llm = RealLLMClient() if os.getenv("ANTHROPIC_API_KEY") else MockLLMClient()
    return Orchestrator(
        llm=llm,
        sessions=InMemorySessionStore(),
        catalog=catalog,
        pricing=pricing,
        quotes=MockQuoteService(pricing, catalog),
        carts=MockCartService(pricing, catalog),
        orders=MockOrderService(),
    )
