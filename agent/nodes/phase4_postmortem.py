"""
phase4_postmortem.py — Position Close & Post-Mortem Synthesis node.

Responsibility:
  1. Call Alpaca close_position (agent/tools/alpaca_tools.py).
  2. Update hypotheses.status → CLOSED in DB (agent/db.py).
  3. Gather all audit_logs for this hypothesis.
  4. Compute PnL percentage from Alpaca's closed position data.
  5. Prompt LLM (agent/llm.py) to synthesise a lesson_learned text
     from: original thesis vs. actual outcome.
  6. Call embed_text (agent/llm.py) on lesson_learned → vector.
  7. Persist to post_mortems table with embedding (agent/db.py).
  8. Return updated AgentState with pnl_percentage and lesson_learned.

Implemented in: Step 7 of worksteps.md
"""
from agent.state import AgentState


async def phase4_post_mortem(state: AgentState) -> dict:
    # TODO: Implement in Step 7
    return {}
