# PRD — medias Conversational Ordering Assistant (V1)

**Owner:** _(you)_
**Status:** Approved for build
**Target build tool:** Claude Code
**Stack:** Python 3.12 · FastAPI · LangChain (single-agent, LangGraph-ready)
**Last updated:** 2026-06-08

---

## 0. V1 Build Decisions (resolved 2026-06-08)

These decisions reconcile the storyboard (`Schaeffler-User Journey.pdf`, frames 20–27) with this PRD. They are authoritative where they conflict with prose below.

| # | Topic | Decision | Rationale |
|---|---|---|---|
| D1 | **Input path** | **Upload widget renders but is DISABLED.** Typed entry is the live V1 path. The "Bulk Upload" landing card and the "Choose Excel File" widget are shown (storyboard-faithful) but non-interactive/greyed; selecting them surfaces the typed-entry prompt. | Pixel-faithful to storyboard frames 21–23 without building Excel parsing in V1. |
| D2 | **Landing card label** | Keep the storyboard label **"Bulk Upload — Quote & Order via file upload"**. Activating it posts the `"I want to buy products"` chip and then renders the (disabled) upload widget + typed prompt. | Matches frame 20 verbatim. |
| D3 | **Quote status badge** | QuoteCard includes a **status badge** (e.g. `"Released"`) next to the quote id. | Matches frame 24. |
| D4 | **Chat shell chrome** | Specify the full shell (see §10.1): green top bar with robot icon + title + close (✕), white sub-header with hamburger + new-chat icons and SCHAEFFLER logo, input row with mic + attach (paperclip) icons. **Mic and attach are decorative/disabled in V1.** | Matches frames 20–27; mic/voice and attach/upload are out of V1 functional scope. |
| D5 | **Cart = accepted quote items** | The cart is populated from the accepted quote's line items (e.g. HC6312×10, HC6308×5). The storyboard's frame 25 shows different SKUs/format — that is a storyboard inconsistency we do **not** replicate. | Internal consistency; matches §15 acceptance criteria. |
| D6 | **Number format** | All money displayed de-DE (`€ 1.234,56`). Storyboard's US-format cart lines are not replicated. | §12 NFR. |
| D7 | **Frontend/backend separation** | **Two separate repos.** Backend = Python/FastAPI (this PRD's §13a). Frontend = React **Vite + TypeScript + Tailwind CSS** (§13b). They communicate **only** over the §11 HTTP/SSE API using the §10 UI payload contract. No shared code or build. | Clean modularity; either side swappable; backend has zero UI logic, frontend has zero business logic. |

---

## 1. Overview

`medias` is a conversational assistant embedded in the Schaeffler B2B web shop. It lets industrial customers place bearing/component orders through a chat interface backed by a **dynamic side panel** that renders structured UI (mapping tables, quote cards, cart, checkout, confirmation).

V1 implements **one intent end-to-end: ordering** — from typed product entry through SKU mapping, quote, cart, checkout, and order confirmation. The other four landing intents (Certificates, Support, Order status, Price & Availability) are visible in the UI but route to a "coming soon" stub.

### Key framing
This is **not a Q&A chatbot**. It is a **tool-calling agent that drives a generative UI through a guided transactional workflow**. The LLM orchestrates and routes; the quote, cart, and order are deterministic backend operations. Keep that boundary strict — the LLM never invents prices, quote IDs, or order numbers.

---

## 2. Goals & Non-Goals

### Goals
- Complete the ordering flow: **type products → map to Schaeffler SKUs → quote → cart → checkout → order confirmed**.
- Every external dependency sits behind a **swappable interface** (mock now, real ERP/pricing/SAP later) with zero orchestration changes on swap.
- The single agent is structured as **one node** so it drops into LangGraph later untouched.
- Catalog data ships as a **JSON file**; sessions/cart/quotes use an in-memory store behind an interface.
- **UI is pixel-faithful to the storyboard**, including the (disabled) upload affordances — see D1–D6.

### Non-Goals (V1)
- ❌ Excel/bulk file **parsing** (deferred — typed entry is the V1 input path; the upload widget renders disabled per D1).
- ❌ RAG / vector store / document retrieval (no Support or Certificates intent in V1).
- ❌ Semantic/embedding SKU matching (fuzzy string matching is sufficient for V1).
- ❌ Real authentication, real ERP integration, persistent DB.
- ❌ Multi-agent supervisor (designed for, not built).
- ❌ Voice/mic input (icon shown but disabled per D4).

---

## 3. V1 Scope — Locked Decisions

| Decision | Choice |
|---|---|
| Scope | Ordering flow only; other 4 intents are stubs |
| Input path | **Typed product list** (live). Upload widget rendered **disabled** for visual fidelity (D1). |
| RAG | None |
| Backend | Mock implementations behind swappable interfaces |
| Stack | Python + FastAPI, single LangChain tool-calling agent |
| Data | Catalog in JSON; sessions in-memory (interface-backed) |

---

## 4. User Flow (V1)

Mirrors the storyboarded journey. Upload affordances are shown but disabled (D1); typed entry is the live path.

1. User opens assistant → sees greeting + quick-action chips (5 cards per frame 20).
2. User clicks **"Bulk Upload"** card (D2) or types intent → posts `"I want to buy products"`.
3. Assistant renders the **disabled upload widget** + asks the user to **type their product list** (SKU + quantity per line).
4. User types a list, e.g. competitor + Schaeffler designations with quantities.
5. Assistant parses the list, runs the **mapping engine**, and renders a **MappingTable** in the side panel showing `Non-Schaeffler → Schaeffler` with an "Accept all" / "Decline all and remove from list" control and per-item status.
6. User accepts mappings and requests a quote.
7. Assistant calls `create_quote` and renders a **QuoteCard** (quote ID + status badge, total, valid-until date, line items, Download / Proceed to checkout).
8. User proceeds → assistant renders the **Cart** (accepted quote items; editable quantities, line totals, running total).
9. User proceeds to checkout → assistant renders the **CheckoutForm** (PO number*, order type, comment, shipment & delivery, payment & billing).
10. User places order → assistant renders the **Confirmation** ("Order confirmed", order id, email/tracking note).

---

## 5. Functional Requirements

### FR-1 — Intent routing
- The agent recognizes the ordering intent from free text **and** from quick-action chip messages (`"I want to buy products"`, `"Request a quote"`, `"Accept all mappings and request a quote"`, `"Proceed to checkout"`, `"Place order"`).
- Non-ordering chips (Certificates, Support, Order, Price & Availability) return a polite "coming soon" stub message.

### FR-2 — Typed product entry (PRIMARY LIVE INPUT)
The upload widget is rendered but disabled (D1). The live input is a free-typed, multi-line product list; the assistant extracts `(designation, quantity)` pairs. The parser must be tolerant of common formats:

| Typed line | Parsed result |
|---|---|
| `6312-2RS1/C3 x 10` | `("6312-2RS1/C3", 10)` |
| `6308-2RS, 5` | `("6308-2RS", 5)` |
| `HC6204-C-22  144` | `("HC6204-C-22", 144)` |
| `ABC-123-XYZ` | `("ABC-123-XYZ", 1)` _(qty defaults to 1)_ |
| `qty 3 6204-C-C3` | `("6204-C-C3", 3)` |

Rules:
- Separators between SKU and qty: `x`, `*`, `,`, `:`, whitespace, or the keyword `qty`.
- Quantity defaults to **1** if absent.
- One product per line; blank lines ignored.
- Quantity must be a positive integer; reject/flag otherwise.
- The designation token is preserved verbatim (raw) for display and passed to the mapping engine.

Implemented as `parse_typed_products(text: str) -> list[ParsedItem]` and routed through the **same `map_products` path** the upload feature would use later.

### FR-3 — Mapping engine
For each parsed item, resolve to a Schaeffler SKU using this cascade:

1. **Exact (normalized) match** against `schaeffler_sku` → status `matched`, confidence `1.0`.
2. **Exact (normalized) match** against any entry in `cross_references` → status `mapped`, confidence `1.0`.
3. **Fuzzy match** (rapidfuzz `token_sort_ratio` / normalized ratio) over all SKUs + cross-refs. If best score ≥ **threshold (default 0.88)** → status `mapped`, confidence = score.
4. Otherwise → status `no_equivalent`, confidence `0.0`, `matched_sku = null`.

Normalization for matching: uppercase, strip spaces / `-` / `/`. Fuzzy is a **fallback only** — never overrides an exact hit.

Output per item:
```json
{ "raw": "6312-2RS1/C3", "matched_sku": "HC6312-C-2HRS-L207-C3",
  "status": "mapped", "confidence": 1.0, "qty": 10 }
```

### FR-4 — Mapping review (human-in-the-loop)
- Side panel shows the mapping table with **Accept all** and **Decline all and remove from list**.
- `no_equivalent` items are flagged and excluded from the quote.
- Accepting proceeds to quote creation with the accepted items only.

### FR-5 — Quote generation
- `create_quote(items)` returns `{ quote_id, status, total, currency, valid_until, lines[] }`.
- `status` defaults to `"Released"` (D3) for the QuoteCard badge.
- Per-line unit price comes from `PricingService` using the catalog **price tiers** for the requested quantity.
- `valid_until` = today + 60 days (mock rule).
- QuoteCard exposes **Download quote** (PDF) and **Proceed to checkout**.

### FR-6 — Cart
- `get_cart` / `update_cart_item` / `remove_cart_item`.
- Cart is seeded from the **accepted quote's line items** (D5).
- Editable integer quantities; line total = unit_price(qty) × qty; cart shows running total and item count.
- Changing quantity re-evaluates the price tier.

### FR-7 — Checkout
- CheckoutForm fields: **Purchase order number** (required, max 35 chars), **Selected order type** (dropdown), **Comment** (optional, max 512 chars), **Shipment & Delivery**, **Payment & billing**.
- Validate required fields before enabling "Place order".

### FR-8 — Place order
- `create_order(cart, order_info)` returns `{ order_id, status: "confirmed" }`.
- Render Confirmation with the order id and the "confirmation email + tracking" note.

### FR-9 — Conversation & workflow state
- Server-side session keyed by `conversation_id` tracks: current step, parsed items, mapping results, active quote, cart, order info.
- State store is interface-backed (in-memory now → Redis/Postgres later).

---

## 6. Data Model — Catalog JSON

`data/catalog.json` is a list of catalog entries. Customer-specific price tiers live here in V1 and move behind `PricingService` later.

```json
{
  "schaeffler_sku": "HC6312-C-2HRS-L207-C3",
  "description": "Deep groove ball bearing",
  "category": "Rolling Bearing",
  "availability": { "in_stock": true, "lead_time_days": 5 },
  "price_tiers": [
    { "min_qty": 1, "max_qty": 249, "unit_price": 18.50 },
    { "min_qty": 250, "max_qty": null, "unit_price": 16.20 }
  ],
  "cross_references": ["6312-2RS1/C3", "6312 2RS1 C3"]
}
```

Seed data (include all six):

| schaeffler_sku | cross_references | tier1 (1–249) |
|---|---|---|
| HC6312-C-2HRS-L207-C3 | 6312-2RS1/C3 | 18.50 |
| HC6308-C-2HRS-L207 | 6308-2RS | 12.95 |
| 6204-C-22 | — | 14.50 |
| 6204-C-HRS | — | 13.10 |
| 6204-C-C3 | — | 15.40 |
| 6204-C-C4 | — | 17.20 |

On load, build a **reverse index**: each normalized `cross_references` entry → its Schaeffler SKU.

---

## 7. Service Interfaces (the swap seam)

Each is an abstract base (`Protocol` or `ABC`) with a `Mock*` implementation in V1. The agent depends only on the interface.

| Interface | V1 mock behavior | Future real impl |
|---|---|---|
| `CatalogService` | Load + index `catalog.json` | Product master / PIM |
| `PricingService` | Tier lookup from catalog | Customer-specific pricing API |
| `QuoteService` | Generate id, total, 60-day validity | ERP quote API |
| `CartService` | In-memory cart per session | Cart service |
| `OrderService` | Return confirmed id | ERP / SAP order API |

---

## 8. Agent Tools

These are the LLM-callable tools (thin wrappers over the services):

- `parse_typed_products(text)` → parsed items
- `map_products(items)` → mapping results
- `create_quote(items)` → quote
- `get_quote(quote_id)` / `download_quote(quote_id)` → PDF
- `add_to_cart(items)` / `get_cart()` / `update_cart_item(sku, qty)` / `remove_cart_item(sku)`
- `create_order(order_info)` → order

Each tool result carries a **UI render hint** (see §10).

---

## 9. Orchestration / LLM

- Single tool-calling loop. **The LLM itself is behind an interface** (`LLMClient`) consistent with the mock-everything decision:
  - `MockLLMClient` — deterministic, rule-based intent → tool routing. Lets the whole flow run **without an API key or network** (required for local dev/tests).
  - `RealLLMClient` — actual provider tool-calling (stub in V1, wired when keys available).
- The orchestrator is a self-contained unit (`run_turn(conversation_id, user_message) -> TurnResult`). **This unit becomes one LangGraph node later** — do not couple it to FastAPI.

---

## 10. UI Payload Contract

Every assistant turn returns text plus zero or more UI payloads. Frontend stays dumb and maps `component` → React widget:

```json
{ "component": "MappingTable", "data": { "rows": [ ... ] } }
```

V1 components: `UploadWidget` _(rendered **disabled** in V1, per D1)_, `TypePrompt`, `MappingTable`, `QuoteCard` _(includes status badge, D3)_, `Cart`, `CheckoutForm`, `Confirmation`, `StubMessage`.

### 10.1 Chat shell chrome (D4 — storyboard-faithful)
The shell wraps the two-pane (chat left / dynamic panel right) layout:
- **Green top bar:** robot icon + "Ask me anything…" title (left), close ✕ (right).
- **White sub-header:** hamburger menu + new-chat/compose icon (left), SCHAEFFLER wordmark (right).
- **Landing view:** centered "medias" title, subtitle "Get instant answers about orders, products, and customer inquiries.", large input, then the 5 intent cards.
- **Input row:** text field, **mic icon (disabled)**, **attach/paperclip icon (disabled)**, send button.
- **Colors:** Schaeffler green (#00893D-family) on header, chips, and primary buttons; white panels; red outline for destructive actions ("Decline all and remove from list").

---

## 11. API Spec

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/conversations` | Create session → `{ conversation_id }` |
| `POST` | `/conversations/{id}/messages` | Send user message; **SSE stream** of assistant text + UI payloads |
| `GET` | `/conversations/{id}/state` | Current workflow state (debug) |
| `GET` | `/quotes/{quote_id}/pdf` | Download quote PDF |

Streaming: Server-Sent Events. Each event is one of `{type: "text"}` or `{type: "ui", payload: {...}}`.

---

## 12. Non-Functional Requirements

- Core domain logic (parser, mapping, services, orchestrator + MockLLM) must run **with stdlib + no network** for tests.
- `rapidfuzz` optional with a `difflib` fallback so mapping works without installs.
- All money handled as `Decimal`; display formatted as `€ 1.234,56` (de-DE) at the edge only (D6).
- Deterministic outputs for mocks (stable quote/order id scheme for tests, e.g. counter-based).
- Graceful errors: unparseable line, empty list, all-no-equivalent, invalid quantity.

---

## 13. Project Structure

Two separate repos (D7), communicating only over the §11 HTTP/SSE API.

### 13a. Backend repo — `schaeffler-medias-backend` (Python · FastAPI · LangChain)

```
schaeffler-medias-backend/
├── README.md
├── requirements.txt
├── .env.example                # API keys (real LLM), CORS origins
├── data/
│   └── catalog.json
├── app/
│   ├── main.py                 # FastAPI app + SSE endpoints + CORS
│   ├── models.py               # dataclasses / pydantic models
│   ├── parsing.py              # parse_typed_products (FR-2)
│   ├── mapping.py              # mapping engine (FR-3)
│   ├── session.py              # SessionStore interface + InMemory impl
│   ├── tools.py                # agent tool registry
│   ├── services/
│   │   ├── interfaces.py       # Catalog/Pricing/Quote/Cart/Order ABCs
│   │   └── mock.py             # Mock* implementations
│   └── agent/
│       ├── orchestrator.py     # run_turn() — future LangGraph node
│       └── llm.py              # LLMClient + MockLLMClient + RealLLMClient stub
├── cli.py                      # run the full flow end-to-end, no server
└── tests/
    ├── test_parsing.py
    └── test_mapping.py
```

### 13b. Frontend repo — `schaeffler-medias-frontend` (React · Vite · TypeScript · Tailwind)

```
schaeffler-medias-frontend/
├── README.md
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts          # Schaeffler green/white theme tokens
├── .env.example                # VITE_API_BASE_URL → backend
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx                 # two-pane layout (chat left / dynamic panel right)
    ├── api/
    │   ├── client.ts           # POST /conversations, /messages
    │   └── sse.ts              # SSE stream parser → text + ui events
    ├── types/
    │   └── contract.ts         # TS types for §10 UI payload contract
    ├── shell/
    │   ├── TopBar.tsx          # green bar: robot icon + title + close (§10.1)
    │   ├── SubHeader.tsx       # hamburger + new-chat + SCHAEFFLER logo
    │   ├── Landing.tsx         # "medias" title, subtitle, input, 5 intent cards
    │   └── ChatInput.tsx       # text field + mic (disabled) + attach (disabled) + send
    ├── components/             # one widget per UI-contract component
    │   ├── registry.ts         # component-name string → React widget
    │   ├── MappingTable.tsx
    │   ├── QuoteCard.tsx       # includes "Released" status badge (D3)
    │   ├── Cart.tsx
    │   ├── CheckoutForm.tsx
    │   ├── Confirmation.tsx
    │   ├── UploadWidget.tsx    # rendered DISABLED (D1)
    │   ├── TypePrompt.tsx
    │   └── StubMessage.tsx
    └── theme/
        └── tokens.ts           # Schaeffler colors (green #00893D-family, etc.)
```

---

## 14. Build Milestones (order matters)

1. **Catalog + mapping + parsing** — `catalog.json`, `CatalogService` mock, reverse index, `parse_typed_products`, mapping cascade. _Unit-test against §15 first._
2. **Mock services** — Pricing/Quote/Cart/Order behind interfaces.
3. **Orchestrator + MockLLMClient** — `run_turn` drives the full flow; add `cli.py` to prove the journey end-to-end with no server/keys.
4. **FastAPI + SSE** — wrap the orchestrator; session endpoints.
5. **Quote PDF + Confirmation.**
6. _(Separate frontend repo, D7)_ React (Vite + TS + Tailwind) two-pane frontend: SSE client, TS types for the §10 contract, component registry, shell chrome (§10.1), disabled upload widget (D1), Schaeffler theme. Backend enables CORS for the frontend dev origin.

---

## 15. Acceptance Criteria & Test Cases

**Parsing** (`test_parsing.py`): each row in the FR-2 table parses to the expected `(designation, qty)`.

**Mapping** (`test_mapping.py`) — the journey's three inputs:

| Input | Expected matched_sku | Expected status |
|---|---|---|
| `6312-2RS1/C3` | `HC6312-C-2HRS-L207-C3` | `mapped` |
| `6308-2RS` | `HC6308-C-2HRS-L207` | `mapped` |
| `ABC-123-XYZ` | `null` | `no_equivalent` |

**End-to-end** (`cli.py`): typing the three lines above with quantities `10, 5, 1` →
- mapping table shows 2 mapped + 1 no_equivalent,
- accepting → quote with **2 line items** (HC6312 ×10, HC6308 ×5),
- quote total computed from tier-1 prices,
- proceed → cart with same 2 items (D5),
- checkout with a PO number → order `confirmed` with an order id.

**Definition of done:** `pytest` green; `python cli.py` prints the full journey from typed input to "Order confirmed".

---

## 16. Future Extension — LangGraph Multi-Agent (not in V1)

The V1 design is built to graduate without rewrite:
- A **supervisor agent** does intent routing and hands off to specialists.
- **Sales agents** as graph nodes: Ordering/Quote agent (the V1 `run_turn`), Cross-reference agent, plus future Support (RAG) and Certificates agents.
- The §7 service interfaces become the shared toolset across nodes.
- The §10 UI payload contract is unchanged.
- The disabled upload widget (D1) becomes the live bulk-upload path with an Excel parser feeding the same `map_products` route.

---

## 17. Instructions for Claude Code

- Build strictly in the milestone order in §14; **do not start the FastAPI layer before §15 mapping/parsing tests pass.**
- Keep the orchestrator (`run_turn`) free of FastAPI imports so it can become a LangGraph node.
- Everything external goes behind an interface in `app/services/interfaces.py`; only `app/services/mock.py` and `app/agent/llm.py:MockLLMClient` contain mock logic.
- Provide a `requirements.txt` (fastapi, uvicorn, pydantic, rapidfuzz, reportlab, pytest) but ensure core logic + tests run if only stdlib is present (difflib fallback for rapidfuzz).
- Do not let the LLM produce prices, quote ids, or order ids — those come only from services.
- Frontend (milestone 6) must match the storyboard shell (§10.1) and render the upload widget **disabled** (D1), routing the user to typed entry.
- Frontend and backend are **separate repos** (D7). They share nothing but the §11 API + §10 payload contract. Keep no backend code in the frontend repo and no UI logic in the backend. Enable FastAPI CORS for the frontend dev origin; the frontend reads the backend URL from `VITE_API_BASE_URL`.
