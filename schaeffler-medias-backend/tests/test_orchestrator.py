"""Milestone 3 — orchestrator + MockLLM end-to-end tests (PRD §15)."""
from pathlib import Path

import pytest

from app.agent.llm import LLMClient, route_intent
from app.agent.orchestrator import build_default_orchestrator
from app.models import WorkflowStep

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"

JOURNEY_INPUT = "6312-2RS1/C3 x 10\n6308-2RS, 5\nABC-123-XYZ"


@pytest.fixture
def orch():
    return build_default_orchestrator(CATALOG_PATH)


def _components(turn):
    return {p["component"] for p in turn.ui}


def _only(turn, component):
    [payload] = [p for p in turn.ui if p["component"] == component]
    return payload["data"]


def test_full_journey_to_confirmed(orch):
    cid = "j1"

    turn = orch.run_turn(cid, "I want to buy products")
    assert turn.step == WorkflowStep.AWAITING_PRODUCTS
    assert {"UploadWidget", "TypePrompt"} <= _components(turn)
    assert _only(turn, "UploadWidget")["enabled"] is False  # D1: disabled upload

    turn = orch.run_turn(cid, JOURNEY_INPUT)
    assert turn.step == WorkflowStep.AWAITING_MAPPING_REVIEW
    rows = _only(turn, "MappingTable")["rows"]
    statuses = [r["status"] for r in rows]
    assert statuses.count("no_equivalent") == 1
    assert sum(1 for s in statuses if s != "no_equivalent") == 2

    turn = orch.run_turn(cid, "Accept all mappings and request a quote")
    assert turn.step == WorkflowStep.QUOTE_READY
    quote = _only(turn, "QuoteCard")
    assert len(quote["lines"]) == 2
    assert quote["total"] == "249.75"
    assert quote["total_display"] == "€ 249,75"
    assert quote["status"] == "Released"

    turn = orch.run_turn(cid, "Proceed to checkout")
    assert turn.step == WorkflowStep.CART_REVIEW
    cart = _only(turn, "Cart")
    assert cart["item_count"] == 2
    assert cart["total"] == "249.75"

    turn = orch.run_turn(cid, "Proceed to checkout")
    assert turn.step == WorkflowStep.CHECKOUT
    assert "CheckoutForm" in _components(turn)

    turn = orch.run_turn(
        cid, "Place order", {"purchase_order_number": "4500001234", "order_type": "Standard"}
    )
    assert turn.step == WorkflowStep.CONFIRMED
    confirmation = _only(turn, "Confirmation")
    assert confirmation["status"] == "confirmed"
    assert confirmation["order_id"].startswith("ORD-")


def test_place_order_without_po_stays_on_checkout(orch):
    cid = "j2"
    orch.run_turn(cid, "I want to buy products")
    orch.run_turn(cid, "6308-2RS, 5")
    orch.run_turn(cid, "Request a quote")
    orch.run_turn(cid, "Proceed to checkout")
    orch.run_turn(cid, "Proceed to checkout")
    turn = orch.run_turn(cid, "Place order")  # no payload
    assert turn.step == WorkflowStep.CHECKOUT
    assert "CheckoutForm" in _components(turn)


@pytest.mark.parametrize(
    "message,title",
    [
        ("Certificates", "Certificates"),
        ("Support", "Support"),
        ("Order", "Order status"),
        ("Price & Availability", "Price & Availability"),
    ],
)
def test_non_ordering_chips_return_stub(orch, message, title):
    turn = orch.run_turn("s1", message)
    stub = _only(turn, "StubMessage")
    assert stub["title"] == title
    assert "coming soon" in stub["message"].lower()


def test_decline_clears_list_and_returns_to_input(orch):
    cid = "d1"
    orch.run_turn(cid, "I want to buy products")
    orch.run_turn(cid, "6308-2RS, 5")
    turn = orch.run_turn(cid, "Decline all and remove from list")
    assert turn.step == WorkflowStep.AWAITING_PRODUCTS


