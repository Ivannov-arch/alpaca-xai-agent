# 🛠️ Debug Log: XAI Trading Agent Troubleshooting

This document summarizes the issues, bugs, root causes, and solutions encountered during system setup, phase testing, and integration.

---

## 1. PowerShell Parameter Parsing Syntax Error
*   **Cause:** Executing PowerShell loop scripts for directory creation in the sandbox CLI failed due to unescaped characters detected by the shell parser.
*   **Solution:** Switched to standard direct native commands (`mkdir` and `type nul >`) via `cmd /c` to scaffold the project structure.

## 2. API v1beta Gemini Embedding Error (text-embedding-004)
*   **Cause:** The default `GoogleGenerativeAIEmbeddings` class in `langchain-google-genai` invoked Google's `v1beta` API endpoint, which threw a 404 for `text-embedding-004` on standard API keys.
*   **Solution:** Rewrote `embed_text()` in `agent/llm.py` using the official `google-genai` SDK (`client.models.embed_content()`) with `gemini-embedding-001` (3072 dimensions).

## 3. Supabase pgvector Size Mismatch (1536 vs 3072)
*   **Cause:** Switching the embedding model to `gemini-embedding-001` produced 3072-dimensional vectors, whereas the initial SQL schema was configured for 1536 (OpenAI standard).
*   **Solution:** Updated the `embedding` column in `schema.sql` and the `match_post_mortems()` function in `rls_policies.sql` to `VECTOR(3072)`, then re-executed the migration in Supabase.

## 4. Windows Terminal CP1252 Encoding Error
*   **Cause:** Unicode box-drawing characters (`──`) in Python `print()` statements caused encoding crashes on Windows consoles defaulting to CP1252.
*   **Solution:** Replaced all unicode divider characters with standard ASCII dashes (`---`).

## 5. Alpaca Market Data Return Null on Weekends
*   **Cause:** Calling `/v2/stocks/{symbol}/bars` without `start`/`end` parameters defaulted Alpaca to query current time bars (weekends = closed = null bars).
*   **Solution:** Updated `get_market_data()` in `agent/tools/alpaca_tools.py` to calculate and supply `"start": (current_time - 45 days)` automatically.

## 6. Deprecated Gemini 2.0 Model Endpoint
*   **Cause:** The Google API deprecated `gemini-2.0-flash`, returning a `404 Not Found` with a recommendation to use `gemini-3.6-flash`.
*   **Solution:** Updated the model name in `agent/llm.py` to `gemini-3.6-flash`.

## 7. Supabase DNS Resolution (getaddrinfo failed)
*   **Cause:** The `.env` file contained the placeholder domain `your-project-ref.supabase.co`, causing DNS lookup failures.
*   **Solution:** Updated `SUPABASE_URL` in `.env` with the active Supabase project URL.

## 8. Relational Foreign Key Constraint Violation (23503)
*   **Cause:** The hardcoded `ACCOUNT_ID` in unit tests did not exist in the Supabase `accounts` table, triggering a foreign key violation when inserting into `hypotheses`.
*   **Solution:** Inserted a dev user record into `accounts` and updated `ACCOUNT_ID` in test files with the valid UUID `id`.

## 9. Premature CLOSE & Constant Breakeven Result on Unfilled Orders
*   **Cause:** When market was closed, orders submitted to Alpaca remained in `pending_new` status (`position is None`). Phase 3 audit misinterpreted missing position data as an invalidation signal, triggering premature `CLOSE` and $0.00 PnL (`BREAKEVEN`).
*   **Solution:** Added *Guard Protection* in `agent/nodes/phase3_audit.py` — if `position is None`, the audit automatically returns `HOLD` and defers evaluation until the order fills.

## 10. Alpaca 422 Unprocessable Entity & Endpoint Error for Crypto Pairs
*   **Cause:** Executing orders and market data requests for crypto pairs (e.g. `BTC/USD`) failed because `/v2/stocks` endpoints do not support crypto, the default `time_in_force: "day"` is rejected for crypto, and unescaped `/` characters broke HTTP URL routing.
*   **Solution:** 
    * Routed crypto market data requests to `/v1beta3/crypto/us/bars` in `agent/tools/alpaca_tools.py`.
    * Enforced `time_in_force: "gtc"` for crypto orders in `create_order()`.
    * Encoded symbols using `urllib.parse.quote(symbol, safe="")` in `get_position()` and `close_position()` so `BTC/USD` safely encodes to `BTC%2FUSD`.
    * Updated `_SYSTEM_PROMPT` in `phase1_hypothesis.py` with position sizing rules (e.g., 0.01 - 0.03 BTC) targeting $500 - $2,000 USD position values.
