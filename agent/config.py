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
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

# Which LLM provider to use: "gemini" | "deepseek" | "openrouter"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")

# ── Embedding ─────────────────────────────────────────────────────────
# "gemini" uses text-embedding-004 (768 dims)
EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "gemini")
EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "3072"))

# ── Agent Behaviour ───────────────────────────────────────────────────
AUDIT_INTERVAL_MINUTES: int = int(os.getenv("AUDIT_INTERVAL_MINUTES", "15"))

# ── FastAPI ───────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
