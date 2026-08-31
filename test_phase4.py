"""
Phase 4 unit test: closes the position and writes the post-mortem.
Uses the same hypothesis_id from Phase 2/3 tests.

Usage: .\\venv\\Scripts\\python.exe test_phase4.py
"""
import asyncio
from agent.state import AgentState
from agent.nodes.phase4_postmortem import phase4_post_mortem
from agent.db import get_hypothesis, list_post_mortems

HYPOTHESIS_ID = "5dca8e37-20e3-4d46-9bb0-72822bd8a65c"
ACCOUNT_ID    = "66e809f1-2f0e-4a3a-8ea3-bdb7c2d5a849"
SYMBOL        = "AAPL"


async def main():
    print(f"[Phase 4] Running post-mortem for hypothesis {HYPOTHESIS_ID}...")

    state: AgentState = {
        "symbol": SYMBOL,
        "account_id": ACCOUNT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "hypothesis_data": None,
        "alpaca_order_id": None,
        "audit_verdict": "CLOSE",
        "pnl_percentage": None,
        "lesson_learned": None,
        "status": "ACTIVE",
        "error": None,
    }

    result = await phase4_post_mortem(state)
    state.update(result)

    print("\n-- Result ------------------------------------------")
    if state.get("error"):
        print(f"[Phase 4] FAILED: {state['error']}")
        return

    print(f"[Phase 4] OK  outcome  : {state['status']}")
    print(f"[Phase 4] OK  pnl      : {state['pnl_percentage']:+.2f}%")
    print(f"\nLesson learned:\n  {state['lesson_learned']}")

    # Verify DB
    hyp = get_hypothesis(HYPOTHESIS_ID)
    mortems = list_post_mortems(ACCOUNT_ID)
    print(f"\n-- DB Verification ----------------------------------")
    print(f"  hypothesis status  : {hyp['status']}")
    print(f"  post_mortems count : {len(mortems)}")
    if mortems:
        pm = mortems[0]
        print(f"  outcome            : {pm['outcome']}")
        print(f"  lesson_learned     : {pm['lesson_learned'][:100]}...")
        has_embedding = pm.get("embedding") is not None
        print(f"  embedding present  : {has_embedding}")

    assert hyp["status"] == "CLOSED", "hypothesis status should be CLOSED"
    assert len(mortems) > 0, "post_mortems should have at least 1 row"
    print(f"\nPHASE 4 UNIT TEST PASSED")


if __name__ == "__main__":
    asyncio.run(main())
