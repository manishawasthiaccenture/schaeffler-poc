"""Mapping engine (FR-3).

Resolves a parsed designation to a Schaeffler SKU via a strict cascade:
  1. exact normalized match on Schaeffler SKU      -> matched   (1.0)
  2. exact normalized match on a cross-reference   -> mapped    (1.0)
  3. fuzzy match >= threshold                       -> mapped    (score)
  4. otherwise                                       -> no_equivalent (0.0)

Fuzzy is a fallback only and never overrides an exact hit. rapidfuzz is used
when available; difflib is the stdlib fallback so mapping runs with no installs.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .models import MappingResult, MappingStatus, ParsedItem

if TYPE_CHECKING:
    from .services.interfaces import CatalogService

DEFAULT_THRESHOLD = 0.88

try:  # pragma: no cover - import path depends on environment
    from rapidfuzz import fuzz

    def _ratio(a: str, b: str) -> float:
        return fuzz.token_sort_ratio(a, b) / 100.0

except ImportError:  # pragma: no cover - stdlib fallback
    from difflib import SequenceMatcher

    def _ratio(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()


_NORM_RE = re.compile(r"[\s\-/]")


def normalize(designation: str) -> str:
    """Uppercase and strip spaces, hyphens and slashes for match comparison."""
    return _NORM_RE.sub("", designation).upper()


def map_product(
    item: ParsedItem,
    catalog: "CatalogService",
    threshold: float = DEFAULT_THRESHOLD,
) -> MappingResult:
    norm = normalize(item.raw)

    sku_index = catalog.sku_index()
    if norm in sku_index:
        return MappingResult(
            item.raw, sku_index[norm], MappingStatus.MATCHED, 1.0, item.qty
        )

    xref_index = catalog.xref_index()
    if norm in xref_index:
        return MappingResult(
            item.raw, xref_index[norm], MappingStatus.MAPPED, 1.0, item.qty
        )

    best_sku, best_score = _best_fuzzy(norm, catalog.fuzzy_candidates())
    if best_sku is not None and best_score >= threshold:
        return MappingResult(
            item.raw, best_sku, MappingStatus.MAPPED, round(best_score, 4), item.qty
        )

    return MappingResult(item.raw, None, MappingStatus.NO_EQUIVALENT, 0.0, item.qty)


def map_products(
    items: list[ParsedItem],
    catalog: "CatalogService",
    threshold: float = DEFAULT_THRESHOLD,
) -> list[MappingResult]:
    return [map_product(item, catalog, threshold) for item in items]


def accepted_lines(results: list[MappingResult]) -> list[tuple[str, int]]:
    """(sku, qty) lines for results that resolved to a SKU (FR-4: drops no_equivalent)."""
    return [
        (r.matched_sku, r.qty)
        for r in results
        if r.matched_sku is not None and r.status is not MappingStatus.NO_EQUIVALENT
    ]


def _best_fuzzy(
    norm: str, candidates: list[tuple[str, str]]
) -> tuple[str | None, float]:
    best_sku: str | None = None
    best_score = 0.0
    for cand_norm, sku in candidates:
        score = _ratio(norm, cand_norm)
        if score > best_score:
            best_score = score
            best_sku = sku
    return best_sku, best_score
