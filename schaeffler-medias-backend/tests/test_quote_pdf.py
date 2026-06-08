"""Milestone 5 — quote PDF rendering (FR-5). Runs on stdlib (minimal PDF fallback)."""
from datetime import date
from decimal import Decimal

from app.models import Quote, QuoteLine
from app.quote_pdf import render_quote_pdf


def _sample_quote() -> Quote:
    return Quote(
        quote_id="12345",
        status="Released",
        currency="EUR",
        total=Decimal("249.75"),
        valid_until=date(2026, 8, 7),
        lines=[
            QuoteLine("HC6312-C-2HRS-L207-C3", "Deep groove ball bearing", 10, Decimal("18.50"), Decimal("185.00")),
            QuoteLine("HC6308-C-2HRS-L207", "Deep groove ball bearing", 5, Decimal("12.95"), Decimal("64.75")),
        ],
    )


def test_render_returns_valid_pdf_bytes():
    pdf = render_quote_pdf(_sample_quote())
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF")
    assert pdf.rstrip().endswith(b"%%EOF")


def test_pdf_contains_quote_details():
    # Without reportlab installed the stdlib fallback embeds uncompressed text.
    pdf = render_quote_pdf(_sample_quote())
    assert b"12345" in pdf
    assert b"HC6312-C-2HRS-L207-C3" in pdf
    assert b"249,75" in pdf  # de-DE amount
