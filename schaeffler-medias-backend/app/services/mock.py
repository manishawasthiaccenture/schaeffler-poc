"""Mock service implementations (PRD §7).

Milestone 1: MockCatalogService.
Milestone 2: MockPricingService, MockQuoteService, MockCartService, MockOrderService.

Ids are deterministic (counter-based) so tests are stable. The quote counter
starts at 12345 to match the storyboard demo.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ..mapping import normalize
from ..models import (
    Availability,
    Cart,
    CartItem,
    CatalogEntry,
    Order,
    OrderInfo,
    PriceTier,
    Quote,
    QuoteLine,
)
from .interfaces import (
    CartService,
    CatalogService,
    OrderService,
    PricingService,
    QuoteService,
    RequestLine,
)


class MockCatalogService(CatalogService):
    """Loads catalog.json and builds the normalized SKU + reverse cross-ref indexes."""

    def __init__(self, catalog_path: str | Path) -> None:
        self._entries = self._load(Path(catalog_path))
        self._by_sku: dict[str, CatalogEntry] = {
            e.schaeffler_sku: e for e in self._entries
        }
        self._sku_index: dict[str, str] = {}
        self._xref_index: dict[str, str] = {}
        self._fuzzy: list[tuple[str, str]] = []

        for entry in self._entries:
            sku = entry.schaeffler_sku
            norm_sku = normalize(sku)
            self._sku_index[norm_sku] = sku
            self._fuzzy.append((norm_sku, sku))
            for xref in entry.cross_references:
                norm_xref = normalize(xref)
                self._xref_index[norm_xref] = sku
                self._fuzzy.append((norm_xref, sku))

    @staticmethod
    def _load(path: Path) -> list[CatalogEntry]:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries: list[CatalogEntry] = []
        for d in data:
            tiers = [
                PriceTier(
                    min_qty=t["min_qty"],
                    max_qty=t["max_qty"],
                    unit_price=Decimal(str(t["unit_price"])),
                )
                for t in d["price_tiers"]
            ]
            availability = Availability(
                in_stock=d["availability"]["in_stock"],
                lead_time_days=d["availability"]["lead_time_days"],
            )
            entries.append(
                CatalogEntry(
                    schaeffler_sku=d["schaeffler_sku"],
                    description=d["description"],
                    category=d["category"],
                    availability=availability,
                    price_tiers=tiers,
                    cross_references=d.get("cross_references", []),
                    attributes=d.get("attributes", {}),
                )
            )
        return entries

    def entries(self) -> list[CatalogEntry]:
        return list(self._entries)

    def sku_index(self) -> dict[str, str]:
        return self._sku_index

    def xref_index(self) -> dict[str, str]:
        return self._xref_index

    def fuzzy_candidates(self) -> list[tuple[str, str]]:
        return self._fuzzy

    def get(self, sku: str) -> CatalogEntry | None:
        return self._by_sku.get(sku)


class MockPricingService(PricingService):
    """Resolves unit price from the catalog's price tiers for the requested qty."""

    def __init__(self, catalog: CatalogService) -> None:
        self._catalog = catalog

    def unit_price(self, sku: str, qty: int) -> Decimal:
        entry = self._catalog.get(sku)
        if entry is None:
            raise KeyError(f"unknown sku: {sku}")
        for tier in entry.price_tiers:
            upper = tier.max_qty if tier.max_qty is not None else qty
            if tier.min_qty <= qty <= upper:
                return tier.unit_price
        return entry.price_tiers[-1].unit_price


class MockQuoteService(QuoteService):
    def __init__(
        self,
        pricing: PricingService,
        catalog: CatalogService,
        start_id: int = 12345,
        validity_days: int = 60,
    ) -> None:
        self._pricing = pricing
        self._catalog = catalog
        self._counter = start_id
        self._validity_days = validity_days
        self._quotes: dict[str, Quote] = {}

    def create_quote(self, lines: list[RequestLine]) -> Quote:
        quote_id = str(self._counter)
        self._counter += 1

        quote_lines: list[QuoteLine] = []
        total = Decimal("0")
        for sku, qty in lines:
            unit_price = self._pricing.unit_price(sku, qty)
            line_total = unit_price * qty
            total += line_total
            entry = self._catalog.get(sku)
            quote_lines.append(
                QuoteLine(
                    sku=sku,
                    description=entry.description if entry else "",
                    qty=qty,
                    unit_price=unit_price,
                    line_total=line_total,
                )
            )

        quote = Quote(
            quote_id=quote_id,
            status="Released",
            currency="EUR",
            total=total,
            valid_until=date.today() + timedelta(days=self._validity_days),
            lines=quote_lines,
        )
        self._quotes[quote_id] = quote
        return quote

    def get_quote(self, quote_id: str) -> Quote | None:
        return self._quotes.get(quote_id)


class MockCartService(CartService):
    """In-memory cart per conversation; quantities re-priced on every read."""

    def __init__(self, pricing: PricingService, catalog: CatalogService) -> None:
        self._pricing = pricing
        self._catalog = catalog
        # conversation_id -> {sku: qty}, insertion-ordered for stable display
        self._carts: dict[str, dict[str, int]] = {}

    def add_to_cart(self, conversation_id: str, lines: list[RequestLine]) -> Cart:
        skus = self._carts.setdefault(conversation_id, {})
        for sku, qty in lines:
            skus[sku] = skus.get(sku, 0) + qty
        return self._build(conversation_id)

    def get_cart(self, conversation_id: str) -> Cart:
        return self._build(conversation_id)

    def update_cart_item(self, conversation_id: str, sku: str, qty: int) -> Cart:
        skus = self._carts.setdefault(conversation_id, {})
        if qty <= 0:
            skus.pop(sku, None)
        else:
            skus[sku] = qty
        return self._build(conversation_id)

    def remove_cart_item(self, conversation_id: str, sku: str) -> Cart:
        self._carts.setdefault(conversation_id, {}).pop(sku, None)
        return self._build(conversation_id)

    def clear_cart(self, conversation_id: str) -> Cart:
        self._carts[conversation_id] = {}
        return self._build(conversation_id)

    def _build(self, conversation_id: str) -> Cart:
        skus = self._carts.setdefault(conversation_id, {})
        items: list[CartItem] = []
        for sku, qty in skus.items():
            entry = self._catalog.get(sku)
            items.append(
                CartItem(
                    sku=sku,
                    description=entry.description if entry else "",
                    qty=qty,
                    unit_price=self._pricing.unit_price(sku, qty),
                )
            )
        return Cart(items=items)


class MockOrderService(OrderService):
    def __init__(self, start_id: int = 100001) -> None:
        self._counter = start_id
        self._orders: dict[str, Order] = {}

    def create_order(self, cart: Cart, order_info: OrderInfo) -> Order:
        if not order_info.purchase_order_number or not order_info.purchase_order_number.strip():
            raise ValueError("purchase_order_number is required")
        order_id = f"ORD-{self._counter}"
        self._counter += 1
        order = Order(order_id=order_id, status="confirmed")
        self._orders[order_id] = order
        return order
