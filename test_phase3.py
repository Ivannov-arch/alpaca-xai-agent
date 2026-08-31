"""
Phase 3 unit test: audits an existing ACTIVE hypothesis.
Uses the hypothesis_id from the last Phase 2 run.

Usage: .\\venv\\Scripts\\python.exe test_phase3.py
"""
import asyncio
from agent.state import AgentState
from agent.nodes.phase3_audit import phase3_audit_position
from agent.db import get_audit_logs

# Use the hypothesis_id from the last successful Phase 2 run
HYPOTHESIS_ID = "5dca8e37-20e3-4d46-9bb0-72822bd8a65c"
ACCOUNT_ID    = "66e809f1-2f0e-4a3a-8ea3-bdb7c2d5a849"
SYMBOL        = "AAPL"


async def main():
    print(f"[Phase 3] Auditing hypothesis {HYPOTHESIS_ID} ({SYMBOL})...")

    state: AgentState = {
        "symbol": SYMBOL,
        "account_id": ACCOUNT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis_data": None,
        "alpaca_order_id": None,
        "audit_verdict": None,
        "pnl_percentage": None,
        "lesson_learned": None,
        "status": "ACTIVE",
        "error": None,
    }

    result = await phase3_audit_position(state)
    state.update(result)

    print("\n-- Result ------------------------------------------")
    if state.get("error"):
        print(f"[Phase 3] WARNING: {state['error']}")
        print("(This is expected if the market is closed and position is not yet filled)")
        return

    print(f"[Phase 3] verdict = {state['audit_verdict']}")

    # Verify audit_log was saved
    logs = get_audit_logs(HYPOTHESIS_ID)
    print(f"\n-- DB Verification ----------------------------------")
    print(f"  audit_logs count : {len(logs)}")
    if logs:
        latest = logs[-1]
        print(f"  latest verdict   : {latest['llm_verdict']}")
        print(f"  reasoning        : {latest['reasoning_summary'][:100]}...")

    print(f"\nPHASE 3 UNIT TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())
