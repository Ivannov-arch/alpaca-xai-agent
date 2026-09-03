"""
mcp_server.py — Official Model Context Protocol (MCP) Server for Alpaca Trading Agent.

Exposes the 5 core Alpaca MCP actions:
  1. get_market_data(symbol, timeframe, limit)   → Fetches OHLCV candlestick bars
  2. get_option_contracts(underlying_symbol)     → Fetches active Alpaca Call/Put option contracts
  3. create_order(symbol, qty, side, order_type) → Submits equity, crypto, or option orders
  4. get_positions()                             → Returns active open positions
  5. close_position(symbol)                      → Closes an open position at market
"""
import json
import sys
from agent.tools.alpaca_tools import (
    get_market_data,
    get_option_contracts,
    create_order,
    get_positions,
    close_position,
    get_account,
)

MCP_TOOLS_MANIFEST = [
    {
        "name": "alpaca_get_market_data",
        "description": "Fetch historical OHLCV market bars for a symbol from Alpaca.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. AAPL or BTC/USD"},
                "timeframe": {"type": "string", "default": "1Day"},
                "limit": {"type": "integer", "default": 30},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "alpaca_get_option_contracts",
        "description": "Fetch active Alpaca Call or Put option contracts for an underlying symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "underlying_symbol": {"type": "string", "description": "Underlying ticker, e.g. AAPL, NVDA, SPY"},
                "option_type": {"type": "string", "enum": ["call", "put"], "default": "call"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["underlying_symbol"],
        },
    },
    {
        "name": "alpaca_create_order",
        "description": "Submit a market or limit order for equity, crypto, or option contract via Alpaca REST API.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol or OCC option symbol"},
                "qty": {"type": "number", "description": "Order quantity"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
            },
            "required": ["symbol", "qty", "side"],
        },
    },
    {
        "name": "alpaca_get_positions",
        "description": "Retrieve all open portfolio positions from Alpaca.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "alpaca_close_position",
        "description": "Close an active position at market price.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol of the position to close"},
            },
            "required": ["symbol"],
        },
    },
]


def dispatch_mcp_tool(tool_name: str, arguments: dict):
    """Executes the requested Alpaca MCP tool action."""
    if tool_name == "alpaca_get_market_data":
        return get_market_data(
            symbol=arguments["symbol"],
            timeframe=arguments.get("timeframe", "1Day"),
            limit=arguments.get("limit", 30),
        )
    elif tool_name == "alpaca_get_option_contracts":
        return get_option_contracts(
            underlying_symbol=arguments["underlying_symbol"],
            option_type=arguments.get("option_type", "call"),
            limit=arguments.get("limit", 5),
        )
    elif tool_name == "alpaca_create_order":
        return create_order(
            symbol=arguments["symbol"],
            qty=arguments["qty"],
            side=arguments["side"],
            order_type=arguments.get("order_type", "market"),
        )
    elif tool_name == "alpaca_get_positions":
        return get_positions()
    elif tool_name == "alpaca_close_position":
        return close_position(symbol=arguments["symbol"])
    else:
        raise ValueError(f"Unknown MCP tool: {tool_name}")


if __name__ == "__main__":
    print(f"[Alpaca MCP Server] Registered {len(MCP_TOOLS_MANIFEST)} MCP Tools:")
    for tool in MCP_TOOLS_MANIFEST:
        print(f"  - {tool['name']}: {tool['description']}")
