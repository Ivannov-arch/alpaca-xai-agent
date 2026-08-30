-- ============================================================
-- XAI Trading Agent — Row Level Security (RLS) Policies
-- Run this AFTER schema.sql
-- ============================================================

-- ============================================================
-- accounts: RLS
-- Users can only see and modify their own account row.
-- ============================================================
ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "accounts_select_own" ON public.accounts
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "accounts_insert_own" ON public.accounts
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "accounts_update_own" ON public.accounts
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "accounts_delete_own" ON public.accounts
    FOR DELETE USING (auth.uid() = user_id);

-- ============================================================
-- hypotheses: RLS
-- Users can only access hypotheses belonging to their account.
-- ============================================================
ALTER TABLE public.hypotheses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "hypotheses_select_own" ON public.hypotheses
    FOR SELECT USING (
        account_id IN (
            SELECT id FROM public.accounts WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "hypotheses_insert_own" ON public.hypotheses
    FOR INSERT WITH CHECK (
        account_id IN (
            SELECT id FROM public.accounts WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "hypotheses_update_own" ON public.hypotheses
    FOR UPDATE USING (
        account_id IN (
            SELECT id FROM public.accounts WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "hypotheses_delete_own" ON public.hypotheses
    FOR DELETE USING (
        account_id IN (
            SELECT id FROM public.accounts WHERE user_id = auth.uid()
        )
    );

-- ============================================================
-- audit_logs: RLS
-- Access scoped through hypothesis ownership chain.
-- ============================================================
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "audit_logs_select_own" ON public.audit_logs
    FOR SELECT USING (
        hypothesis_id IN (
            SELECT h.id FROM public.hypotheses h
            JOIN public.accounts a ON h.account_id = a.id
            WHERE a.user_id = auth.uid()
        )
    );

CREATE POLICY "audit_logs_insert_own" ON public.audit_logs
    FOR INSERT WITH CHECK (
        hypothesis_id IN (
            SELECT h.id FROM public.hypotheses h
            JOIN public.accounts a ON h.account_id = a.id
            WHERE a.user_id = auth.uid()
        )
    );

-- ============================================================
-- post_mortems: RLS
-- Access scoped through hypothesis ownership chain.
-- ============================================================
ALTER TABLE public.post_mortems ENABLE ROW LEVEL SECURITY;

CREATE POLICY "post_mortems_select_own" ON public.post_mortems
    FOR SELECT USING (
        hypothesis_id IN (
            SELECT h.id FROM public.hypotheses h
            JOIN public.accounts a ON h.account_id = a.id
            WHERE a.user_id = auth.uid()
        )
    );

CREATE POLICY "post_mortems_insert_own" ON public.post_mortems
    FOR INSERT WITH CHECK (
        hypothesis_id IN (
            SELECT h.id FROM public.hypotheses h
            JOIN public.accounts a ON h.account_id = a.id
            WHERE a.user_id = auth.uid()
        )
    );

-- ============================================================
-- VECTOR SIMILARITY SEARCH FUNCTION
-- Used by agent/memory.py to retrieve relevant past lessons.
-- ============================================================
CREATE OR REPLACE FUNCTION match_post_mortems(
    query_embedding VECTOR(3072),
    match_threshold FLOAT DEFAULT 0.78,
    match_count     INT DEFAULT 3
)
RETURNS TABLE (
    id              UUID,
    hypothesis_id   UUID,
    pnl_percentage  NUMERIC,
    outcome         TEXT,
    lesson_learned  TEXT,
    similarity      FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        pm.id,
        pm.hypothesis_id,
        pm.pnl_percentage,
        pm.outcome,
        pm.lesson_learned,
        1 - (pm.embedding <=> query_embedding) AS similarity
    FROM public.post_mortems pm
    WHERE 1 - (pm.embedding <=> query_embedding) > match_threshold
    ORDER BY similarity DESC
    LIMIT match_count;
$$;
