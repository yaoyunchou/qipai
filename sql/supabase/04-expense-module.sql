-- 报销审批模块（PostgreSQL / Supabase）
-- 在已有 schema 上执行

DO $$ BEGIN
  CREATE TYPE expense_claim_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE expense_approver_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'SKIPPED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS expense_approve_permission (
  user_id     BIGINT PRIMARY KEY REFERENCES sys_user(id),
  granted_by  BIGINT NOT NULL REFERENCES sys_user(id),
  created_at  TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
);

CREATE TABLE IF NOT EXISTS expense_claim (
  id            BIGSERIAL PRIMARY KEY,
  claim_no      VARCHAR(32) NOT NULL UNIQUE,
  applicant_id  BIGINT NOT NULL REFERENCES sys_user(id),
  amount        NUMERIC(10, 2) NOT NULL,
  remark        VARCHAR(500),
  status        expense_claim_status NOT NULL DEFAULT 'PENDING',
  submitted_at  TIMESTAMPTZ(3) NOT NULL,
  created_at    TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at    TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
);

CREATE TABLE IF NOT EXISTS expense_claim_attachment (
  id            BIGSERIAL PRIMARY KEY,
  claim_id      BIGINT NOT NULL REFERENCES expense_claim(id) ON DELETE CASCADE,
  filename      VARCHAR(255) NOT NULL,
  content_type  VARCHAR(128) NOT NULL DEFAULT 'image/jpeg',
  data_base64   TEXT NOT NULL,
  created_at    TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
);

CREATE TABLE IF NOT EXISTS expense_claim_approver (
  id           BIGSERIAL PRIMARY KEY,
  claim_id     BIGINT NOT NULL REFERENCES expense_claim(id) ON DELETE CASCADE,
  approver_id  BIGINT NOT NULL REFERENCES sys_user(id),
  status       expense_approver_status NOT NULL DEFAULT 'PENDING',
  comment      VARCHAR(500),
  acted_at     TIMESTAMPTZ(3),
  created_at   TIMESTAMPTZ(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  UNIQUE (claim_id, approver_id)
);

CREATE INDEX IF NOT EXISTS idx_expense_claim_applicant ON expense_claim(applicant_id, submitted_at);
CREATE INDEX IF NOT EXISTS idx_expense_claim_status ON expense_claim(status, submitted_at);
CREATE INDEX IF NOT EXISTS idx_expense_approver ON expense_claim_approver(approver_id, status);
