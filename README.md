# MoneyOS

> AI-powered merchant service with ACP-style checkout on Razorpay test mode.

MoneyOS lets **AI buyers autonomously discover products, initiate checkout, and pay**, while a deterministic merchant **service** handles the storefront and payment lifecycle, and a human authorizes every capture. Built for the Razorpay Buildathon — AI Growth & Agentic Commerce track.

The architecture separates **one agent from one service**:

- **Merchant Service** (FastAPI) — deterministic. No LLM. Exposes a catalog, handles checkout, enforces spend policy, runs the human-approval gate, and mirrors every money mutation to a tamper-evident audit trail.
- **Buyer Agent** (LLM via LiteLLM) — the only agent. Reads the catalog, picks a product from a natural-language goal, and drives the create → pay → complete loop over HTTP.

Two independent processes talking over HTTP. Either side could be swapped for a real external system without rewriting the other.

---

## Transaction Lifecycle (Gated)

```
Buyer Agent             Merchant Service (FastAPI)          Razorpay Test API
----------------------------------------
search_catalog  ──────>  GET /api/catalog
create_checkout ──────>  POST /api/checkout_sessions        create_order
                         [SPEND POLICY CHECKED — 403 if over cap, no order]
get_payment_link ─────>  /pay/{session_id}                  checkout.js
complete_checkout ────>  POST .../complete                  verify payment
                         status → pending_approval
                         returns approval_url
Human (merchant) opens approval_url
  ────────────────>      POST /api/approval/{token}/approve → capture_payment
                         status → completed                 capture_payment
  ────────────────>      POST /api/approval/{token}/deny   → cancel_order
                         status → denied
Buyer Agent polls status → reports outcome to user
```

Two rules anchor the design:

1. **The buyer agent never captures.** It can only put money on hold and hand back a URL. Only a human can authorize the capture.
2. **Every money mutation writes an audit row** (HMAC-SHA256 signed, append-only).

---

## Architecture

```
Buyer Agent (LLM)  ──HTTP──>  Merchant Service (FastAPI)  ──SDK──>  Razorpay Test API
     │                              │
     │  tools:                      │
     │  - search_catalog            │
     │  - create_checkout_session   ▼
     │  - complete_checkout    audit_log (Postgres, HMAC-signed)
     │  - cancel_checkout
     │  - get_checkout_session
     │  - get_payment_link
     │  - pay_with_test_card
     ▼
 LiteLLM (multi-provider, fallback)
```

- **Merchant Service** — deterministic FastAPI routes, no LLM. Every route writes one audit row. Exposes ACP-style endpoints backed by Razorpay test-mode APIs.
- **Buyer Agent** — LLM-powered via LiteLLM. Tool-calling loop with multi-provider fallbacks and rate-limit handling. Two variants: `core` (catalog + checkout) and `stretch` (adds Tavily web search + deterministic review scoring).
- **Audit Trail** — append-only Postgres table, HMAC-SHA256 signed rows. Tamper-evident.

---

## Repository Layout

```
MoneyOS/
  README.md                 This file
  LOCKED_DECISIONS.md       Phase 0 decisions frozen
  REMAINING_WORK.md         Work tracker
  vercel.json               Vercel routes -> app/main.py (@vercel/python)
  app/
    main.py                 FastAPI app — mounts routers, inits DB, serves frontend/dist
    pyproject.toml          Backend deps + ruff/pytest config
    .env.example            Env template (no real secrets)
    alembic/                Migrations — checkout session, audit ts fix, approval cols, system_settings
    data/catalog.json       Food-court fixture catalog (10 INR items, priced in paise)
    buyer_agent/
      __main__.py / cli.py  CLI: `python -m buyer_agent "goal" [-v] [--model]`
      tools.py              5 ACP tools — search, create, complete, cancel, get
      payment_tools.py      get_payment_link + pay_with_test_card tool defs
      core/agent.py         Core buyer agent — LLM tool-calling loop
      stretch/              Phase 4B — Tavily search + deterministic scoring
    service/                The merchant service
      settings.py           Static pydantic-settings (env / .env)
      runtime_settings.py   Runtime settings — DB-backed (system_settings) with cache
      api/
        agent.py            POST /api/agent/run — SSE stream (core + stretch)
        catalog.py          GET /api/catalog
        checkout.py         create/get/complete/cancel/fail checkout sessions
        checkout_page.py    GET /pay/{session_id} — Razorpay checkout.js page
        approval.py         approval flow — approve/deny/expired, inline HTML pages
        audit.py            GET /api/audit
        settings.py         GET/PUT /api/settings — runtime-configurable values
        webhooks.py         POST /webhooks/razorpay (+ alt paths) — HMAC verified
      db/
        models.py           AuditLog, CheckoutSession, SystemSetting ORM models
        audit_writer.py     Single append-only write path with HMAC signing
      razorpay_client/      Orders, payments, refunds, local payment links, test cards
    tests/                  31 tests — phases 1, checkout flow, gated payments, audit
  frontend/
    src/
      pages/                Home, Catalog, Agent, Audit, Settings
      lib/api.ts            API client + SSE streamAgentRun
      hooks/useGoal.tsx     Goal-building state shared across pages
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL (Neon free tier works)
- Razorpay test-mode keys ([dashboard](https://dashboard.razorpay.com))
- An LLM API key (OpenAI, Groq, Gemini, etc.) for the buyer agent

### 1. Clone and install

```bash
git clone <repo-url> && cd MoneyOS

