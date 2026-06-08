"""LLM client behind an interface (PRD §9).

Two responsibilities, deliberately split:
  - decide(): intent routing. Rule-based and shared by both clients so the chip
    flow is always reliable (deterministic tool selection).
  - generate_reply(): the assistant's conversational text. MockLLMClient returns
    grounded canned text; RealLLMClient asks Claude to phrase a reply from grounded
    FACTS — it never invents prices, quote IDs, order numbers, dates, or mappings.

The orchestrator depends only on LLMClient.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from enum import Enum

from ..models import WorkflowStep
from ..parsing import looks_like_products


class Intent(str, Enum):
    BUY_PRODUCTS = "buy_products"
    SUBMIT_PRODUCTS = "submit_products"
    REQUEST_QUOTE = "request_quote"
    DECLINE_MAPPINGS = "decline_mappings"
    PROCEED = "proceed"
    PLACE_ORDER = "place_order"
    PRODUCT_DETAILS = "product_details"
    ORDER_DETAILS = "order_details"
    ADD_TO_CART = "add_to_cart"
    UPDATE_CART = "update_cart"
    REMOVE_CART = "remove_cart"
    SHOW_CART = "show_cart"
    STUB_CERTIFICATES = "stub_certificates"
    STUB_SUPPORT = "stub_support"
    STUB_ORDER_STATUS = "stub_order_status"
    STUB_PRICE_AVAILABILITY = "stub_price_availability"
    UNKNOWN = "unknown"


_BUY = {"i want to buy products", "buy products", "i want to buy"}
_QUOTE = {
    "request a quote",
    "accept all mappings and request a quote",
    "accept all",
    "accept all mappings",
}
_DECLINE = {"decline all and remove from list", "decline all", "decline"}
_PROCEED = {"proceed to checkout", "proceed", "checkout"}
_PLACE = {"place order", "place the order"}


def route_intent(message: str, step: WorkflowStep) -> Intent:
    """Deterministic intent routing shared by all LLM clients."""
    norm = " ".join(message.strip().lower().split())

    if norm in _BUY:
        return Intent.BUY_PRODUCTS
    if norm in _QUOTE:
        return Intent.REQUEST_QUOTE
    if norm in _DECLINE:
        return Intent.DECLINE_MAPPINGS
    if norm in _PROCEED:
        return Intent.PROCEED
    if norm in _PLACE:
        return Intent.PLACE_ORDER

    # Cart control actions (sent by widget buttons).
    if norm == "add to cart":
        return Intent.ADD_TO_CART
    if norm in {"update cart", "update cart item", "set quantity"}:
        return Intent.UPDATE_CART
    if norm in {"remove item", "remove from cart"}:
        return Intent.REMOVE_CART
    if norm in {"show cart", "view cart", "my cart", "see cart", "open cart"}:
        return Intent.SHOW_CART

    # Post-order / restart actions.
    if norm in {"place another order", "start over", "new order", "place a new order", "order more"}:
        return Intent.BUY_PRODUCTS
    if norm in {"view order details", "order details", "my order", "order summary"}:
        return Intent.ORDER_DETAILS

    # Non-ordering landing chips -> coming-soon stubs (exact).
    if norm == "certificates":
        return Intent.STUB_CERTIFICATES
    if norm == "support":
        return Intent.STUB_SUPPORT
    if norm in {"order", "order status", "check current status"}:
        return Intent.STUB_ORDER_STATUS
    if norm in {"price & availability", "price and availability"}:
        return Intent.STUB_PRICE_AVAILABILITY

    # Explicit product lookup that names a product code -> details + "add to cart?".
    if looks_like_products(message) and any(
        kw in norm
        for kw in (
            "detail", "spec", "tell me about", "show me", "info about", "availab",
            "price of", "search", "find", "look up", "lookup",
        )
    ):
        return Intent.PRODUCT_DETAILS

    # Anything that contains a product-code-like token is product input (submit/add).
    if looks_like_products(message):
        return Intent.SUBMIT_PRODUCTS

    if step == WorkflowStep.AWAITING_MAPPING_REVIEW and "quote" in norm:
        return Intent.REQUEST_QUOTE

    if any(kw in norm for kw in ("buy", "order", "purchase", "quote")):
        return Intent.BUY_PRODUCTS

    # Plain conversation — no product codes, no command. Let the LLM reply naturally.
    return Intent.UNKNOWN


def default_reply(kind: str, facts: dict | None = None) -> str:
    """Grounded canned reply text. Used by MockLLMClient and as RealLLMClient's fallback."""
    f = facts or {}
    replies = {
        "buy_products": (
            "Great! I can help you place an order. You can upload a bulk product list "
            "or just tell me what you need — type your products below, one per line with "
            "quantities."
        ),
        "empty_list": "I couldn't find any products in that. Type one product per line, e.g. 6312-2RS1/C3 x 10.",
        "invalid_qty": "Each product needs a positive quantity. Please re-enter your list.",
        "request_quote_too_early": "Let's start by adding the products you'd like to order.",
        "no_mapping": (
            "None of those products could be mapped to a Schaeffler equivalent, so I can't "
            "create a quote. Please try a different list."
        ),
        "quote_ready": (
            "I've prepared your quote — please review it on the right. You can download it "
            "or proceed to checkout when you're ready."
        ),
        "decline": "No problem — I've cleared the list. Type your products again whenever you're ready.",
        "cart": "Here's your shopping cart. Review your items and proceed to checkout when ready.",
        "checkout": "Please fill in your order information to complete the purchase.",
        "proceed_nothing": "There's nothing to proceed with yet.",
        "place_order_too_early": "Please review your cart and checkout details first.",
        "need_po": "A purchase order number is required to place the order.",
        "confirmed": "Thank you for your order! Your confirmation is on the right.",
        "added_items": "I've added that to your cart — review it on the right or proceed to checkout.",
        "added_none": (
            "I couldn't match those to a Schaeffler product, so nothing was added. "
            "Please check the code and try again."
        ),
        "product_details": "Here are the product details on the right. Would you like to add it to your cart?",
        "product_details_missing": (
            "I couldn't find that product in our catalog. Please double-check the code and try again."
        ),
        "cart_empty": "Your cart is empty. Add some products and they'll show up here.",
    }
    if kind == "mapping_ready":
        recognized, mapped, no_eq = f.get("recognized", 0), f.get("mapped", 0), f.get("no_eq", 0)
        parts = []
        if recognized:
            parts.append(f"{recognized} recognized Schaeffler product(s)")
        if mapped:
            parts.append(f"{mapped} mapped to Schaeffler equivalents")
        if no_eq:
            parts.append(f"{no_eq} with no direct equivalent")
        summary = ", ".join(parts) if parts else "your items"
        return f"I've reviewed your list — {summary}. Please confirm on the right to continue."
    if kind == "order_recap":
        return f"Your order {f.get('order_id', '')} is confirmed. Anything else I can help you with?"
    if kind == "stub":
        return f.get("message", "That feature is coming soon.")
    return replies.get(
        kind,
        'I can help you place an order. Click "I want to buy products" or tell me what you need.',
    )


