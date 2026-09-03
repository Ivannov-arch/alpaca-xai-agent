"""
api/main.py — FastAPI application entry point.

Endpoints exposed to the Next.js frontend:

  POST /trade/start            → Run Phase 1+2 (formulate + execute a new trade)
  GET  /trade/hypotheses       → List all hypotheses for an account
  GET  /trade/{id}             → Get a single hypothesis with its audit logs
  POST /trade/{id}/audit       → Manually trigger one audit cycle (Phase 3)
  POST /trade/scan-watchlist   → Batch scan a custom list of tickers
  GET  /portfolio              → Live Alpaca account + open positions
  GET  /memory                 → List all post-mortems (vector memory)
  GET  /market-data            → Historical OHLCV bars
  GET  /risk-settings/defaults → Default risk rules & hard ceilings

  # Auto-Scanner Endpoints:
  GET  /scanner/status         → Live scanner worker telemetry, cycle stats & countdown
  POST /scanner/toggle         → Enable / Disable the background auto-scanner
  POST /scanner/trigger        → Run an instant on-demand auto-discovery cycle
  GET  /scanner/config         → Get 50+ ticker watchlist & 2-of-3 criteria settings
  POST /scanner/config         → Update watchlist & criteria settings without redeploy
  GET  /scanner/portfolio-risk → Aggregate portfolio risk exposure vs 6.0% cap
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.graph import trade_graph, audit_graph
from agent.db import (
    list_hypotheses,
    get_hypothesis,
    get_audit_logs,
    list_post_mortems,
    get_active_hypotheses,
)
from agent.tools.alpaca_tools import get_account, get_positions
from agent.worker import create_scheduler, update_scanner_job_interval
from agent.scanner import (
    get_scanner_status,
    load_scanner_config,
    save_scanner_config,
    run_scanner_cycle,
)
from agent.risk import calculate_portfolio_risk_exposure


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
    strategy_profile: str = "SWING"
    risk_mode: str = "percent"   # "percent" | "dollar"
    risk_value: float = 1.0      # 1.0 = 1% of equity (percent mode) or $1.00 (dollar mode)
    triggered_by: str = "manual" # "manual" | "scanner"


class ScanWatchlistRequest(BaseModel):
    account_id: str
    symbols: list[str]
    strategy_profile: str = "SWING"
    risk_mode: str = "percent"
    risk_value: float = 1.0
    triggered_by: str = "manual"


class ToggleScannerRequest(BaseModel):
    enabled: bool


class TriggerScanRequest(BaseModel):
    account_id: str | None = None


class UpdateScannerConfigRequest(BaseModel):
    enabled: bool | None = None
    interval_minutes: int | None = None
    watchlist: list[str] | None = None
    criteria_threshold: int | None = None
    volume_spike_multiplier: float | None = None
    rsi_oversold: float | None = None
    rsi_overbought: float | None = None
    breakout_period: int | None = None
    max_escalations_per_cycle: int | None = None
    aggregate_risk_cap_pct: float | None = None
    daily_circuit_breaker_pct: float | None = None
    strategy_profile: str | None = None
    risk_mode: str | None = None
    risk_value: float | None = None


# ── Routes: Core Trading & Hypotheses ─────────────────────────────────

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
        "symbol": req.symbol.strip().upper(),
        "account_id": req.account_id,
        "strategy_profile": req.strategy_profile,
        # Risk sizing inputs
        "risk_mode": req.risk_mode,
        "risk_value": req.risk_value,
        "triggered_by": req.triggered_by,
        "computed_qty": None,
        "dollar_risk": None,
        "pct_of_equity": None,
        # Graph state
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
        "computed_qty": final_state.get("computed_qty"),
        "dollar_risk": final_state.get("dollar_risk"),
        "pct_of_equity": final_state.get("pct_of_equity"),
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
            "strategy_profile": req.strategy_profile,
            # Risk sizing inputs
            "risk_mode": req.risk_mode,
            "risk_value": req.risk_value,
            "triggered_by": req.triggered_by,
            "computed_qty": None,
            "dollar_risk": None,
            "pct_of_equity": None,
            # Graph state
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
                "computed_qty": final_state.get("computed_qty"),
                "dollar_risk": final_state.get("dollar_risk"),
                "pct_of_equity": final_state.get("pct_of_equity"),
                "error": final_state.get("error"),
            })
        except Exception as e:
            results.append({
                "symbol": symbol,
                "status": "FAILED",
                "error": str(e),
            })
    return {"account_id": req.account_id, "scanned_count": len(req.symbols), "results": results}


# ── Routes: Portfolio & Account ───────────────────────────────────────

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
                "last_equity": account.get("last_equity"),
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


@app.get("/risk-settings/defaults")
async def get_risk_defaults():
    """
    Returns the hard-coded risk ceiling and default values.
    The frontend queries this to display the cap warning to users.
    """
    from agent.risk import (
        HARD_CEILING_PCT,
        DEFAULT_RISK_PCT,
        DEFAULT_AGGREGATE_RISK_CAP_PCT,
        DEFAULT_DAILY_CIRCUIT_BREAKER_PCT,
    )
    return {
        "hard_ceiling_pct": HARD_CEILING_PCT * 100,   # 5.0%
        "default_risk_pct": DEFAULT_RISK_PCT * 100,    # 1.0%
        "aggregate_risk_cap_pct": DEFAULT_AGGREGATE_RISK_CAP_PCT * 100, # 6.0%
        "daily_circuit_breaker_pct": DEFAULT_DAILY_CIRCUIT_BREAKER_PCT * 100, # -5.0%
        "supported_modes": ["percent", "dollar"],
    }


# ── Routes: Automated Multi-Asset Scanner ─────────────────────────────

@app.get("/scanner/status")
async def get_scanner_telemetry():
    """Returns current scanner status, config, and last cycle metrics."""
    return get_scanner_status()


@app.post("/scanner/toggle")
async def toggle_scanner(req: ToggleScannerRequest):
    """Enables or disables the background auto-scanner."""
    cfg = save_scanner_config({"enabled": req.enabled})
    return {"enabled": cfg["enabled"], "message": f"Scanner {'enabled' if req.enabled else 'disabled'} successfully"}


@app.post("/scanner/trigger")
async def trigger_scanner_cycle(req: TriggerScanRequest = None):
    """Triggers an immediate auto-discovery scan cycle."""
    acc_id = req.account_id if req else None
    result = await run_scanner_cycle(account_id=acc_id, is_manual=True)
    return result


@app.get("/scanner/config")
async def get_scanner_configuration():
    """Returns the current 50+ asset watchlist and 2-of-3 criteria configuration."""
    return load_scanner_config()


@app.post("/scanner/config")
async def update_scanner_configuration(req: UpdateScannerConfigRequest):
    """Updates the scanner watchlist and criteria parameters without redeployment."""
    updates = req.model_dump(exclude_unset=True)
    new_cfg = save_scanner_config(updates)
    if "interval_minutes" in updates and updates["interval_minutes"]:
        update_scanner_job_interval(updates["interval_minutes"])
    return new_cfg


@app.get("/scanner/portfolio-risk")
async def get_portfolio_risk_overview(account_id: str = "66e809f1-2f0e-4a3a-8ea3-bdb7c2d5a849"):
    """Returns live aggregate portfolio risk exposure across all active positions."""
    try:
        account_data = get_account()
        equity = float(account_data.get("equity") or account_data.get("portfolio_value") or 100_000.0)
    except Exception:
        equity = 100_000.0

    try:
        active_hypotheses = get_active_hypotheses()
    except Exception:
        active_hypotheses = []

    exposure = calculate_portfolio_risk_exposure(equity, active_hypotheses)
    return exposure