def test_all_no_equivalent_blocks_quote(orch):
    cid = "n1"
    orch.run_turn(cid, "I want to buy products")
    orch.run_turn(cid, "ABC-123-XYZ\nNOPE-000-QQQ")
    turn = orch.run_turn(cid, "Request a quote")
    assert turn.step == WorkflowStep.AWAITING_MAPPING_REVIEW  # quote blocked


def test_unknown_message_is_handled_gracefully(orch):
    turn = orch.run_turn("u1", "hello there")
    assert turn.step == WorkflowStep.GREETING
    assert turn.text


def _to_confirmed(orch, cid):
    orch.run_turn(cid, "I want to buy products")
    orch.run_turn(cid, "6308-2RS, 5")
    orch.run_turn(cid, "Request a quote")
    orch.run_turn(cid, "Proceed to checkout")
    orch.run_turn(cid, "Proceed to checkout")
    return orch.run_turn(cid, "Place order", {"purchase_order_number": "PO-1"})


def test_chitchat_is_not_treated_as_a_product(orch):
    cid = "chat1"
    orch.run_turn(cid, "I want to buy products")
    turn = orch.run_turn(cid, "thanks, how does this work?")
    assert turn.step == WorkflowStep.AWAITING_PRODUCTS
    assert "MappingTable" not in _components(turn)


def test_schaeffler_sku_is_recognized_as_matched(orch):
    cid = "sku1"
    orch.run_turn(cid, "I want to buy products")
    turn = orch.run_turn(cid, "HC6312-C-2HRS-L207-C3 x 2")
    rows = _only(turn, "MappingTable")["rows"]
    assert rows[0]["status"] == "matched"
    assert rows[0]["matched_sku"] == "HC6312-C-2HRS-L207-C3"


def test_add_item_after_quote_keeps_quoted_items(orch):
    cid = "add1"
    orch.run_turn(cid, "I want to buy products")
    orch.run_turn(cid, "6308-2RS, 5")
    orch.run_turn(cid, "Request a quote")
    turn = orch.run_turn(cid, "6204-C-C3 x 2")
    assert turn.step == WorkflowStep.CART_REVIEW
    cart = _only(turn, "Cart")
    skus = {item["sku"] for item in cart["items"]}
    assert {"HC6308-C-2HRS-L207", "6204-C-C3"} <= skus


def test_product_details_for_known_sku(orch):
    turn = orch.run_turn("pd1", "show me details for 6204-C-C3")
    details = _only(turn, "ProductDetails")
    assert details["sku"] == "6204-C-C3"
    assert details["price_tiers"]


def test_product_details_unknown_sku(orch):
    turn = orch.run_turn("pd2", "details for ZZZ-999-NOPE")
    assert "ProductDetails" not in _components(turn)
    assert turn.text


def test_place_another_order_after_confirmed_resets(orch):
    cid = "re1"
    _to_confirmed(orch, cid)
    turn = orch.run_turn(cid, "Place another order")
    assert turn.step == WorkflowStep.AWAITING_PRODUCTS
    state = orch.get_state(cid)
    assert state.order_id is None and state.quote_id is None
    assert orch._carts.get_cart(cid).item_count == 0


def test_view_order_details_after_confirmed(orch):
    cid = "od1"
    _to_confirmed(orch, cid)
    turn = orch.run_turn(cid, "View order details")
    assert turn.step == WorkflowStep.CONFIRMED
    assert turn.text


def _to_cart(orch, cid):
    orch.run_turn(cid, "I want to buy products")
    orch.run_turn(cid, "6308-2RS, 5")
    orch.run_turn(cid, "Request a quote")
    orch.run_turn(cid, "Proceed to checkout")  # -> CART_REVIEW, cart has HC6308