# Backend
cd app
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Frontend (separate terminal)
cd frontend
npm install
```

### 2. Configure

```bash
cd app
cp .env.example .env
```

Edit `.env` with your keys (template only — no secrets committed):

```
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
DATABASE_URL=postgresql://...?sslmode=require
AUDIT_HMAC_SECRET=change-this-to-a-random-string
LLM_MODEL=openai/gpt-4o-mini
LLM_API_KEY=sk-...
LLM_FALLBACK_MODELS=groq/llama-3.3-70b-versatile,gemini/gemini-2.0-flash
SERVICE_URL=http://localhost:8000
TAVILY_API_KEY=tvly-...   # optional, for stretch agent
```

### 3. Run

```bash
cd app

# Apply migrations
alembic upgrade head

# Start the merchant service (FastAPI)
uvicorn main:app --reload --port 8000

# Run the buyer agent (CLI, separate terminal)
python -m buyer_agent "buy chicken biriyani under ₹500" -v
```

Frontend: `cd frontend && npm run dev` → open http://localhost:5173

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/catalog` | Merchant product catalog |
| `POST` | `/api/checkout_sessions` | Create checkout session (spend policy enforced) |
| `GET` | `/api/checkout_sessions/{id}` | Get session status |
| `POST` | `/api/checkout_sessions/{id}/complete` | Verify payment & start approval hold (`poll=true` fallback) |
| `POST` | `/api/checkout_sessions/{id}/cancel` | Cancel session |
| `POST` | `/api/checkout_sessions/{id}/fail` | Mark session as failed |
| `GET` | `/api/razorpay_key` | Get publishable key (for frontend checkout) |
| `GET` | `/pay/{session_id}` | Razorpay checkout.js page for a session |
| `GET` | `/api/approval/{token}` | Human approval page (Approve/Deny) |
| `POST` | `/api/approval/{token}/approve` | Approve — capture payment |
| `POST` | `/api/approval/{token}/deny` | Deny — cancel order |
| `GET` | `/api/audit` | View audit trail (newest first, `limit` param) |
| `GET` | `/api/settings` | List runtime settings |
| `GET` / `PUT` | `/api/settings/{key}` | Get / update a runtime setting |
| `POST` | `/api/agent/run` | SSE stream for buyer agent (body: goal, stretch, history) |
| `POST` | `/webhooks/razorpay` | Razorpay webhook receiver (HMAC-SHA256) |
| `POST` | `/app/webhooks` | Alt webhook path (Vercel routing) |
| `POST` | `/app/webhooks/razorpay` | Alt webhook path (Vercel routing) |

---

## Buyer Agent Usage

The buyer agent is the **only** LLM in the system.

```bash
# Basic usage (core agent)
python -m buyer_agent "buy chicken biriyani under ₹500"

# Verbose — shows each tool call and result
python -m buyer_agent "buy the cheapest item on the menu" -v

# Override model
python -m buyer_agent "buy butter chicken" --model groq/llama-3.3-70b-versatile
```

The agent autonomously:
1. Searches the catalog
2. Picks the best match
3. Creates a checkout session
4. Gets a payment link or test card
5. Completes the checkout → enters human approval hold
6. Reports what it bought and the approval URL

### Stretch Agent (web search + scoring)

In the frontend, toggle **Research ON** or set `stretch: true` on `POST /api/agent/run`. The stretch agent adds a `search_and_score` tool — it searches Tavily for real reviews and picks the highest-rated item with enough reviews (falling back to cheapest when no review data exists).

---

## Spend Policy & Approval Flow

### Spend Policy (bounded spend)
- Enforced in `create_checkout_session`, **before** creating a Razorpay order.
- Default cap ₹600 (`spend_policy_max_per_transaction_paise` = 60000).
- On violation: `403 policy_violation` + audit row `policy_rejected`, **no order created**.
- Set to `0` to disable.

