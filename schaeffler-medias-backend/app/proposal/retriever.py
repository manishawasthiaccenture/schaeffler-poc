"""Lightweight semantic retrieval over the proposal knowledge base.

A dependency-free TF-IDF + cosine-similarity index built from FLOWS at startup.
It gives the proposal router fuzzy, meaning-aware matching of free-text questions
to topics — no embeddings service, no API key, no extra packages.

The class is intentionally a thin seam: `search()` returns a (intent, score)
match, and the routing layer applies confidence bands exactly like the original
app.py RAG retriever. To swap in real embeddings later, implement the same
`search()` contract behind this interface.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .flows import FLOWS

# "welcome" is a control node (the landing greeting), not an answerable destination,
# so it is excluded from the search index.
_EXCLUDED = {"welcome"}

_HTML_TAG = re.compile(r"<[^>]+>")
_TOKEN = re.compile(r"[a-z0-9]+")

# Very small English stopword list — enough to stop common words from dominating
# the short proposal documents without pulling in a dependency.
_STOPWORDS = frozenset(
    """
    a an and are as at be been by для for from has have how in into is it its
    me my of on or our that the their them they this to us was we what when where
    which who will with you your about can do does me show tell give walk
    """.split()
)


@dataclass(frozen=True)
class Match:
    intent: str
    score: float


def _tokenize(text: str) -> list[str]:
    text = _HTML_TAG.sub(" ", text).lower()
    return [t for t in _TOKEN.findall(text) if t not in _STOPWORDS and len(t) > 1]


def _document_text(intent: str, flow: dict) -> str:
    """The searchable text for a topic: its prose, slide labels and question aliases."""
    parts = [intent.replace("_", " "), flow.get("text", "")]
    parts += [s.get("label", "") for s in flow.get("slides", [])]
    parts += list(flow.get("aliases", []))
    return " ".join(parts)


class RagRetriever:
    """TF-IDF cosine retriever over the proposal flows."""

    backend_name = "tfidf"

    def __init__(self, flows: dict[str, dict] | None = None) -> None:
        flows = flows or FLOWS
        self._intents: list[str] = []
        self._doc_vectors: list[dict[str, float]] = []
        self._doc_norms: list[float] = []

        # Document frequency across the corpus, for IDF weighting.
        doc_freq: Counter[str] = Counter()
        tokenized: list[tuple[str, Counter[str]]] = []
        for intent, flow in flows.items():
            if intent in _EXCLUDED:
                continue
            tokens = _tokenize(_document_text(intent, flow))
            if not tokens:
                continue
            tf = Counter(tokens)
            tokenized.append((intent, tf))
            for term in tf:
                doc_freq[term] += 1

        n_docs = len(tokenized)
        self._idf: dict[str, float] = {
            term: math.log((1 + n_docs) / (1 + df)) + 1.0 for term, df in doc_freq.items()
        }

        for intent, tf in tokenized:
            vec = self._tfidf_vector(tf)
            self._intents.append(intent)
            self._doc_vectors.append(vec)
            self._doc_norms.append(math.sqrt(sum(w * w for w in vec.values())) or 1.0)

    def _tfidf_vector(self, tf: Counter[str]) -> dict[str, float]:
        total = sum(tf.values()) or 1
        return {term: (count / total) * self._idf.get(term, 1.0) for term, count in tf.items()}

    def search(self, query: str) -> Match | None:
        """Return the best-matching topic and its cosine similarity (0..1), or None."""
        q_tf = Counter(_tokenize(query))
        if not q_tf or not self._doc_vectors:
            return None
        q_vec = self._tfidf_vector(q_tf)
        q_norm = math.sqrt(sum(w * w for w in q_vec.values()))
        if q_norm == 0:
            return None

        best_intent, best_score = None, 0.0
        for intent, vec, norm in zip(self._intents, self._doc_vectors, self._doc_norms):
            # Dot product over the smaller vector's terms.
            small, large = (q_vec, vec) if len(q_vec) < len(vec) else (vec, q_vec)
            dot = sum(w * large.get(term, 0.0) for term, w in small.items())
            if dot == 0.0:
                continue
            score = dot / (q_norm * norm)
            if score > best_score:
                best_intent, best_score = intent, score

        return Match(intent=best_intent, score=best_score) if best_intent else None
