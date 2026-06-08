# schaeffler-medias-frontend

React frontend for the **medias** conversational ordering assistant (V1). Vite · TypeScript · Tailwind CSS. Separate repo from the backend (PRD D7); the only contract between them is the HTTP/SSE API (PRD §11) and the UI payload contract (PRD §10).

## Architecture

- **`src/api/client.ts`** — `createConversation()`, `quotePdfUrl()`.
- **`src/api/sse.ts`** — `sendMessage()` POSTs a message and parses the SSE stream (`text` / `ui` / `done`) by reading the response body (EventSource can't POST).
- **`src/types/contract.ts`** — TypeScript mirror of the backend §10 payloads.
- **`src/shell/`** — chat chrome (PRD §10.1): `TopBar` (green bar), `SubHeader` (menu + new-chat + SCHAEFFLER logo), `Landing` (medias title, input, 5 intent cards), `ChatInput`. Mic + attach icons are decorative/disabled (PRD D4).
- **`src/components/`** — one widget per UI component + `registry.tsx` (component name → widget). `UploadWidget` renders **disabled** (PRD D1).
- **`src/App.tsx`** — two-pane layout: chat left, dynamic side panel right. Streams each turn, accumulating text into the chat and rendering UI payloads in the panel.

## Setup

```bash
npm install
cp .env.example .env        # point VITE_API_BASE_URL at the backend (default http://localhost:8000)
npm run dev                 # http://localhost:5173
```

Run the backend first (`uvicorn app.main:app --reload` in `schaeffler-medias-backend`); its CORS allows `http://localhost:5173`.

## Scripts

- `npm run dev` — Vite dev server
- `npm run build` — type-check (`tsc -b`) + production build
- `npm run typecheck` — types only
- `npm run preview` — preview the production build
