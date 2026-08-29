-- ============================================================
-- XAI Trading Agent — Seed Data
-- Run this AFTER schema.sql and rls_policies.sql
-- Creates a placeholder account row for local development.
-- Replace the user_id with your actual Supabase auth user UUID.
-- ============================================================

-- NOTE: You must be authenticated as the user with this UUID
-- for RLS policies to permit future access to related rows.

INSERT INTO public.accounts (user_id, display_name, alpaca_paper)
VALUES (
    '00000000-0000-0000-0000-000000000000',  -- Replace with your auth.users UUID
    'Dev Account',
    TRUE
)
ON CONFLICT (user_id) DO NOTHING;
