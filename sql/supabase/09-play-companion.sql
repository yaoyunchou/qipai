-- 陪玩记账（独立模块）
-- 场景：客人不够人时安排陪玩，陪玩相关收支单独记账，不混入台位订单

CREATE TABLE IF NOT EXISTS play_companion_record (
  id             BIGSERIAL PRIMARY KEY,
  play_date      DATE        NOT NULL,
  table_id       BIGINT      REFERENCES room_table (id) ON DELETE SET NULL,
  table_name     VARCHAR(64) NOT NULL DEFAULT '',
  duration_hours NUMERIC(6, 2),
  amount         NUMERIC(10, 2) NOT NULL,
  remark         VARCHAR(500),
  created_by     BIGINT      NOT NULL REFERENCES sys_user (id),
  created_at     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at     TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  CONSTRAINT chk_play_companion_amount CHECK (amount >= 0),
  CONSTRAINT chk_play_companion_duration CHECK (duration_hours IS NULL OR duration_hours >= 0)
);

CREATE INDEX IF NOT EXISTS idx_play_companion_date
  ON play_companion_record (play_date DESC);

CREATE INDEX IF NOT EXISTS idx_play_companion_creator
  ON play_companion_record (created_by, play_date DESC);

DROP TRIGGER IF EXISTS trg_play_companion_updated_at ON play_companion_record;
CREATE TRIGGER trg_play_companion_updated_at
  BEFORE UPDATE ON play_companion_record
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
