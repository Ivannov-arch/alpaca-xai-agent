# 🧠 Project Blueprint: Explainable AI (XAI) Trading Agent

**Core Concept:** Building an autonomous trading agent that prioritizes transparency (Explainable AI). The agent is strictly prohibited from executing orders blindly. The system requires the AI to write a detailed "hypothesis document" before transacting, perform continuous reasoning audits, and compile post-mortem reports into vector memory for long-term self-learning.

---

## 1. Tech Stack Breakdown

The selection of these technologies focuses on rapid development iteration, strict security isolation for a single-user application, and highly responsive data visualization for the audit trail.

| Architecture Layer | Selected Technology | Core Function & Rationale |
| :--- | :--- | :--- |
| **Frontend & UI** | **Next.js (React) + Vite** | Builds an interactive dashboard interface. Vite's fast refresh bundling accelerates the rendering of the audit log timeline and real-time portfolio status. |
| **Agent Engine** | **Python + LangGraph** | Orchestrates the agent's logic flow (State Machine). Python is highly robust and stable for handling background worker monitoring loops without memory leaks. |
| **LLM Reasoning** | **DeepSeek V3 / Gemini API** | The primary reasoning engine used to analyze the market, validate invalidation triggers, and perform reflections. Highly reliable for deterministic logic and cost-effective. |
| **Database & Memory** | **Supabase (PostgreSQL + pgvector)** | Stores transactional relational data (hypotheses & audit logs) and vector embeddings for long-term memory within a single ecosystem. |
| **Broker & Tools** | **Alpaca API & MCP Server** | Executes paper trading orders and retrieves structured market data via the Model Context Protocol (MCP) standard. |
| **Version Control** | **Git & GitHub** | Handles source code management, collaboration, and version tracking. |

> **Security Focus (Data Isolation):** 
> Because this agent handles transactional logic, database-level security is a top priority. Supabase is utilized to implement **Row Level Security (RLS)**. RLS policies will be strictly configured (especially on the `public.accounts` table and hypothesis records) to ensure data isolation for a single-user application, completely sealing off potential unauthorized access.

---

## 2. Agent Logic Flow (State Machine)

This process operates as a deterministic chain system. If one phase fails or its conditions are unmet, the transaction execution is immediately aborted. The chain consists of 4 distinct phases:

### Phase 1: Pre-Trade (Hypothesis Formulation)
The agent gathers market data (price, volume, trends). The LLM is required to process this data and render a **Hypothesis Record** in a strict JSON format. This document must specifically describe the rationale for market entry (thesis), price targets, and **Invalidation Triggers** (the fundamental or technical conditions that will invalidate the plan).
*Absolute Rule: No transaction may be sent to the broker without this validated document.*

### Phase 2: Execution (API & Asset Locking)
Only after the JSON Hypothesis is programmatically schema-validated does the agent use an Alpaca MCP instruction (e.g., `create_order`) to send an execution command to the paper trading account. When Alpaca returns a confirmation (an `alpaca_order_id`), the system locks this ID with the hypothesis document in Supabase and updates its status to `ACTIVE`.

### Phase 3: Continuous Audit (The Monitoring Loop)
A background worker runs at specific time intervals (e.g., every 15 minutes). This worker queries all database rows with an `ACTIVE` status, then fetches the latest market condition snapshot from Alpaca. The LLM then acts as an internal auditor: it evaluates whether any *Invalidation Triggers* have been met. If the original argument still holds, the log records a `HOLD` verdict. If the hypothesis is broken, it triggers the transition to Phase 4.

### Phase 4: Post-Mortem & Vector Memory
If the agent issues a `CLOSE` verdict (because profit targets are met or risk limits are breached), it immediately calls the position-closing instruction in Alpaca. Once the position is closed, the LLM synthesizes a post-mortem report analyzing the variance between the expectations set in Phase 1 and the execution reality. This post-mortem text is converted into vectors using `pgvector`. On subsequent trades, the agent will automatically perform a vector search to retrieve past memories, ensuring it does not repeat similar mistakes.

---

## 3. Database Architecture Components (Supabase Schema)

The database schema is designed to ensure full relational integrity between broker transaction records and the AI agent's internal reasoning logic.

*   **Table `accounts`**
    *   *Function:* Manages profiles and stores encrypted Alpaca paper trading API keys. Fully protected by a unified RLS policy.
*   **Table `hypotheses`**
    *   *Function:* The initial transaction contract.
    *   *Key Columns:* `id` (PK), `alpaca_order_id`, `symbol`, `thesis_text`, `invalidation_triggers` (JSONB), `status` (ACTIVE/CLOSED).
*   **Table `audit_logs`**
    *   *Function:* Records the audit trail of every reasoning process executed by the continuous agent.
    *   *Key Columns:* `id` (PK), `hypothesis_id` (FK), `market_snapshot` (JSONB), `llm_verdict`, `reasoning_summary`.
*   **Table `post_mortems`**
    *   *Function:* The agent's adaptive memory hub (Long-term memory).
    *   *Key Columns:* `id` (PK), `hypothesis_id` (FK), `pnl_percentage`, `lesson_learned`, `embedding` (Vector 1536/768 dimensions).

---

## 4. Alpaca API & MCP Tools Integration

The AI agent interacts with the outside world exclusively through the rigidly mapped Model Context Protocol (MCP) bridge.

| Agent Action | Endpoint / MCP Tool | Operational Details |
| :--- | :--- | :--- |
| **Ingestion** (Market Data) | `alpaca_get_market_data` | Retrieves historical OHLCV (Open, High, Low, Close, Volume) data as a baseline for the LLM to formulate hypotheses. |
| **Commitment** (Buy Execution) | `alpaca_create_order` | Opens an asset position with quantity parameters and order type (Market/Limit) based on Phase 1 calculations. |
| **Observation** (Position Audit) | `alpaca_get_positions` | Returns a list of currently held asset statuses along with unrealized PnL (Profit and Loss) calculations. |
| **Resolution** (Close Position) | `alpaca_close_position` | Called exclusively if the Continuous Audit LLM (Phase 3) yields a valid decision to CLOSE the position. |