# schaeffler-medias-backend

Backend for the **medias** conversational ordering assistant (V1). Python · FastAPI · LangChain (single-agent, LangGraph-ready). See `../PRD.md` for full scope.

## Milestone 1: catalog + parsing + mapping

- `data/catalog.json` — six seed catalog entries with price tiers and cross-references.
- `app/models.py` — domain dataclasses (`ParsedItem`, `MappingResult`, `CatalogEntry`, ...).
- `app/parsing.py` — `parse_typed_products` (FR-2): tolerant typed-list parser.
- `app/mapping.py` — mapping cascade (FR-3): exact SKU → cross-reference → fuzzy → no-equivalent, plus `accepted_lines` (FR-4). rapidfuzz with stdlib `difflib` fallback.
- `app/services/interfaces.py` — `CatalogService` ABC (the swap seam, PRD §7).
- `app/services/mock.py` — `MockCatalogService`: loads the catalog and builds the SKU + reverse cross-reference indexes.

## Milestone 2: mock Pricing / Quote / Cart / Order services

- `app/models.py` — `Quote`/`QuoteLine`, `Cart`/`CartItem`, `OrderInfo`, `Order`.
- `app/services/interfaces.py` — `PricingService`, `QuoteService`, `CartService`, `OrderService` ABCs.
- `app/services/mock.py` —
  - `MockPricingService` — tier lookup from the catalog (FR-5/FR-6).
  - `MockQuoteService` — quote id (counter from 12345), 60-day validity, `Released` status (FR-5).
  - `MockCartService` — in-memory cart per conversation; re-prices on quantity change (FR-6).
  - `MockOrderService` — confirmed order with deterministic `ORD-` id; requires a PO number (FR-8).

## Milestone 3 (current): orchestrator + MockLLM + CLI

- `app/models.py` — `WorkflowStep`, `SessionState`, `TurnResult`.
- `app/session.py` — `SessionStore` ABC + `InMemorySessionStore` (FR-9).
- `app/formatting.py` — `format_eur` (de-DE money, PRD §12).
- `app/tools.py` — UI render-hint builders for each §10 component (JSON-safe payloads).
- `app/agent/llm.py` — `LLMClient` ABC, `MockLLMClient` (deterministic intent routing, FR-1), `RealLLMClient` stub.
- `app/agent/orchestrator.py` — `Orchestrator.run_turn(...)` drives the guided workflow (no FastAPI imports → future LangGraph node); `build_default_orchestrator()` wires the all-mock stack.
- `cli.py` — runs the full journey end-to-end with no server/keys.

Run the journey:

```bash
python cli.py     # prints typed input -> mapping -> quote -> cart -> checkout -> Order confirmed
```

## Milestone 4: FastAPI + SSE

- `app/main.py` — HTTP transport wrapping the orchestrator (no orchestration logic here):
  - `POST /conversations` → `{ conversation_id }`
  - `POST /conversations/{id}/messages` → **SSE stream** of `text` / `ui` / `done` events
  - `GET /conversations/{id}/state` → workflow state (debug)
- CORS enabled for the React dev origin (PRD D7); override with `CORS_ORIGINS`.

Run the server:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://127.0.0.1:8000
```

The FastAPI layer needs `fastapi`/`httpx` installed; the API tests skip automatically when they're absent, so the core domain tests still run on stdlib alone.

## Milestone 5 (current): quote PDF

- `app/quote_pdf.py` — `render_quote_pdf(quote)` renders a one-page quote PDF. Uses
  `reportlab` when installed, with a pure-stdlib minimal-PDF fallback so it works with
  no installs (PRD §12).
- `GET /quotes/{quote_id}/pdf` — returns `application/pdf` (404 if the quote is unknown).
  Backs the QuoteCard's "Download quote" action.

The backend (milestones 1–5) is now feature-complete. The remaining milestone 6 is the
React frontend, which lives in a separate repo (PRD D7).

## Run tests

No installs required (core logic runs on stdlib):

```bash
python -m pytest
```

Optionally install the full stack for the later milestones:

```bash
pip install -r requirements.txt
```
