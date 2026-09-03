"""
config.py — Single source of truth for all environment variables.
Every other module imports from here. Never call os.getenv() elsewhere.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Alpaca ────────────────────────────────────────────────────────────
ALPACA_API_KEY: str = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET_KEY: str = os.environ["ALPACA_SECRET_KEY"]
ALPACA_BASE_URL: str = os.getenv(
    "ALPACA_BASE_URL", "https://paper-api.alpaca.markets"
)

# ── Supabase ──────────────────────────────────────────────────────────
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_PUBLISHABLE_KEY: str = os.environ["SUPABASE_PUBLISHABLE_KEY"]
# Secret key bypasses RLS — only used server-side (agent backend)
SUPABASE_SECRET_KEY: str = os.environ["SUPABASE_SECRET_KEY"]

# ── LLM ───────────────────────────────────────────────────────────────
def _get_gemini_keys() -> list[str]:
    keys = []
    # 1. Comma-separated list from GEMINI_API_KEYS
    raw_keys = os.getenv("GEMINI_API_KEYS", "")
    if raw_keys:
        for k in raw_keys.split(","):
            cleaned = k.strip()
            if cleaned and cleaned not in keys:
                keys.append(cleaned)

    # 2. Check standard GEMINI_API_KEY
    single_key = os.getenv("GEMINI_API_KEY", "").strip()
    if single_key and single_key not in keys:
        keys.append(single_key)

    # 3. Check numbered keys GEMINI_API_KEY_1 ... GEMINI_API_KEY_10
    for i in range(1, 11):
        numbered = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if numbered and numbered not in keys:
            keys.append(numbered)
    return keys

GEMINI_API_KEYS: list[str] = _get_gemini_keys()
GEMINI_API_KEY: str = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else os.getenv("GEMINI_API_KEY", "")

# Fallback model ladder for Gemini
_raw_fallback_models = os.getenv(
    "GEMINI_FALLBACK_MODELS",
    "gemini-2.5-flash,gemini-2.0-flash,gemini-1.5-flash,gemini-1.5-pro,gemini-2.0-flash-lite,gemini-3.6-flash"
)
GEMINI_FALLBACK_MODELS: list[str] = [m.strip() for m in _raw_fallback_models.split(",") if m.strip()]

DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

# Which LLM provider to use: "gemini" | "deepseek" | "openrouter" | "mock"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")

# ── Embedding ─────────────────────────────────────────────────────────
# "gemini" uses gemini-embedding-001 (3072 dims)
EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "gemini")
EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "3072"))

# ── Agent Behaviour ───────────────────────────────────────────────────
AUDIT_INTERVAL_MINUTES: int = int(os.getenv("AUDIT_INTERVAL_MINUTES", "15"))

# ── FastAPI ───────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
