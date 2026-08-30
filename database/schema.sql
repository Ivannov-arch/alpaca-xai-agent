-- ============================================================
-- XAI Trading Agent — Supabase Database Schema
-- Run this in the Supabase SQL Editor BEFORE rls_policies.sql
-- ============================================================

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- TABLE: accounts
-- Stores user profiles and encrypted Alpaca API credentials.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name    TEXT,
    -- Store only the encrypted key references, never plaintext secrets
    alpaca_api_key  TEXT,
    alpaca_secret   TEXT,
    alpaca_paper    BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id)
);

-- ============================================================
-- TABLE: hypotheses
-- The pre-trade contract. One row = one trade cycle.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.hypotheses (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id              UUID NOT NULL REFERENCES public.accounts(id) ON DELETE CASCADE,
    alpaca_order_id         TEXT,
    symbol                  TEXT NOT NULL,
    side                    TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    order_type              TEXT NOT NULL CHECK (order_type IN ('market', 'limit')),
    qty                     NUMERIC NOT NULL,
    entry_price             NUMERIC,
    target_price            NUMERIC,
    stop_loss_price         NUMERIC,
    thesis_text             TEXT NOT NULL,
    invalidation_triggers   JSONB NOT NULL DEFAULT '[]',
    status                  TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACTIVE', 'CLOSED', 'ABORTED')),
    -- Memory context: past lessons retrieved at hypothesis creation
    retrieved_memory_ids    UUID[] DEFAULT '{}',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE: audit_logs
-- Every monitoring loop result, one row per audit cycle per hypothesis.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_id       UUID NOT NULL REFERENCES public.hypotheses(id) ON DELETE CASCADE,
    market_snapshot     JSONB NOT NULL DEFAULT '{}',
    llm_verdict         TEXT NOT NULL CHECK (llm_verdict IN ('HOLD', 'CLOSE')),
    reasoning_summary   TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TABLE: post_mortems
-- Long-term adaptive memory. Stores lessons + pgvector embeddings.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.post_mortems (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_id       UUID NOT NULL REFERENCES public.hypotheses(id) ON DELETE CASCADE,
    pnl_percentage      NUMERIC,
    pnl_absolute        NUMERIC,
    outcome             TEXT CHECK (outcome IN ('WIN', 'LOSS', 'BREAKEVEN')),
    lesson_learned      TEXT NOT NULL,
    -- 3072 dims for gemini-embedding-001
    embedding           VECTOR(3072),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_hypotheses_account_id ON public.hypotheses(account_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_status ON public.hypotheses(status);
CREATE INDEX IF NOT EXISTS idx_hypotheses_symbol ON public.hypotheses(symbol);
CREATE INDEX IF NOT EXISTS idx_audit_logs_hypothesis_id ON public.audit_logs(hypothesis_id);
CREATE INDEX IF NOT EXISTS idx_post_mortems_hypothesis_id ON public.post_mortems(hypothesis_id);

-- Vector similarity search index (IVFFlat — adjust lists based on row count)
CREATE INDEX IF NOT EXISTS idx_post_mortems_embedding
    ON public.post_mortems
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
