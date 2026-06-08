"""LLM layer tests — routing is deterministic and runs with no network/key."""
import pytest

from app.agent.llm import (
    Intent,
    MockLLMClient,
    RealLLMClient,
    default_reply,
    route_intent,
)
from app.models import WorkflowStep


@pytest.mark.parametrize(
    "message,step,expected",
    [
        ("I want to buy products", WorkflowStep.GREETING, Intent.BUY_PRODUCTS),
        ("Accept all mappings and request a quote", WorkflowStep.AWAITING_MAPPING_REVIEW, Intent.REQUEST_QUOTE),
        ("Proceed to checkout", WorkflowStep.QUOTE_READY, Intent.PROCEED),
        ("Place order", WorkflowStep.CHECKOUT, Intent.PLACE_ORDER),
        ("Certificates", WorkflowStep.GREETING, Intent.STUB_CERTIFICATES),
        ("6308-2RS, 5", WorkflowStep.AWAITING_PRODUCTS, Intent.SUBMIT_PRODUCTS),
        ("hello there", WorkflowStep.GREETING, Intent.UNKNOWN),
    ],
)
def test_route_intent(message, step, expected):
    assert route_intent(message, step) == expected


def test_both_clients_route_identically():
    mock = MockLLMClient()
    real = RealLLMClient(api_key=None)
    for msg, step in [("Place order", WorkflowStep.CHECKOUT), ("Support", WorkflowStep.GREETING)]:
        assert mock.decide(msg, step) == real.decide(msg, step)


def test_real_client_without_key_falls_back_to_canned_text():
    real = RealLLMClient(api_key=None)
    text = real.generate_reply(kind="buy_products", user_message="hi", step="greeting")
    assert text and "order" in text.lower()


def test_default_reply_is_grounded_on_facts():
    text = default_reply("mapping_ready", {"mapped": 2, "no_eq": 1})
    assert "2" in text and "1" in text
