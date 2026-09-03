"""
phase1_hypothesis.py — Pre-Trade Hypothesis Formulation (Phase 1).

Execution order within this node:
  1. retrieve_relevant_memories()   — vector search for past lessons
  2. get_market_data()              — fetch 30 days of OHLCV from Alpaca
  3. build_hypothesis_prompt()      — assemble LLM system + user prompt
  4. LLM call with structured output → HypothesisSchema (Pydantic)
  5. calculate_position_size()      — risk-based qty override (agent/risk.py)
  6. create_hypothesis() in DB      — persist with status=PENDING
  7. Return updated AgentState

Imports from:
  - agent/memory.py            (retrieve_relevant_memories, format_memories_for_prompt)
  - agent/tools/alpaca_tools.py (get_market_data, get_account)
  - agent/llm.py               (get_llm)
  - agent/db.py                (create_hypothesis)
  - agent/state.py             (AgentState)
  - agent/risk.py              (calculate_position_size, risk_settings_from_state, is_crypto_symbol)
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import AgentState
from agent.llm import get_llm
from agent.db import create_hypothesis
from agent.memory import retrieve_relevant_memories, format_memories_for_prompt
from agent.tools.alpaca_tools import get_market_data, get_account
from agent.risk import (
    calculate_position_size,
    risk_settings_from_state,
    is_crypto_symbol,
    HARD_CEILING_PCT,
)


# ── Pydantic schema for LLM structured output ─────────────────────────

class InvalidationTrigger(BaseModel):
    condition: str = Field(description="The specific market condition to watch")
    threshold: str = Field(description="The quantifiable level that breaks the thesis, e.g. 'price closes below $180'")


class HypothesisSchema(BaseModel):
    """
    The mandatory pre-trade contract. The agent cannot execute an order
    without producing and validating this document first.
    """
    symbol: str = Field(description="Ticker symbol, e.g. AAPL or BTC/USD")
    side: Literal["buy", "sell"] = Field(description="Direction of the trade")
    order_type: Literal["market", "limit"] = Field(description="Order execution type")
    instrument_type: Optional[Literal["equity", "crypto", "option"]] = Field(
        "equity", description="Financial instrument type: equity, crypto, or option contract"
    )
    option_type: Optional[Literal["call", "put"]] = Field(
        None, description="If trading options: call for bullish, put for bearish"
    )
    qty: float = Field(description="Advisory quantity — will be overridden by server-side risk calculation", gt=0)
    entry_price: Optional[float] = Field(None, description="Limit entry price (null if market order)")
    target_price: float = Field(description="Price target where profit is taken")
    stop_loss_price: float = Field(description="Price level where the position is cut for risk management")
    thesis_text: str = Field(description="Detailed reasoning for the trade entry (2-4 sentences minimum)")
    invalidation_triggers: list[InvalidationTrigger] = Field(
        description="2-4 specific conditions that would invalidate this hypothesis",
        min_length=2,
        max_length=4,
    )


# ── Prompt builders ───────────────────────────────────────────────────

def _get_system_prompt(strategy_profile: str | None = "SWING") -> str:
    profile = (strategy_profile or "SWING").upper()

    if profile == "SCALPING":
        persona = """You are an AGGRESSIVE SCALPER. Your objective is quick intraday momentum setups with tight risk.
Rules:
- Stop Loss MUST be tight (0.5% to 1.5% from entry).
- Target Price should target immediate momentum resistance/support (1.5:1 to 2:1 R:R).
- Invalidation triggers must focus on 1-5 minute structural breaches."""
    elif profile == "CONSERVATIVE":
        persona = """You are a CONSERVATIVE LONG-TERM INVESTOR. Your objective is high-conviction accumulation on deep pullbacks.
Rules:
- Stop Loss should be wide and structural (5% to 10% below entry).
- Target Price should aim for major historical swing highs (3:1+ R:R).
- Invalidation triggers must focus on multi-week macro trend changes."""
    else:
        persona = """You are a BALANCED SWING TRADER. Your objective is capturing 1-5 day trend expansions.
Rules:
- Stop Loss should be realistic (2% to 4% below entry).
- Target Price must offer at least a 2:1 reward-to-risk ratio.
- Invalidation triggers must focus on key daily price level breaches."""

    return f"""{persona}

General Rules:
1. You must provide a clear, evidence-based thesis — not vague generalities.
2. Position sizing (`qty`): provide a reasonable advisory quantity — the server will override it
   using a risk-based formula. Focus your energy on accurate `entry_price` and `stop_loss_price`
   values, as the stop-loss distance is the key input for computing final position size.
