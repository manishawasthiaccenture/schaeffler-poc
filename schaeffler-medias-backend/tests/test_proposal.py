"""Proposal Q&A: topic routing for the five canonical questions, the never-refuse
answer path, and the unified ordering-vs-proposal router. Runs on stdlib (no API
key -> curated prose, no network)."""
from __future__ import annotations

from app.models import WorkflowStep
from app.proposal import ProposalService
from app.router import is_ordering_message

svc = ProposalService()


# --- the five canonical demo questions route to the right slides ----------------

def test_realize_vision_question():
    reply = svc.answer("How could Accenture help Schaeffler to realize this vision?")
    assert reply.intent == "realize_vision"
    assert [s["image"] for s in reply.slides] == ["orals-6", "orals-7", "orals-8"]


def test_approach_question():
    reply = svc.answer(
        "Now that we know what we want to realize, what's the Accenture approach "
        "and what will they do to realize this?"
    )
    assert reply.intent == "approach"
    assert [s["image"] for s in reply.slides] == ["orals-9", "orals-10", "orals-12", "orals-18", "orals-20"]


def test_collaboration_question():
    reply = svc.answer("And how would Accenture collaborate with us? How would they staff this project?")
    assert reply.intent == "collaboration"
    assert [s["image"] for s in reply.slides] == ["orals-21", "orals-22"]


def test_credentials_question():
    reply = svc.answer("Has Accenture done this before?")
    assert reply.intent == "credentials"
    assert [s["image"] for s in reply.slides] == ["orals-23", "orals-24"]


def test_why_accenture_question():
    reply = svc.answer("What makes Accenture a suitable partner?")
    assert reply.intent == "why_accenture"
    assert [s["image"] for s in reply.slides] == ["orals-25", "orals-26", "orals-27", "orals-28"]


# --- behaviour: no chips, no refusal --------------------------------------------

def test_proposal_has_no_suggestion_chips():
    assert svc.answer("What makes Accenture a suitable partner?").suggestions == []


def test_unclear_question_gets_generic_prompt_no_slides():
    # An out-of-scope/unclear message gets a generic prompt (no proposal content/slides)
    # with action chips to place an order or go home.
    reply = svc.answer("what is the meaning of life")
    assert reply.intent == "fallback"
    assert reply.slides == []
    labels = [s.label for s in reply.suggestions]
    assert "I want to buy products" in labels and "Home Screen" in labels


def test_slides_carry_image_and_label():
    for s in svc.answer("why accenture?").slides:
        assert s["image"] and s["label"]


# --- unified router -------------------------------------------------------------

def test_ordering_commands_still_route_to_ordering():
    assert is_ordering_message("I want to buy products", WorkflowStep.GREETING, svc) is True
    assert is_ordering_message("6312-2RS1/C3 x 10", WorkflowStep.GREETING, svc) is True


def test_proposal_question_routes_to_proposal():
    assert is_ordering_message("has accenture done this before?", WorkflowStep.GREETING, svc) is False


def test_ambiguous_chat_stays_in_active_order():
    # Mid-order vague chat shouldn't drop the guided workflow.
    assert is_ordering_message("zzz", WorkflowStep.CART_REVIEW, svc) is True
