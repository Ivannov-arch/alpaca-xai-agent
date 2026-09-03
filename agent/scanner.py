"""
scanner.py — Automated Multi-Asset Scanner (Auto-Discovery Engine).

Responsibilities:
  1. Universe: Maintains a configurable 50+ ticker watchlist (crypto + liquid equities).
  2. Screening: Fast OHLCV pre-filter (2-of-3 criteria: Volume Spike, RSI Extreme, Range Breakout).
  3. Risk Awareness: Enforces portfolio aggregate risk cap (6%), daily loss circuit breaker (-5%),
     and escalation caps (max 3 tickers/cycle).
  4. Execution: Passes filtered candidates into the Phase 1 & 2 trade graph with `triggered_by: 'scanner'`.
  5. Telemetry: Tracks scan history and telemetry for real-time frontend terminal updates.
"""
from __future__ import annotations
import json
import logging
import os
import math
from datetime import datetime, timezone
from typing import Optional, Any

from agent.risk import (
    calculate_portfolio_risk_exposure,
    validate_portfolio_risk_budget,
    check_daily_circuit_breaker,
    DEFAULT_AGGREGATE_RISK_CAP_PCT,
    DEFAULT_DAILY_CIRCUIT_BREAKER_PCT,
    DEFAULT_MAX_ESCALATIONS_PER_CYCLE,
)

logger = logging.getLogger(__name__)

# ── Default 50+ Asset Universe ────────────────────────────────────────────────
DEFAULT_CRYPTO_WATCHLIST = [
    "BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "AVAX/USD",
    "LINK/USD", "DOT/USD", "ADA/USD", "LTC/USD", "XRP/USD",
    "NEAR/USD", "UNI/USD", "MATIC/USD", "SHIB/USD", "BCH/USD", "ATOM/USD"
]

DEFAULT_STOCK_WATCHLIST = [
    "AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "GOOGL", "META", "AMD",
    "INTC", "NFLX", "SPY", "QQQ", "IWM", "COIN", "PLTR", "ARM",
    "SMCI", "MU", "AVGO", "DIS", "JPM", "BAC", "V", "MA",
    "PYPL", "CRM", "ORCL", "CSCO", "ADBE", "UBER", "ABNB", "SQ",
    "MARA", "RIOT", "MSTR", "HOOD"
]

DEFAULT_WATCHLIST = DEFAULT_CRYPTO_WATCHLIST + DEFAULT_STOCK_WATCHLIST

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "scanner_config.json")

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "interval_minutes": 15,
    "watchlist": DEFAULT_WATCHLIST,
    "criteria_threshold": 2,          # 2 of 3 criteria must pass
    "volume_spike_multiplier": 1.5,  # 1.5x of 20-period volume SMA
    "rsi_oversold": 35.0,
    "rsi_overbought": 65.0,
    "breakout_period": 20,            # 20-day high/low breakout
    "max_escalations_per_cycle": DEFAULT_MAX_ESCALATIONS_PER_CYCLE,
    "aggregate_risk_cap_pct": DEFAULT_AGGREGATE_RISK_CAP_PCT * 100, # 6.0 %
    "daily_circuit_breaker_pct": DEFAULT_DAILY_CIRCUIT_BREAKER_PCT * 100, # -5.0 %
    "strategy_profile": "SWING",
    "risk_mode": "percent",
    "risk_value": 1.0,
}


# ── Configuration Management ──────────────────────────────────────────────────

def load_scanner_config() -> dict[str, Any]:
    """Loads scanner configuration from disk or returns default config."""
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
                merged = {**DEFAULT_CONFIG, **saved}
                return merged
        except Exception as e:
            logger.warning(f"[scanner] Error loading config from {CONFIG_FILE_PATH}: {e}")
    return DEFAULT_CONFIG.copy()


def save_scanner_config(config: dict[str, Any]) -> dict[str, Any]:
    """Saves updated scanner configuration to disk."""
    merged = {**load_scanner_config(), **config}
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
        logger.info("[scanner] Saved updated scanner config.")
    except Exception as e:
        logger.error(f"[scanner] Failed to save config: {e}")
    return merged


# ── In-Memory Scanner Telemetry & State ────────────────────────────────────────

