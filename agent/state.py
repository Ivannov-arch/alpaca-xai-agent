"""
state.py — The LangGraph AgentState TypedDict.

This is the "baton" that gets passed between every node in the graph.
Each node reads from it and returns a dict with updated keys only.

Flow of state mutations:
  START
    → phase1_formulate_hypothesis writes: hypothesis_id, hypothesis_data, status,
                                          computed_qty, dollar_risk, pct_of_equity
    → phase2_execute_order writes:        alpaca_order_id, status
    → (worker loop re-enters here per ACTIVE hypothesis)
    → phase3_audit_position writes:       audit_verdict
    → phase4_post_mortem writes:          pnl_percentage, lesson_learned, status
  END
"""
from typing import TypedDict, Optional


class AgentState(TypedDict):
    # ── Inputs ──────────────────────────────────────────────────────
    symbol: str           # e.g. "AAPL"
    account_id: str       # UUID from the accounts table
    strategy_profile: Optional[str]  # "SCALPING", "SWING", or "CONSERVATIVE"

    # ── Risk sizing inputs (from UI / API request) ───────────────────
    risk_mode: Optional[str]    # "percent" | "dollar"
    risk_value: Optional[float] # e.g. 1.0 (percent mode) or 500.0 (dollar mode)
    triggered_by: Optional[str] # "manual" | "scanner"

    # ── Phase 1 outputs ─────────────────────────────────────────────
    hypothesis_id: Optional[str]    # UUID assigned after DB insert
    hypothesis_data: Optional[dict] # Validated JSON from the LLM

    # ── Risk sizing outputs (computed in Phase 1) ────────────────────
    computed_qty: Optional[float]       # Final risk-adjusted quantity
    dollar_risk: Optional[float]        # Dollar amount at risk (stop distance × qty)
    pct_of_equity: Optional[float]      # Fraction of equity risked (e.g. 0.01 = 1%)

    # ── Phase 2 outputs ─────────────────────────────────────────────
    alpaca_order_id: Optional[str]  # Returned by Alpaca create_order

    # ── Phase 3 outputs ─────────────────────────────────────────────
    audit_verdict: Optional[str]    # "HOLD" or "CLOSE"

    # ── Phase 4 outputs ─────────────────────────────────────────────
    pnl_percentage: Optional[float]
    lesson_learned: Optional[str]

    # ── Control ─────────────────────────────────────────────────────
    status: Optional[str]  # mirrors hypotheses.status: PENDING/ACTIVE/CLOSED/ABORTED
    error: Optional[str]   # set by any node on failure → triggers abort branch
