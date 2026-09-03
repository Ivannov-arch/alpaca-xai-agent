"""
worker.py — Background monitoring worker.

Responsibilities:
  - Runs continuously as a long-lived process alongside the FastAPI server.
  - Every AUDIT_INTERVAL_MINUTES, fetches all ACTIVE hypotheses from the DB.
  - For each ACTIVE hypothesis, invokes the audit_graph (Phase 3 → optionally Phase 4).
  - If audit_verdict == CLOSE, Phase 4 (post-mortem) runs automatically via the graph.

Usage (standalone):
  .\\venv\\Scripts\\python.exe -m agent.worker

Usage (via FastAPI lifespan):
  Called automatically when the FastAPI server starts (see api/main.py).
"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agent.config import AUDIT_INTERVAL_MINUTES
from agent.db import get_active_hypotheses
from agent.graph import audit_graph
from agent.scanner import run_scanner_cycle, load_scanner_config

logger = logging.getLogger(__name__)

_global_scheduler: AsyncIOScheduler | None = None


async def _run_audit_cycle() -> None:
    """
    Core audit loop: runs once per scheduled interval.
    Fetches all ACTIVE hypotheses and audits each one.
    """
    active = get_active_hypotheses()
    if not active:
        logger.info("[worker] No ACTIVE hypotheses — skipping audit cycle.")
        return

    logger.info(f"[worker] Audit cycle started: {len(active)} active hypothesis(es).")

    for hyp in active:
        hypothesis_id = hyp["id"]
        symbol = hyp["symbol"]
        account_id = hyp["account_id"]
        logger.info(f"[worker]   Auditing {symbol} ({hypothesis_id})...")

        try:
            # Build the minimal state required by audit_graph (Phase 3 entry)
            initial_state = {
                "symbol": symbol,
                "account_id": account_id,
                "hypothesis_id": hypothesis_id,
                "hypothesis_data": None,       # Phase 3 re-fetches from DB
                "alpaca_order_id": hyp.get("alpaca_order_id"),
                "audit_verdict": None,
                "pnl_percentage": None,
                "lesson_learned": None,
                "status": "ACTIVE",
                "error": None,
            }

            # audit_graph: Phase 3 → (if CLOSE) Phase 4
            final_state = await audit_graph.ainvoke(initial_state)

            verdict = final_state.get("audit_verdict", "HOLD")
            logger.info(
                f"[worker]   {symbol} verdict={verdict}  "
                f"status={final_state.get('status', 'unknown')}"
            )

            if final_state.get("error"):
                logger.warning(f"[worker]   Error for {symbol}: {final_state['error']}")

        except Exception as exc:
            logger.exception(f"[worker]   Unhandled error auditing {symbol}: {exc}")


async def _run_scanner_job() -> None:
    """Background task running the multi-asset auto-scanner cycle."""
    try:
        await run_scanner_cycle(is_manual=False)
    except Exception as exc:
        logger.exception(f"[worker] Unhandled error in scanner job: {exc}")


def create_scheduler() -> AsyncIOScheduler:
    """
    Creates and configures the APScheduler instance.
    Call start() on the returned scheduler to activate the loops.
    """
    global _global_scheduler
    scheduler = AsyncIOScheduler()

    # 1. Audit Cycle (Phase 3 & 4)
    scheduler.add_job(
        _run_audit_cycle,
        trigger="interval",
        minutes=AUDIT_INTERVAL_MINUTES,
        id="audit_cycle",
        name="Audit all ACTIVE hypotheses",
        replace_existing=True,
    )

    # 2. Scanner Cycle (Multi-Asset Auto-Discovery)
    cfg = load_scanner_config()
    interval = cfg.get("interval_minutes", 15)
    scheduler.add_job(
        _run_scanner_job,
        trigger="interval",
        minutes=interval,
        id="scanner_cycle",
        name="Auto-Discovery Multi-Asset Scanner",
        replace_existing=True,
    )

    _global_scheduler = scheduler
    return scheduler


def get_scheduler() -> AsyncIOScheduler | None:
    return _global_scheduler


def update_scanner_job_interval(minutes: int) -> None:
    """Updates the scanner job trigger interval dynamically."""
    if _global_scheduler:
        job = _global_scheduler.get_job("scanner_cycle")
        if job:
            _global_scheduler.reschedule_job(
                "scanner_cycle",
                trigger="interval",
                minutes=max(1, minutes),
            )
            logger.info(f"[worker] Rescheduled scanner job to every {minutes} minutes.")


# ── Standalone entry point ────────────────────────────────────────────

async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger.info(f"[worker] Starting — audit interval: {AUDIT_INTERVAL_MINUTES} min")

    scheduler = create_scheduler()
    scheduler.start()

    # Run initial audit and scanner passes on startup
    await _run_audit_cycle()
    await _run_scanner_job()

    # Keep the process alive
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("[worker] Stopped.")


if __name__ == "__main__":
    asyncio.run(_main())
