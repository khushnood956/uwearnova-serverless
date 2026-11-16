-- ==============================================================================
-- UniNova E-Commerce: Security Definer Views Fix & Store Settings RLS
-- Migration: 20261116000004_fix_security_definer_views_and_settings_rls.sql
-- Description:
-- 1. Fix Security Definer View linter alerts on v_admin_sales_overview and v_low_stock_alerts
--    by configuring Postgres (security_invoker = true).
-- 2. Add INSERT RLS policy on public.audit_logs for authenticated staff.
-- 3. Create dedicated public.store_settings table with public read RLS and authenticated write RLS.
-- ==============================================================================

-- 1. Security Invoker Views (Postgres 15+)
ALTER VIEW public.v_admin_sales_overview SET (security_invoker = true);
ALTER VIEW public.v_low_stock_alerts SET (security_invoker = true);

-- 2. Audit Logs Insert Policy for Authenticated Operations
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policy WHERE polname = 'Staff insert audit logs' AND polrelid = 'public.audit_logs'::regclass
  ) THEN
    CREATE POLICY "Staff insert audit logs" ON public.audit_logs
      FOR INSERT WITH CHECK (auth.role() = 'authenticated');
  END IF;
END $$;

-- 3. Dedicated Store Settings Table for Dynamic Rates, Methods & Bank Info
CREATE TABLE IF NOT EXISTS public.store_settings (
  key VARCHAR(64) PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by VARCHAR(255)
);

ALTER TABLE public.store_settings ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policy WHERE polname = 'Allow public read store_settings' AND polrelid = 'public.store_settings'::regclass
  ) THEN
    CREATE POLICY "Allow public read store_settings" ON public.store_settings
      FOR SELECT USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policy WHERE polname = 'Allow staff manage store_settings' AND polrelid = 'public.store_settings'::regclass
  ) THEN
    CREATE POLICY "Allow staff manage store_settings" ON public.store_settings
      FOR ALL USING (auth.role() = 'authenticated')
      WITH CHECK (auth.role() = 'authenticated');
  END IF;
END $$;
