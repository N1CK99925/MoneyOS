# REMAINING WORK — MoneyOS

**Version:** 0.1.0  
**Status:** Phase 1 Complete — Core build functional  
**Target:** Razorpay Buildathon — AI Growth & Agentic Commerce track

---

## ⚠️ Current State Summary

The core MoneyOS platform is functionally complete for a Phase 1 demo:

- **Merchant agent** (FastAPI) — 5 ACP-style endpoints, catalog, checkout, webhooks, audit
- **Buyer agent** (LiteLLM) — full tool-calling loop with multi-provider fallbacks
- **Audit trail** — append-only Postgres with HMAC-SHA256 signed rows
- **Frontend** — React + Vite, Agent/Catalog/Home pages with UI

However, several Phase 2/3 / stretch items remain before the build is "complete" per the roadmap.

---

## 📦 What's Done (Reference)

| Decision | Location | Callout |
|---|---|---|
| Merchant fixture (food-court catalog) | `app/data/catalog.json` | ✅ 10 items, INR, priced in paise |
| Buyer agent core (Phase 4) | `app/buyer_agent/core/agent.py` | ✅ LLM tool-calling, 5 tools, CLI entry |
| Checkout flow (create/get/complete/cancel) | `app/service/api/checkout.py` | ✅ Razorpay SDK wrappers, audit rows |
| Webhook receiver (HMAC-SHA256) | `app/service/api/webhooks.py` | ✅ Signature verification, append-only log |
| Audit schema + signed hashes | `app/service/db/audit_writer.py` | ✅ SHA256 hex, tamper evidence |
| PostgreSQL models + init | `app/service/db/` | ✅ SQLAlchemy 2.x, Alembic migrations |
| Frontend UI | `frontend/src/` | ✅ Agent, Catalog, Home, Layout, Navbar, Footer |
| Locked Decisions | `LOCKED_DECISIONS.md` | ✅ Phase 0 decisions frozen |
| Roadmap | `ROADMAP.md` (refer to LOCKED_DECISIONS) | ✅ Phase 0 → Phase 4 mapped |

---

## 🛠 What's Left

### 1. **Local Webhook Testing** (HIGH priority)
- **Problem:** Razorpay webhooks require a public HTTPS URL. Localhost won't receive POSTs from Razorpay.
- **Decision (per LOCKED_DECISIONS §3):** Budget ngrok or similar for local testing in Phase 2, not the night before demo.
- **Action:** Set up ngrok tunnel to `localhost:8000/webhooks/razorpay` and test with Razorpay test-mode webhook events.
- **Verification:** Send a `payment.captured` event from Razorpay and verify audit row appears in Postgres.

### 2. **Polling Fallback for Payment Status** (MEDIUM priority)
- **Problem:** `complete_checkout` only handles webhook path. If webhook fails or is delayed, no fallback.
- **Decision (per LOCKED_DECISIONS §3):** Issue #6 — polling `GET /payments/:id` as same-day swap. Rest of flow doesn't change.
- **Action:** Add polling helper in `app/razorpay_client/` that queries Razorpay order status when webhook hasn't arrived yet. Integrate into `complete_checkout` as fallback after a timeout.
- **Verification:** Mock a delayed webhook scenario and verify polling recovers the payment status.

### 3. **Stretch Phase 4B — Web Search + Scoring Buyer Agent** (LOW — defer unless time permits)
- **Problem:** Catalog is fixture data; web search results won't map cleanly to specific SKUs.
- **Decisions still open (per LOCKED_DECISIONS §2):**
  - **Search method:** Which API? Brave Search, SerpAPI, Tavily, or LLM native web search?
  - **Scoring metric:** Must be explicit (e.g. "highest rating with ≥20 reviews") — LLM shouldn't invent criteria live.
- **Action:** If pursuing, decide search API + scoring metric first. If deferring, document as "Phase 4B — optional, after core is done" per roadmap.
- **Verification:** N/A — this is a design decision, not code.

