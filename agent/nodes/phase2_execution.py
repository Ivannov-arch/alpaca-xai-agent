"""
phase2_execution.py — Order Execution node.

Responsibility:
  1. Guard: abort if hypothesis_id is missing or status != PENDING.
  2. Call alpaca create_order (agent/tools/alpaca_tools.py) with
     parameters derived from hypothesis_data.
  3. On Alpaca confirmation, extract alpaca_order_id.
  4. Update the hypotheses row in DB (agent/db.py):
     - alpaca_order_id = <returned id>
     - status = ACTIVE
  5. Return updated AgentState.

Implemented in: Step 5 of worksteps.md
"""
from agent.state import AgentState


async def phase2_execute_order(state: AgentState) -> dict:
    # TODO: Implement in Step 5
    return {}
