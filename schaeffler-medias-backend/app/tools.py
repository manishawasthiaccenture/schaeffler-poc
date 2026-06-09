"""UI render hints (PRD §10). Each builder maps domain data to a component payload.

Payloads are JSON-safe (Decimals -> strings, dates -> ISO) so the SSE layer
(milestone 4) and the React frontend can consume them directly. Display strings
are formatted de-DE at this edge (PRD §12).
"""
from __future__ import annotations

from .formatting import format_eur
from .models import Cart, CatalogEntry, MappingResult, Order, Quote


def upload_widget_payload() -> dict:
    """UploadWidget — rendered but DISABLED in V1 (PRD D1)."""
    return {
        "component": "UploadWidget",
        "data": {
            "enabled": False,
            "title": "Upload an Excel file with your product list",
            "button": "Choose Excel File",
            "note": "File upload is coming soon — please type your product list below.",
        },
    }


def type_prompt_payload() -> dict:
    return {
        "component": "TypePrompt",
        "data": {
            "placeholder": "Type your products, one per line — e.g. 6312-2RS1/C3 x 10",
        },
    }


def mapping_table_payload(results: list[MappingResult]) -> dict:
    return {
        "component": "MappingTable",
        "data": {
            "rows": [
                {
                    "raw": r.raw,
                    "matched_sku": r.matched_sku,
                    "status": r.status.value,
                    "confidence": r.confidence,
                    "qty": r.qty,
                }
                for r in results
            ],
            "actions": ["accept_all", "decline_all"],
        },
    }


def quote_card_payload(quote: Quote) -> dict:
    return {
        "component": "QuoteCard",
        "data": {
            "quote_id": quote.quote_id,
            "status": quote.status,
            "currency": quote.currency,
            "total": str(quote.total),
            "total_display": format_eur(quote.total),
            "valid_until": quote.valid_until.isoformat(),
            "lines": [
                {
                    "sku": line.sku,
                    "description": line.description,
                    "qty": line.qty,
                    "unit_price": str(line.unit_price),
                    "unit_price_display": format_eur(line.unit_price),
                    "line_total": str(line.line_total),
                    "line_total_display": format_eur(line.line_total),
                }
                for line in quote.lines
            ],
            "actions": ["download_quote", "proceed_to_checkout"],
        },
    }


def cart_payload(cart: Cart) -> dict:
    return {
        "component": "Cart",
        "data": {
            "items": [
                {
                    "sku": item.sku,
                    "description": item.description,
                    "qty": item.qty,
                    "unit_price": str(item.unit_price),
                    "unit_price_display": format_eur(item.unit_price),
                    "line_total": str(item.line_total),
                    "line_total_display": format_eur(item.line_total),
                }
                for item in cart.items
            ],
            "item_count": cart.item_count,
            "total_qty": cart.total_qty,
            "total": str(cart.total),
            "total_display": format_eur(cart.total),
            "actions": ["proceed_to_checkout"],
        },
    }


def checkout_form_payload() -> dict:
    return {
        "component": "CheckoutForm",
        "data": {
            "fields": {
                "purchase_order_number": {
                    "label": "Purchase order number",
                    "required": True,
                    "max_length": 35,
                },
                "order_type": {
                    "label": "Selected order type",
                    "type": "dropdown",
                    "options": ["Standard", "Express", "Consignment"],
                },
                "comment": {
                    "label": "Comment",
                    "required": False,
                    "max_length": 512,
                },
            },
            "sections": ["Shipment & Delivery", "Payment & billing"],
            "actions": ["place_order"],
        },
    }


def confirmation_payload(order: Order) -> dict:
    return {
        "component": "Confirmation",
        "data": {
            "order_id": order.order_id,
            "status": order.status,
            "message": (
                "Your order has been successfully placed and is being processed. "
                "You will receive a confirmation email shortly with your order "
                "details and tracking information."
            ),
        },
    }


def product_details_payload(entry: CatalogEntry) -> dict:
    tiers = []
    for tier in entry.price_tiers:
        rng = f"{tier.min_qty}–{tier.max_qty}" if tier.max_qty else f"{tier.min_qty}+"
        tiers.append({"range": rng, "unit_price_display": format_eur(tier.unit_price)})
    return {
        "component": "ProductDetails",
        "data": {
            "sku": entry.schaeffler_sku,
            "description": entry.description,
            "category": entry.category,
            "in_stock": entry.availability.in_stock,
            "lead_time_days": entry.availability.lead_time_days,
            "price_tiers": tiers,
            "from_price_display": format_eur(entry.price_tiers[0].unit_price) if entry.price_tiers else None,
            "attributes": entry.attributes,
        },
    }


def equivalent_prompt_payload(raw: str, entry: CatalogEntry) -> dict:
    """Customer designation -> Schaeffler equivalent, asking before showing details."""
    return {
        "component": "EquivalentPrompt",
        "data": {
            "raw": raw,
            "sku": entry.schaeffler_sku,
            "description": entry.description,
        },
    }


def already_in_cart_payload(entry: CatalogEntry, current_qty: int) -> dict:
    """Confirm prompt for adding an item that's already in the cart, with a quantity to add."""
    return {
        "component": "AlreadyInCart",
        "data": {
            "sku": entry.schaeffler_sku,
            "description": entry.description,
            "current_qty": current_qty,
        },
    }


def stub_payload(title: str, message: str) -> dict:
    return {"component": "StubMessage", "data": {"title": title, "message": message}}
