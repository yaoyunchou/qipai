-- 报销附件：Base64 改为磁盘路径
-- 已有库执行本脚本后，再运行 python -m scripts.migrate_expense_attachments

ALTER TABLE expense_claim_attachment
  ADD COLUMN IF NOT EXISTS file_path VARCHAR(512);

-- 迁移脚本跑完后再手动执行（或 migrate 脚本自动执行）：
-- ALTER TABLE expense_claim_attachment DROP COLUMN IF EXISTS data_base64;
-- ALTER TABLE expense_claim_attachment ALTER COLUMN file_path SET NOT NULL;
