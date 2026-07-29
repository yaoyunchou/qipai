-- 报销单作废：新增 VOIDED 状态及审计字段

DO $$ BEGIN
  ALTER TYPE expense_claim_status ADD VALUE IF NOT EXISTS 'VOIDED';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE expense_claim
  ADD COLUMN IF NOT EXISTS void_reason VARCHAR(500),
  ADD COLUMN IF NOT EXISTS voided_by BIGINT REFERENCES sys_user(id),
  ADD COLUMN IF NOT EXISTS voided_at TIMESTAMPTZ(3);
