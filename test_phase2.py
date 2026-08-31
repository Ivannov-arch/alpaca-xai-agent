"""
Phase 2 unit test: runs Phase 1 + Phase 2 in sequence.
  1. Phase 1 formulates and saves a hypothesis (status=PENDING)
  2. Phase 2 places the order on Alpaca paper trading (status=ACTIVE)
  3. Verifies DB row is updated correctly

Usage: .\\venv\\Scripts\\python.exe test_phase2.py
"""
import asyncio, json
from agent.state import AgentState
from agent.nodes.phase1_hypothesis import phase1_formulate_hypothesis
from agent.nodes.phase2_execution import phase2_execute_order
from agent.db import get_hypothesis

ACCOUNT_ID = "66e809f1-2f0e-4a3a-8ea3-bdb7c2d5a849"
SYMBOL = "AAPL"


async def main():
    # ── Run Phase 1 ────────────────────────────────────────────────────
    print(f"[Phase 1] Formulating hypothesis for {SYMBOL}...")
    state: AgentState = {
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
    p1 = await phase1_formulate_hypothesis(state)
    state.update(p1)

    if state.get("error"):
        print(f"[Phase 1] FAILED: {state['error']}")
        return
    print(f"[Phase 1] OK  hypothesis_id={state['hypothesis_id']}  status={state['status']}")

    # ── Run Phase 2 ────────────────────────────────────────────────────
    print(f"\n[Phase 2] Placing order on Alpaca paper trading...")
    p2 = await phase2_execute_order(state)
    state.update(p2)

    print("\n-- Result ------------------------------------------")
    if state.get("error"):
        print(f"[Phase 2] FAILED: {state['error']}")
        return

    print(f"[Phase 2] OK  alpaca_order_id={state['alpaca_order_id']}  status={state['status']}")

    # ── Verify DB row ──────────────────────────────────────────────────
    record = get_hypothesis(state["hypothesis_id"])
    print(f"\n-- DB Verification ----------------------------------")
    print(f"  hypothesis_id   : {record['id']}")
    print(f"  status          : {record['status']}")
    print(f"  alpaca_order_id : {record['alpaca_order_id']}")
    print(f"  symbol / side   : {record['symbol']} / {record['side']}")
    print(f"  qty             : {record['qty']}")

    assert record["status"] == "ACTIVE", "Status should be ACTIVE!"
    assert record["alpaca_order_id"] is not None, "alpaca_order_id should be set!"
    print(f"\nPHASE 2 UNIT TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())