### 4. **End-to-End LLM Agent Test** (MEDIUM priority)
- **Problem:** Buyer agent works with mock/test data but hasn't been run against a real LLM with API keys.
- **Action:** Configure `.env` with real LLM API key (OpenAI/Groq/Gemini) and Razorpay test keys. Run:
  ```bash
  python -m buyer_agent "buy chicken biriyani under ₹500" -v
  ```
- **Verification:** Agent autonomously searches catalog, creates checkout, completes payment, and reports result.

### 5. **Vercel Deployment Checklist** (LOW — for deployed demo, not local)
- **Problem:** Serverless functions have no persistent filesystem; Postgres chosen for Vercel compatibility.
- **Action:** If deploying, verify:
  - `vercel.json` routes correctly
  - DATABASE_URL points to managed Postgres (Neon/Supabase/Vercel Postgres)
  - LLM_API_KEY is set as environment variable in Vercel dashboard
  - Webhook URL is the Vercel deployment URL (not localhost)
- **Verification:** Deploy and verify webhook receives `payment.captured` events.

---

## 📊 Priority Matrix

| | **Now (Phase 1 demo)** | **Next (Phase 2+3)** | **Stretch (4B)** |
|---|---|---|---|
| Webhook local testing | ✅ Essential | ngrok setup | — |
| Polling fallback | ✅ Recommended | Integrate in checkout | — |
| E2E LLM test | ✅ If keys available | Configure .env | — |
| Search + scoring | — | — | Decision required |
| Vercel deployment | — | — | Optional demo |

---

## ✅ Acceptance Criteria for "Complete"

1. **Local demo works end-to-end:**
   - `uvicorn main:app --reload --port 8000` starts the merchant agent
   - `python -m buyer_agent "buy chicken biriyani under ₹500" -v` runs the buyer agent
   - Agent searches catalog → creates checkout → completes payment → reports result
   - Audit rows appear in Postgres with valid signed hashes

2. **Webhook testable locally:**
   - Ngrok tunnel forwards Razorpay webhook POSTs to `localhost:8000/webhooks/razorpay`
   - Verified: audit log entry created with `actor: "razorpay_webhook"`

3. **Polling fallback functional:**
   - When webhook hasn't arrived within N seconds, `complete_checkout` polls Razorpay order status
   - Returns `status: "completed"` once Razorpay reports `paid`

4. **Stretch decision documented:**
   - If 4B is pursued: search API chosen + scoring metric written
   - If deferred: noted in README as "Phase 4B — optional, after core is done"

---

## 📁 Related Files

| File | Purpose |
|---|---|
| `LOCKED_DECISIONS.md` | Phase 0 decisions — do not change without re-evaluating roadmap |
| `ROADMAP.md` | High-level phase mapping (see LOCKED_DECISIONS for details) |
| `app/buyer_agent/stretch/` | Empty — correctly deferred per roadmap |
| `app/service/api/checkout.py` | Checkout endpoints — add polling fallback here |
| `app/service/api/webhooks.py` | Webhook receiver — already has HMAC verification |
| `frontend/src/lib/api.ts` | Frontend API calls — may need polling status check |
| `.env.example` | Add ngrok URL, API keys for local testing |

---

## 🛤 Suggested Execution Order

1. **This week:** Set up ngrok, test webhooks locally → verify audit logging
2. **This week:** Add polling fallback to `complete_checkout` → mock delayed webhook scenario
3. **If time permits:** Configure `.env` with API keys, run E2E buyer agent test
4. **If time permits:** Decide on Phase 4B search API + scoring metric (or document defer)
5. **Deployment optional:** Vercel Postgres setup + environment variables → deploy + verify

---

*This spec is derived from the MoneyOS codebase, LOCKED_DECISIONS.md, and ROADMAP.md. All decisions referenced are "locked" per Phase 0 — any changes require re-evaluating the roadmap tradeoffs.*