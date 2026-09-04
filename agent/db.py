"""
db.py — Supabase client singleton + CRUD helpers for all 4 tables.

Interaction pattern:
  - All nodes (phase1–4) call these helpers to read/write the database.
  - Uses the SECRET KEY so it can bypass RLS from the backend.
  - memory.py also calls search_similar_post_mortems() here.
"""
from supabase import create_client, Client
from agent.config import SUPABASE_URL, SUPABASE_SECRET_KEY

# ── Singleton client ──────────────────────────────────────────────────
_client: Client | None = None


def get_client() -> Client:
    """Returns a cached Supabase secret-role client."""
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
    return _client


# ── accounts ──────────────────────────────────────────────────────────

def get_account(account_id: str) -> dict:
    return (
        get_client()
        .table("accounts")
        .select("*")
        .eq("id", account_id)
        .single()
        .execute()
        .data
    )


# ── hypotheses ────────────────────────────────────────────────────────

def ensure_account_exists(account_id: str):
    """Ensures account_id exists in accounts table to prevent foreign key violations."""
    try:
        client = get_client()
        res = client.table("accounts").select("id").eq("id", account_id).execute()
        if not res.data:
            client.table("accounts").insert({"id": account_id, "label": "Recorded Account"}).execute()
    except Exception as e:
        print(f"Warning: ensure_account_exists failed: {e}")


def create_hypothesis(data: dict) -> dict:
    """Insert a new hypothesis row and return the created record."""
    if data.get("account_id"):
        ensure_account_exists(data["account_id"])
    return (
        get_client()
        .table("hypotheses")
        .insert(data)
        .execute()
        .data[0]
    )


def update_hypothesis(hypothesis_id: str, data: dict) -> dict:
    """Patch specific fields on a hypothesis row."""
    return (
        get_client()
        .table("hypotheses")
        .update(data)
        .eq("id", hypothesis_id)
        .execute()
        .data[0]
    )


def get_hypothesis(hypothesis_id: str) -> dict:
    return (
        get_client()
        .table("hypotheses")
        .select("*")
        .eq("id", hypothesis_id)
        .single()
        .execute()
        .data
    )


def get_active_hypotheses() -> list[dict]:
    """Returns all hypotheses with status = ACTIVE (used by Phase 3 worker)."""
    return (
        get_client()
        .table("hypotheses")
        .select("*")
        .eq("status", "ACTIVE")
        .execute()
        .data
    )


