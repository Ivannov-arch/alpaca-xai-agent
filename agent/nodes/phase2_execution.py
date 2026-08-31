"""
phase2_execution.py — Order Execution node (Phase 2).

Responsibility:
  1. Guard: abort immediately if hypothesis_id is missing or status != PENDING.
  2. Extract trade parameters from hypothesis_data (side, qty, order_type, entry_price).
  3. Call Alpaca create_order (agent/tools/alpaca_tools.py).
  4. On Alpaca confirmation: extract alpaca_order_id from the response.
  5. Update hypotheses DB row:
       - alpaca_order_id = <returned id>
       - status = "ACTIVE"
  6. Return updated AgentState.

Imports from:
  - agent/state.py             (AgentState)
  - agent/tools/alpaca_tools.py (create_order)
  - agent/db.py                (update_hypothesis)
"""
from agent.state import AgentState
from agent.tools.alpaca_tools import create_order
from agent.db import update_hypothesis


async def phase2_execute_order(state: AgentState) -> dict:
    """
    Phase 2 node: places the trade on Alpaca paper trading and activates
    the hypothesis in the database.
    """
    # ── 1. Guard ───────────────────────────────────────────────────────
    if not state.get("hypothesis_id"):
        return {"error": "Phase 2 aborted: no hypothesis_id in state.", "status": "ABORTED"}

    if state.get("status") != "PENDING":
        return {
            "error": f"Phase 2 aborted: expected status PENDING, got '{state.get('status')}'.",
            "status": "ABORTED",
        }

    hyp = state.get("hypothesis_data", {})
    if not hyp:
        return {"error": "Phase 2 aborted: hypothesis_data is empty.", "status": "ABORTED"}

    try:
        # ── 2. Extract order parameters from hypothesis ────────────────
        symbol = hyp["symbol"]
        qty = hyp["qty"]
        side = hyp["side"]
        order_type = hyp["order_type"]
        entry_price = hyp.get("entry_price")  # None for market orders

        # ── 3. Place order on Alpaca ───────────────────────────────────
        order_response = create_order(
            symbol=symbol,
            qty=qty,
            side=side,
            order_type=order_type,
            limit_price=entry_price,
        )

        # ── 4. Extract Alpaca order ID ─────────────────────────────────
        alpaca_order_id = order_response["id"]

        # ── 5. Update hypothesis in DB → ACTIVE ───────────────────────
        update_hypothesis(
            state["hypothesis_id"],
            {
                "alpaca_order_id": alpaca_order_id,
                "status": "ACTIVE",
            },
        )

        return {
            "alpaca_order_id": alpaca_order_id,
            "status": "ACTIVE",
            "error": None,
        }

    except Exception as e:
        # Mark hypothesis ABORTED so it doesn't get re-audited
        if state.get("hypothesis_id"):
            try:
                update_hypothesis(state["hypothesis_id"], {"status": "ABORTED"})
            except Exception:
                pass
        return {
            "error": f"Phase 2 failed: {str(e)}",
            "status": "ABORTED",
        }
