-- 陪玩员工账号与陪玩向股东借款
-- 1. 角色增加 COMPANION（陪玩）。用户名即工号，显示名即别名。停用账号不删历史。
-- 2. 陪玩记账精确到小时，并记到具体陪玩。
-- 3. companion_loan 是陪玩和股东之间的往来，与客人借钱 loan_record 分开。
--    放款待陪玩确认，还款待股东确认；只有已确认的流水计入欠款。

DO $$ BEGIN
  ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'COMPANION';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE play_companion_record
  ALTER COLUMN play_date TYPE TIMESTAMP(3) USING play_date::timestamp;

ALTER TABLE play_companion_record
  ADD COLUMN IF NOT EXISTS companion_user_id BIGINT REFERENCES sys_user (id);

CREATE INDEX IF NOT EXISTS idx_play_companion_staff
  ON play_companion_record (companion_user_id, play_date DESC);

CREATE TABLE IF NOT EXISTS companion_loan (
  id                 BIGSERIAL PRIMARY KEY,
  companion_user_id  BIGINT       NOT NULL REFERENCES sys_user (id),
  direction          VARCHAR(8)   NOT NULL,
  amount             NUMERIC(12, 2) NOT NULL,
  status             VARCHAR(16)  NOT NULL DEFAULT 'PENDING',
  occurred_at        TIMESTAMP(3) NOT NULL,
  remark             VARCHAR(500),
  created_by         BIGINT       NOT NULL REFERENCES sys_user (id),
  confirmed_by       BIGINT       REFERENCES sys_user (id),
  confirmed_at       TIMESTAMP(3),
  created_at         TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at         TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  CONSTRAINT chk_companion_loan_direction CHECK (direction IN ('LEND', 'REPAY')),
  CONSTRAINT chk_companion_loan_amount CHECK (amount > 0),
  CONSTRAINT chk_companion_loan_status CHECK (status IN ('PENDING', 'CONFIRMED'))
);

COMMENT ON TABLE companion_loan IS '陪玩向股东借款：LEND=放款待陪玩确认，REPAY=还款待股东确认';
COMMENT ON COLUMN companion_loan.amount IS '正数金额。欠款 = 已确认放款 − 已确认还款';

CREATE INDEX IF NOT EXISTS idx_companion_loan_staff
  ON companion_loan (companion_user_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_companion_loan_status
  ON companion_loan (status, occurred_at DESC);

DROP TRIGGER IF EXISTS trg_companion_loan_updated_at ON companion_loan;
CREATE TRIGGER trg_companion_loan_updated_at
  BEFORE UPDATE ON companion_loan
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE companion_loan ENABLE ROW LEVEL SECURITY;
