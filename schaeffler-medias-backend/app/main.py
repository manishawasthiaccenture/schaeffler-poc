"""FastAPI + SSE transport (PRD §11). Thin wrapper over the orchestrator.

The orchestrator stays transport-agnostic; this module only adapts HTTP <-> run_turn
and streams each turn as Server-Sent Events:
  - {"type": "text", "text": "..."}
  - {"type": "ui",   "payload": {"component": "...", "data": {...}}}
  - {"type": "done", "step": "..."}
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from the backend-root .env into os.environ (stdlib only)."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()  # must run before the orchestrator reads ANTHROPIC_API_KEY

from fastapi import FastAPI, HTTPException, Response  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app.agent.orchestrator import build_default_orchestrator  # noqa: E402
from app.models import SessionState  # noqa: E402
from app.quote_pdf import render_quote_pdf  # noqa: E402

app = FastAPI(title="medias Conversational Ordering Assistant", version="0.1.0")

# CORS for the separate React frontend dev origin (PRD D7).
_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared orchestrator => in-memory sessions persist across requests.
orchestrator = build_default_orchestrator()


class MessageIn(BaseModel):
    message: str
    payload: dict | None = None


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _serialize_state(state: SessionState) -> dict:
    return {
        "conversation_id": state.conversation_id,
        "step": state.step.value,
        "parsed_items": [
            {"raw": i.raw, "qty": i.qty, "valid": i.valid, "error": i.error}
            for i in state.parsed_items
        ],
        "mapping_results": [r.to_dict() for r in state.mapping_results],
        "quote_id": state.quote_id,
        "order_id": state.order_id,
        "order_info": (
            {
                "purchase_order_number": state.order_info.purchase_order_number,
                "order_type": state.order_info.order_type,
                "comment": state.order_info.comment,
            }
            if state.order_info
            else None
        ),
    }


@app.post("/conversations")
def create_conversation() -> dict:
    return {"conversation_id": orchestrator.create_conversation()}


@app.post("/conversations/{conversation_id}/messages")
def post_message(conversation_id: str, body: MessageIn) -> StreamingResponse:
    if orchestrator.get_state(conversation_id) is None:
        raise HTTPException(status_code=404, detail="conversation not found")

    turn = orchestrator.run_turn(conversation_id, body.message, body.payload)

    def event_stream() -> Iterator[str]:
        yield _sse({"type": "text", "text": turn.text})
        for payload in turn.ui:
            yield _sse({"type": "ui", "payload": payload})
        yield _sse({"type": "done", "step": turn.step.value})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/conversations/{conversation_id}/state")
def get_state(conversation_id: str) -> dict:
    state = orchestrator.get_state(conversation_id)
    if state is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    return _serialize_state(state)


@app.get("/quotes/{quote_id}/pdf")
def quote_pdf(quote_id: str) -> Response:
    quote = orchestrator.get_quote(quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="quote not found")
    return Response(
        content=render_quote_pdf(quote),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="quote-{quote_id}.pdf"'},
    )
