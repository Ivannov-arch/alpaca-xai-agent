"""
api/main.py — FastAPI application entry point.

Endpoints exposed to the Next.js frontend:

  POST /trade/start          → Run Phase 1+2 (formulate + execute a new trade)
  GET  /trade/hypotheses     → List all hypotheses for an account
  GET  /trade/{id}           → Get a single hypothesis with its audit logs
  POST /trade/{id}/audit     → Manually trigger one audit cycle (Phase 3)
  GET  /portfolio            → Live Alpaca account + open positions
  GET  /memory               → List all post-mortems (vector memory)

All endpoints require an `account_id` header or query param for scoping.
The worker scheduler starts automatically via FastAPI lifespan.
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header

from agent.graph import trade_graph, audit_graph
from agent.db import (
    list_hypotheses,
    get_hypothesis,
    get_audit_logs,
    list_post_mortems,
)
from agent.tools.alpaca_tools import get_account, get_positions
from agent.worker import create_scheduler


# ── Lifespan: start/stop the background worker ────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown()


# ── App setup ─────────────────────────────────────────────────────────

app = FastAPI(
    title="XAI Trading Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (Vercel deployment + localhost)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request schemas ───────────────────────────────────────────────────

class StartTradeRequest(BaseModel):
    account_id: str
    symbol: str


class ScanWatchlistRequest(BaseModel):
    account_id: str
    symbols: list[str]


# ── Routes ────────────────────────────────────────────────────────────

@app.get("/")
@app.get("/health")
async def health():
    return {"status": "ok", "message": "XAI Trading Agent API is running"}


@app.post("/trade/start")
async def start_trade(req: StartTradeRequest, background_tasks: BackgroundTasks):
    """
    Phase 1 + Phase 2: Formulate hypothesis and execute order.
    Returns immediately with the created hypothesis_id.
    """
    initial_state = {
        "symbol": req.symbol,
        "account_id": req.account_id,
        "hypothesis_id": None,
        "hypothesis_data": None,
        "alpaca_order_id": None,
        "audit_verdict": None,
        "pnl_percentage": None,
        "lesson_learned": None,
        "status": None,
        "error": None,
    }

    final_state = await trade_graph.ainvoke(initial_state)

    if final_state.get("error"):
        raise HTTPException(status_code=400, detail=final_state["error"])

    return {
        "hypothesis_id": final_state["hypothesis_id"],
        "status": final_state["status"],
        "alpaca_order_id": final_state.get("alpaca_order_id"),
    }


@app.get("/trade/hypotheses")
async def list_all_hypotheses(account_id: str):
    """Returns all hypotheses for a given account_id (most recent first)."""
    return list_hypotheses(account_id)


@app.get("/trade/{hypothesis_id}")
async def get_trade(hypothesis_id: str):
    """Returns a single hypothesis with all its audit logs."""
    try:
        hyp = get_hypothesis(hypothesis_id)
        logs = get_audit_logs(hypothesis_id)
        return {"hypothesis": hyp, "audit_logs": logs}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/trade/{hypothesis_id}/audit")
async def manual_audit(hypothesis_id: str):
    """Manually trigger one Phase 3 audit cycle for an ACTIVE hypothesis."""
    try:
        hyp = get_hypothesis(hypothesis_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    if hyp["status"] != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail=f"Hypothesis status is '{hyp['status']}' — only ACTIVE hypotheses can be audited."
        )

    audit_state = {
        "symbol": hyp["symbol"],
        "account_id": hyp["account_id"],
        "hypothesis_id": hypothesis_id,
        "hypothesis_data": None,
        "alpaca_order_id": hyp.get("alpaca_order_id"),
        "audit_verdict": None,
        "pnl_percentage": None,
        "lesson_learned": None,
        "status": "ACTIVE",
        "error": None,
    }

    final_state = await audit_graph.ainvoke(audit_state)

    if final_state.get("error"):
        raise HTTPException(status_code=500, detail=final_state["error"])

    return {
        "hypothesis_id": hypothesis_id,
        "audit_verdict": final_state.get("audit_verdict"),
        "status": final_state.get("status"),
        "lesson_learned": final_state.get("lesson_learned"),
    }


@app.post("/trade/scan-watchlist")
async def scan_watchlist(req: ScanWatchlistRequest):
    """
    Scans a list of user-selected investment symbols (watchlist).
    Formulates hypotheses and auto-executes trades for valid opportunities.
    """
    results = []
    for symbol in req.symbols:
        initial_state = {
            "symbol": symbol.strip().upper(),
            "account_id": req.account_id,
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
            results.append({
                "symbol": symbol,
                "status": final_state.get("status"),
                "hypothesis_id": final_state.get("hypothesis_id"),
                "alpaca_order_id": final_state.get("alpaca_order_id"),
                "error": final_state.get("error"),
            })
        except Exception as e:
            results.append({
                "symbol": symbol,
                "status": "FAILED",
                "error": str(e),
            })
    return {"account_id": req.account_id, "scanned_count": len(req.symbols), "results": results}


@app.get("/portfolio")
async def get_portfolio(
    account_id: str,
    x_alpaca_key: str | None = Header(None, alias="X-Alpaca-Key"),
    x_alpaca_secret: str | None = Header(None, alias="X-Alpaca-Secret"),
):
    """Returns live Alpaca account balance and all open positions (supports custom API keys via headers)."""
    try:
        account = get_account(api_key=x_alpaca_key, secret_key=x_alpaca_secret)
        positions = get_positions(api_key=x_alpaca_key, secret_key=x_alpaca_secret)
        return {
            "account": {
                "portfolio_value": account.get("portfolio_value"),
                "cash": account.get("cash"),
                "buying_power": account.get("buying_power"),
                "equity": account.get("equity"),
            },
            "positions": positions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory")
async def get_memory(account_id: str):
    """Returns all post-mortems (vector memory) for an account."""
    return list_post_mortems(account_id)


@app.get("/market-data")
async def fetch_bars(symbol: str, timeframe: str = "1Day", limit: int = 40):
    """Returns historical OHLCV bars for any stock or crypto symbol with customizable timeframe."""
    from agent.tools.alpaca_tools import get_market_data
    try:
        bars = get_market_data(symbol, timeframe=timeframe, limit=limit)
        return {"symbol": symbol, "timeframe": timeframe, "bars": bars}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

