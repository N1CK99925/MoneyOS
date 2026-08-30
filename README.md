# MoneyOS

> AI-powered merchant agent with ACP-style checkout on Razorpay test mode.

Two agents talking over HTTP: a **Merchant Agent** that exposes a catalog and handles checkout, and a **Buyer Agent** that autonomously finds and purchases products using an LLM.

Built for the Razorpay Buildathon — AI Growth & Agentic Commerce track.

---

## Architecture

```
Buyer Agent (LLM)  ──HTTP──>  Merchant Agent (FastAPI)  ──SDK──>  Razorpay Test API
     │                              │
     │  tools:                      │
     │  - search_catalog            │
     │  - create_checkout_session   ▼
     │  - complete_checkout    audit_log (Postgres)
     │  - cancel_checkout
     ▼
 LiteLLM (multi-provider)
```

- **Merchant Agent** — deterministic FastAPI routes. No LLM. Every route writes one audit row. Exposes 5 ACP-style endpoints backed by Razorpay test-mode APIs.
- **Buyer Agent** — LLM-powered via LiteLLM. Reads catalog, picks a product, runs checkout autonomously. Supports fallbacks across providers.
- **Audit Trail** — append-only Postgres table with HMAC-SHA256 signed rows. Tamper-evident.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL (Neon free tier works)
- Razorpay test-mode keys ([dashboard](https://dashboard.razorpay.com))
- An LLM API key (OpenAI, Groq, Gemini, etc.)

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

Edit `.env` with your keys:

```
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
DATABASE_URL=postgresql://...?sslmode=require
LLM_MODEL=openai/gpt-4o-mini
LLM_API_KEY=sk-...
```

### 3. Run

```bash
cd app

# Apply migrations
alembic upgrade head

# Start merchant agent
uvicorn main:app --reload --port 8000

# Start buyer agent (separate terminal)
python -m buyer_agent "buy chicken biriyani under ₹500" -v
```

Frontend: `cd frontend && npm run dev` → open http://localhost:5173

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/catalog` | Merchant product catalog |
| `POST` | `/api/checkout_sessions` | Create checkout session |
| `GET` | `/api/checkout_sessions/{id}` | Get session status |
| `POST` | `/api/checkout_sessions/{id}/complete` | Verify payment & complete |
| `POST` | `/api/checkout_sessions/{id}/cancel` | Cancel session |
| `GET` | `/api/razorpay_key` | Get publishable key (for frontend) |
| `POST` | `/webhooks/razorpay` | Razorpay webhook receiver |
| `GET` | `/api/audit` | View audit trail |
| `GET` | `/health` | Health check |

---

## Buyer Agent Usage

```bash
# Basic usage
python -m buyer_agent "buy chicken biriyani under ₹500"

# Verbose (shows tool calls)
python -m buyer_agent "buy the cheapest item on the menu" -v

# Override model
python -m buyer_agent "buy butter chicken" --model groq/llama-3.3-70b-versatile
```

The agent will autonomously:
1. Search the catalog
2. Pick the best match
3. Create a checkout session
4. Complete payment
5. Report what it bought

---

## Testing

```bash
cd app
pytest tests/ -v
```

---

## What Broke (Honest Writeup)

1. **Catalog mismatch** — started with generic grocery items (almond butter, sourdough). Replaced with food-court-style items (biriyani, dosa, thali) to match the brief. High visual impact, should have done this first.

2. **Checkout 404** — the checkout router was missing `prefix="/api"` while the catalog router had it. Frontend called `/api/checkout_sessions` but the route was `/checkout_sessions`. Fixed by adding the prefix.

3. **Audit timestamp overflow** — `VARCHAR(30)` was too short for ISO timestamps with timezone (`35 chars`). Fixed to `VARCHAR(35)` via Alembic migration.

4. **Alembic migration loop** — ran Alembic programmatically in the FastAPI lifespan, which blocked the async event loop and caused infinite reloads. Reverted to `init_db()` for startup, kept Alembic for schema changes only.

5. **No buyer agent** — the entire `buyer_agent/` directory was stubs. Built an LLM tool-calling agent using LiteLLM with multi-provider fallbacks.

6. **No failure handling** — the `complete` endpoint only handled `paid` and `not-yet-paid`. Added explicit handling for `failed`, `cancelled`, and `expired` order statuses with structured error responses and audit rows.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL (Neon) |
| Payments | Razorpay test mode (official Python SDK) |
| Buyer Agent | LiteLLM (multi-provider), tool-calling loop |
| Frontend | React 19, Vite, TypeScript |
| Audit | Append-only Postgres, HMAC-SHA256 signed rows |

---

## License

MIT
