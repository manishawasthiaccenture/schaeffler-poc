"""Milestone 4 — FastAPI + SSE endpoint tests (PRD §11).

Skipped automatically if FastAPI isn't installed (core logic stays stdlib-only).
"""
import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

JOURNEY_INPUT = "6312-2RS1/C3 x 10\n6308-2RS, 5\nABC-123-XYZ"


def _parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        line = block.strip()
        if line.startswith("data:"):
            events.append(json.loads(line[len("data:"):].strip()))
    return events


def _new_conversation() -> str:
    return client.post("/conversations").json()["conversation_id"]


def _send(cid: str, message: str, payload: dict | None = None) -> list[dict]:
    resp = client.post(
        f"/conversations/{cid}/messages", json={"message": message, "payload": payload}
    )
    assert resp.status_code == 200
    return _parse_sse(resp.text)


def test_create_conversation_returns_id():
    resp = client.post("/conversations")
    assert resp.status_code == 200
    assert resp.json()["conversation_id"]


def test_message_streams_text_ui_done():
    cid = _new_conversation()
    events = _send(cid, "I want to buy products")
    assert events[0]["type"] == "text"
    assert any(
        e["type"] == "ui" and e["payload"]["component"] == "UploadWidget" for e in events
    )
    assert events[-1] == {
        "type": "done",
        "step": "awaiting_products",
        "mode": "order",
        "suggestions": [],
    }


def test_state_endpoint_tracks_workflow():
    cid = _new_conversation()
    _send(cid, "I want to buy products")
    state = client.get(f"/conversations/{cid}/state").json()
    assert state["step"] == "awaiting_products"
    assert state["conversation_id"] == cid


def test_full_journey_over_http():
    cid = _new_conversation()
    _send(cid, "I want to buy products")
    _send(cid, JOURNEY_INPUT)

    events = _send(cid, "Accept all mappings and request a quote")
    quote = next(
        e["payload"]["data"]
        for e in events
        if e["type"] == "ui" and e["payload"]["component"] == "QuoteCard"
    )
    assert quote["total"] == "249.75"
    assert quote["total_display"] == "€ 249,75"

    _send(cid, "Proceed to checkout")
    _send(cid, "Proceed to checkout")
    events = _send(cid, "Place order", {"purchase_order_number": "4500001234"})
    confirmation = next(
        e["payload"]["data"]
        for e in events
        if e["type"] == "ui" and e["payload"]["component"] == "Confirmation"
    )
    assert confirmation["status"] == "confirmed"

    state = client.get(f"/conversations/{cid}/state").json()
    assert state["step"] == "confirmed"
    assert state["order_id"] == confirmation["order_id"]


def test_message_to_unknown_conversation_404():
    resp = client.post("/conversations/does-not-exist/messages", json={"message": "hi"})
    assert resp.status_code == 404


def test_state_for_unknown_conversation_404():
    assert client.get("/conversations/does-not-exist/state").status_code == 404


def test_quote_pdf_download():
    cid = _new_conversation()
    _send(cid, "I want to buy products")
    _send(cid, JOURNEY_INPUT)
    _send(cid, "Request a quote")
    quote_id = client.get(f"/conversations/{cid}/state").json()["quote_id"]

    resp = client.get(f"/quotes/{quote_id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert f'quote-{quote_id}.pdf' in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")


def test_quote_pdf_missing_404():
    assert client.get("/quotes/does-not-exist/pdf").status_code == 404
