"""
phase3_audit.py — Continuous Audit node (called by the monitoring worker).

Responsibility:
  1. Fetch current market snapshot for the hypothesis symbol
     (agent/tools/alpaca_tools.py → get_positions / get_market_data).
  2. Build an audit prompt: original hypothesis + invalidation triggers
     + current market conditions.
  3. Call LLM (agent/llm.py) → parse verdict: "HOLD" or "CLOSE".
  4. Persist audit result to audit_logs table (agent/db.py).
  5. Return updated AgentState with audit_verdict.
     - If CLOSE → graph routes to phase4_post_mortem.
     - If HOLD  → graph ends this cycle; worker will re-run later.

Implemented in: Step 6 of worksteps.md
"""
from agent.state import AgentState


async def phase3_audit_position(state: AgentState) -> dict:
    # TODO: Implement in Step 6
    return {}