3. Respond ONLY with the structured JSON — no extra text.
"""


def _format_ohlcv(bars: list[dict]) -> str:
    """Formats raw OHLCV bars into a compact table for the LLM prompt."""
    if not bars:
        return "No market data available."
    lines = ["Date       | Open    | High    | Low     | Close   | Volume"]
    lines.append("-" * 65)
    for bar in bars[-15:]:  # Last 15 bars to keep prompt concise
        date = bar.get("t", "")[:10]
        lines.append(
            f"{date} | {bar['o']:7.2f} | {bar['h']:7.2f} | "
            f"{bar['l']:7.2f} | {bar['c']:7.2f} | {bar['v']:,.0f}"
        )
    return "\n".join(lines)


# ── Main node function ────────────────────────────────────────────────

async def phase1_formulate_hypothesis(state: AgentState) -> dict:
    """
    Phase 1 node: formulates a validated trade hypothesis for the given symbol.
    Applies risk-based position sizing and returns a partial AgentState update dict.
    """
    symbol = state["symbol"]
    account_id = state["account_id"]

    try:
        # ── 1. Retrieve past lessons from vector memory ────────────
        memory_query = f"trading {symbol} stock — entry, momentum, risk management"
        memories = retrieve_relevant_memories(memory_query, top_k=3)
        memory_block = format_memories_for_prompt(memories)

        # ── 2. Fetch OHLCV market data ─────────────────────────────
        bars = get_market_data(symbol, timeframe="1Day", limit=30)
        if not bars:
            return {"error": f"No market data returned for {symbol}.", "status": "ABORTED"}

        ohlcv_table = _format_ohlcv(bars)
        latest_close = bars[-1]["c"]
        latest_volume = bars[-1]["v"]

        # ── 3. Build LLM prompt ────────────────────────────────────
        user_prompt = f"""Analyze {symbol} and produce a trade hypothesis.

## Current Market Data (last 15 days, daily OHLCV):
{ohlcv_table}

Latest close: ${latest_close:.2f}
Latest volume: {latest_volume:,.0f}

{memory_block}

Produce a complete HypothesisSchema JSON for {symbol}.
Important: set `entry_price` and `stop_loss_price` precisely — the server uses the
stop-loss distance to compute the actual position size. The `qty` field is advisory only.
"""

        # ── 4. LLM call with structured output ─────────────────────
        llm = get_llm()
        structured_llm = llm.with_structured_output(HypothesisSchema)
        system_prompt_text = _get_system_prompt(state.get("strategy_profile"))
        hypothesis: HypothesisSchema = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt_text),
            HumanMessage(content=user_prompt),
        ])

        # ── 5. Risk-based position sizing ──────────────────────────
        # Determine entry price (use latest close for market orders)
        entry_price = hypothesis.entry_price or latest_close
        stop_loss_price = hypothesis.stop_loss_price

        # Fetch live account equity for sizing
        try:
            account_info = get_account()
            equity = float(account_info.get("equity") or account_info.get("portfolio_value") or 100_000)
            buying_power = float(account_info.get("buying_power") or equity)
        except Exception:
            # Fail gracefully — fall back to a conservative default
            equity = 100_000.0
            buying_power = 100_000.0

        risk_settings = risk_settings_from_state(state)
        crypto = is_crypto_symbol(symbol)

        size_result = calculate_position_size(
            equity=equity,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            risk_settings=risk_settings,
            is_crypto=crypto,
            buying_power=buying_power,
        )

        # ── 6. Reject if sizing failed ─────────────────────────────
        if size_result.rejection_reason:
            return {
                "error": f"Risk sizing rejected trade: {size_result.rejection_reason}",
                "status": "ABORTED",
            }

        final_qty = size_result.qty

        triggered_by = state.get("triggered_by") or "manual"

        # Build risk metadata to store alongside the hypothesis
        risk_metadata = {
            "triggered_by": triggered_by,
            "risk_mode": state.get("risk_mode") or "percent",
            "risk_value": state.get("risk_value") or 1.0,
            "dollar_risk": size_result.dollar_risk,
            "pct_of_equity": round(size_result.pct_of_equity * 100, 4),  # stored as %, e.g. 1.0
            "position_value": size_result.position_value,
            "capped": size_result.capped,
            "equity_at_trade": round(equity, 2),
            "hard_ceiling_pct": HARD_CEILING_PCT * 100,
        }

        # ── 7. Persist to database ─────────────────────────────────
        db_payload = {
            "account_id": account_id,
            "symbol": hypothesis.symbol,
            "side": hypothesis.side,
            "order_type": hypothesis.order_type,
            "qty": final_qty,                  # risk-adjusted qty, not LLM advisory
            "entry_price": hypothesis.entry_price,
            "target_price": hypothesis.target_price,
            "stop_loss_price": hypothesis.stop_loss_price,
            "thesis_text": hypothesis.thesis_text,
            "invalidation_triggers": [t.model_dump() for t in hypothesis.invalidation_triggers],
            "status": "PENDING",
            "risk_metadata": risk_metadata,
        }
        record = create_hypothesis(db_payload)

        return {
            "hypothesis_id": record["id"],
            "hypothesis_data": {**hypothesis.model_dump(), "qty": final_qty},
            "computed_qty": final_qty,
            "dollar_risk": size_result.dollar_risk,
            "pct_of_equity": size_result.pct_of_equity,
            "status": "PENDING",
            "error": None,
        }

    except Exception as e:
        return {
            "error": f"Phase 1 failed: {str(e)}",
            "status": "ABORTED",
        }
