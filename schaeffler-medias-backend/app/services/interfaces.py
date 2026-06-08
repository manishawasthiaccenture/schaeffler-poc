"""Service interfaces — the swap seam (PRD §7).

The agent and domain logic depend only on these abstractions. V1 ships Mock*
implementations; real ERP/PIM/pricing impls drop in later with no orchestration
changes. Milestone 1 defines CatalogService only.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from ..models import Cart, CatalogEntry, Order, OrderInfo, Quote

# A request line is a resolved (Schaeffler SKU, quantity) pair.
RequestLine = tuple[str, int]


class CatalogService(ABC):
    @abstractmethod
    def entries(self) -> list[CatalogEntry]:
        """All catalog entries."""

    @abstractmethod
    def sku_index(self) -> dict[str, str]:
        """normalized Schaeffler SKU -> canonical Schaeffler SKU."""

    @abstractmethod
    def xref_index(self) -> dict[str, str]:
        """normalized cross-reference -> Schaeffler SKU (the reverse index)."""

    @abstractmethod
    def fuzzy_candidates(self) -> list[tuple[str, str]]:
        """(normalized candidate string, Schaeffler SKU) over all SKUs + cross-refs."""

    @abstractmethod
    def get(self, sku: str) -> CatalogEntry | None:
        """Look up a catalog entry by canonical Schaeffler SKU."""


class PricingService(ABC):
    @abstractmethod
    def unit_price(self, sku: str, qty: int) -> Decimal:
        """Unit price for the given SKU at the requested quantity (tier lookup)."""


class QuoteService(ABC):
    @abstractmethod
    def create_quote(self, lines: list[RequestLine]) -> Quote:
        """Create a quote from resolved (sku, qty) lines (FR-5)."""

    @abstractmethod
    def get_quote(self, quote_id: str) -> Quote | None:
        """Retrieve a previously created quote."""


class CartService(ABC):
    @abstractmethod
    def add_to_cart(self, conversation_id: str, lines: list[RequestLine]) -> Cart:
        """Add resolved (sku, qty) lines to the session cart (FR-6)."""

    @abstractmethod
    def get_cart(self, conversation_id: str) -> Cart:
        """Return the current cart for the session."""

    @abstractmethod
    def update_cart_item(self, conversation_id: str, sku: str, qty: int) -> Cart:
        """Set the quantity for a line (re-evaluates the price tier); qty<=0 removes it."""

    @abstractmethod
    def remove_cart_item(self, conversation_id: str, sku: str) -> Cart:
        """Remove a line from the cart."""

    @abstractmethod
    def clear_cart(self, conversation_id: str) -> Cart:
        """Empty the session cart (e.g. when starting a new order)."""


class OrderService(ABC):
    @abstractmethod
    def create_order(self, cart: Cart, order_info: OrderInfo) -> Order:
        """Place the order and return a confirmed order (FR-8)."""
