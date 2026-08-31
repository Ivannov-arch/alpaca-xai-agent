"""
phase1_hypothesis.py — Pre-Trade Hypothesis Formulation (Phase 1).

Execution order within this node:
  1. retrieve_relevant_memories()   — vector search for past lessons
  2. get_market_data()              — fetch 30 days of OHLCV from Alpaca
  3. build_hypothesis_prompt()      — assemble LLM system + user prompt
  4. LLM call with structured output → HypothesisSchema (Pydantic)
  5. create_hypothesis() in DB      — persist with status=PENDING
  6. Return updated AgentState

Imports from:
  - agent/memory.py            (retrieve_relevant_memories, format_memories_for_prompt)
  - agent/tools/alpaca_tools.py (get_market_data)
  - agent/llm.py               (get_llm)
  - agent/db.py                (create_hypothesis)
  - agent/state.py             (AgentState)
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import AgentState
from agent.llm import get_llm
from agent.db import create_hypothesis
from agent.memory import retrieve_relevant_memories, format_memories_for_prompt
from agent.tools.alpaca_tools import get_market_data


# ── Pydantic schema for LLM structured output ─────────────────────────

class InvalidationTrigger(BaseModel):
    condition: str = Field(description="The specific market condition to watch")
    threshold: str = Field(description="The quantifiable level that breaks the thesis, e.g. 'price closes below $180'")


class HypothesisSchema(BaseModel):
    """
    The mandatory pre-trade contract. The agent cannot execute an order
    without producing and validating this document first.
    """
    symbol: str = Field(description="Ticker symbol, e.g. AAPL")
    side: Literal["buy", "sell"] = Field(description="Direction of the trade")
    order_type: Literal["market", "limit"] = Field(description="Order execution type")
    qty: float = Field(description="Number of shares to trade", gt=0)
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

_SYSTEM_PROMPT = """You are an expert quantitative trader and risk manager.
Your job is to analyze market data and produce a rigorous, structured trade hypothesis.

Rules you MUST follow:
1. You must provide a clear, evidence-based thesis — not vague generalities.
2. Position sizing (`qty`): target position value around $500 - $2,000 USD.
   - For BTC/USD: qty between 0.01 and 0.03 BTC.
   - For ETH/USD: qty between 0.1 and 0.5 ETH.
   - For SOL/USD: qty between 2 and 10 SOL.
   - For Stocks (e.g. AAPL, NVDA): qty between 5 and 50 shares.
3. The stop_loss_price must be defined and realistic (max 3-5% risk).
4. The target_price must offer at least a 2:1 reward-to-risk ratio vs the stop.
5. You must provide at least 2 specific, measurable invalidation triggers.
6. Respond ONLY with the structured JSON — no extra text.
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
    Returns a partial AgentState update dict.
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
"""

        # ── 4. LLM call with structured output ─────────────────────
        llm = get_llm()
        structured_llm = llm.with_structured_output(HypothesisSchema)
        hypothesis: HypothesisSchema = await structured_llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])

        # ── 5. Persist to database ─────────────────────────────────
        db_payload = {
            "account_id": account_id,
            "symbol": hypothesis.symbol,
            "side": hypothesis.side,
            "order_type": hypothesis.order_type,
            "qty": hypothesis.qty,
            "entry_price": hypothesis.entry_price,
            "target_price": hypothesis.target_price,
            "stop_loss_price": hypothesis.stop_loss_price,
            "thesis_text": hypothesis.thesis_text,
            "invalidation_triggers": [t.model_dump() for t in hypothesis.invalidation_triggers],
            "status": "PENDING",
        }
        record = create_hypothesis(db_payload)

        return {
            "hypothesis_id": record["id"],
            "hypothesis_data": hypothesis.model_dump(),
            "status": "PENDING",
            "error": None,
        }

    except Exception as e:
        return {
            "error": f"Phase 1 failed: {str(e)}",
            "status": "ABORTED",
        }
