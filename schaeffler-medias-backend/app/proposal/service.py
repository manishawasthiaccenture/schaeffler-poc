"""ProposalService — the proposal Q&A entry point.

Ties the knowledge base (flows), topic routing (regex + semantic), and optional
Claude summarisation into a single, transport-agnostic turn object. The FastAPI
layer serialises a ProposalReply into SSE events exactly like an ordering turn:
the answer text, an optional SlideDeck UI payload, and a set of suggestion chips.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .flows import CO_DRIVER_GREETING, DEFAULT_INTENT, FLOWS
from .routing import ProposalRouter
from .summarize import ProposalSummarizer


@dataclass(frozen=True)
class Suggestion:
    """A clickable chip. `intent` is set for topic drill-downs (sub-options);
    follow-up questions carry only `message` (sent as free text)."""

    label: str
    message: str
    intent: str | None = None

    def to_dict(self) -> dict:
        return {"label": self.label, "message": self.message, "intent": self.intent}


@dataclass(frozen=True)
class ProposalReply:
    intent: str
    text: str
    slides: list[dict] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)
    mode: str = "proposal"


# Shown when a message is neither an order action nor a clear proposal question.
# Same friendly greeting as the landing screen — no proposal content/slides.
GENERIC_TEXT = CO_DRIVER_GREETING
# Action chips on the generic reply. "Home Screen" is handled client-side (reset);
# "I want to buy products" starts the ordering workflow.
_GENERIC_SUGGESTIONS = [
    Suggestion(label="I want to buy products", message="I want to buy products"),
    Suggestion(label="Home Screen", message="Home Screen"),
]


class ProposalService:
    def __init__(
        self,
        router: ProposalRouter | None = None,
        summarizer: ProposalSummarizer | None = None,
    ) -> None:
        self._router = router or ProposalRouter()
        self._summarizer = summarizer or ProposalSummarizer()

    @property
    def backend_name(self) -> str:
        return self._router.backend_name

    def route(self, text: str) -> str:
        """Map free text to a proposal topic id (or 'fallback'). Used by the unified router."""
        return self._router.route(text)

    def welcome(self) -> ProposalReply:
        return self._build("welcome", query=None)

    def reply(self, intent: str, query: str | None = None) -> ProposalReply:
        """Answer for a known topic id; unknown ids fall back to the default overview."""
        if intent not in FLOWS:
            intent = DEFAULT_INTENT
        return self._build(intent, query)

    def answer(self, text: str) -> ProposalReply:
        """Answer a question. A clear proposal question gets the topic + slides; an
        unclear/out-of-scope message gets a generic prompt to pick a path (no slides,
        no proposal context)."""
        intent = self._router.route(text)  # confidence-gated; may be "fallback"
        if intent == "fallback":
            return ProposalReply(
                intent="fallback", text=GENERIC_TEXT, slides=[],
                suggestions=list(_GENERIC_SUGGESTIONS),
            )
        return self._build(intent, query=text)

    # --- internal --------------------------------------------------------

    def _build(self, intent: str, query: str | None) -> ProposalReply:
        flow = FLOWS.get(intent, FLOWS[DEFAULT_INTENT])
        text = self._summarizer.summarize(intent, flow, query)
        # No suggestion chips: the proposal answers with text + slides only.
        return ProposalReply(
            intent=intent,
            text=text,
            slides=[{"image": s["image"], "label": s["label"]} for s in flow.get("slides", [])],
            suggestions=[],
        )
