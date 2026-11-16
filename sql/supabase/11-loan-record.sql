-- 借钱还钱（独立模块）
-- 场景：客人临时向店里借钱、之后还钱，独立成账，不混入台位订单与报销
-- 金额语义：正数为「借出」（客人欠店里），负数为「还钱」（客人还款）；按客人汇总即可得到未还余额

CREATE TABLE IF NOT EXISTS loan_record (
  id          BIGSERIAL PRIMARY KEY,
  loan_date   DATE         NOT NULL,
  borrower    VARCHAR(64)  NOT NULL,
  contact     VARCHAR(64),
  amount      NUMERIC(12, 2) NOT NULL,
  remark      VARCHAR(500),
  created_by  BIGINT       NOT NULL REFERENCES sys_user (id),
  created_at  TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at  TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  CONSTRAINT chk_loan_record_amount CHECK (amount <> 0),
  CONSTRAINT chk_loan_record_borrower CHECK (length(btrim(borrower)) > 0)
);

COMMENT ON TABLE loan_record IS '借钱还钱记录：正数=借出（客人欠款），负数=还钱';
COMMENT ON COLUMN loan_record.amount IS '带符号金额：正数为借出，负数为客人还钱';

CREATE INDEX IF NOT EXISTS idx_loan_record_date
  ON loan_record (loan_date DESC);

CREATE INDEX IF NOT EXISTS idx_loan_record_borrower
  ON loan_record (borrower, loan_date DESC);

CREATE INDEX IF NOT EXISTS idx_loan_record_creator
  ON loan_record (created_by, loan_date DESC);

DROP TRIGGER IF EXISTS trg_loan_record_updated_at ON loan_record;
CREATE TRIGGER trg_loan_record_updated_at
  BEFORE UPDATE ON loan_record
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 禁止通过 Supabase Data API 匿名访问（后端直连 postgres 用户不受影响）
ALTER TABLE loan_record ENABLE ROW LEVEL SECURITY;
