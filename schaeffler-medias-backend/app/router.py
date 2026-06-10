"""Unified per-message router: ordering workflow vs. proposal Q&A.

For each user turn we decide which engine answers it (mirrors app.py's
`is_ordering_message`):

  1. An explicit ordering command or a product code always wins -> ordering.
  2. Otherwise, a recognised proposal question -> proposal Q&A.
  3. No clear signal: stay in the ordering flow only if one is actively in
     progress (i.e. not at GREETING/CONFIRMED), so a guided order isn't dropped
     mid-way; at the start/end of an order, hand ambiguous chat to the proposal.
"""
from __future__ import annotations

from .agent.llm import Intent, route_intent as route_ordering_intent
from .models import WorkflowStep
from .proposal import ProposalService

_IDLE_STEPS = (WorkflowStep.GREETING, WorkflowStep.CONFIRMED)


def is_ordering_message(text: str, step: WorkflowStep, proposal: ProposalService) -> bool:
    """True -> route to the ordering orchestrator; False -> proposal Q&A."""
    if route_ordering_intent(text, step) is not Intent.UNKNOWN:
        return True
    if proposal.route(text) != "fallback":
        return False
    return step not in _IDLE_STEPS
