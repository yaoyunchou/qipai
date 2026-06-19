-- 报销审批模块
USE `qipai`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 审批权限：由超管/股东授权，被授权用户可被选为审批人
DROP TABLE IF EXISTS `expense_approve_permission`;
CREATE TABLE `expense_approve_permission` (
  `user_id`     BIGINT UNSIGNED NOT NULL COMMENT '被授权可审批的用户',
  `granted_by`  BIGINT UNSIGNED NOT NULL COMMENT '授权人',
  `created_at`  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`user_id`),
  CONSTRAINT `fk_exp_perm_user` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`),
  CONSTRAINT `fk_exp_perm_granter` FOREIGN KEY (`granted_by`) REFERENCES `sys_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报销审批权限';

DROP TABLE IF EXISTS `expense_claim`;
CREATE TABLE `expense_claim` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `claim_no`      VARCHAR(32)     NOT NULL COMMENT '报销单号',
  `applicant_id`  BIGINT UNSIGNED NOT NULL COMMENT '申请人',
  `amount`        DECIMAL(10, 2)  NOT NULL COMMENT '报销金额',
  `remark`        VARCHAR(500)    NULL COMMENT '申请备注',
  `status`        ENUM('PENDING','APPROVED','REJECTED') NOT NULL DEFAULT 'PENDING',
  `submitted_at`  DATETIME(3)     NOT NULL COMMENT '提交时间',
  `created_at`    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at`    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_claim_no` (`claim_no`),
  KEY `idx_applicant_submitted` (`applicant_id`, `submitted_at`),
  KEY `idx_status_submitted` (`status`, `submitted_at`),
  CONSTRAINT `fk_claim_applicant` FOREIGN KEY (`applicant_id`) REFERENCES `sys_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报销申请';

DROP TABLE IF EXISTS `expense_claim_attachment`;
CREATE TABLE `expense_claim_attachment` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `claim_id`      BIGINT UNSIGNED NOT NULL,
  `filename`      VARCHAR(255)    NOT NULL,
  `content_type`  VARCHAR(128)    NOT NULL DEFAULT 'image/jpeg',
  `data_base64`   MEDIUMTEXT      NOT NULL COMMENT 'Base64 编码附件',
  `created_at`    DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  KEY `idx_claim_id` (`claim_id`),
  CONSTRAINT `fk_att_claim` FOREIGN KEY (`claim_id`) REFERENCES `expense_claim` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报销附件';

DROP TABLE IF EXISTS `expense_claim_approver`;
CREATE TABLE `expense_claim_approver` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `claim_id`     BIGINT UNSIGNED NOT NULL,
  `approver_id`  BIGINT UNSIGNED NOT NULL COMMENT '审批人',
  `status`       ENUM('PENDING','APPROVED','REJECTED','SKIPPED') NOT NULL DEFAULT 'PENDING',
  `comment`      VARCHAR(500)    NULL COMMENT '审批意见',
  `acted_at`     DATETIME(3)     NULL COMMENT '审批时间',
  `created_at`   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_claim_approver` (`claim_id`, `approver_id`),
  KEY `idx_approver_status` (`approver_id`, `status`),
  CONSTRAINT `fk_approver_claim` FOREIGN KEY (`claim_id`) REFERENCES `expense_claim` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_approver_user` FOREIGN KEY (`approver_id`) REFERENCES `sys_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报销审批记录';

SET FOREIGN_KEY_CHECKS = 1;
