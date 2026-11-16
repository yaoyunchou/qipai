-- 报销分类新增「生活支出」LIVING
-- 注意：ALTER TYPE ... ADD VALUE 需在自动提交模式下执行（迁移脚本已使用 autocommit）

DO $$ BEGIN
  ALTER TYPE expense_category ADD VALUE IF NOT EXISTS 'LIVING';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
