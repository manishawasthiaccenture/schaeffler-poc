"""Milestone 2 — mock service tests (FR-5 quote, FR-6 cart, FR-8 order)."""
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.mapping import accepted_lines, map_products
from app.models import OrderInfo
from app.parsing import parse_typed_products
from app.services.mock import (
    MockCartService,
    MockCatalogService,
    MockOrderService,
    MockPricingService,
    MockQuoteService,
)

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"

JOURNEY_INPUT = "6312-2RS1/C3 x 10\n6308-2RS, 5\nABC-123-XYZ"


@pytest.fixture
def catalog():
    return MockCatalogService(CATALOG_PATH)


@pytest.fixture
def pricing(catalog):
    return MockPricingService(catalog)


def test_price_tier_lookup(pricing):
    assert pricing.unit_price("HC6312-C-2HRS-L207-C3", 10) == Decimal("18.50")
    assert pricing.unit_price("HC6312-C-2HRS-L207-C3", 249) == Decimal("18.50")
    assert pricing.unit_price("HC6312-C-2HRS-L207-C3", 250) == Decimal("16.20")
    assert pricing.unit_price("HC6308-C-2HRS-L207", 5) == Decimal("12.95")


def test_pricing_unknown_sku_raises(pricing):
    with pytest.raises(KeyError):
        pricing.unit_price("DOES-NOT-EXIST", 1)


def test_create_quote_from_journey(catalog, pricing):
    quotes = MockQuoteService(pricing, catalog)
    results = map_products(parse_typed_products(JOURNEY_INPUT), catalog)
    quote = quotes.create_quote(accepted_lines(results))

    assert len(quote.lines) == 2  # ABC-123-XYZ excluded
    assert [(line.sku, line.qty) for line in quote.lines] == [
        ("HC6312-C-2HRS-L207-C3", 10),
        ("HC6308-C-2HRS-L207", 5),
    ]
    assert quote.total == Decimal("249.75")  # 18.50*10 + 12.95*5
    assert quote.status == "Released"
    assert quote.currency == "EUR"
    assert quote.valid_until == date.today() + timedelta(days=60)


def test_quote_ids_are_deterministic(catalog, pricing):
    quotes = MockQuoteService(pricing, catalog)
    q1 = quotes.create_quote([("6204-C-22", 1)])
    q2 = quotes.create_quote([("6204-C-22", 1)])
    assert q1.quote_id == "12345"
    assert q2.quote_id == "12346"
    assert quotes.get_quote("12345") is q1


def test_cart_seeded_from_accepted_quote_lines(catalog, pricing):
    carts = MockCartService(pricing, catalog)
    cart = carts.add_to_cart(
        "c1", [("HC6312-C-2HRS-L207-C3", 10), ("HC6308-C-2HRS-L207", 5)]
    )
    assert cart.item_count == 2
    assert cart.total_qty == 15
    assert cart.total == Decimal("249.75")


def test_update_cart_item_reevaluates_price_tier(catalog, pricing):
    carts = MockCartService(pricing, catalog)
    carts.add_to_cart("c1", [("HC6312-C-2HRS-L207-C3", 10)])
    cart = carts.update_cart_item("c1", "HC6312-C-2HRS-L207-C3", 250)
    [item] = cart.items
    assert item.unit_price == Decimal("16.20")
    assert item.line_total == Decimal("4050.00")


def test_update_to_zero_removes_item(catalog, pricing):
    carts = MockCartService(pricing, catalog)
    carts.add_to_cart("c1", [("6204-C-22", 3)])
    cart = carts.update_cart_item("c1", "6204-C-22", 0)
    assert cart.item_count == 0


def test_remove_cart_item(catalog, pricing):
    carts = MockCartService(pricing, catalog)
    carts.add_to_cart("c1", [("6204-C-22", 2), ("6204-C-C3", 3)])
    cart = carts.remove_cart_item("c1", "6204-C-22")
    assert cart.item_count == 1
    assert cart.items[0].sku == "6204-C-C3"


def test_carts_are_isolated_per_conversation(catalog, pricing):
    carts = MockCartService(pricing, catalog)
    carts.add_to_cart("c1", [("6204-C-22", 1)])
    assert carts.get_cart("c2").item_count == 0


def test_create_order_is_confirmed_with_deterministic_id(catalog, pricing):
    carts = MockCartService(pricing, catalog)
    cart = carts.add_to_cart("c1", [("6204-C-22", 1)])
    orders = MockOrderService()
    order = orders.create_order(cart, OrderInfo(purchase_order_number="PO-123"))
    assert order.status == "confirmed"
    assert order.order_id == "ORD-100001"


def test_create_order_requires_po_number(catalog, pricing):
    carts = MockCartService(pricing, catalog)
    cart = carts.add_to_cart("c1", [("6204-C-22", 1)])
    orders = MockOrderService()
    with pytest.raises(ValueError):
        orders.create_order(cart, OrderInfo(purchase_order_number="   "))
