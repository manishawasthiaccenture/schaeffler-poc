"""Typed product-list parser (FR-2).

Extracts (designation, quantity) pairs from a free-typed, multi-line list. Per line
it finds the product-code token and a quantity anywhere in the line, so natural
phrasings work too: "HC6312-C-2HRS-L207-C3 with 100 quantity", "qty 3 6204-C-C3",
"6312-2RS1/C3 x 10", "6308-2RS, 5". The designation token is preserved verbatim;
quantity defaults to 1.
"""
from __future__ import annotations

import re

from .models import ParsedItem

# Quantity expressed with a keyword/separator, e.g. "x 10", "qty 3", "quantity: 100".
_QTY_KEYWORD = re.compile(r"(?:qty|quantity|qnty|x|×|\*)\s*[:=]?\s*(\d+)", re.IGNORECASE)
# Any standalone integer (fallback).
_QTY_BARE = re.compile(r"\b(\d+)\b")


def _is_product_code(token: str) -> bool:
    """A product code carries a digit and is alphanumeric with - / . — and either has a
    letter or a separator (so plain numbers like '5' or a bare '10' aren't mistaken for one)."""
    core = token.strip(".,:;")
    if len(core) < 3 or not re.fullmatch(r"[A-Za-z0-9\-/.]+", core):
        return False
    if not re.search(r"\d", core):
        return False
    return bool(re.search(r"[A-Za-z]", core) or re.search(r"[-/]", core))


def looks_like_products(text: str) -> bool:
    """True if the text contains at least one product-code-like token (vs. plain chat)."""
    for line in text.splitlines():
        if any(_is_product_code(tok) for tok in re.split(r"[\s,]+", line) if tok):
            return True
    return False


def first_product_token(text: str) -> str | None:
    """Return the first product-code-like token in the text, or None."""
    for tok in re.split(r"[\s,]+", text):
        if tok and _is_product_code(tok):
            return tok.strip(".,:;")
    return None


def extract_quantity(text: str) -> int | None:
    """Pull a quantity out of free text (e.g. "make it 20", "20 units", "qty 3").

    Any product-code token is removed first so the code's own digits aren't read
    as the quantity. Returns None when no number is present.
    """
    code = first_product_token(text)
    remainder = text.replace(code, " ", 1) if code else text
    m = _QTY_KEYWORD.search(remainder)
    if m:
        return int(m.group(1))
    m = _QTY_BARE.search(remainder)
    if m:
        return int(m.group(1))
    return None


def parse_typed_products(text: str) -> list[ParsedItem]:
    """Parse a multi-line product list into ParsedItems. Blank lines are ignored."""
    items: list[ParsedItem] = []
    for line in text.splitlines():
        item = _parse_line(line)
        if item is not None:
            items.append(item)
    return items


def _parse_line(line: str) -> ParsedItem | None:
    s = line.strip()
    if not s:
        return None

    code = first_product_token(s)
    if code is None:
        # No recognizable product code — keep the whole line as the designation.
        return ParsedItem(raw=s, qty=1)

    qty = _extract_quantity(s, code)
    if qty is None:
        return ParsedItem(raw=code, qty=1)
    if qty <= 0:
        return ParsedItem(raw=code, qty=qty, valid=False, error="quantity must be a positive integer")
    return ParsedItem(raw=code, qty=qty)


def _extract_quantity(line: str, code: str) -> int | None:
    """Find the quantity in the line, ignoring the product code's own digits."""
    remainder = line.replace(code, " ", 1)
    m = _QTY_KEYWORD.search(remainder)
    if m:
        return int(m.group(1))
    m = _QTY_BARE.search(remainder)
    if m:
        return int(m.group(1))
    return None
