"""
risk.py — Dynamic Position Sizing Engine.

Formula:
    position_size = (equity * risk_amount) / stop_loss_distance_per_unit

Where:
    risk_amount       = equity * risk_pct  OR  fixed_dollar_amount (depending on mode)
    stop_loss_distance = abs(entry_price - stop_loss_price)

Safeguards enforced here (server-side, cannot be bypassed by the UI):
    HARD_CEILING_PCT  = 5%  — max % of equity allowed in a single trade
    MIN_NOTIONAL      = $1  — any position worth less than $1 is rejected

Rounding:
    Crypto (symbol contains "/"):  6 decimal places
    Stocks:                        nearest whole share (floor, never round up)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import math


# ── Constants ─────────────────────────────────────────────────────────────────

HARD_CEILING_PCT: float = 0.05   # 5 % of equity max per single trade
MIN_NOTIONAL: float = 1.0        # Minimum $1 position value
DEFAULT_RISK_PCT: float = 0.01   # 1 % default when no settings supplied


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class RiskSettings:
    """
    User-configured risk budget for a single trade.

    mode:
        "percent" — risk_value is interpreted as a percentage of total equity
                    e.g. value=1.0 means "risk 1 % of equity"
        "dollar"  — risk_value is a fixed dollar amount to risk per trade
    value:
        The numeric amount. For percent mode: 1.0 = 1 %, 2.5 = 2.5 %, etc.
        For dollar mode: 500.0 = $500 at risk per trade.
    """
    mode: str = "percent"   # "percent" | "dollar"
    value: float = 1.0      # default 1 %

    @classmethod
    def default(cls) -> "RiskSettings":
        return cls(mode="percent", value=DEFAULT_RISK_PCT * 100)

    def __post_init__(self):
        if self.mode not in ("percent", "dollar"):
            raise ValueError(f"RiskSettings.mode must be 'percent' or 'dollar', got '{self.mode}'")
        if self.value <= 0:
            raise ValueError(f"RiskSettings.value must be > 0, got {self.value}")


@dataclass
class PositionSizeResult:
    """Result returned by calculate_position_size()."""
    qty: float                          # Final computed quantity to trade
    dollar_risk: float                  # Dollar amount at risk (stop-loss distance × qty)
    pct_of_equity: float                # Percentage of equity risked (0–1 scale, e.g. 0.01 = 1%)
    position_value: float               # Total notional value of the position (qty × entry_price)
    capped: bool                        # True if the hard ceiling was hit
    rejection_reason: Optional[str]     # Non-None → trade must be rejected


# ── Core calculation ──────────────────────────────────────────────────────────

def calculate_position_size(
    equity: float,
    entry_price: float,
    stop_loss_price: float,
    risk_settings: RiskSettings,
    is_crypto: bool = False,
    buying_power: Optional[float] = None,
) -> PositionSizeResult:
    """
    Compute the risk-adjusted position size.

    Args:
        equity:           Total account equity in USD.
        entry_price:      Price at which the position will be entered.
        stop_loss_price:  Price level that triggers a loss exit.
        risk_settings:    User-configured risk budget.
        is_crypto:        True for fractional crypto assets; False for whole-share stocks.
        buying_power:     Available buying power. If provided, position value is capped to it.

    Returns:
        PositionSizeResult (check .rejection_reason before placing order)
    """
    # ── 1. Validate inputs ──────────────────────────────────────────────
    if equity <= 0:
        return PositionSizeResult(
            qty=0, dollar_risk=0, pct_of_equity=0,
            position_value=0, capped=False,
            rejection_reason=f"Invalid equity: ${equity:.2f}",
        )
    if entry_price <= 0:
        return PositionSizeResult(
            qty=0, dollar_risk=0, pct_of_equity=0,
            position_value=0, capped=False,
            rejection_reason=f"Invalid entry price: ${entry_price:.2f}",
        )

    stop_distance = abs(entry_price - stop_loss_price)
    if stop_distance < 0.0001:
        return PositionSizeResult(
            qty=0, dollar_risk=0, pct_of_equity=0,
            position_value=0, capped=False,
            rejection_reason=(
                f"Stop-loss distance is effectively zero "
                f"(entry=${entry_price:.4f}, stop=${stop_loss_price:.4f}). "
                "Cannot compute position size."
            ),
        )

    # ── 2. Compute raw dollar-risk budget ───────────────────────────────
    if risk_settings.mode == "percent":
        # value is e.g. 1.0 → means 1 % of equity
        raw_risk_pct = risk_settings.value / 100.0
        raw_dollar_risk = equity * raw_risk_pct
    else:
        # dollar mode: value is the fixed dollar amount
        raw_dollar_risk = risk_settings.value
        raw_risk_pct = raw_dollar_risk / equity

    # ── 3. Apply hard ceiling ───────────────────────────────────────────
    capped = False
    max_dollar_risk = equity * HARD_CEILING_PCT
    if raw_dollar_risk > max_dollar_risk:
        raw_dollar_risk = max_dollar_risk
        raw_risk_pct = HARD_CEILING_PCT
        capped = True

    # ── 4. Calculate raw quantity ────────────────────────────────────────
    raw_qty = raw_dollar_risk / stop_distance

    # ── 5. Cap by buying power ───────────────────────────────────────────
    if buying_power is not None and buying_power > 0:
        max_qty_by_bp = buying_power / entry_price
        if raw_qty > max_qty_by_bp:
            raw_qty = max_qty_by_bp

    # ── 6. Round appropriately ───────────────────────────────────────────
    if is_crypto:
        qty = round(raw_qty, 6)
    else:
        # Stocks: floor to whole shares (never round up — would exceed risk budget)
        qty = math.floor(raw_qty)

    # ── 7. Final sanity checks ───────────────────────────────────────────
    position_value = qty * entry_price
    if qty <= 0:
        return PositionSizeResult(
            qty=0, dollar_risk=0, pct_of_equity=0,
            position_value=0, capped=capped,
            rejection_reason=(
                f"Computed quantity is {qty} after rounding. "
                f"Risk budget (${raw_dollar_risk:.2f}) is too small relative to "
                f"stop distance (${stop_distance:.4f}) and entry price (${entry_price:.2f}). "
                "Consider increasing risk % or using a tighter stop-loss."
            ),
        )

    if position_value < MIN_NOTIONAL:
        return PositionSizeResult(
            qty=0, dollar_risk=0, pct_of_equity=0,
            position_value=0, capped=capped,
            rejection_reason=(
                f"Position value ${position_value:.4f} is below minimum ${MIN_NOTIONAL:.2f}. "
                "Trade rejected."
            ),
        )

    # Recompute actual dollar risk after rounding
    actual_dollar_risk = qty * stop_distance
    actual_pct_of_equity = actual_dollar_risk / equity

    return PositionSizeResult(
        qty=qty,
        dollar_risk=round(actual_dollar_risk, 2),
        pct_of_equity=round(actual_pct_of_equity, 6),
        position_value=round(position_value, 2),
        capped=capped,
        rejection_reason=None,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_crypto_symbol(symbol: str) -> bool:
    """Returns True for crypto-style symbols like BTC/USD, ETH/USD, BTCUSD."""
    return "/" in symbol or symbol.upper().endswith("USD") or symbol.upper().endswith("USDT")


def risk_settings_from_state(state: dict) -> RiskSettings:
    """
    Build a RiskSettings object from AgentState dict.
    Falls back to default (1% percent mode) if fields are missing.
    """
    mode = state.get("risk_mode") or "percent"
    value = state.get("risk_value")
    if value is None or value <= 0:
        value = 1.0  # default 1 %
    try:
        return RiskSettings(mode=mode, value=value)
    except ValueError:
        return RiskSettings.default()
