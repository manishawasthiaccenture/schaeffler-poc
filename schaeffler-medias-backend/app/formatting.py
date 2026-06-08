"""Edge formatting helpers (PRD §12). Money is de-DE: `€ 1.234,56`."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def format_eur(amount: Decimal) -> str:
    """Format a Decimal as a de-DE euro string, e.g. Decimal('4050.00') -> '€ 4.050,00'."""
    q = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if q < 0 else ""
    # f-string gives en-US grouping (1,234.56); swap separators to de-DE.
    body = f"{abs(q):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€ {sign}{body}"
