-- 计时/自动计费 · 增量迁移（在 01、02 之后执行一次）
USE `qipai`;

ALTER TABLE `sys_store_config`
  ADD COLUMN `enable_timing` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1启用计时自动计费' AFTER `base_price`,
  ADD COLUMN `billing_unit_minutes` INT UNSIGNED NOT NULL DEFAULT 60 COMMENT '计费单位分钟数' AFTER `enable_timing`,
  ADD COLUMN `min_billing_units` INT UNSIGNED NOT NULL DEFAULT 1 COMMENT '最低计费单位数' AFTER `billing_unit_minutes`;

ALTER TABLE `biz_order`
  ADD COLUMN `billing_minutes` INT UNSIGNED NULL COMMENT '清台结算计费分钟' AFTER `actual_price`;