def test_quantity_phrasing_maps_known_sku(orch):
    cid = "q1"
    orch.run_turn(cid, "I want to buy products")
    turn = orch.run_turn(cid, "HC6312-C-2HRS-L207-C3 with 100 quantity")
    rows = _only(turn, "MappingTable")["rows"]
    assert rows[0]["status"] == "matched"
    assert rows[0]["qty"] == 100


def test_update_cart_quantity(orch):
    cid = "u1"
    _to_cart(orch, cid)
    turn = orch.run_turn(cid, "update cart", {"sku": "HC6308-C-2HRS-L207", "qty": 9})
    cart = _only(turn, "Cart")
    item = next(i for i in cart["items"] if i["sku"] == "HC6308-C-2HRS-L207")
    assert item["qty"] == 9


def test_remove_cart_item_empties_cart(orch):
    cid = "u2"
    _to_cart(orch, cid)
    turn = orch.run_turn(cid, "remove item", {"sku": "HC6308-C-2HRS-L207"})
    assert _only(turn, "Cart")["item_count"] == 0
    assert orch._carts.get_cart(cid).item_count == 0


def test_show_cart_anytime(orch):
    cid = "u3"
    _to_cart(orch, cid)
    orch.run_turn(cid, "Proceed to checkout")  # move to CHECKOUT
    turn = orch.run_turn(cid, "show cart")
    assert "Cart" in _components(turn)


def test_control_actions_stay_out_of_transcript(orch):
    cid = "u4"
    _to_cart(orch, cid)
    before = len(orch.get_state(cid).transcript)
    orch.run_turn(cid, "show cart")
    orch.run_turn(cid, "update cart", {"sku": "HC6308-C-2HRS-L207", "qty": 3})
    assert len(orch.get_state(cid).transcript) == before


def test_view_details_then_add_retains_existing_cart(orch):
    cid = "u5"
    _to_cart(orch, cid)  # cart has HC6308
    orch.run_turn(cid, "details for 6204-C-C3")  # view only
    assert orch._carts.get_cart(cid).item_count == 1
    turn = orch.run_turn(cid, "add to cart", {"sku": "6204-C-C3", "qty": 2})
    skus = {i["sku"] for i in _only(turn, "Cart")["items"]}
    assert {"HC6308-C-2HRS-L207", "6204-C-C3"} <= skus


class _SpyLLM(LLMClient):
    """Captures the history window handed to generate_reply on each turn."""

    def __init__(self):
        self.calls: list[dict] = []

    def decide(self, message, step):
        return route_intent(message, step)

    def generate_reply(self, kind, user_message, step, facts=None, history=None):
        self.calls.append({"kind": kind, "history": list(history or [])})
        return "ok"


def test_transcript_history_is_passed_to_llm():
    spy = _SpyLLM()
    orch = build_default_orchestrator(CATALOG_PATH, llm=spy)

    orch.run_turn("h1", "I want to buy products")
    orch.run_turn("h1", "6308-2RS, 5")

    # First turn has no prior history; second turn sees the first exchange.
    assert spy.calls[0]["history"] == []
    second = spy.calls[1]["history"]
    assert len(second) == 2
    assert second[0]["role"] == "user" and "buy products" in second[0]["text"].lower()
    assert second[1] == {"role": "assistant", "text": "ok"}

    # Transcript persists on the session (user + assistant per turn).
    state = orch.get_state("h1")
    assert len(state.transcript) == 4


def test_history_window_is_bounded():
    spy = _SpyLLM()
    orch = build_default_orchestrator(CATALOG_PATH, llm=spy)
    for _ in range(20):
        orch.run_turn("w1", "hello")
    # The window handed to the LLM never exceeds MAX_HISTORY_MESSAGES (16).
    assert all(len(call["history"]) <= 16 for call in spy.calls)
    # The stored transcript is also bounded (MAX_STORED_MESSAGES = 40).
    assert len(orch.get_state("w1").transcript) <= 40
