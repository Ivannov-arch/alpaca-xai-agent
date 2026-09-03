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
    return (
        get_client()
        .table("post_mortems")
        .select("*, hypotheses(symbol, side)")
        .order("created_at", desc=True)
        .execute()
        .data
    )
