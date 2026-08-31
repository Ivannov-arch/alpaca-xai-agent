"""
phase3_audit.py — Continuous Audit node (Phase 3).

Called periodically by the background worker (agent/worker.py) for every
ACTIVE hypothesis. Determines whether to HOLD the position or CLOSE it.

Execution order within this node:
  1. Fetch current live position snapshot from Alpaca (get_position).
  2. Fetch recent OHLCV bars for additional context (get_market_data).
  3. Build audit prompt:
       - Original thesis + invalidation triggers (from DB hypothesis)
       - Current price, unrealised PnL, and recent price action
  4. LLM call → parse verdict: "HOLD" or "CLOSE".
  5. Persist result to audit_logs table (agent/db.py).
  6. Return updated AgentState with audit_verdict.
     - If "CLOSE" → graph routes to Phase 4 (post-mortem + close position).
     - If "HOLD"  → graph ends this cycle; worker re-triggers in N minutes.

Imports from:
  - agent/state.py              (AgentState)
  - agent/llm.py                (get_llm)
  - agent/db.py                 (get_hypothesis, create_audit_log, update_hypothesis)
  - agent/tools/alpaca_tools.py (get_position, get_market_data)
"""
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import AgentState
from agent.llm import get_llm
from agent.db import get_hypothesis, create_audit_log
from agent.tools.alpaca_tools import get_position, get_market_data


# ── Prompt ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a disciplined risk manager auditing an open trading position.
Your job is to determine whether to HOLD or CLOSE the position based on:
1. Whether the original trade thesis is still valid.
2. Whether any invalidation triggers have been breached.
3. The current unrealised PnL and price momentum.

Rules:
- Respond with ONLY one word: either HOLD or CLOSE.
- If ANY invalidation trigger has been breached, you MUST respond CLOSE.
- If the position has exceeded target price, respond CLOSE (take profit).
- If the position has breached stop_loss_price, respond CLOSE (cut losses).
- Otherwise respond HOLD.
"""


def _build_audit_prompt(hypothesis: dict, position: dict | None, recent_bars: list[dict]) -> str:
    """Assembles the audit prompt from the hypothesis and current market state."""

    # Recent close prices (last 5 bars)
    price_summary = "No recent price data."
    if recent_bars:
        closes = [f"  {b['t'][:10]}: ${b['c']:.2f}" for b in recent_bars[-5:]]
        price_summary = "\n".join(closes)

    # Live position data (may be None if order not yet filled)
    if position:
        current_price = float(position.get("current_price", 0))
        unrealised_pnl = float(position.get("unrealized_pl", 0))
        unrealised_pnl_pct = float(position.get("unrealized_plpc", 0)) * 100
        position_block = (
            f"Current price : ${current_price:.2f}\n"
            f"Unrealised PnL: ${unrealised_pnl:.2f} ({unrealised_pnl_pct:.2f}%)\n"
            f"Quantity held : {position.get('qty', 'unknown')}"
        )
    else:
        position_block = "Position not yet filled or not found in Alpaca."

    # Invalidation triggers
    triggers = hypothesis.get("invalidation_triggers") or []
    trigger_lines = "\n".join(
        f"  - {t.get('condition', '')}: {t.get('threshold', '')}"
        for t in triggers
    )

    return f"""You are auditing the following open position:

## Original Thesis
{hypothesis.get("thesis_text", "No thesis recorded.")}

## Trade Parameters
Symbol      : {hypothesis.get("symbol")}
Side        : {hypothesis.get("side")}
Entry price : ${hypothesis.get("entry_price") or "market"}
Target      : ${hypothesis.get("target_price")}
Stop loss   : ${hypothesis.get("stop_loss_price")}

## Invalidation Triggers
{trigger_lines if trigger_lines else "None recorded."}

## Current Position
{position_block}

## Recent Price Action (last 5 sessions)
{price_summary}

Based on the above, should we HOLD or CLOSE this position?
Respond with ONE word only: HOLD or CLOSE.
"""


# ── Main node function ────────────────────────────────────────────────

async def phase3_audit_position(state: AgentState) -> dict:
    """
    Phase 3 node: audits an ACTIVE position and returns HOLD or CLOSE verdict.
    """
    hypothesis_id = state.get("hypothesis_id")
    if not hypothesis_id:
        return {"error": "Phase 3 aborted: no hypothesis_id in state.", "audit_verdict": "HOLD"}

    try:
        # ── 1. Fetch hypothesis from DB (has original targets + triggers) ──
        hypothesis = get_hypothesis(hypothesis_id)
        symbol = hypothesis["symbol"]

        # ── 2. Fetch live position from Alpaca ──────────────────────────
        position = get_position(symbol)  # Returns None if not filled yet

        # ── 3. Fetch recent OHLCV for context ──────────────────────────
        recent_bars = get_market_data(symbol, timeframe="1Day", limit=10)

        # ── 4. Build prompt and call LLM ────────────────────────────────
        prompt = _build_audit_prompt(hypothesis, position, recent_bars)
        llm = get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        # ── 5. Parse verdict (expect "HOLD" or "CLOSE") ─────────────────
        # Gemini may return content as a list of parts or a plain string
        raw_content = response.content
        if isinstance(raw_content, list):
            raw = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in raw_content
            ).strip().upper()
        else:
            raw = str(raw_content).strip().upper()
        verdict = "CLOSE" if "CLOSE" in raw else "HOLD"

        # ── 6. Persist audit log ────────────────────────────────────────
        market_snapshot = {
            "current_price": float(position["current_price"]) if position else None,
            "unrealised_pnl": float(position["unrealized_pl"]) if position else None,
            "unrealised_pnl_pct": float(position["unrealized_plpc"]) * 100 if position else None,
        }
        create_audit_log({
            "hypothesis_id": hypothesis_id,
            "llm_verdict": verdict,
            "reasoning_summary": raw,
            "market_snapshot": market_snapshot,
        })

        return {
            "audit_verdict": verdict,
            "error": None,
        }

    except Exception as e:
        return {
            "error": f"Phase 3 failed: {str(e)}",
            "audit_verdict": "HOLD",  # Default to HOLD on error — don't auto-close
        }
