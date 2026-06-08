"""FR-3 mapping acceptance tests (PRD §15)."""
from pathlib import Path

import pytest

from app.mapping import map_products, normalize
from app.parsing import parse_typed_products
from app.services.mock import MockCatalogService

CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"


@pytest.fixture(scope="module")
def catalog():
    return MockCatalogService(CATALOG_PATH)


@pytest.mark.parametrize(
    "raw,expected_sku,status",
    [
        ("6312-2RS1/C3", "HC6312-C-2HRS-L207-C3", "mapped"),
        ("6308-2RS", "HC6308-C-2HRS-L207", "mapped"),
        ("ABC-123-XYZ", None, "no_equivalent"),
    ],
)
def test_mapping_cascade(catalog, raw, expected_sku, status):
    [result] = map_products(parse_typed_products(raw), catalog)
    assert result.matched_sku == expected_sku
    assert result.status.value == status


def test_exact_schaeffler_sku_is_matched(catalog):
    [result] = map_products(parse_typed_products("6204-C-22"), catalog)
    assert result.matched_sku == "6204-C-22"
    assert result.status.value == "matched"
    assert result.confidence == 1.0


def test_cross_reference_is_mapped_with_full_confidence(catalog):
    [result] = map_products(parse_typed_products("6312-2RS1/C3"), catalog)
    assert result.status.value == "mapped"
    assert result.confidence == 1.0


def test_reverse_index_built(catalog):
    assert catalog.xref_index()[normalize("6312-2RS1/C3")] == "HC6312-C-2HRS-L207-C3"
    assert catalog.xref_index()[normalize("6312 2RS1 C3")] == "HC6312-C-2HRS-L207-C3"


def test_no_equivalent_has_zero_confidence_and_null_sku(catalog):
    [result] = map_products(parse_typed_products("ABC-123-XYZ"), catalog)
    assert result.matched_sku is None
    assert result.confidence == 0.0


def test_qty_is_carried_through_mapping(catalog):
    results = map_products(parse_typed_products("6312-2RS1/C3 x 10\n6308-2RS, 5"), catalog)
    assert [(r.matched_sku, r.qty) for r in results] == [
        ("HC6312-C-2HRS-L207-C3", 10),
        ("HC6308-C-2HRS-L207", 5),
    ]
