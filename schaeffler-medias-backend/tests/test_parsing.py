"""FR-2 parsing acceptance tests (PRD §15)."""
import pytest

from app.parsing import parse_typed_products


@pytest.mark.parametrize(
    "line,raw,qty",
    [
        ("6312-2RS1/C3 x 10", "6312-2RS1/C3", 10),
        ("6308-2RS, 5", "6308-2RS", 5),
        ("HC6204-C-22  144", "HC6204-C-22", 144),
        ("ABC-123-XYZ", "ABC-123-XYZ", 1),
        ("qty 3 6204-C-C3", "6204-C-C3", 3),
    ],
)
def test_parse_single_line(line, raw, qty):
    items = parse_typed_products(line)
    assert len(items) == 1
    assert items[0].raw == raw
    assert items[0].qty == qty
    assert items[0].valid


def test_colon_separator():
    [item] = parse_typed_products("6308-2RS: 7")
    assert (item.raw, item.qty) == ("6308-2RS", 7)


def test_blank_lines_ignored():
    items = parse_typed_products("\n6308-2RS, 5\n\n   \n")
    assert len(items) == 1
    assert items[0].raw == "6308-2RS"


def test_multiline_journey_input():
    text = "6312-2RS1/C3 x 10\n6308-2RS, 5\nABC-123-XYZ"
    items = parse_typed_products(text)
    assert [(i.raw, i.qty) for i in items] == [
        ("6312-2RS1/C3", 10),
        ("6308-2RS", 5),
        ("ABC-123-XYZ", 1),
    ]


def test_invalid_quantity_is_flagged():
    [item] = parse_typed_products("6204-C-C3 x 0")
    assert item.valid is False
    assert item.error


@pytest.mark.parametrize(
    "line,raw,qty",
    [
        ("HC6312-C-2HRS-L207-C3 with 100 quantity", "HC6312-C-2HRS-L207-C3", 100),
        ("HC6312-C-2HRS-L207-C3 quantity 100", "HC6312-C-2HRS-L207-C3", 100),
        ("100 of 6204-C-C3", "6204-C-C3", 100),
        ("add 5 6204-C-C3", "6204-C-C3", 5),
        ("I'd like 12 of HC6308-C-2HRS-L207 please", "HC6308-C-2HRS-L207", 12),
    ],
)
def test_natural_language_quantity(line, raw, qty):
    [item] = parse_typed_products(line)
    assert item.raw == raw
    assert item.qty == qty
    assert item.valid
