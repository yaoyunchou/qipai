-- 报销分类字段（在已有 expense_claim 表上执行）

DO $$ BEGIN
  CREATE TYPE expense_category AS ENUM ('FIXED', 'OPERATIONS', 'SANDBOX');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE expense_claim
  ADD COLUMN IF NOT EXISTS category expense_category NOT NULL DEFAULT 'FIXED';
