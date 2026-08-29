# 🗺️ Worksteps: Explainable AI (XAI) Trading Agent

> Follow these steps in order. Each step should be independently completable and testable before moving to the next.

---

## Step 1: Environment & Repository Setup

**Goal:** Get all tooling, credentials, and the repo scaffolded.

- [x] Create a GitHub repository `alpaca-xai-agent`
- [x] Clone it into this project folder
- [x] Set up a Python virtual environment (`venv` or `uv`) for the agent backend
- [x] Initialize a Next.js project in `frontend/` using `npx create-next-app`
- [x] Create `.env.example` with all required keys (no real values) ✅
- [x] Add `.env.local` and `.env` to `.gitignore`
- [ ] Collect all API keys and fill in `.env` (copy from `.env.example`):
  - `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` (paper trading account)
  - `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY`
  - `DEEPSEEK_API_KEY` or `GEMINI_API_KEY`

---

## Step 2: Supabase Database Schema

**Goal:** Build the full relational schema with RLS enabled.

- [ ] Create a new Supabase project
- [ ] Enable the `pgvector` extension in Supabase SQL Editor
- [ ] Run `database/schema.sql` to create all 4 tables:
  - `accounts`, `hypotheses`, `audit_logs`, `post_mortems`
- [ ] Run `database/rls_policies.sql` to apply Row Level Security + create `match_post_mortems()` function
- [ ] Update `database/seed.sql` with your actual `auth.users` UUID and run it
- [ ] Verify schema in Supabase Table Editor

---

## Step 3: Agent Backend — Core Setup & LangGraph Skeleton

**Goal:** Wire up the Python agent project structure and LangGraph state machine scaffold.

- [ ] Install Python dependencies:
  ```
  pip install langgraph langchain langchain-openai langchain-google-genai supabase httpx python-dotenv pydantic apscheduler fastapi uvicorn
  ```
- [ ] Implement `agent/config.py` — loads all env vars
- [ ] Implement `agent/db.py` — Supabase client singleton and CRUD helpers for all 4 tables
- [ ] Implement `agent/llm.py` — LLM client wrapper (DeepSeek or Gemini)
- [ ] Implement `agent/state.py` — LangGraph `AgentState` TypedDict definition
- [ ] Implement `agent/graph.py` — LangGraph graph with 4 node stubs:
  - `formulate_hypothesis` → `execute_order` → `audit_position` → `close_and_post_mortem`
- [ ] Smoke test: instantiate the graph and confirm it compiles without errors

---

## Step 4: Phase 1 — Hypothesis Formulation Node

**Goal:** Implement the Pre-Trade reasoning phase.

- [ ] Implement `agent/tools/alpaca_tools.py`:
  - `get_market_data(symbol, timeframe)` — calls Alpaca API for OHLCV data
- [ ] Implement `agent/nodes/phase1_hypothesis.py`:
  - Fetch OHLCV data for the target symbol
  - Build a structured prompt for the LLM with market data
  - Parse LLM response into a `HypothesisSchema` Pydantic model (thesis, targets, invalidation_triggers)
  - Validate the schema strictly — abort if invalid
  - Persist the validated hypothesis to `hypotheses` table with status `PENDING`
- [ ] Unit test: run with a test symbol (e.g., `AAPL`) and verify a valid JSON hypothesis row is saved to DB

---

## Step 5: Phase 2 — Execution Node

**Goal:** Send a paper trade order to Alpaca and lock the hypothesis.

- [ ] Extend `agent/tools/alpaca_tools.py`:
  - `create_order(symbol, qty, side, order_type)` — places an order via Alpaca API
- [ ] Implement `agent/nodes/phase2_execution.py`:
  - Only runs if Phase 1 hypothesis status is `PENDING` (validated)
  - Call `create_order` with parameters derived from the hypothesis
  - On Alpaca confirmation, extract `alpaca_order_id`
  - Update `hypotheses` row: set `alpaca_order_id` and status → `ACTIVE`
- [ ] Unit test: confirm an order appears in Alpaca paper dashboard and the DB row status is `ACTIVE`

---

## Step 6: Phase 3 — Continuous Audit (Monitoring Loop)

**Goal:** Background worker that audits all ACTIVE positions on a schedule.

- [ ] Extend `agent/tools/alpaca_tools.py`:
  - `get_positions()` — fetches all open positions with unrealized PnL
- [ ] Implement `agent/nodes/phase3_audit.py`:
  - Query `hypotheses` table for all rows with status `ACTIVE`
  - For each: fetch latest market snapshot from Alpaca
  - Build an audit prompt with the original hypothesis + current market state
  - LLM returns verdict: `HOLD` or `CLOSE` with reasoning
  - Persist result to `audit_logs` table
  - If `CLOSE` verdict → transition state to trigger Phase 4
