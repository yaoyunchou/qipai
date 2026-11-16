     
     -- 陪玩记账：金额支持输赢
-- 语义：amount 正数 = 赢（进账），负数 = 输（支出）
-- 原来 chk_play_companion_amount 限定 amount >= 0，导致输了无法录入，此处放开。

ALTER TABLE play_companion_record
  DROP CONSTRAINT IF EXISTS chk_play_companion_amount;

COMMENT ON COLUMN play_companion_record.amount IS '金额：正数为赢，负数为输';
