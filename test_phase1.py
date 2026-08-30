"""
Smoke test for Phase 1: Hypothesis Formulation.
Runs a full end-to-end cycle for AAPL:
  - Fetches OHLCV from Alpaca
  - Calls Gemini LLM for hypothesis
  - Saves to Supabase

Usage: .\\venv\\Scripts\\python.exe test_phase1.py
"""
import asyncio
from agent.state import AgentState
from agent.nodes.phase1_hypothesis import phase1_formulate_hypothesis
from agent.db import get_hypothesis

# Replace with your actual account_id from the accounts table in Supabase
ACCOUNT_ID = "66e809f1-2f0e-4a3a-8ea3-bdb7c2d5a849"
SYMBOL = "AAPL"


async def main():
    print(f"Running Phase 1 for {SYMBOL}...")

    initial_state: AgentState = {
        "symbol": SYMBOL,
        "account_id": ACCOUNT_ID,
        "hypothesis_id": None,
        "hypothesis_data": None,
        "alpaca_order_id": None,
        "audit_verdict": None,
        "pnl_percentage": None,
        "lesson_learned": None,
        "status": None,
        "error": None,
    }

    result = await phase1_formulate_hypothesis(initial_state)
    print("\n-- Result ------------------------------------------")

    if result.get("error"):
        print(f"FAILED: {result['error']}")
        return

    hyp_id = result["hypothesis_id"]
    print(f"hypothesis_id : {hyp_id}")
    print(f"status        : {result['status']}")
    print(f"\nHypothesis data:")
    import json
    print(json.dumps(result["hypothesis_data"], indent=2))

    # Verify it was saved to DB
    record = get_hypothesis(hyp_id)
    print(f"\n-- DB Record (status={record['status']}) ------------")
    print(f"symbol        : {record['symbol']}")
    print(f"thesis_text   : {record['thesis_text'][:120]}...")
    print(f"\nPHASE 1 UNIT TEST PASSED ✅")


if __name__ == "__main__":
    asyncio.run(main())
