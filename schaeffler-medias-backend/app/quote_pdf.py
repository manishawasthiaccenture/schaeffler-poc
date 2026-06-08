"""Quote PDF rendering (FR-5 download / PRD §11 GET /quotes/{id}/pdf).

Uses reportlab when installed; falls back to a tiny pure-stdlib PDF writer so the
endpoint and tests work with no installs (PRD §12). Amounts are written as
`EUR 1.234,56` (no euro glyph) to stay within Helvetica's safe character set.
"""
from __future__ import annotations

from decimal import Decimal

from .formatting import format_eur
from .models import Quote


def render_quote_pdf(quote: Quote) -> bytes:
    lines = _quote_lines(quote)
    try:
        return _reportlab_pdf(lines)
    except ImportError:
        return _minimal_pdf(lines)


def _amount(value: Decimal) -> str:
    """de-DE amount without the euro glyph, e.g. '249,75'."""
    return format_eur(value).replace("€ ", "")


def _quote_lines(quote: Quote) -> list[str]:
    lines = [
        f"Schaeffler medias - Quote {quote.quote_id}",
        f"Status: {quote.status}",
        f"Valid until: {quote.valid_until.isoformat()}",
        "",
        "Items:",
    ]
    for line in quote.lines:
        lines.append(
            f"  {line.sku}  x{line.qty}  @ EUR {_amount(line.unit_price)}"
            f"  = EUR {_amount(line.line_total)}"
        )
    lines += ["", f"Total: EUR {_amount(quote.total)} {quote.currency}"]
    return lines


def _reportlab_pdf(lines: list[str]) -> bytes:
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _, height = A4
    y = height - 50
    pdf.setFont("Helvetica", 12)
    for line in lines:
        pdf.drawString(50, y, line)
        y -= 16
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _minimal_pdf(lines: list[str]) -> bytes:
    """Hand-built single-page PDF (stdlib only) with an uncompressed text stream."""
    content_parts = ["BT", "/F1 12 Tf", "50 800 Td", "16 TL"]
    for line in lines:
        content_parts.append(f"({_escape(line)}) Tj")
        content_parts.append("T*")
    content_parts.append("ET")
    content = "\n".join(content_parts).encode("latin-1", "replace")

    objects = [
        b"<</Type /Catalog /Pages 2 0 R>>",
        b"<</Type /Pages /Kids [3 0 R] /Count 1>>",
        b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources <</Font <</F1 4 0 R>>>> /Contents 5 0 R>>",
        b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>",
        b"<</Length %d>>\nstream\n%s\nendstream" % (len(content), content),
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"

    xref_pos = len(out)
    size = len(objects) + 1
    out += b"xref\n0 %d\n" % size
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<</Size %d /Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (size, xref_pos)
    return bytes(out)