class LLMClient(ABC):
    @abstractmethod
    def decide(self, message: str, step: WorkflowStep) -> Intent:
        """Route a user message (free text or chip) to an intent given the workflow step."""

    @abstractmethod
    def generate_reply(
        self,
        kind: str,
        user_message: str,
        step: str,
        facts: dict | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """Produce the assistant's conversational text for this turn.

        `history` is the recent transcript ([{"role", "text"}, ...]) for memory.
        """


class MockLLMClient(LLMClient):
    """Deterministic routing + grounded canned replies. No API key or network."""

    def decide(self, message: str, step: WorkflowStep) -> Intent:
        return route_intent(message, step)

    def generate_reply(
        self,
        kind: str,
        user_message: str,
        step: str,
        facts: dict | None = None,
        history: list[dict] | None = None,
    ) -> str:
        # Canned replies are per-turn; history is not needed for the mock.
        return default_reply(kind, facts)


_SYSTEM_PROMPT = (
    "You are medias, Schaeffler's friendly B2B ordering assistant inside a web-shop chat. "
    "Keep replies short (1-2 sentences), warm and professional. You are given the situation, "
    "the workflow step, the customer's message, and grounded FACTS. Compose a natural reply "
    "that fits the situation and moves the order along. "
    "STRICT RULES: never invent or change prices, totals, quote IDs, order numbers, dates, "
    "SKUs, or mapping results — only reference values present in FACTS. Do not use markdown, "
    "bullet lists, or code formatting. "
    "A product with status 'matched' is already a Schaeffler product and is ready to order — "
    "never say it has no equivalent and never offer alternatives for it. Only mention 'no direct "
    "equivalent' or suggest alternatives for items whose status is 'no_equivalent'. "
    "If the situation is 'unknown', answer briefly and gently steer the customer toward placing an order."
)


class RealLLMClient(LLMClient):
    """Routes deterministically; phrases replies with Claude. Falls back to canned text on error."""

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._model = model or os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        self._client = None

    def decide(self, message: str, step: WorkflowStep) -> Intent:
        return route_intent(message, step)

    def generate_reply(
        self,
        kind: str,
        user_message: str,
        step: str,
        facts: dict | None = None,
        history: list[dict] | None = None,
    ) -> str:
        facts = facts or {}
        if not self._api_key:
            return default_reply(kind, facts)
        try:
            return self._complete(kind, user_message, step, facts, history or [])
        except Exception:
            # Never break the conversation on a transient API error.
            return default_reply(kind, facts)

    def _complete(
        self, kind: str, user_message: str, step: str, facts: dict, history: list[dict]
    ) -> str:
        import json

        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self._api_key)

        # Prior turns become the conversation history; the Anthropic API requires the
        # sequence to start with a user message, so drop any leading assistant turn.
        messages: list[dict] = []
        for turn in history:
            role = turn.get("role")
            text = turn.get("text", "")
            if role in ("user", "assistant") and text:
                messages.append({"role": role, "content": text})
        while messages and messages[0]["role"] == "assistant":
            messages.pop(0)

        context = json.dumps(
            {"situation": kind, "workflow_step": step, "customer_message": user_message, "facts": facts},
            ensure_ascii=False,
        )
        messages.append({"role": "user", "content": f"Context:\n{context}\n\nWrite the assistant's reply."})

        response = self._client.messages.create(
            model=self._model,
            max_tokens=200,
            system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        return text or default_reply(kind, facts)
