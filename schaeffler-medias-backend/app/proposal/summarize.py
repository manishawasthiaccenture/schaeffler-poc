"""Optional grounded summarisation of a proposal topic.

When ANTHROPIC_API_KEY is set, Claude rephrases the topic's grounded content into
a warm, conversational answer to the user's specific question. Otherwise (or on any
error) we return the topic's existing prose, which is already written
conversationally. The model is strictly grounded — it never invents figures, dates,
names, or commitments not present in the supplied content.
"""
from __future__ import annotations

import os
import re

_HTML_TAG = re.compile(r"<[^>]+>")

_SYSTEM_PROMPT = (
    "You are Co-Driver, Accenture's friendly guide to its proposal for Schaeffler's medias "
    "project. Answer the user's question in a warm, natural, conversational style — 2 to 4 short "
    "sentences — that summarises the key outcome. Ground your answer ONLY in the provided proposal "
    "content; never invent figures, dates, names, percentages, or commitments that are not in it. "
    "No markdown, bullets, or headings."
)


def plain_text(text: str) -> str:
    """Strip light HTML to plain text for grounding the model."""
    return re.sub(r"\s+", " ", _HTML_TAG.sub(" ", text.replace("<br>", " "))).strip()


class ProposalSummarizer:
    """Lazily-initialised Claude summariser with a canned-prose fallback."""

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._model = model or os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    def summarize(self, intent: str, flow: dict, query: str | None) -> str:
        """Natural-language answer for a topic; falls back to the flow's own prose."""
        # Control nodes and the key-less path return the curated prose unchanged.
        if intent == "welcome" or not self._api_key:
            return flow["text"]
        try:
            title = flow["slides"][0]["label"] if flow.get("slides") else intent.replace("_", " ")
            summary = self._complete(query or title, title, plain_text(flow["text"]))
            return summary or flow["text"]
        except Exception:
            return flow["text"]

    def _complete(self, question: str, title: str, content: str) -> str:
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self._api_key)
        prompt = (
            f"Proposal section: {title}\n"
            f"Proposal content: {content}\n\n"
            f"User question: {question}\n\n"
            "Summarise the key outcome for the user in a natural, conversational reply."
        )
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=220,
            system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip()
