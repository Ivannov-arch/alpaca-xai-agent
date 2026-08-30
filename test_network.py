"""Quick network diagnostic — runs each API call independently."""
import socket
import sys

hosts = [
    ("data.alpaca.markets", 443),
    ("paper-api.alpaca.markets", 443),
    ("generativelanguage.googleapis.com", 443),
]

print("=== DNS / Network Check ===")
for host, port in hosts:
    try:
        socket.setdefaulttimeout(5)
        socket.getaddrinfo(host, port)
        print(f"  OK   {host}")
    except Exception as e:
        print(f"  FAIL {host} -> {e}")

print()
print("=== Alpaca Market Data Test ===")
try:
    from dotenv import load_dotenv; load_dotenv()
    from agent.tools.alpaca_tools import get_market_data
    bars = get_market_data("AAPL", limit=5)
    print(f"  OK   got {len(bars)} bars")
except Exception as e:
    print(f"  FAIL {e}")

print()
print("=== Gemini Embedding Test ===")
try:
    from agent.llm import embed_text
    v = embed_text("test")
    print(f"  OK   vector dims={len(v)}")
except Exception as e:
    print(f"  FAIL {e}")
