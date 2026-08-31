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
- [x] Collect all API keys and fill in `.env` (copy from `.env.example`):
  - `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` (paper trading account)
  - `SUPABASE_URL` / `SUPABASE_PUBLISHABLE_KEY` / `SUPABASE_SECRET_KEY`
  - `DEEPSEEK_API_KEY` or `GEMINI_API_KEY`

---

## Step 2: Supabase Database Schema

**Goal:** Build the full relational schema with RLS enabled.

- [x] Create a new Supabase project
- [x] Enable the `pgvector` extension in Supabase SQL Editor
- [x] Run `database/schema.sql` to create all 4 tables:
  - `accounts`, `hypotheses`, `audit_logs`, `post_mortems`
- [x] Run `database/rls_policies.sql` to apply Row Level Security + create `match_post_mortems()` function
- [x] Update `database/seed.sql` with your actual `auth.users` UUID and run it
- [xq] Verify schema in Supabase Table Editor

---

## Step 3: Agent Backend — Core Setup & LangGraph Skeleton

**Goal:** Wire up the Python agent project structure and LangGraph state machine scaffold.

- [x] Install Python dependencies
- [x] Implement `agent/config.py` — loads all env vars
- [x] Implement `agent/db.py` — Supabase client singleton and CRUD helpers for all 4 tables
- [x] Implement `agent/llm.py` — LLM client wrapper (Gemini)
- [x] Implement `agent/state.py` — LangGraph `AgentState` TypedDict definition
- [x] Implement `agent/graph.py` — Two compiled graphs: `trade_graph` (Phase 1→2) and `audit_graph` (Phase 3→4)
- [x] Implement `agent/memory.py` — Vector memory retrieval helper
- [x] Smoke test: both graphs compile without errors ✅

---

## Step 4: Phase 1 — Hypothesis Formulation Node

**Goal:** Implement the Pre-Trade reasoning phase.

- [x] Implement `agent/tools/alpaca_tools.py`:
  - `get_market_data()`, `create_order()`, `get_positions()`, `get_position()`, `close_position()`, `get_account()`
- [x] Implement `agent/nodes/phase1_hypothesis.py`:
  - Retrieves past lessons from vector memory (memory.py)
  - Fetches 30-day OHLCV data from Alpaca
  - Builds structured LLM prompt with market data + memory context
  - LLM responds with `HypothesisSchema` Pydantic model (structured output)
  - Validates schema — sets `error` + `ABORTED` if invalid
  - Persists validated hypothesis to `hypotheses` table with status `PENDING`
- [x] Unit test: fill in `ACCOUNT_ID` in `test_phase1.py` and run it (PASSED ✅)

---

## Step 5: Phase 2 — Execution Node

**Goal:** Send a paper trade order to Alpaca and lock the hypothesis.

- [x] Extend `agent/tools/alpaca_tools.py`:
  - `create_order(symbol, qty, side, order_type)` — places an order via Alpaca API ✅
- [x] Implement `agent/nodes/phase2_execution.py`:
  - Guard: validates status == PENDING before executing
  - Calls `create_order` with params from hypothesis_data
  - Extracts `alpaca_order_id` from Alpaca response
  - Updates hypothesis: status → ACTIVE
- [x] Unit test: order appeared in Alpaca paper dashboard, DB status = ACTIVE ✅

---

## Step 6: Phase 3 — Continuous Audit (Monitoring Loop)

**Goal:** Background worker that audits all ACTIVE positions on a schedule.

- [x] Extend `agent/tools/alpaca_tools.py`:
  - `get_positions()`, `get_position(symbol)` — fetches positions with unrealized PnL ✅
- [x] Implement `agent/nodes/phase3_audit.py`:
  - Fetches hypothesis from DB (targets + triggers)
  - Fetches live position snapshot from Alpaca
  - Fetches recent OHLCV bars for context
  - LLM returns verdict: `HOLD` or `CLOSE`
  - Persists to `audit_logs` table (llm_verdict, reasoning_summary, market_snapshot)
  - Returns `audit_verdict` in state → graph routes to Phase 4 if CLOSE
- [ ] Implement `agent/worker.py` — APScheduler loop running Phase 3 every 15 minutes
- [x] Test: audit_logs row created with verdict CLOSE ✅

---

## Step 7: Phase 4 — Post-Mortem & Vector Memory

**Goal:** Close the position, synthesize learnings, and store embeddings.

- [x] Extend `agent/tools/alpaca_tools.py`:
  - `close_position(symbol)` — closes an open position ✅
- [x] Implement `agent/nodes/phase4_postmortem.py`:
  - Calls `close_position` on Alpaca
  - Updates `hypotheses` status → CLOSED
  - Gathers: original hypothesis + all audit logs + PnL from Alpaca
  - LLM synthesizes `lesson_learned` text
  - Embeds lesson with `gemini-embedding-001` (3072 dims)
  - Stores in `post_mortems` table with embedding vector
- [x] `agent/memory.py` already implemented in Step 3 ✅
- [x] Memory retrieval integrated into Phase 1 (inject past lessons into LLM prompt) ✅
- [x] Test: full cycle complete, post_mortems row with embedding saved ✅

---

## Step 8: Agent API Layer (FastAPI)

**Goal:** Expose agent actions and data as HTTP endpoints for the frontend.

- [x] Implement `agent/api/main.py` — FastAPI app with CORS + lifespan worker ✅
- [x] Routes implemented directly in `main.py`:
  - `POST /trade/start` — Phase 1+2: formulate + execute
  - `GET  /trade/hypotheses` — list all hypotheses
  - `GET  /trade/{id}` — hypothesis detail + audit log timeline
  - `POST /trade/{id}/audit` — manual audit trigger (Phase 3)
  - `GET  /portfolio` — live Alpaca account + positions
  - `GET  /memory` — list all post-mortems
- [x] `agent/worker.py` — APScheduler loop, starts via FastAPI lifespan ✅
- [ ] Test all endpoints with a REST client (Bruno / Postman / curl)

---

## Step 9: Frontend Dashboard (Next.js)

**Goal:** Build the audit trail & portfolio visualization UI.

- [x] Set up API client in `frontend/src/lib/api.ts` ✅
- [x] Build pages and components:
  - **`/` (Dashboard):** Portfolio summary (balance, open positions, unrealized PnL), Trigger Trade Panel ✅
  - **`/hypotheses`:** Table of all trades with PENDING / ACTIVE / CLOSED / ABORTED status badges ✅
  - **`/hypotheses/[id]`:** Hypothesis spec + Audit log timeline with HOLD/CLOSE verdicts + Manual Audit trigger ✅
  - **`/memory`:** Post-Mortem library — lessons learned with PnL outcomes & 3072-dim vector indicator ✅
  - **Trigger Panel:** Input symbol → calls `POST /trade/start` ✅
- [x] Real-time polling (15s interval) on dashboard ✅
- [x] Styled with dark-mode trading terminal aesthetic ✅

---

## Step 10: Integration Testing & Demo Polish

**Goal:** Ensure the full system works end-to-end and is demo-ready.

- [x] Run full end-to-end cycle: Phase 1 → 2 → 3 → 4 verified & tested ✅
- [x] Verify Supabase RLS policies & vector search RPC ✅
- [x] Write `README.md` with setup instructions & architecture diagram ✅
- [x] Final cleanup: created `debug_log.md` with all error resolutions ✅

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
