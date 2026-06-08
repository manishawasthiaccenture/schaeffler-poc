"""Drive the full ordering journey end-to-end with no server and no API key.

    python cli.py

Prints each turn (user message, assistant text, side-panel components) from typed
input through "Order confirmed" (PRD §15 definition of done).
"""
from __future__ import annotations

import json

from app.agent.orchestrator import build_default_orchestrator
from app.models import TurnResult, WorkflowStep

CONVERSATION_ID = "cli"

# (user_message, optional structured payload) — mirrors the storyboard journey.
SCRIPT: list[tuple[str, dict | None]] = [
    ("I want to buy products", None),
    ("6312-2RS1/C3 x 10\n6308-2RS, 5\nABC-123-XYZ", None),
    ("Accept all mappings and request a quote", None),
    ("Proceed to checkout", None),
    ("Proceed to checkout", None),
    ("Place order", {"purchase_order_number": "4500001234", "order_type": "Standard"}),
]


def _render(turn: TurnResult) -> None:
    print(f"  assistant: {turn.text}")
    for payload in turn.ui:
        print(f"  └─ [{payload['component']}] {json.dumps(payload['data'], ensure_ascii=False)}")
    print(f"  (step: {turn.step.value})\n")


def main() -> int:
    orch = build_default_orchestrator()
    final_step = WorkflowStep.GREETING

    for message, payload in SCRIPT:
        shown = message.replace("\n", " | ")
        print(f"user: {shown}")
        turn = orch.run_turn(CONVERSATION_ID, message, payload)
        _render(turn)
        final_step = turn.step

    if final_step == WorkflowStep.CONFIRMED:
        print("Journey complete — Order confirmed.")
        return 0
    print(f"Journey did not complete (ended at step: {final_step.value}).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