def list_hypotheses(account_id: str) -> list[dict]:
    try:
        hypotheses = (
            get_client()
            .table("hypotheses")
            .select("*, post_mortems(pnl_percentage, pnl_absolute, outcome), audit_logs(market_snapshot, created_at)")
            .eq("account_id", account_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )
    except Exception:
        # Fallback to standard query if join fails
        hypotheses = (
            get_client()
            .table("hypotheses")
            .select("*")
            .eq("account_id", account_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )

    for hyp in (hypotheses or []):
        pm_list = hyp.pop("post_mortems", None)
        if pm_list and isinstance(pm_list, list) and len(pm_list) > 0:
            pm = pm_list[0]
            hyp["pnl_percentage"] = pm.get("pnl_percentage")
            hyp["pnl_absolute"] = pm.get("pnl_absolute")
            hyp["outcome"] = pm.get("outcome")
        else:
            hyp.setdefault("pnl_percentage", None)
            hyp.setdefault("pnl_absolute", None)
            hyp.setdefault("outcome", None)

        logs = hyp.pop("audit_logs", None)
        latest_price = None
        if logs and isinstance(logs, list) and len(logs) > 0:
            sorted_logs = sorted(logs, key=lambda x: x.get("created_at", ""), reverse=True)
            snap = sorted_logs[0].get("market_snapshot", {})
            latest_price = snap.get("current_price")
            if hyp.get("status") == "ACTIVE" and hyp.get("pnl_percentage") is None:
                hyp["pnl_percentage"] = snap.get("unrealised_pnl_pct")
                hyp["pnl_absolute"] = snap.get("unrealised_pnl")

        hyp["exit_price"] = latest_price if hyp.get("status") in ("CLOSED", "ACTIVE") else None

        # Dynamic fallback calculation if stored PnL is 0.0 or None while exit_price and entry_price exist
        entry_p = float(hyp.get("entry_price") or 0.0)
        exit_p = float(hyp.get("exit_price") or 0.0)
        qty = float(hyp.get("qty") or 1.0)
        side = (hyp.get("side") or "buy").lower()

        if entry_p > 0 and exit_p > 0:
            calc_pnl_pct = ((exit_p - entry_p) / entry_p) * 100.0 if side == "buy" else ((entry_p - exit_p) / entry_p) * 100.0
            calc_pnl_abs = (exit_p - entry_p) * qty if side == "buy" else (entry_p - exit_p) * qty
            stored_pct = hyp.get("pnl_percentage")
            if stored_pct is None or (abs(float(stored_pct or 0)) < 0.0001 and abs(calc_pnl_pct) > 0.001):
                hyp["pnl_percentage"] = round(calc_pnl_pct, 4)
                hyp["pnl_absolute"] = round(calc_pnl_abs, 2)
                hyp["outcome"] = "WIN" if calc_pnl_pct > 0.1 else ("LOSS" if calc_pnl_pct < -0.1 else "BREAKEVEN")

    return hypotheses or []


# ── audit_logs ────────────────────────────────────────────────────────

def create_audit_log(data: dict) -> dict:
    """Insert a Phase 3 audit result row."""
    return (
        get_client()
        .table("audit_logs")
        .insert(data)
        .execute()
        .data[0]
    )


def get_audit_logs(hypothesis_id: str) -> list[dict]:
    return (
        get_client()
        .table("audit_logs")
        .select("*")
        .eq("hypothesis_id", hypothesis_id)
        .order("created_at", desc=False)
        .execute()
        .data
    )


# ── post_mortems ──────────────────────────────────────────────────────

def create_post_mortem(data: dict) -> dict:
    """Insert a Phase 4 post-mortem row (including embedding vector)."""
    return (
        get_client()
        .table("post_mortems")
        .insert(data)
        .execute()
        .data[0]
    )


def search_similar_post_mortems(
    embedding: list[float],
    threshold: float = 0.78,
    limit: int = 3,
) -> list[dict]:
    """
    Vector similarity search via the match_post_mortems() SQL function.
    Called by memory.py before Phase 1 to retrieve relevant past lessons.
    """
    return (
        get_client()
        .rpc(
            "match_post_mortems",
            {
                "query_embedding": embedding,
                "match_threshold": threshold,
                "match_count": limit,
            },
        )
        .execute()
        .data
    )


def list_post_mortems(account_id: str) -> list[dict]:
    data = (
        get_client()
        .table("post_mortems")
        .select("*, hypotheses(symbol, side, entry_price, qty)")
        .order("created_at", desc=True)
        .execute()
        .data
    )

    for pm in (data or []):
        stored_pct = float(pm.get("pnl_percentage") or 0.0)
        if abs(stored_pct) < 0.0001 and pm.get("hypothesis_id"):
            try:
                hyp = pm.get("hypotheses") or {}
                entry_p = float(hyp.get("entry_price") or 0.0)
                qty = float(hyp.get("qty") or 1.0)
                side = (hyp.get("side") or "buy").lower()
                logs = get_audit_logs(pm["hypothesis_id"])
                if logs and entry_p > 0:
                    sorted_logs = sorted(logs, key=lambda x: x.get("created_at", ""), reverse=True)
                    snap = sorted_logs[0].get("market_snapshot", {})
                    exit_p = float(snap.get("current_price") or 0.0)
                    if exit_p > 0:
                        calc_pct = ((exit_p - entry_p) / entry_p) * 100.0 if side == "buy" else ((entry_p - exit_p) / entry_p) * 100.0
                        calc_abs = (exit_p - entry_p) * qty if side == "buy" else (entry_p - exit_p) * qty
                        if abs(calc_pct) > 0.001:
                            pm["pnl_percentage"] = round(calc_pct, 4)
                            pm["pnl_absolute"] = round(calc_abs, 2)
                            pm["outcome"] = "WIN" if calc_pct > 0.1 else ("LOSS" if calc_pct < -0.1 else "BREAKEVEN")
            except Exception:
                pass

    return data or []
