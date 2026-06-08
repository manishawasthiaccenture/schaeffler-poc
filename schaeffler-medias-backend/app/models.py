"""Domain models for the medias ordering assistant (V1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class MappingStatus(str, Enum):
    MATCHED = "matched"          # exact hit on a Schaeffler SKU
    MAPPED = "mapped"            # resolved via cross-reference or fuzzy match
    NO_EQUIVALENT = "no_equivalent"


class WorkflowStep(str, Enum):
    """The guided ordering workflow's current step (FR-9)."""

    GREETING = "greeting"
    AWAITING_PRODUCTS = "awaiting_products"
    AWAITING_MAPPING_REVIEW = "awaiting_mapping_review"
    QUOTE_READY = "quote_ready"
    CART_REVIEW = "cart_review"
    CHECKOUT = "checkout"
    CONFIRMED = "confirmed"


@dataclass
class ParsedItem:
    """A single (designation, quantity) pair extracted from typed input (FR-2)."""

    raw: str
    qty: int
    valid: bool = True
    error: Optional[str] = None


@dataclass
class MappingResult:
    """Outcome of resolving one parsed item to a Schaeffler SKU (FR-3)."""

    raw: str
    matched_sku: Optional[str]
    status: MappingStatus
    confidence: float
    qty: int

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "matched_sku": self.matched_sku,
            "status": self.status.value,
            "confidence": self.confidence,
            "qty": self.qty,
        }


@dataclass
class PriceTier:
    min_qty: int
    max_qty: Optional[int]
    unit_price: Decimal


@dataclass
class Availability:
    in_stock: bool
    lead_time_days: int


@dataclass
class CatalogEntry:
    schaeffler_sku: str
    description: str
    category: str
    availability: Availability
    price_tiers: list[PriceTier]
    cross_references: list[str] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)


@dataclass
class QuoteLine:
    sku: str
    description: str
    qty: int
    unit_price: Decimal
    line_total: Decimal


@dataclass
class Quote:
    quote_id: str
    status: str
    currency: str
    total: Decimal
    valid_until: date
    lines: list[QuoteLine] = field(default_factory=list)


@dataclass
class CartItem:
    sku: str
    description: str
    qty: int
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.qty


@dataclass
class Cart:
    items: list[CartItem] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum((item.line_total for item in self.items), Decimal("0"))

    @property
    def item_count(self) -> int:
        """Number of distinct line items."""
        return len(self.items)

    @property
    def total_qty(self) -> int:
        """Sum of quantities across all lines."""
        return sum(item.qty for item in self.items)


@dataclass
class OrderInfo:
    purchase_order_number: str
    order_type: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class Order:
    order_id: str
    status: str


@dataclass
class SessionState:
    """Server-side workflow state keyed by conversation_id (FR-9)."""

    conversation_id: str
    step: WorkflowStep = WorkflowStep.GREETING
    parsed_items: list[ParsedItem] = field(default_factory=list)
    mapping_results: list[MappingResult] = field(default_factory=list)
    quote_id: Optional[str] = None
    order_info: Optional[OrderInfo] = None
    order_id: Optional[str] = None
    # Chat transcript: [{"role": "user"|"assistant", "text": str}, ...] (bounded).
    transcript: list[dict] = field(default_factory=list)


@dataclass
class TurnResult:
    """One assistant turn: text plus zero or more UI payloads (PRD §10)."""

    text: str
    ui: list[dict] = field(default_factory=list)
    step: WorkflowStep = WorkflowStep.GREETING
