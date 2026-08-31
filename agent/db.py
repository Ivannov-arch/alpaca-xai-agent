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

def create_hypothesis(data: dict) -> dict:
    """Insert a new hypothesis row and return the created record."""
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
    return (
        get_client()
        .table("hypotheses")
        .select("*")
        .eq("account_id", account_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


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