- [ ] Implement `agent/worker.py` — scheduler loop (APScheduler) running Phase 3 every 15 minutes
- [ ] Test: run the worker, verify `audit_logs` rows are created with correct verdicts

---

## Step 7: Phase 4 — Post-Mortem & Vector Memory

**Goal:** Close the position, synthesize learnings, and store embeddings.

- [ ] Extend `agent/tools/alpaca_tools.py`:
  - `close_position(symbol)` — closes an open position
- [ ] Implement `agent/nodes/phase4_postmortem.py`:
  - Call `close_position` on Alpaca
  - Update `hypotheses` status → `CLOSED`
  - Gather: original hypothesis, all audit logs, final PnL from Alpaca
  - LLM synthesizes a post-mortem report (`lesson_learned` text)
  - Embed the `lesson_learned` text using the configured embedding model
  - Store in `post_mortems` table with the `embedding` vector column
- [ ] Implement `agent/memory.py`:
  - `search_similar_post_mortems(query_text, top_k=3)` — calls `match_post_mortems()` RPC in Supabase
- [ ] Integrate memory retrieval into Phase 1: before formulating a hypothesis, retrieve past relevant lessons and inject them into the LLM prompt
- [ ] Test: complete a full cycle, verify the `post_mortems` row with embedding is saved

---

## Step 8: Agent API Layer (FastAPI)

**Goal:** Expose agent actions and data as HTTP endpoints for the frontend.

- [ ] Implement `agent/api/main.py` — FastAPI app entry point with CORS middleware
- [ ] Implement route files in `agent/api/routes/`:
  - `hypotheses.py`:
    - `POST /hypotheses/trigger` — trigger a new hypothesis for a given symbol
    - `GET /hypotheses` — list all hypotheses with status
    - `GET /hypotheses/{id}` — detail + audit log timeline
  - `post_mortems.py`:
    - `GET /post-mortems` — list all post-mortems
  - `portfolio.py`:
    - `GET /portfolio` — proxy Alpaca positions & account balance
  - `worker.py`:
    - `POST /worker/start` & `POST /worker/stop` — control the monitoring loop
- [ ] Test all endpoints with a REST client (Bruno / Postman / curl)

---

## Step 9: Frontend Dashboard (Next.js)

**Goal:** Build the audit trail & portfolio visualization UI.

- [ ] Set up API client in `frontend/src/lib/api.ts`
- [ ] Build pages and components:
  - **`/` (Dashboard):** Portfolio summary (balance, open positions, unrealized PnL)
  - **`/hypotheses`:** Table of all trades with PENDING / ACTIVE / CLOSED status badges
  - **`/hypotheses/[id]`:** Hypothesis JSON viewer + Audit log timeline with HOLD/CLOSE verdicts
  - **`/memory`:** Post-Mortem library — lessons learned with PnL outcomes
  - **Trigger Panel:** Input a symbol → call `POST /hypotheses/trigger`
- [ ] Add real-time polling (every 30s) on the dashboard for live updates
- [ ] Style with a premium dark-mode trading terminal aesthetic

---

## Step 10: Integration Testing & Demo Polish

**Goal:** Ensure the full system works end-to-end and is demo-ready.

- [ ] Run a full end-to-end cycle:
  1. Trigger hypothesis for `AAPL` via UI
  2. Confirm order in Alpaca paper dashboard
  3. Manually trigger an audit cycle via API
  4. Manually close the position and verify post-mortem is saved with embedding
  5. Trigger a second hypothesis — verify memory retrieval context appears in the new hypothesis
- [ ] Verify Supabase RLS policies block unauthorized access (test with a different user / anon key)
- [ ] Write `README.md` with setup instructions, architecture diagram, and screenshots
- [ ] Final cleanup: remove debug logs, add error handling, UI polish
- [ ] Record a 2–3 min demo video

---

## Key Dependencies Reference

| Layer | Package |
|---|---|
| Agent core | `langgraph`, `langchain` |
| LLM | `langchain-openai` or `langchain-google-genai` |
| Database | `supabase` |
| API server | `fastapi`, `uvicorn` |
| Scheduler | `apscheduler` |
| Validation | `pydantic` v2 |
| HTTP | `httpx` |
| Frontend | `next` 14+, `axios` or `ky` |

---

## ⚠️ Important Notes

- **Test Phase 1 → 2 before enabling the Phase 3 scheduler** to avoid runaway API calls.
- Use Alpaca **paper trading** endpoints only (`https://paper-api.alpaca.markets`) during development.
- The `embedding` vector dimension (1536 for OpenAI, 768 for Gemini) **must match** the `vector(N)` column definition in `schema.sql`.
- If you change the embedding dimension, drop and recreate the `post_mortems` table and update the `match_post_mortems()` function signature.
