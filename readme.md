# medias — Conversational Ordering Assistant

**A chat assistant embedded in the Schaeffler B2B web shop that lets industrial customers place bearing/component orders by typing, while a live side panel renders the quote, cart, and checkout as structured UI.**

- **Status:** Built and running (backend + frontend).
- **Stack:** Backend — Python · FastAPI · Anthropic (Claude). Frontend — React · Vite · TypeScript · Tailwind. Two separate repos talking only over an HTTP/SSE API.
- **Audience for this doc:** product, engineering, and client stakeholders. It describes *what the system does and how it is built today* — read top-to-bottom for the full picture, or jump to a section.

---

## Table of contents
1. [What this product is (and isn't)](#1-what-this-product-is-and-isnt)
2. [How it works — the guided journey](#2-how-it-works--the-guided-journey)
3. [Feature catalogue](#3-feature-catalogue)
4. [The conversation engine](#4-the-conversation-engine)
5. [Domain data — the catalog](#5-domain-data--the-catalog)
6. [Workflow state & sessions](#6-workflow-state--sessions)
7. [Backend architecture](#7-backend-architecture)
8. [UI contract — the generative side panel](#8-ui-contract--the-generative-side-panel)
9. [API reference](#9-api-reference)
10. [Frontend architecture](#10-frontend-architecture)
11. [Design decisions](#11-design-decisions)
12. [Non-functional requirements](#12-non-functional-requirements)
13. [Tech stack & project layout](#13-tech-stack--project-layout)
14. [How to run & test](#14-how-to-run--test)
15. [Not built yet — stubs & roadmap pointers](#15-not-built-yet--stubs--roadmap-pointers)
16. [Glossary](#16-glossary)

---

## 1. What this product is (and isn't)

`medias` is **not a Q&A chatbot.** It is a **tool-using assistant that drives a generative UI through a guided, transactional workflow.** The customer chats on the left; the assistant renders structured widgets (mapping table, quote card, cart, checkout form, confirmation) on the right and walks them through placing an order.

The guiding principle that everything else follows from:

> **The assistant phrases; the system decides and computes.** Prices, quote IDs, order numbers, SKUs, mappings, and cart contents are produced by deterministic backend services. The language model only routes the conversation and writes the natural-language replies — grounded on facts the backend hands it. It never invents a number or claims an action the backend didn't perform.

### In scope (built today)
- The full **ordering flow**: type products → map to Schaeffler SKUs → quote → cart → checkout → order confirmed.
- **Product discovery**: look up a product's details; for a competitor designation, surface the Schaeffler equivalent first.
- **Conversational cart management**: add to cart with duplicate-confirmation, change quantities in natural language, add more items to an in-progress order.
- A **swap seam**: every external dependency (catalog, pricing, quote, cart, order) sits behind an interface with a mock implementation, so real ERP/PIM/SAP services drop in later without touching orchestration.

### Not in scope yet (visible but stubbed — see §15)
- Excel/file **upload parsing** (the upload widget is shown but disabled).
- **Certificates**, **Support**, **Order status**, **Price & Availability** landing intents (each returns a "coming soon" message).
- Voice/mic input, real authentication, real ERP integration, a persistent database, multi-agent orchestration.

---

## 2. How it works — the guided journey

A conversation moves through a small **state machine**. Each step knows which actions make sense, so the assistant can guide the user and ignore out-of-order requests gracefully.

```
greeting
   │  "I want to buy products"
   ▼
awaiting_products
   │  user types a product list  (e.g. "6312-2RS1/C3 x 10 | 6308-2RS, 5 | ABC-123-XYZ")
   ▼
awaiting_mapping_review        → side panel: MappingTable (Accept all / Decline all)
   │  "Accept all and request a quote"
   ▼
quote_ready                    → side panel: QuoteCard (id, Released badge, total, valid-until, Download / Proceed)
   │  "Proceed to checkout"
   ▼
cart_review                    → side panel: Cart (editable quantities, line totals, running total)
   │  "Proceed to checkout"
   ▼
checkout                       → side panel: CheckoutForm (PO number*, order type, comment)
   │  "Place order"
   ▼
confirmed                      → side panel: Confirmation (order id, email/tracking note)
```

**Worked example (the canonical demo):**
1. User types three lines with quantities 10, 5, 1.
2. Mapping table shows **2 mapped** to Schaeffler SKUs + **1 no-equivalent** (excluded from the quote).
3. Accept → quote with **2 line items** (HC6312 ×10, HC6308 ×5), totals from tier-1 prices, valid for 60 days.
4. Proceed → cart with the same 2 items.
5. Checkout with a PO number → order **confirmed** with an `ORD-` id.

**Branches off the happy path** (any time, see §3): asking about a single product opens the product-details / equivalent flow; typing a quantity phrase like "make it 20" edits the cart; starting over after an order resets cleanly.

---

## 3. Feature catalogue

### 3.1 Ordering core
| Capability | Behaviour |
|---|---|
| **Typed product entry** | Free, multi-line list. Tolerant parser extracts `(designation, quantity)` per line. Separators: `x`, `*`, `,`, `:`, whitespace, or `qty`/`quantity`. Quantity defaults to 1; must be a positive integer or it's flagged. |
| **SKU mapping** | Each designation resolved through a strict cascade (§7.3): exact Schaeffler SKU → cross-reference → fuzzy → no-equivalent. |
| **Mapping review** | MappingTable shows each row's status (`matched` / `mapped` / `no_equivalent`) with **Accept all** / **Decline all**. No-equivalent rows are excluded from the quote. |
| **Quote** | Deterministic id (counter from 12345), `Released` status, per-line tier pricing, total, `valid_until` = today + 60 days. Downloadable as a one-page PDF. |
| **Cart** | Seeded from the accepted quote. Editable integer quantities; line total = unit_price(qty) × qty; re-prices on quantity change; shows item count + running total. |
| **Checkout** | Form with **PO number** (required, ≤35 chars), **order type** (Standard / Express / Consignment), **comment** (optional, ≤512 chars), plus Shipment & Payment sections. PO number is enforced. |
| **Order** | Deterministic `ORD-` id, status `confirmed`, confirmation card with email/tracking note. |

### 3.2 Product discovery
| Capability | Behaviour |
|---|---|
| **Product details** | Asking about a product (e.g. "show me details for 6204-C-C3") renders a **ProductDetails** card: description, category, stock + lead time, full attribute table (bore, OD, width, weight, load rating, sealing, clearance, max speed), and price tiers. |
| **Schaeffler vs. equivalent** | If the typed code **is** a Schaeffler SKU → details shown directly. If it's a **competitor designation** that maps to a Schaeffler equivalent → an **EquivalentPrompt** names the equivalent and asks whether to show its details first (then the normal details + add-to-cart flow). If there's **no equivalent** → a clear "couldn't find that product" message. |
| **Bare code = look-up, not silent add** | While a cart/quote exists, typing a *bare* product code (no quantity) opens the look-up flow above rather than silently adding it. A code *with* a quantity (`6204-C-C3 x 2`) or a multi-line list is treated as an explicit add. |

### 3.3 Cart management (conversational)
| Capability | Behaviour |
|---|---|
| **Add to cart** | From a ProductDetails card. If the item is **already in the cart**, an **AlreadyInCart** prompt says so (with the current quantity) and asks whether to add again and how many — nothing is added until confirmed. |
| **Change quantity in natural language** | In a cart step, phrases like "make it 20", "20 units", "set quantity to 20", "add 5 more" actually update the cart. "add/more" adds to the current quantity; otherwise the quantity is **set**. Single-item carts resolve automatically; multi-item carts ask which product. |
| **Add to an in-progress order** | Typing a product list (with quantities) while a quote/cart exists adds those items to the cart. |
| **Edit controls** | The Cart widget also offers per-line +/- and Remove. |
| **Order recap / start over** | After confirmation, "view order details" recaps the order; "place another order" / "start over" resets state and empties the cart. |

### 3.4 Stubbed / disabled (visible in the UI)
Bulk **Upload** (widget shown, disabled), **Certificates**, **Support**, **Order status**, **Price & Availability** (each returns a "coming soon" StubMessage), and **mic / attach** icons (decorative). See §15.

---

## 4. The conversation engine

The language model sits behind one interface, `LLMClient`, with two deliberately separated jobs:

1. **`decide(message, step) → Intent` — routing.** This is **rule-based and shared by both clients**, so the chip/button flow is always reliable and deterministic. It maps a user message (free text or a widget action) to one of the intents below, using the current workflow step for context.
2. **`generate_reply(...) → text` — phrasing.** This produces the assistant's conversational reply from **grounded FACTS** the orchestrator passes for the turn.

Two implementations:
- **`MockLLMClient`** — rule-based routing + canned, fact-grounded replies. Runs with **no API key and no network**, so the whole journey works offline and in tests.
- **`RealLLMClient`** — same rule-based routing; phrases replies with **Claude** (Anthropic SDK). It receives the recent conversation history (sliding window) and the turn's facts, and falls back to the canned text on any API error. Default model `claude-haiku-4-5-20251001`, overridable via `ANTHROPIC_MODEL`.

The orchestrator picks `RealLLMClient` when `ANTHROPIC_API_KEY` is set, otherwise `MockLLMClient`.

**Grounding guardrail (in the system prompt):** the model must never invent prices, totals, quote IDs, order numbers, dates, SKUs, or mappings — only reference values present in FACTS — and must never claim it changed a quantity, added/removed an item, created a quote, or placed an order unless that turn's FACTS show it. If it can't do what's asked, it says so plainly instead of pretending.

### Intents

| Intent | Triggered by | Outcome |
|---|---|---|
| `BUY_PRODUCTS` | "I want to buy products", restart phrases | Reset order, prompt for product list |
| `SUBMIT_PRODUCTS` | a typed product list / code+qty | Parse → map → MappingTable (or add to existing cart) |
| `REQUEST_QUOTE` | "Accept all and request a quote" | Create quote → QuoteCard |
| `DECLINE_MAPPINGS` | "Decline all" | Clear mappings, re-prompt |
| `PROCEED` | "Proceed to checkout" | quote→cart, or cart→checkout |
| `PLACE_ORDER` | "Place order" | Create order → Confirmation |
| `PRODUCT_DETAILS` | "details/spec/show me … <code>", or a bare code in a cart step | ProductDetails / EquivalentPrompt / not-found |
| `ADD_TO_CART` | ProductDetails "Add to cart" | Add, or AlreadyInCart prompt if a duplicate |
| `CHANGE_QTY` | quantity phrases in a cart step ("make it 20", "add 5 more") | Set/add quantity on a cart line |
| `UPDATE_CART` / `REMOVE_CART` / `SHOW_CART` | Cart widget +/- / Remove / cart icon | Deterministic cart edit/view (no LLM call) |
| `ORDER_DETAILS` | "view order details" (post-order) | Recap the confirmed order |
| `STUB_*` | Certificates / Support / Order / Price & Availability | "Coming soon" StubMessage |
| `UNKNOWN` | anything else | Brief reply that gently steers back to ordering |

---

## 5. Domain data — the catalog

The catalog ships as a JSON file (`data/catalog.json`) loaded behind `CatalogService`. **18 entries across 4 categories** (Rolling, Cylindrical Roller, Spherical Roller, Tapered Roller bearings). Each entry:

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
  "cross_references": ["6312-2RS1/C3", "6312 2RS1 C3"],
  "attributes": {
    "bore_diameter_mm": 60, "outside_diameter_mm": 130, "width_mm": 31,
    "weight_kg": 1.71, "dynamic_load_rating_kN": 81.9,
    "sealing": "2HRS (contact seals)", "radial_clearance": "C3", "max_speed_rpm": 4800
  }
}
```

Notes:
- **Cross-references** are competitor/legacy designations that map to the Schaeffler SKU. On load, the service builds a **reverse index** (normalized cross-reference → SKU) plus a SKU index and a fuzzy-candidate list.
- **Price tiers** give quantity-break pricing; the last tier's `max_qty` is `null` (open-ended).
- **Availability** includes `in_stock` and `lead_time_days`; a few entries are intentionally out of stock with long lead times (useful for demos).
- **Attributes** are rich engineering specs, surfaced in ProductDetails.

Representative entries (full list in the file): `HC6312-C-2HRS-L207-C3` (xref `6312-2RS1/C3`), `HC6308-C-2HRS-L207` (xref `6308-2RS`), the `6204-C-*` variant family, `NU2210-E-XL`, `22210-E1-XL` (out of stock), `32011-X`.

> Customer-specific price tiers live in the catalog for V1 and move behind `PricingService` when real pricing is integrated.

---

## 6. Workflow state & sessions

Server-side session state is keyed by `conversation_id` and tracks: current **step**, parsed items, mapping results, active quote id, cart (per conversation), order info, order id, and a bounded chat **transcript** (sliding window for LLM memory; capped to keep memory flat).

State lives behind `SessionStore` (interface). V1 ships `InMemorySessionStore` — a single shared orchestrator keeps sessions in memory across requests. Swappable for Redis/Postgres later.

> **Demo caveat:** because sessions are in-memory, a server restart or a fresh browser session starts over. (Persistence is a roadmap item, §15.)

---

## 7. Backend architecture

```
HTTP/SSE (FastAPI)  →  Orchestrator.run_turn()  →  LLMClient (route + phrase)
                                              └→  Services behind interfaces
                                                  (Catalog, Pricing, Quote, Cart, Order)
```

### 7.1 Orchestrator — `app/agent/orchestrator.py`
The heart of the system, and **free of any FastAPI imports** so it can become a single LangGraph node later. `run_turn(conversation_id, message, payload) → TurnResult` does, per turn:
1. Load/create session.
2. `llm.decide()` → intent.
3. Dispatch to the matching handler, which calls the deterministic services and builds the UI payloads + grounded facts.
4. `llm.generate_reply()` phrases the text from those facts.
5. Append the exchange to the transcript (UI-control intents are kept out of it) and save.

A `TurnResult` is `{ text, ui: [payloads], step }`.

### 7.2 Services — the swap seam (`app/services/`)
Each is an abstract base (`interfaces.py`) with a `Mock*` implementation (`mock.py`). The orchestrator depends only on the interfaces.

| Interface | Key methods | V1 mock behaviour | Future real impl |
|---|---|---|---|
| `CatalogService` | `entries`, `sku_index`, `xref_index`, `fuzzy_candidates`, `get(sku)` | Load + index `catalog.json` | Product master / PIM |
| `PricingService` | `unit_price(sku, qty)` | Tier lookup from the catalog | Customer-specific pricing API |
| `QuoteService` | `create_quote(lines)`, `get_quote(id)` | Counter id, total, 60-day validity, in-memory store | ERP quote API |
| `CartService` | `add_to_cart`, `get_cart`, `update_cart_item`, `remove_cart_item`, `clear_cart` | In-memory cart per conversation; re-prices on read | Cart service |
| `OrderService` | `create_order(cart, info)` | Confirmed `ORD-` id (requires PO number) | ERP / SAP order API |

### 7.3 Mapping engine — `app/mapping.py`
For each parsed item, resolve to a Schaeffler SKU:
1. **Exact (normalized) match** on `schaeffler_sku` → `matched`, confidence 1.0.
2. **Exact (normalized) match** on a cross-reference → `mapped`, confidence 1.0.
3. **Fuzzy match** ≥ threshold (default **0.88**) over all SKUs + cross-refs → `mapped`, confidence = score.
4. Otherwise → `no_equivalent`, confidence 0.0.

Normalization = uppercase + strip spaces/`-`/`/`. Fuzzy is a **fallback only** (never overrides an exact hit). Uses `rapidfuzz` when installed, with a stdlib `difflib` fallback so mapping runs with zero installs.

### 7.4 Parsing — `app/parsing.py`
`parse_typed_products(text)` → `[ParsedItem]` (tolerant per-line parsing, see §3.1). Helpers: `looks_like_products`, `first_product_token`, and `extract_quantity` (pulls a number out of free text, stripping the product code first so a SKU's own digits aren't misread).

### 7.5 Quote PDF — `app/quote_pdf.py`
`render_quote_pdf(quote)` returns a one-page PDF (`reportlab` when installed, with a pure-stdlib minimal-PDF fallback). Served by `GET /quotes/{id}/pdf`.

### 7.6 Other modules
`models.py` (domain dataclasses + the `WorkflowStep` / `MappingStatus` enums), `tools.py` (builders that turn domain objects into the §8 UI payloads; money formatted de-DE here at the edge), `formatting.py` (`format_eur`), `session.py` (§6).

---

## 8. UI contract — the generative side panel

Every assistant turn returns text plus zero or more UI payloads. The frontend stays "dumb": it maps `component` → React widget via a registry. Payloads are JSON-safe (Decimals as strings, dates ISO, money pre-formatted de-DE).

```json
{ "component": "MappingTable", "data": { "rows": [ ... ], "actions": ["accept_all", "decline_all"] } }
```

**Components (11):**

| Component | Purpose |
|---|---|
| `UploadWidget` | Bulk-upload affordance — **rendered disabled** (D1) |
| `TypePrompt` | Prompts the user to type their product list |
| `MappingTable` | Per-row mapping result + Accept all / Decline all |
| `QuoteCard` | Quote id + `Released` badge, lines, total, valid-until, Download / Proceed |
| `Cart` | Line items, editable qty (+/- / Remove), totals, Proceed |
| `CheckoutForm` | PO number, order type, comment, sections; Place order |
| `Confirmation` | Order id, status, email/tracking note |
| `ProductDetails` | Description, stock/lead time, attributes, price tiers, Add to cart |
| `EquivalentPrompt` | "Not a Schaeffler designation → here's the equivalent; see details?" |
| `AlreadyInCart` | "Already in cart (qty N) — add again? choose a quantity" |
| `StubMessage` | "Coming soon" for the four stubbed intents |

---

## 9. API reference

The backend is a thin HTTP/SSE transport over the orchestrator — no business logic lives here.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/conversations` | Create a session → `{ "conversation_id": "..." }` |
| `POST` | `/conversations/{id}/messages` | Send a user message; **SSE stream** of the assistant turn. Body: `{ "message": string, "payload"?: object }`. |
| `GET` | `/conversations/{id}/state` | Current workflow state (debugging) |
| `GET` | `/quotes/{quote_id}/pdf` | Download the quote PDF (`application/pdf`) |

**SSE events** (each line is `data: {json}`):
- `{ "type": "text", "text": "..." }` — the assistant's reply text.
- `{ "type": "ui", "payload": { "component": "...", "data": {...} } }` — zero or more, the side-panel widgets.
- `{ "type": "done", "step": "cart_review" }` — end of turn + the new workflow step.

`payload` on a message carries widget action data (e.g. `{ "sku": "...", "qty": 3, "confirm_add": true }`). **CORS** is enabled for the React dev origin (default `http://localhost:5173` and `:3000`; override with `CORS_ORIGINS`). The backend loads `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` from a root `.env`.

---

## 10. Frontend architecture

A two-pane layout — **chat on the left, dynamic side panel on the right** — wrapped in the storyboard shell.

- **`src/api/`** — `client.ts` (`createConversation`, `quotePdfUrl`) and `sse.ts` (POSTs a message and parses the SSE stream; `EventSource` can't POST, so it reads the response body).
- **`src/types/contract.ts`** — TypeScript mirror of the §8 payloads.
- **`src/shell/`** — chrome: `TopBar` (green bar, robot icon, close), `SubHeader` (hamburger + new-chat + SCHAEFFLER wordmark + cart badge), `Landing` (medias title, search input, **five intent cards**), `ChatInput` (text + disabled mic/attach + send), `icons.tsx`.
- **`src/components/`** — one widget per UI component + `registry.tsx` (component name → widget). Unknown components render a graceful placeholder.
- **`src/theme/tokens.ts`**, **Tailwind** — Schaeffler green (`#00893D` family) on header/chips/primary buttons; white panels; red outline for destructive actions.
- **`App.tsx`** — owns the conversation: streams each turn, accumulates text into the chat, renders UI payloads in the panel, tracks the cart badge and step-based quick-reply chips.

**Landing intent cards:** Certificates · **Bulk Upload** (the live ordering entry — posts "I want to buy products") · Support · Order · Price & Availability.

---

## 11. Design decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Upload widget renders but is disabled.** Typed entry is the live input path; activating upload affordances surfaces the typed-entry prompt. | Storyboard-faithful without building file parsing yet. |
| D2 | **"Bulk Upload" landing card** posts `"I want to buy products"`, then shows the disabled upload widget + typed prompt. | Matches the storyboard entry point. |
| D3 | **QuoteCard shows a status badge** (`Released`). | Matches the storyboard quote view. |
| D4 | **Full chat shell chrome** (green top bar, sub-header with SCHAEFFLER logo, input row). **Mic & attach are decorative/disabled.** | Storyboard fidelity; voice/upload out of scope. |
| D5 | **Cart = accepted quote's line items.** | Internal consistency through the flow. |
| D6 | **All money displayed de-DE** (`€ 1.234,56`); handled as `Decimal`, formatted only at the edge. | Locale correctness. |
| D7 | **Frontend and backend are separate repos** sharing only the §9 API + §8 payload contract. No shared code; backend has zero UI logic, frontend zero business logic. | Clean modularity; either side swappable. |
| D8 | **LLM split into rule-based routing + grounded phrasing** (not a free tool-calling loop). The model never performs actions or invents data; the backend is the source of truth. | Reliability and trust — deterministic flow, no hallucinated prices/orders. |

---

## 12. Non-functional requirements

- **Runs offline for dev/tests:** core logic (parser, mapping, services, orchestrator + MockLLM) works on **stdlib alone, no network** — `rapidfuzz` optional (difflib fallback), API tests skip when FastAPI/httpx aren't installed.
- **Money:** `Decimal` throughout; displayed `€ 1.234,56` (de-DE) at the edge only.
- **Determinism:** mock ids are counter-based (quotes from 12345, orders from ORD-100001) so tests are stable.
- **Graceful errors:** unparseable line, empty list, all-no-equivalent, invalid quantity, unknown SKU, missing PO number, transient LLM API error (falls back to canned text).
- **Transport-agnostic core:** the orchestrator has no FastAPI imports (LangGraph-ready).

---

## 13. Tech stack & project layout

**Backend** — Python 3.12+ (developed/running on 3.14) · FastAPI · Pydantic · Anthropic SDK · rapidfuzz · reportlab · pytest.
**Frontend** — React 18 · Vite 5 · TypeScript 5 · Tailwind 3.

```
schaeffler-poc/
├── PRD.md                              # this document
├── schaeffler-medias-backend/          # Python · FastAPI
│   ├── README.md  requirements.txt  pyproject.toml  cli.py
│   ├── .env.example                    # ANTHROPIC_API_KEY, ANTHROPIC_MODEL, CORS_ORIGINS
│   ├── data/catalog.json               # 18 entries, 4 categories
│   ├── app/
│   │   ├── main.py                     # FastAPI app + SSE endpoints + CORS + .env loader
│   │   ├── models.py                   # domain dataclasses + WorkflowStep / MappingStatus
│   │   ├── parsing.py                  # parse_typed_products, extract_quantity, ...
│   │   ├── mapping.py                  # mapping cascade (rapidfuzz/difflib)
│   │   ├── formatting.py               # format_eur (de-DE)
│   │   ├── session.py                  # SessionStore + InMemorySessionStore
│   │   ├── tools.py                    # UI payload builders (§8)
│   │   ├── quote_pdf.py                # render_quote_pdf (reportlab/stdlib)
│   │   ├── services/
│   │   │   ├── interfaces.py           # Catalog/Pricing/Quote/Cart/Order ABCs
│   │   │   └── mock.py                 # Mock* implementations
│   │   └── agent/
│   │       ├── orchestrator.py         # run_turn() — future LangGraph node
│   │       └── llm.py                  # LLMClient + Mock/Real + intent routing
│   └── tests/                          # parsing, mapping, services, orchestrator, llm, api, quote_pdf
└── schaeffler-medias-frontend/         # React · Vite · TS · Tailwind
    ├── README.md  package.json  vite.config.ts  tailwind.config.ts
    ├── .env.example                    # VITE_API_BASE_URL → backend
    └── src/
        ├── App.tsx  main.tsx  index.css
        ├── api/{client.ts, sse.ts}
        ├── types/contract.ts
        ├── shell/{TopBar, SubHeader, Landing, ChatInput, icons}.tsx
        ├── components/{registry, MappingTable, QuoteCard, Cart, CheckoutForm,
        │               Confirmation, ProductDetails, EquivalentPrompt, AlreadyInCart,
        │               UploadWidget, TypePrompt, StubMessage, widget}.tsx
        └── theme/tokens.ts
```

---

## 14. How to run & test

**Backend**
```bash
cd schaeffler-medias-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # optional: core logic + tests run on stdlib alone
cp .env.example .env                      # add ANTHROPIC_API_KEY to enable Claude replies (else MockLLM)
uvicorn app.main:app --reload            # http://127.0.0.1:8000  (docs at /docs)

python cli.py                            # prints the full journey end-to-end, no server/keys
python -m pytest                         # test suite
```

**Frontend**
```bash
cd schaeffler-medias-frontend
npm install
cp .env.example .env                      # point VITE_API_BASE_URL at the backend (default :8000)
npm run dev                               # http://localhost:5173  (run the backend first)
```

**Definition of done:** `pytest` green and `python cli.py` prints the journey from typed input to "Order confirmed". Without an API key the app still runs fully on the MockLLM (canned, grounded replies).

---

## 15. Not built yet — stubs & roadmap pointers

These are **visible in the UI** so the product looks complete, but route to a "coming soon" message (or render disabled):

- **Bulk upload (Excel/CSV) parsing** — the widget is wired and disabled (D1); the intended path feeds the *same* `map_products` route the typed list uses.
- **Certificates · Support · Order status · Price & Availability** — the four non-ordering landing intents.
- **Mic / voice input** and **attach** — decorative icons (D4).

Strong candidates to build next (high client value, mostly mockable on existing data):
- **Bulk upload parser** (the headline feature). **Price & Availability** and **Order status** lit up from existing catalog/order data. **Smart alternatives** for no-equivalent items and **spec-based product finder** (the rich `attributes` already support this). **Quantity-tier upsell** and **out-of-stock alternatives**. **Session persistence** (Redis/Postgres) so a refresh resumes the order.

Architectural runway (designed for, not built): the orchestrator's `run_turn` is a self-contained, FastAPI-free unit intended to become **one LangGraph node**; a future **supervisor agent** routes to specialist nodes (Ordering, Cross-reference, Support/RAG, Certificates) over the same §7 service interfaces and §8 UI contract.

---

## 16. Glossary

| Term | Meaning |
|---|---|
| **Designation** | The product code a customer types (could be a Schaeffler SKU or a competitor/legacy code). |
| **Cross-reference** | A competitor/legacy designation listed on a catalog entry that maps to its Schaeffler SKU. |
| **`matched` / `mapped` / `no_equivalent`** | Mapping outcomes: exact Schaeffler SKU / resolved via cross-reference or fuzzy / no Schaeffler equivalent. |
| **Workflow step** | The conversation's position in the state machine (§2). |
| **UI payload / component** | A structured side-panel render hint (§8); the frontend maps it to a React widget. |
| **Swap seam** | The service interfaces (§7.2) that let mock backends be replaced by real ERP/PIM/pricing systems without touching orchestration. |
| **Grounding / FACTS** | The deterministic data the backend hands the LLM each turn; the model may only phrase from these, never invent. |
| **SSE** | Server-Sent Events — the one-way stream the backend uses to push each assistant turn to the browser. |
