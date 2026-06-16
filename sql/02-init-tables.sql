-- 棋牌室开单系统 · 表结构初始化
-- 请在 DbClient 中选定的 MySQL 连接上执行；先执行 01-create-database-qipai.sql

USE `qipai`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
-- 1. 用户与角色
-- 角色: CASHIER 收银员 | MANAGER 门店经理 | SHAREHOLDER 股东 | ADMIN 超级管理员
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  `username`      VARCHAR(64)     NOT NULL COMMENT '登录名',
  `password_hash` VARCHAR(255)    NOT NULL COMMENT '密码哈希（bcrypt 等）',
  `display_name`  VARCHAR(64)     NOT NULL DEFAULT '' COMMENT '显示名称',
  `role`          ENUM('CASHIER','MANAGER','SHAREHOLDER','ADMIN') NOT NULL COMMENT '角色',
  `is_enabled`    TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1启用 0禁用',
  `created_at`    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at`    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_role_enabled` (`role`, `is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户';

-- ---------------------------------------------------------------------------
-- 2. 门店全局配置（单行，超管维护）
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS `sys_store_config`;
CREATE TABLE `sys_store_config` (
  `id`                         TINYINT UNSIGNED NOT NULL DEFAULT 1 COMMENT '固定为 1',
  `base_price`                 DECIMAL(10, 2)   NOT NULL DEFAULT 0.00 COMMENT '当前全场基准价（仅影响新开单）',
  `cashier_allow_custom_price` TINYINT(1)       NOT NULL DEFAULT 1 COMMENT '收银员是否允许改实收价',
  `cashier_allow_export`       TINYINT(1)       NOT NULL DEFAULT 0 COMMENT '收银员是否允许导出 Excel',
  `cashier_report_months`      INT UNSIGNED     NULL COMMENT '收银员报表可查月数，NULL=不限制',
  `admin_report_days`          INT UNSIGNED     NULL COMMENT '超管报表筛选天数上限，NULL=不限制',
  `updated_by`                 BIGINT UNSIGNED  NULL COMMENT '最后修改人',
  `updated_at`                 DATETIME(3)      NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  CONSTRAINT `chk_store_config_singleton` CHECK (`id` = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='门店全局配置';

-- ---------------------------------------------------------------------------
-- 3. 基准价变更记录（审计，不影响历史订单）
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS `price_change_log`;
CREATE TABLE `price_change_log` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `old_price`   DECIMAL(10, 2)  NOT NULL COMMENT '变更前',
  `new_price`   DECIMAL(10, 2)  NOT NULL COMMENT '变更后',
  `changed_by`  BIGINT UNSIGNED NOT NULL COMMENT '操作人',
  `created_at`  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_price_log_user` FOREIGN KEY (`changed_by`) REFERENCES `sys_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='基准价变更日志';

-- ---------------------------------------------------------------------------
-- 4. 台位（桌台）
-- 空闲/占用由 biz_order.status=OPEN 推导，不在此表存实时状态
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS `room_table`;
CREATE TABLE `room_table` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name`        VARCHAR(64)     NOT NULL COMMENT '桌台名称，如 A01',
  `sort_order`  INT             NOT NULL DEFAULT 0 COMMENT '前台展示排序，越小越靠前',
  `is_enabled`  TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '1启用 0停用（停用不可新开单）',
  `created_at`  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at`  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_enabled_sort` (`is_enabled`, `sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='台位';

-- ---------------------------------------------------------------------------
-- 5. 开单订单（核心业务）
-- 一桌一单：同一 table_id 同时仅允许一条 status=OPEN
-- 归档后价格字段不可再改（应用层 + 无 UPDATE 接口）
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS `biz_order`;
CREATE TABLE `biz_order` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `order_no`     VARCHAR(32)     NOT NULL COMMENT '业务单号，可读',
  `table_id`     BIGINT UNSIGNED NOT NULL COMMENT '台位 ID',
  `base_price`   DECIMAL(10, 2)  NOT NULL COMMENT '开单时快照的基准价',
  `actual_price` DECIMAL(10, 2)  NOT NULL COMMENT '实收价',
  `status`       ENUM('OPEN','CLOSED') NOT NULL DEFAULT 'OPEN' COMMENT 'OPEN进行中 CLOSED已清台归档',
  `remark`       VARCHAR(500)    NULL COMMENT '备注',
  `opened_by`    BIGINT UNSIGNED NOT NULL COMMENT '开单人',
  `opened_at`    DATETIME(3)     NOT NULL COMMENT '开单时间',
  `closed_by`    BIGINT UNSIGNED NULL COMMENT '清台人',
  `closed_at`    DATETIME(3)     NULL COMMENT '清台归档时间（报表按此统计营收）',
  `created_at`   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at`   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_table_status` (`table_id`, `status`),
  KEY `idx_opened_by_opened_at` (`opened_by`, `opened_at`),
  KEY `idx_status_closed_at` (`status`, `closed_at`),
  KEY `idx_opened_at` (`opened_at`),
  CONSTRAINT `fk_order_table` FOREIGN KEY (`table_id`) REFERENCES `room_table` (`id`),
  CONSTRAINT `fk_order_opened_by` FOREIGN KEY (`opened_by`) REFERENCES `sys_user` (`id`),
  CONSTRAINT `fk_order_closed_by` FOREIGN KEY (`closed_by`) REFERENCES `sys_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='开单订单';

-- ---------------------------------------------------------------------------
-- 6. 触发器：一桌一单（同桌不可同时两条 OPEN）
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_biz_order_one_open_insert`;
DELIMITER $$
CREATE TRIGGER `trg_biz_order_one_open_insert`
BEFORE INSERT ON `biz_order`
FOR EACH ROW
BEGIN
  IF NEW.`status` = 'OPEN' AND EXISTS (
    SELECT 1 FROM `biz_order` o
    WHERE o.`table_id` = NEW.`table_id` AND o.`status` = 'OPEN'
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '该桌台已有进行中订单，请先清台';
  END IF;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS `trg_biz_order_one_open_update`;
DELIMITER $$
CREATE TRIGGER `trg_biz_order_one_open_update`
BEFORE UPDATE ON `biz_order`
FOR EACH ROW
BEGIN
  IF NEW.`status` = 'OPEN' AND NEW.`table_id` <> OLD.`table_id` AND EXISTS (
    SELECT 1 FROM `biz_order` o
    WHERE o.`table_id` = NEW.`table_id` AND o.`status` = 'OPEN' AND o.`id` <> NEW.`id`
  ) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '目标桌台已有进行中订单';
  END IF;
END$$
DELIMITER ;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------------
-- 7. 初始数据（可按环境修改后执行）
-- 默认超管密码请在部署时替换 password_hash
-- ---------------------------------------------------------------------------
INSERT INTO `sys_store_config` (`id`, `base_price`, `cashier_allow_custom_price`, `cashier_allow_export`, `cashier_report_months`, `admin_report_days`)
VALUES (1, 100.00, 1, 0, 3, NULL)
ON DUPLICATE KEY UPDATE `id` = `id`;

-- 示例台位（可按门店实际删改）
INSERT INTO `room_table` (`name`, `sort_order`, `is_enabled`) VALUES
  ('A01', 10, 1),
  ('A02', 20, 1),
  ('A03', 30, 1),
  ('B01', 40, 1),
  ('B02', 50, 1);

-- 默认超管（密码 placeholder，部署时必须修改）
-- 明文示例 admin123 仅作说明，勿用于生产
INSERT INTO `sys_user` (`username`, `password_hash`, `display_name`, `role`, `is_enabled`)
VALUES (
  'admin',
  '$2b$12$PLACEHOLDER_REPLACE_ON_DEPLOY',
  '超级管理员',
  'ADMIN',
  1
)
ON DUPLICATE KEY UPDATE `username` = `username`;
