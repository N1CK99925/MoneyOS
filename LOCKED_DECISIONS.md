# MoneyOS — Locked Decisions (Phase 0)

Companion to PRD, issues draft, and roadmap. These are the Phase 0 decisions from the roadmap, now locked. Update this file if any decision changes mid-build — don't let the roadmap and this file drift apart.

---

## 1. Merchant fixture
**Decision: Food/mart-style items** (biriyani, groceries-adjacent SKUs). Matches the one proven-live India pattern (Zomato/Swiggy/Zepto via Razorpay x NPCI x Claude on UPI Reserve Pay). Catalog will use natural item-level queries ("Chicken Biriyani, ₹350") rather than generic categories, matching how people actually ask for food.

✅ **Implemented.** `app/data/catalog.json` has 10 food-court-style items: Chicken Biriyani, Veg Thali, Masala Dosa, Butter Chicken, Mutton Biryani, etc.

---

## 2. Buyer agent — two-tier decision
- **Core submission (Phase 4, required):** LLM-powered buyer agent using LiteLLM with tool-calling. Reads catalog, picks a product based on a goal prompt, runs full checkout autonomously. Supports multi-provider fallbacks.
- **Stretch (Phase 4B, optional, only after core is done):** web-search-and-score buyer agent — LLM searches the web for reviews on a food item, scores against a defined metric, picks the best match, then hands off to the same checkout flow as the core agent. Two things still unresolved and must be decided before building this phase:
  - **Search method:** use a real search API (Brave Search, SerpAPI, Tavily — check free tiers) or your LLM's native web search tool if the API you're using has one built in. Do not scrape sites directly.
  - **Scoring metric:** not yet defined. Must be written down explicitly before Phase 4B starts (e.g. "highest rating with ≥20 reviews" or similar) — the LLM shouldn't be inventing its own criteria live, you need to be able to explain the system's behavior to a judge.
  - **Known constraint:** your catalog is fake/fixture data, so search results won't map cleanly to real reviews for your specific SKUs. Phase 4B will likely need a workaround (e.g. search for the dish generically, not for your fictional merchant specifically) — solve this when you get there, don't let it block Phase 4.

✅ **Implemented (core).** `app/buyer_agent/core/agent.py` — full LLM tool-calling agent with 5 tools (search_catalog, create_checkout_session, complete_checkout, cancel_checkout, get_checkout_session). CLI entry point at `python -m buyer_agent "goal"`. `app/buyer_agent/stretch/` files are stubs (correctly deferred).

---

## 3. Payment confirmation — webhook
**Decision: webhook**, using Razorpay's built-in webhook support (`payment.captured` event).
**Flagged risk, accepted:** webhook requires your Merchant Agent to be reachable at a public HTTPS URL, since Razorpay's servers need to POST to it — this isn't optional infrastructure, it's how webhooks work regardless of provider. Deploying to Vercel (decision below) resolves this cleanly for the deployed version. For any local-only testing before deployment, you'll need ngrok or similar — budget time to test this specific piece early (Phase 2), not the night before the demo, since it's the one piece of this decision with real live-failure risk if untested.
**Fallback if webhook proves unreliable under time pressure:** polling `GET /payments/:id` is a same-day swap in issue #6 — the rest of the checkout flow doesn't change. Don't be precious about this decision if it's costing you demo-reliability late in the build.

✅ **Implemented.** Full webhook receiver at `POST /webhooks/razorpay` with HMAC-SHA256 signature verification. Audit-logged on receipt.

---

## 4. API design — own ACP-style endpoints
**Decision: build your own** `/checkout_sessions` routes from scratch, backed by Razorpay test-mode APIs. This is the actual deliverable the track asks for. The official Razorpay MCP server (37 tools) remains a stretch-only option — see roadmap stretch phase — not part of the core build.

✅ **Implemented.** Four custom routes in `app/merchant_agent/api/checkout.py`: create, get, complete, cancel. Razorpay consumed via hand-written wrappers in `app/merchant_agent/razorpay_client/`.

---

## 5. Failure case — declined payment
**Decision: declined payment**, triggered via Razorpay's documented test-mode failure card numbers. Most reliably reproducible option for a live demo.

✅ **Implemented.** `complete_checkout` endpoint now handles `failed`, `cancelled`, and `expired` order statuses. Returns structured error (HTTP 402) with `razorpay_status` field. Audit row written with `result: "failure"` and `error_reason`. Buyer agent tools handle HTTP errors gracefully.

---

## 6. Cancel endpoint
**Decision: build it, but lowest priority** — cut first (per roadmap cut list) if time runs short. Not required for the core create→complete flow.

✅ **Implemented.** `POST /checkout_sessions/{session_id}/cancel` in `app/merchant_agent/api/checkout.py`. Sets status to `canceled`, audit-logged.

---

## Infrastructure decisions

### Deployment: Vercel
**Decision: deploy to Vercel.** Reasonable call — removes the "is this reachable" question for webhooks entirely, and the application form doesn't require deployment but it does make your repo more credible ("clone and run" plus a live link beats just the repo).

**Consequence you need to know:** Vercel's serverless functions do not provide a persistent local filesystem the way a traditional server does — each invocation can run in a fresh, ephemeral environment. This directly affects decision below.

✅ **Implemented.** `vercel.json` routes all requests through `app/main.py` via `@vercel/python`.

### Database: Postgres, not SQLite
**Decision: Postgres**, specifically because of the Vercel deployment choice above — not because SQLite is worse in general. SQLite's append-only file approach needs a persistent disk to live on, which Vercel serverless doesn't reliably guarantee across invocations. This isn't "Postgres is better," it's "the deployment target already decided this for you."

**Recommended provider:** a free-tier managed Postgres that plugs into Vercel with minimal setup — Vercel Postgres (native integration), Neon, or Supabase are all reasonable, pick whichever has the smoothest signup. You're mostly swapping a connection string and using an ORM/query layer (SQLAlchemy is fine, or raw `psycopg2`/`asyncpg` if you want to keep it minimal) instead of `sqlite3`. The audit log schema from the PRD (§6) is standard SQL — it works in Postgres with no meaningful changes, just swap `INTEGER PRIMARY KEY` autoincrement syntax for Postgres's `SERIAL`/`BIGSERIAL`.

**If Postgres setup eats too much time:** fall back to SQLite for local development only, and either (a) don't deploy — submit local-run + video, which the form allows, or (b) deploy to a platform with persistent disk (Render, Railway) instead of Vercel. Don't let database setup block your actual build — if you're stuck more than an hour on Postgres config, drop to this fallback and move on.

✅ **Implemented.** `app/merchant_agent/db/connection.py` defaults to PostgreSQL. SQLite used only in test fixtures (`app/tests/conftest.py`).
