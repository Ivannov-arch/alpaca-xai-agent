"""Debug raw Alpaca API response."""
from dotenv import load_dotenv; load_dotenv()
import httpx, os

API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

headers = {
    "APCA-API-KEY-ID": API_KEY,
    "APCA-API-SECRET-KEY": API_SECRET,
}

# Test 1: no date range (current default)
print("=== No date range ===")
r = httpx.get(
    "https://data.alpaca.markets/v2/stocks/AAPL/bars",
    headers=headers,
    params={"timeframe": "1Day", "limit": 5, "sort": "desc", "feed": "iex"},
    timeout=10,
)
print(f"status={r.status_code}")
print(r.json())

# Test 2: explicit date range (last 30 trading days up to yesterday)
print("\n=== With explicit end date (2026-08-29) ===")
r2 = httpx.get(
    "https://data.alpaca.markets/v2/stocks/AAPL/bars",
    headers=headers,
    params={
        "timeframe": "1Day",
        "limit": 5,
        "sort": "desc",
        "feed": "iex",
        "end": "2026-08-29T23:59:00Z",
    },
    timeout=10,
)
print(f"status={r2.status_code}")
print(r2.json())