### Approval Flow (gated capture)
- The buyer agent can only hold money, never capture it. A human must click Approve.
- Token: 32 random bytes, single-use, TTL 5 min (configurable).
- Approve → `capture_payment` → `completed`. Deny → `cancel_order` → `denied`.
- Idempotent, expiry-aware, fully audit-logged.

---

## Audit Trail

Single write path (`write_audit_row`). Every row is HMAC-SHA256 signed and append-only (no UPDATE/DELETE).

| Actor | Actions |
|-------|---------|
| `service` | checkout_session_created, approval_requested, approval_expired, checkout_completed, checkout_failed, checkout_canceled |
| `policy` | policy_rejected |
| `human_approval` | approval_granted, approval_denied |
| `razorpay_webhook` | payment.captured, payment.failed, order.paid, order.failed, etc. |

---

## Runtime Settings

Settings are editable at runtime without redeploying (DB-backed `system_settings` with in-memory cache, falling back to static defaults):

```bash
# List all settings
curl http://localhost:8000/api/settings

# Update the spend policy cap live (e.g. ₹2000)
curl -X PUT http://localhost:8000/api/settings/spend_policy_max_per_transaction_paise \
  -H "Content-Type: application/json" -d '{"value":"200000"}'
```

---

## Catalog

10 food-court items (Indian cuisine), all INR, priced in paise:

| ID | Name | Price |
|----|------|-------|
| item_001 | Chicken Biriyani | ₹350 |
| item_002 | Veg Thali | ₹250 |
| item_003 | Masala Dosa | ₹150 |
| item_004 | Egg Fried Rice | ₹180 |
| item_005 | Paneer Tikka | ₹280 |
| item_006 | Butter Chicken | ₹380 |
| item_007 | Idli Sambar | ₹120 |
| item_008 | Mutton Biryani | ₹450 |
| item_009 | Chai + Samosa | ₹80 |
| item_010 | Gulab Jamun (4 pcs) | ₹100 |

---

## Testing

```bash
cd app
pytest tests/ -v
```

31 tests, all passing:

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_phase1.py` | 6 | Catalog endpoint, audit endpoint |
| `tests/test_checkout_flow.py` | 14 | Create, complete, cancel, fail, not-found |
| `tests/test_gated_payments.py` | 8 | Spend policy (3), approval flow (5) |
| `tests/test_audit_viewer.py` | 3 | Audit viewer |

Razorpay SDK is mocked at the same boundary as production; the DB is a real in-memory SQLite (not mocked).

---

## Deployment (Vercel)

- `vercel.json`: routes all requests through `app/main.py` via `@vercel/python`.
- No persistent filesystem → Postgres (Neon) chosen over SQLite.
- Webhook URL must be the Vercel deployment URL (not localhost).
- Built frontend served from `frontend/dist/` via FastAPI.

**Env variables needed on Vercel:** `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `DATABASE_URL`, `LLM_API_KEY`, `SERVICE_URL` (pointing to the deployment), `TAVILY_API_KEY` (optional).

---

## What Broke (Honest Writeup)

1. **Catalog mismatch** — started with generic grocery items (almond butter, sourdough). Replaced with food-court-style items (biriyani, dosa, thali) to match the brief.

2. **Checkout 404** — the checkout router was missing `prefix="/api"` while the catalog router had it. Fixed by adding the prefix.

3. **Audit timestamp overflow** — `VARCHAR(30)` too short for ISO timestamps with timezone (35 chars). Fixed to `VARCHAR(35)` via Alembic migration.

4. **Alembic migration loop** — ran Alembic programmatically in the FastAPI lifespan, which blocked the async event loop and caused infinite reloads. Reverted to `init_db()` for startup, kept Alembic for schema changes only.

5. **No buyer agent** — the entire `buyer_agent/` directory was stubs. Built an LLM tool-calling agent using LiteLLM with multi-provider fallbacks.

6. **No failure handling** — the `complete` endpoint only handled `paid` and `not-yet-paid`. Added explicit handling for `failed`, `cancelled`, and `expired` order statuses with structured error responses and audit rows.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2.x, Alembic |
| Database | PostgreSQL (Neon free tier; SQLite in tests) |
| Payments | Razorpay test mode (official Python SDK) |
| Buyer Agent | LiteLLM tool-calling loop, multi-provider fallbacks, Tavily search (stretch) |
| Frontend | React 19, Vite 8, TypeScript, Tailwind 4, react-router 7 |
| Audit | Append-only Postgres, HMAC-SHA256 signed rows |
| SSE Streaming | sse-starlette (agent progress events) |

---

## License

MIT
