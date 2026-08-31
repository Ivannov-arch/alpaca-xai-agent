"""
phase4_postmortem.py — Position Close & Post-Mortem Synthesis (Phase 4).

Triggered when Phase 3 audit_verdict == "CLOSE".

Execution order within this node:
  1. Close the open position on Alpaca (close_position).
  2. Update hypotheses status → CLOSED in DB.
  3. Fetch all audit_logs for this hypothesis.
  4. Compute final PnL percentage from Alpaca close response.
  5. Determine outcome: WIN / LOSS / BREAKEVEN.
  6. Prompt LLM to synthesise lesson_learned text from:
       - Original thesis vs. actual outcome
       - All audit verdicts and reasoning
  7. Embed lesson_learned text → 3072-dim vector (embed_text).
  8. Persist to post_mortems table (with embedding).
  9. Return updated AgentState with pnl_percentage, lesson_learned.

Imports from:
  - agent/state.py              (AgentState)
  - agent/llm.py                (get_llm, embed_text)
  - agent/db.py                 (get_hypothesis, get_audit_logs, update_hypothesis,
                                 create_post_mortem)
  - agent/tools/alpaca_tools.py (close_position)
"""
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import AgentState
from agent.llm import get_llm, embed_text
from agent.db import get_hypothesis, get_audit_logs, update_hypothesis, create_post_mortem
from agent.tools.alpaca_tools import close_position


# ── Prompt ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a professional trading journal assistant.
Your job is to write a concise, actionable post-mortem lesson based on a completed trade.

Rules:
- Focus on WHAT went right or wrong and WHY.
- Extract the single most important lesson to avoid repeating the same mistake or to reinforce the winning behaviour.
- Write 2-3 sentences maximum, in plain English.
- Do NOT include the trade symbol or specific price levels — keep it general and reusable.
"""


def _build_postmortem_prompt(
    hypothesis: dict,
    audit_logs: list[dict],
    outcome: str,
    pnl_pct: float,
) -> str:
    audit_summary = "\n".join(
        f"  - [{log.get('llm_verdict', '?')}] {log.get('reasoning_summary', '')[:100]}"
        for log in audit_logs
    ) or "  No audit records."

    return f"""Completed trade post-mortem:

## Original Thesis
{hypothesis.get("thesis_text", "N/A")}

## Trade Parameters
Side           : {hypothesis.get("side")}
Target price   : ${hypothesis.get("target_price")}
Stop loss      : ${hypothesis.get("stop_loss_price")}

## Audit History
{audit_summary}

## Outcome
Result  : {outcome}
PnL     : {pnl_pct:+.2f}%

Write a concise, reusable lesson_learned from this trade.
"""


# ── Main node function ────────────────────────────────────────────────

async def phase4_post_mortem(state: AgentState) -> dict:
    """
    Phase 4 node: closes the Alpaca position, writes a post-mortem,
    embeds it into vector memory, and closes the hypothesis.
    """
    hypothesis_id = state.get("hypothesis_id")
    if not hypothesis_id:
        return {"error": "Phase 4 aborted: no hypothesis_id in state."}

    try:
        hypothesis = get_hypothesis(hypothesis_id)
        symbol = hypothesis["symbol"]

        # ── 1. Close position on Alpaca ────────────────────────────────
        try:
            close_resp = close_position(symbol)
            # Alpaca returns the closed order; PnL in profit_loss field
            raw_pnl = close_resp.get("profit_loss") or 0.0
            avg_entry = float(hypothesis.get("entry_price") or close_resp.get("avg_entry_price") or 1)
            pnl_pct = (float(raw_pnl) / (avg_entry * float(hypothesis.get("qty", 1)))) * 100
            pnl_abs = float(raw_pnl)
        except Exception:
            # Position may already be closed (market closed, or filled at 0)
            pnl_pct = 0.0
            pnl_abs = 0.0

        # ── 2. Determine outcome ───────────────────────────────────────
        if pnl_pct > 0.5:
            outcome = "WIN"
        elif pnl_pct < -0.5:
            outcome = "LOSS"
        else:
            outcome = "BREAKEVEN"

        # ── 3. Update hypothesis status → CLOSED ──────────────────────
        update_hypothesis(hypothesis_id, {"status": "CLOSED"})

        # ── 4. Fetch all audit logs for context ────────────────────────
        audit_logs = get_audit_logs(hypothesis_id)

        # ── 5. LLM post-mortem synthesis ──────────────────────────────
        prompt = _build_postmortem_prompt(hypothesis, audit_logs, outcome, pnl_pct)
        llm = get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        # Parse response (handle Gemini list or string)
        raw_content = response.content
        if isinstance(raw_content, list):
            lesson = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in raw_content
            ).strip()
        else:
            lesson = str(raw_content).strip()

        # ── 6. Embed lesson → vector ───────────────────────────────────
        embedding = embed_text(lesson)

        # ── 7. Persist post-mortem ─────────────────────────────────────
        create_post_mortem({
            "hypothesis_id": hypothesis_id,
            "pnl_percentage": round(pnl_pct, 4),
            "pnl_absolute": round(pnl_abs, 2),
            "outcome": outcome,
            "lesson_learned": lesson,
            "embedding": embedding,
        })

        return {
            "pnl_percentage": pnl_pct,
            "lesson_learned": lesson,
            "status": "CLOSED",
            "error": None,
        }

    except Exception as e:
        return {
            "error": f"Phase 4 failed: {str(e)}",
            "status": "ABORTED",
        }
