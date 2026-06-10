"""Route a free-text question to a proposal topic.

Two signals:
  1. Regex intent patterns — fast, deterministic, high-precision keyword rules.
  2. Semantic retrieval (retriever.RagRetriever) — fuzzy, meaning-aware fallback.

route() may return "fallback" when confidence is low. The caller decides what that
means: the unified router keeps an in-progress order rather than hijacking it for a
vague utterance, and the proposal service answers a "fallback" with a generic prompt
(no proposal content) instead of guessing a topic.
"""
from __future__ import annotations

import os
import re

from .retriever import RagRetriever

# Acceptance threshold for a semantic (cosine) match used as a regex fallback in route().
# Above this, a paraphrase the regex missed still maps to a topic; below it the message
# is treated as unclear and the service answers with a generic prompt (no proposal content).
RAG_MIN = float(os.getenv("PROPOSAL_RAG_MIN", "0.20"))

# (intent, [regex, ...]) — first match wins, evaluated top to bottom. Order matters:
# the most specific topics are checked before the general "realize the vision" catch.
INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("proven_partner", [r"why accenture", r"suitable partner", r"right partner", r"why acn",
                        r"makes accenture", r"why.*choose", r"trusted partner", r"unique.*position",
                        r"done.*before", r"delivered.*similar", r"similar.*initiative", r"credential",
                        r"experience", r"reference", r"case stud", r"past project", r"proven",
                        r"track record", r"execute this engagement"]),
    ("collaboration",  [r"collaborat", r"staff", r"how.*work.*together", r"team.*setup", r"team proposal",
                        r"on.?shore", r"offshore", r"raci", r"working model", r"who.*on.*team", r"shoring"]),
    ("approach",       [r"approach", r"what.*will.*they.*do", r"what.*do.*to.*realize", r"now that we know",
                        r"scope", r"\bservices?\b", r"timeline", r"sizing", r"complexity", r"how.*build", r"deliver"]),
    ("realize_vision", [r"realize", r"vision", r"help.*schaeffler", r"how.*accenture.*help",
                        r"value propos", r"executive summary", r"overview"]),
]


def route_intent_regex(text: str) -> str:
    """Regex-only routing to a proposal topic; 'fallback' if nothing matches."""
    t = text.lower().strip()
    for intent, patterns in INTENT_PATTERNS:
        for pat in patterns:
            if re.search(pat, t):
                return intent
    return "fallback"


class ProposalRouter:
    """Combines regex routing (high precision) with semantic retrieval (recall)."""

    def __init__(self, retriever: RagRetriever | None = None) -> None:
        # Never block startup on the retriever; fall back to regex-only if it fails.
        if retriever is not None:
            self._retriever = retriever
        else:
            try:
                self._retriever = RagRetriever()
            except Exception:
                self._retriever = None

    @property
    def backend_name(self) -> str:
        return self._retriever.backend_name if self._retriever else "regex-only"

    def route(self, text: str) -> str:
        """Confidence-gated topic, or 'fallback'. Regex first, then a semantic match
        above RAG_MIN. Used only for the ordering-vs-proposal decision."""
        regex = route_intent_regex(text)
        if regex != "fallback":
            return regex
        match = self._retriever.search(text) if self._retriever else None
        if match and match.score >= RAG_MIN:
            return match.intent
        return "fallback"
