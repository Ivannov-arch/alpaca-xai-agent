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

def get_alpaca_headers(api_key: str | None = None, secret_key: str | None = None) -> dict:
    """Returns HTTP headers for Alpaca, defaulting to env vars if custom keys not provided or invalid."""
    key = (
        api_key.strip()
        if (api_key and api_key.strip() and api_key.strip() not in ("undefined", "null"))
        else ALPACA_API_KEY
    )
    secret = (
        secret_key.strip()
        if (secret_key and secret_key.strip() and secret_key.strip() not in ("undefined", "null"))
        else ALPACA_SECRET_KEY
    )
    return {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
    }

_HEADERS = get_alpaca_headers()


# ── Market Data ───────────────────────────────────────────────────────

def get_market_data(symbol: str, timeframe: str = "1Day", limit: int = 30) -> list[dict]:
    """
    Fetches historical OHLCV bars for a given symbol (supports Stocks and Crypto).
    Crypto symbols: BTC/USD, ETH/USD, SOL/USD, DOGE/USD, BTCUSD, etc.
    """
    from datetime import datetime, timedelta
    start_date = (datetime.utcnow() - timedelta(days=45)).strftime("%Y-%m-%dT00:00:00Z")
    
    # Standardize crypto symbol format if slash missing (e.g. BTCUSD -> BTC/USD)
    is_crypto = "/" in symbol or symbol.endswith("USD") or symbol.endswith("USDT")
    clean_symbol = symbol
    if is_crypto and "/" not in symbol:
        clean_symbol = f"{symbol[:-3]}/{symbol[-3:]}"

    if is_crypto:
        url = f"{_DATA_URL}/v1beta3/crypto/us/bars"
        params = {
            "symbols": clean_symbol,
            "timeframe": timeframe,
            "limit": limit,
            "start": start_date,
        }
        resp = httpx.get(url, headers=_HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        bars_dict = resp.json().get("bars") or {}
        return bars_dict.get(clean_symbol) or []
    else:
        url = f"{_DATA_URL}/v2/stocks/{symbol}/bars"
        params = {
            "timeframe": timeframe,
            "limit": limit,
            "sort": "asc",
            "feed": "iex",
            "start": start_date,
        }
        resp = httpx.get(url, headers=_HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("bars") or []


# ── Order Execution ───────────────────────────────────────────────────

def create_order(
    symbol: str,
    qty: float,
    side: str,
    order_type: str = "market",
    time_in_force: str = "gtc",
    limit_price: float | None = None,
    api_key: str | None = None,
    secret_key: str | None = None,
) -> dict:
    """
    Places a paper trading order on Alpaca.
    Supports both stocks and crypto (e.g. BTC/USD, ETH/USD).
    """
    is_crypto = "/" in symbol or symbol.endswith("USD") or symbol.endswith("USDT")
    clean_symbol = symbol
    if is_crypto and "/" not in symbol:
        clean_symbol = f"{symbol[:-3]}/{symbol[-3:]}"

    payload = {
        "symbol": clean_symbol,
        "qty": str(qty),
        "side": side,
        "type": order_type,
        "time_in_force": "gtc" if is_crypto else time_in_force,
    }
    if order_type == "limit" and limit_price is not None:
        payload["limit_price"] = str(limit_price)

    headers = get_alpaca_headers(api_key, secret_key)
    resp = httpx.post(
        f"{_BROKER_URL}/v2/orders",
        headers=headers,
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Position Observation ──────────────────────────────────────────────

def get_positions(api_key: str | None = None, secret_key: str | None = None) -> list[dict]:
    """
    Returns all currently open positions with unrealized PnL.
    Used by the Phase 3 audit worker and /portfolio endpoint.
    """
    headers = get_alpaca_headers(api_key, secret_key)
    resp = httpx.get(
        f"{_BROKER_URL}/v2/positions",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_position(symbol: str, api_key: str | None = None, secret_key: str | None = None) -> dict | None:
    """Returns the open position for a specific symbol, or None if not held."""
    import urllib.parse
    clean_sym = urllib.parse.quote(symbol, safe="")
    headers = get_alpaca_headers(api_key, secret_key)
    try:
        resp = httpx.get(
            f"{_BROKER_URL}/v2/positions/{clean_sym}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


# ── Position Close ────────────────────────────────────────────────────

def close_position(symbol: str, api_key: str | None = None, secret_key: str | None = None) -> dict:
    """
    Closes an open position for the given symbol at market price.
    Called exclusively by Phase 4 when audit_verdict == "CLOSE".
    """
    import urllib.parse
    clean_sym = urllib.parse.quote(symbol, safe="")
    headers = get_alpaca_headers(api_key, secret_key)
    resp = httpx.delete(
        f"{_BROKER_URL}/v2/positions/{clean_sym}",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Account Info ──────────────────────────────────────────────────────

def get_account(api_key: str | None = None, secret_key: str | None = None) -> dict:
    """
    Returns Alpaca account metadata (equity, cash, buying power).
    Used by the FastAPI /portfolio endpoint.
    """
    headers = get_alpaca_headers(api_key, secret_key)
    resp = httpx.get(
        f"{_BROKER_URL}/v2/account",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
