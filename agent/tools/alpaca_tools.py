"""
alpaca_tools.py — HTTP wrappers for the Alpaca REST API.

All agent nodes interact with Alpaca exclusively through this module.
Each function corresponds to one of the 4 MCP actions in the blueprint:

  get_market_data()   → Ingestion   (OHLCV bars for hypothesis formulation)
  create_order()      → Commitment  (open a position — Phase 2)
  get_positions()     → Observation (live PnL snapshot — Phase 3)
  close_position()    → Resolution  (close a position — Phase 4)
  get_account()       → Portfolio   (account balance — API /portfolio endpoint)
"""
import httpx
from agent.config import ALPACA_API_KEY, ALPACA_SECRET_KEY, ALPACA_BASE_URL

# Alpaca market data endpoint (separate from the broker endpoint)
_DATA_URL = "https://data.alpaca.markets"

# Normalise broker URL — strip any trailing /v2 the user may have included in .env
# so we always append /v2/... exactly once when constructing endpoint paths.
_BROKER_URL = ALPACA_BASE_URL.rstrip("/").removesuffix("/v2")

_HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
}


# ── Market Data ───────────────────────────────────────────────────────

def get_market_data(symbol: str, timeframe: str = "1Day", limit: int = 30) -> list[dict]:
    """
    Fetches historical OHLCV bars for a given symbol.
    """
    from datetime import datetime, timedelta
    # Calculate start date (e.g. 45 days ago to ensure we get 'limit' trading days)
    start_date = (datetime.utcnow() - timedelta(days=45)).strftime("%Y-%m-%dT00:00:00Z")
    
    url = f"{_DATA_URL}/v2/stocks/{symbol}/bars"
    params = {
        "timeframe": timeframe,
        "limit": limit,
        "sort": "asc",
        "feed": "iex",  # Go back to iex (free tier)
        "start": start_date
    }
    resp = httpx.get(url, headers=_HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    # Alpaca returns {"bars": null} when market is closed (weekend/holiday)
    # Use 'or []' to handle explicit null, not just missing key
    return resp.json().get("bars") or []


# ── Order Execution ───────────────────────────────────────────────────

def create_order(
    symbol: str,
    qty: float,
    side: str,
    order_type: str = "market",
    limit_price: float | None = None,
    time_in_force: str = "day",
) -> dict:
    """
    Places a paper trading order via Alpaca.

    Args:
        symbol:         Ticker symbol, e.g. "AAPL"
        qty:            Number of shares (fractional supported)
        side:           "buy" or "sell"
        order_type:     "market" or "limit"
        limit_price:    Required if order_type == "limit"
        time_in_force:  "day", "gtc", "ioc", "fok" (default: "day")

    Returns:
        Alpaca order dict including "id" (alpaca_order_id).
    """
    payload: dict = {
        "symbol": symbol,
        "qty": str(qty),
        "side": side,
        "type": order_type,
        "time_in_force": time_in_force,
    }
    if order_type == "limit" and limit_price is not None:
        payload["limit_price"] = str(limit_price)

    resp = httpx.post(
        f"{_BROKER_URL}/v2/orders",
        headers=_HEADERS,
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Position Observation ──────────────────────────────────────────────

def get_positions() -> list[dict]:
    """
    Returns all currently open positions with unrealized PnL.
    Used by the Phase 3 audit worker.
    """
    resp = httpx.get(
        f"{_BROKER_URL}/v2/positions",
        headers=_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_position(symbol: str) -> dict | None:
    """Returns the open position for a specific symbol, or None if not held."""
    try:
        resp = httpx.get(
            f"{_BROKER_URL}/v2/positions/{symbol}",
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


# ── Position Close ────────────────────────────────────────────────────

def close_position(symbol: str) -> dict:
    """
    Closes an open position for the given symbol at market price.
    Called exclusively by Phase 4 when audit_verdict == "CLOSE".
    """
    resp = httpx.delete(
        f"{_BROKER_URL}/v2/positions/{symbol}",
        headers=_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Account Info ──────────────────────────────────────────────────────

def get_account() -> dict:
    """
    Returns account info including cash, portfolio_value, and buying_power.
    Used by the FastAPI /portfolio endpoint.
    """
    resp = httpx.get(
        f"{_BROKER_URL}/v2/account",
        headers=_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