class ScannerState:
    def __init__(self):
        self.is_scanning: bool = False
        self.last_scan_time: Optional[str] = None
        self.next_scan_time: Optional[str] = None
        self.last_cycle_summary: dict[str, Any] = {
            "timestamp": None,
            "scanned_count": 0,
            "passed_count": 0,
            "escalated_count": 0,
            "circuit_breaker_tripped": False,
            "circuit_breaker_msg": None,
            "tickers": [],
            "errors": [],
        }
        self.last_error: Optional[str] = None

_scanner_state = ScannerState()


# ── Lightweight Technical Pre-Filter ──────────────────────────────────────────

def compute_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """Calculates Wilder's RSI from a series of close prices."""
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0.0, d) for d in deltas]
    losses = [max(0.0, -d) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0 and avg_gain == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_volume_spike(volumes: list[float], period: int = 20, multiplier: float = 1.5) -> tuple[bool, float]:
    """Checks if latest volume is greater than multiplier * average volume."""
    if len(volumes) < period:
        return False, 1.0
    recent_vols = volumes[-period - 1:-1]
    avg_vol = sum(recent_vols) / len(recent_vols) if recent_vols else 1.0
    if avg_vol <= 0:
        avg_vol = 1.0
    latest_vol = volumes[-1]
    ratio = latest_vol / avg_vol
    return ratio >= multiplier, round(ratio, 2)


def compute_range_breakout(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 20
) -> tuple[bool, str]:
    """
    Checks if latest close breaks above the highest high or below lowest low of the last `period` bars.
    Also considers ATR expansion.
    """
    if len(closes) < period + 1 or len(highs) < period + 1 or len(lows) < period + 1:
        return False, "insufficient_data"

    recent_highs = highs[-period - 1:-1]
    recent_lows = lows[-period - 1:-1]
    latest_close = closes[-1]

    highest_high = max(recent_highs)
    lowest_low = min(recent_lows)

    if latest_close > highest_high:
        return True, "bullish_breakout"
    if latest_close < lowest_low:
        return True, "bearish_breakdown"

    # ATR expansion check
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    
    if len(trs) >= 14:
        atr = sum(trs[-14:]) / 14
        latest_tr = trs[-1]
        if atr > 0 and latest_tr >= (1.75 * atr):
            return True, "volatility_expansion"

    return False, "in_range"


def screen_ticker(symbol: str, bars: list[dict], config: dict[str, Any]) -> dict[str, Any]:
    """
    Screens a single ticker using OHLCV bars against the 2-of-3 technical criteria.
    Criteria:
      1. Volume Spike (latest volume >= volume_spike_multiplier * 20-bar avg)
      2. RSI Extreme (RSI <= rsi_oversold OR RSI >= rsi_overbought)
      3. Range Breakout / ATR Expansion (20-day High/Low breakout)
    """
    if not bars or len(bars) < 15:
        return {
            "symbol": symbol,
            "passed": False,
            "passed_count": 0,
            "criteria_met": [],
            "metrics": {},
            "reason": "Insufficient OHLCV data",
        }

    closes = [float(b["c"]) for b in bars]
    highs = [float(b["h"]) for b in bars]
    lows = [float(b["l"]) for b in bars]
    volumes = [float(b["v"]) for b in bars]

    criteria_met: list[str] = []

    # 1. Volume Spike
    vol_mult = float(config.get("volume_spike_multiplier", 1.5))
    is_vol_spike, vol_ratio = compute_volume_spike(volumes, period=min(20, len(volumes) - 1), multiplier=vol_mult)
    if is_vol_spike:
        criteria_met.append(f"Volume Spike ({vol_ratio:.1f}x avg)")

    # 2. RSI Extreme
    rsi_val = compute_rsi(closes, period=14)
    oversold = float(config.get("rsi_oversold", 35.0))
    overbought = float(config.get("rsi_overbought", 65.0))
    if rsi_val is not None:
        if rsi_val <= oversold:
            criteria_met.append(f"RSI Oversold ({rsi_val:.1f})")
        elif rsi_val >= overbought:
            criteria_met.append(f"RSI Overbought ({rsi_val:.1f})")

    # 3. Range Breakout
    breakout_period = int(config.get("breakout_period", 20))
    is_breakout, breakout_type = compute_range_breakout(
        highs, lows, closes, period=min(breakout_period, len(closes) - 1)
    )
    if is_breakout:
        criteria_met.append(f"Breakout ({breakout_type.replace('_', ' ')})")

    threshold = int(config.get("criteria_threshold", 2))
    passed = len(criteria_met) >= threshold

    return {
        "symbol": symbol,
        "passed": passed,
        "passed_count": len(criteria_met),
        "criteria_met": criteria_met,
        "metrics": {
            "latest_close": closes[-1],
            "volume_ratio": vol_ratio,
            "rsi": round(rsi_val, 2) if rsi_val is not None else None,
            "breakout_type": breakout_type,
        },
        "reason": f"Passed {len(criteria_met)}/{threshold} criteria" if passed else f"Only {len(criteria_met)}/{threshold} criteria met",
    }


# ── Core Scanner Cycle Orchestrator ───────────────────────────────────────────

async def run_scanner_cycle(
    account_id: Optional[str] = None,
    is_manual: bool = False,
) -> dict[str, Any]:
    """
    Executes a complete scanning and auto-discovery cycle:
      1. Loads latest config & checks if enabled.
      2. Evaluates Alpaca account equity & daily circuit breaker.
      3. Gathers active open hypotheses to avoid duplicate positions.
      4. Calculates current aggregate portfolio risk exposure against 6% cap.
      5. Scans each watchlist asset with lightweight pre-filter.
      6. Selects top candidates (up to max_escalations_per_cycle).
      7. For each candidate, verifies remaining risk budget and triggers Phase 1+2.
      8. Persists cycle telemetry.
    """
    global _scanner_state
    if _scanner_state.is_scanning:
        logger.warning("[scanner] Scan cycle already in progress — skipping.")
        return {"status": "SKIPPED", "reason": "Scan cycle already in progress"}

    config = load_scanner_config()
    if not config.get("enabled", True) and not is_manual:
        logger.info("[scanner] Auto-scanner is disabled in configuration.")
        return {"status": "DISABLED", "reason": "Auto-scanner is disabled"}

    # Lazy imports to ensure clean initialization
    from agent.tools.alpaca_tools import get_market_data, get_account
    from agent.db import get_active_hypotheses
    from agent.graph import trade_graph

    _scanner_state.is_scanning = True
    start_time = datetime.now(timezone.utc)
    _scanner_state.last_scan_time = start_time.isoformat()

    logger.info(f"[scanner] Starting scan cycle (manual={is_manual}) across {len(config.get('watchlist', []))} tickers...")

    cycle_errors: list[str] = []
    screened_tickers: list[dict[str, Any]] = []
    escalated_tickers: list[dict[str, Any]] = []

    try:
        # ── 1. Fetch Alpaca Account & Check Circuit Breaker ───────────
        try:
            account_data = get_account()
            equity = float(account_data.get("equity") or account_data.get("portfolio_value") or 100_000.0)
            last_equity = float(account_data.get("last_equity") or equity)
        except Exception as e:
            logger.warning(f"[scanner] Failed to get live account data from Alpaca: {e}")
            equity = 100_000.0
            last_equity = 100_000.0
            cycle_errors.append(f"Alpaca account fetch warning: {e}")

        # Check daily loss circuit breaker (-5% limit)
        circuit_threshold = float(config.get("daily_circuit_breaker_pct", -5.0)) / 100.0
        tripped, daily_pnl_pct = check_daily_circuit_breaker(equity, last_equity, circuit_threshold)
        if tripped:
            msg = f"Daily Circuit Breaker TRIPPED! Daily equity dropped {daily_pnl_pct:.2f}% (Limit: {circuit_threshold * 100:.1f}%). Scanner halted."
            logger.error(f"[scanner] {msg}")
            _scanner_state.last_cycle_summary = {
                "timestamp": start_time.isoformat(),
                "scanned_count": 0,
                "passed_count": 0,
                "escalated_count": 0,
                "circuit_breaker_tripped": True,
                "circuit_breaker_msg": msg,
                "tickers": [],
                "errors": [msg],
            }
            _scanner_state.is_scanning = False
            return {"status": "HALTED", "reason": msg, "daily_pnl_pct": daily_pnl_pct}

        # ── 2. Get Active Hypotheses (Deduplication + Risk Calc) ──────
        try:
            active_hypotheses = get_active_hypotheses()
        except Exception as e:
            logger.warning(f"[scanner] Failed to fetch active hypotheses from DB: {e}")
            active_hypotheses = []

        # Find symbols already in an active or pending state
        active_symbols = set()
        for h in active_hypotheses:
            sym = h.get("symbol", "").strip().upper()
            if sym:
                active_symbols.add(sym)

        # Check aggregate portfolio risk exposure
        portfolio_risk = calculate_portfolio_risk_exposure(equity, active_hypotheses)
        current_dollar_risk = portfolio_risk["total_dollar_risk"]
        aggregate_cap_pct = float(config.get("aggregate_risk_cap_pct", 6.0)) / 100.0

        if portfolio_risk["is_over_cap"]:
            logger.warning(
                f"[scanner] Aggregate risk cap already reached: "
                f"{portfolio_risk['total_risk_pct']:.2f}% / {portfolio_risk['aggregate_cap_pct']:.1f}%. "
                "Scanner will screen but will not open new trades."
            )

        # ── 3. Screen All Watchlist Symbols (Lightweight OHLCV) ────────
        watchlist = config.get("watchlist", DEFAULT_WATCHLIST)
        candidates_passed: list[dict[str, Any]] = []

        for symbol in watchlist:
            clean_sym = symbol.strip().upper()
            if not clean_sym:
                continue

            # Skip symbols that are already active/pending in the portfolio
            is_already_active = clean_sym in active_symbols
            
            try:
                bars = get_market_data(clean_sym, timeframe="1Day", limit=30)
                screen_res = screen_ticker(clean_sym, bars, config)
                screen_res["already_active"] = is_already_active
                screened_tickers.append(screen_res)

                if screen_res["passed"]:
                    if not is_already_active:
                        candidates_passed.append(screen_res)
                    else:
                        screen_res["escalation_status"] = "SKIPPED_ALREADY_ACTIVE"
            except Exception as exc:
                err_str = f"Market data/screening failed for {clean_sym}: {exc}"
                logger.warning(f"[scanner] {err_str}")
                cycle_errors.append(err_str)
                screened_tickers.append({
                    "symbol": clean_sym,
                    "passed": False,
                    "passed_count": 0,
                    "criteria_met": [],
                    "metrics": {},
                    "reason": str(exc),
                    "already_active": is_already_active,
                })

        # Sort candidates by number of passed criteria descending
        candidates_passed.sort(key=lambda x: x.get("passed_count", 0), reverse=True)

        # ── 4. Escalate Top Candidates (Up to Max Escalation Cap) ──────
        max_escalations = int(config.get("max_escalations_per_cycle", DEFAULT_MAX_ESCALATIONS_PER_CYCLE))
        strategy_profile = config.get("strategy_profile", "SWING")
        risk_mode = config.get("risk_mode", "percent")
        risk_value = float(config.get("risk_value", 1.0))
        target_account_id = account_id or "66e809f1-2f0e-4a3a-8ea3-bdb7c2d5a849"

        escalation_count = 0
        running_portfolio_dollar_risk = current_dollar_risk

        for candidate in candidates_passed:
            if escalation_count >= max_escalations:
                candidate["escalation_status"] = "SKIPPED_ESCALATION_CAP_REACHED"
                continue

            sym = candidate["symbol"]

            # Estimate required risk budget before triggering
            estimated_trade_risk = equity * (risk_value / 100.0) if risk_mode == "percent" else risk_value
            can_take_risk, risk_rejection = validate_portfolio_risk_budget(
                equity=equity,
                current_dollar_risk=running_portfolio_dollar_risk,
                new_trade_dollar_risk=estimated_trade_risk,
                aggregate_cap_pct=aggregate_cap_pct,
            )

            if not can_take_risk:
                logger.warning(f"[scanner] Skipping {sym} due to portfolio risk cap: {risk_rejection}")
                candidate["escalation_status"] = f"REJECTED_PORTFOLIO_RISK_CAP: {risk_rejection}"
                continue

            # Escalate candidate through Phase 1 & 2 pipeline
            logger.info(f"[scanner] Escalating {sym} (Passed {candidate['passed_count']} criteria) to Phase 1 & 2...")
            candidate["escalation_status"] = "ESCALATING"

            initial_state = {
                "symbol": sym,
                "account_id": target_account_id,
                "strategy_profile": strategy_profile,
                "risk_mode": risk_mode,
                "risk_value": risk_value,
                "triggered_by": "scanner",
                "computed_qty": None,
                "dollar_risk": None,
                "pct_of_equity": None,
                "hypothesis_id": None,
                "hypothesis_data": None,
                "alpaca_order_id": None,
                "audit_verdict": None,
                "pnl_percentage": None,
                "lesson_learned": None,
                "status": None,
                "error": None,
            }

            try:
                final_state = await trade_graph.ainvoke(initial_state)
                hyp_id = final_state.get("hypothesis_id")
                order_id = final_state.get("alpaca_order_id")
                final_status = final_state.get("status")
                actual_dollar_risk = final_state.get("dollar_risk") or estimated_trade_risk

                if final_state.get("error"):
                    candidate["escalation_status"] = f"FAILED: {final_state['error']}"
                    candidate["error"] = final_state["error"]
                else:
                    candidate["escalation_status"] = f"EXECUTED (Status: {final_status})"
                    candidate["hypothesis_id"] = hyp_id
                    candidate["alpaca_order_id"] = order_id
                    escalation_count += 1
                    running_portfolio_dollar_risk += actual_dollar_risk
                    escalated_tickers.append(candidate)
                    logger.info(f"[scanner] Successfully created trade for {sym} (Hypothesis: {hyp_id}, Order: {order_id})")

            except Exception as e:
                err_msg = f"Execution error for {sym}: {e}"
                logger.error(f"[scanner] {err_msg}")
                candidate["escalation_status"] = f"EXCEPTION: {e}"
                cycle_errors.append(err_msg)

        # ── 5. Record Telemetry Summary ───────────────────────────────
        summary = {
            "timestamp": start_time.isoformat(),
            "scanned_count": len(screened_tickers),
            "passed_count": len([t for t in screened_tickers if t.get("passed")]),
            "escalated_count": escalation_count,
            "circuit_breaker_tripped": False,
            "circuit_breaker_msg": None,
            "portfolio_risk_exposure": calculate_portfolio_risk_exposure(equity, active_hypotheses),
            "tickers": screened_tickers,
            "errors": cycle_errors,
        }

        _scanner_state.last_cycle_summary = summary
        logger.info(
            f"[scanner] Cycle complete: {len(screened_tickers)} scanned, "
            f"{summary['passed_count']} passed pre-filter, {escalation_count} escalated to trade graph."
        )
        return summary

    except Exception as exc:
        err_text = f"Unhandled exception in scanner cycle: {exc}"
        logger.exception(f"[scanner] {err_text}")
        _scanner_state.last_error = err_text
        return {"status": "ERROR", "error": err_text}

    finally:
        _scanner_state.is_scanning = False


# ── Status Query Helper ───────────────────────────────────────────────────────

def get_scanner_status() -> dict[str, Any]:
    """Returns current scanner status, config, and last cycle metrics for frontend."""
    config = load_scanner_config()
    return {
        "enabled": config.get("enabled", True),
        "is_scanning": _scanner_state.is_scanning,
        "last_scan_time": _scanner_state.last_scan_time,
        "next_scan_time": _scanner_state.next_scan_time,
        "interval_minutes": config.get("interval_minutes", 15),
        "watchlist_count": len(config.get("watchlist", [])),
        "criteria_threshold": config.get("criteria_threshold", 2),
        "max_escalations_per_cycle": config.get("max_escalations_per_cycle", DEFAULT_MAX_ESCALATIONS_PER_CYCLE),
        "aggregate_risk_cap_pct": config.get("aggregate_risk_cap_pct", DEFAULT_AGGREGATE_RISK_CAP_PCT * 100),
        "daily_circuit_breaker_pct": config.get("daily_circuit_breaker_pct", DEFAULT_DAILY_CIRCUIT_BREAKER_PCT * 100),
        "last_cycle": _scanner_state.last_cycle_summary,
        "last_error": _scanner_state.last_error,
    }
