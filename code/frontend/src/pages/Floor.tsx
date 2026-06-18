import { Input, InputNumber, Layout, Modal, Tag, Typography, message } from "antd";
import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api, type TableBoardItem } from "../api/client";
import AppHeader from "../components/AppHeader";
import { useIsMobile } from "../hooks/useIsMobile";
import { useMe } from "../hooks/useMe";

const { Content } = Layout;

type StoreConfig = {
  enable_timing: boolean;
  billing_unit_minutes: number;
  base_price: string;
  cashier_allow_custom_price: boolean;
};

function formatOpenTime(openedAt: string) {
  const d = new Date(openedAt);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatElapsed(openedAt: string) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(openedAt).getTime()) / 1000));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function unitLabel(minutes: number) {
  if (minutes === 60) return "小时";
  if (minutes === 30) return "半小时";
  return `${minutes}分钟`;
}

export default function FloorPage() {
  const { me, loading: meLoading } = useMe();
  const isMobile = useIsMobile();
  const [tables, setTables] = useState<TableBoardItem[]>([]);
  const [storeCfg, setStoreCfg] = useState<StoreConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);
  const [openModal, setOpenModal] = useState<TableBoardItem | null>(null);
  const [closeModal, setCloseModal] = useState<TableBoardItem | null>(null);
  const [actualPrice, setActualPrice] = useState<number | null>(null);
  const [remark, setRemark] = useState("");
  const [closePrice, setClosePrice] = useState<number | null>(null);
  const [openSubmitting, setOpenSubmitting] = useState(false);
  const [closeSubmitting, setCloseSubmitting] = useState(false);

  const timingEnabled = storeCfg?.enable_timing ?? tables.some((t) => t.enable_timing);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [data, cfg] = await Promise.all([
        api<TableBoardItem[]>("/api/v1/tables/board"),
        api<StoreConfig>("/api/v1/config/store"),
      ]);
      setTables(data);
      setStoreCfg(cfg);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!tables.some((t) => t.status === "OCCUPIED" && t.opened_at)) return;
    const timer = window.setInterval(() => setTick((n) => n + 1), 1000);
    return () => window.clearInterval(timer);
  }, [tables]);

  const handleOpen = async () => {
    if (!openModal || openSubmitting) return;
    setOpenSubmitting(true);
    try {
      const payload: { table_id: number; actual_price?: number; remark?: string } = {
        table_id: openModal.id,
      };
      if (!timingEnabled && actualPrice != null) payload.actual_price = actualPrice;
      if (remark.trim()) payload.remark = remark.trim();
      await api("/api/v1/orders/open", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      message.success(timingEnabled ? `${openModal.name} 已开始计时` : `${openModal.name} 开单成功`);
      setOpenModal(null);
      setRemark("");
      load();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "开单失败");
    } finally {
      setOpenSubmitting(false);
    }
  };

  const handleClose = async () => {
    if (!closeModal?.open_order_id || closeSubmitting) return;
    setCloseSubmitting(true);
    try {
      const body: { actual_price?: number } = {};
      if (closePrice != null) body.actual_price = closePrice;
      await api(`/api/v1/orders/${closeModal.open_order_id}/close`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      message.success("已清台归档");
      setCloseModal(null);
      setClosePrice(null);
      load();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "清台失败");
    } finally {
      setCloseSubmitting(false);
    }
  };

  const openCloseModal = (t: TableBoardItem) => {
    setCloseModal(t);
    setClosePrice(null);
  };

  if (meLoading) return null;
  if (me?.role === "SHAREHOLDER") return <Navigate to="/reports" replace />;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader title="前台开单" />
      <Content style={{ padding: isMobile ? 10 : 16, paddingBottom: isMobile ? 16 : 16 }} data-tick={tick}>
        {timingEnabled && storeCfg && (
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12 }}>
            计时计费：¥{storeCfg.base_price}/{unitLabel(storeCfg.billing_unit_minutes)}，清台自动结算
          </Typography.Paragraph>
        )}
        <div style={{
          display: "grid",
          gridTemplateColumns: `repeat(auto-fill, minmax(${isMobile ? 100 : 130}px, 1fr))`,
          gap: isMobile ? 8 : 12,
        }}>
          {tables.map((t) => {
            const occupied = t.status === "OCCUPIED";
            return (
              <div
                key={t.id}
                onClick={() => {
                  if (!occupied) {
                    setActualPrice(null);
                    setRemark("");
                    setOpenModal(t);
                  } else {
                    openCloseModal(t);
                  }
                }}
                style={{
                  height: isMobile ? 110 : 130,
                  border: `2px solid ${occupied ? "#ff4d4f" : "#52c41a"}`,
                  borderRadius: 8,
                  background: occupied ? "#fff2f0" : "#f6ffed",
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: isMobile ? 4 : 6,
                  padding: "8px 6px",
                  userSelect: "none",
                  opacity: loading ? 0.5 : 1,
                  WebkitTapHighlightColor: "transparent",
                }}
              >
                <Typography.Text strong style={{ fontSize: 16 }}>{t.name}</Typography.Text>
                <Tag color={occupied ? "red" : "green"} style={{ margin: 0 }}>
                  {occupied ? "占用" : "空闲"}
                </Tag>
                {occupied && t.opened_at ? (
                  <div style={{ fontSize: 11, color: "#ff4d4f", textAlign: "center", lineHeight: "18px" }}>
                    <div>开台 {formatOpenTime(t.opened_at)}</div>
                    <div>用时 {formatElapsed(t.opened_at)}</div>
                    {t.actual_price && <div>¥{t.actual_price}</div>}
                  </div>
                ) : (
                  <div style={{ fontSize: 11, color: "#95de64", textAlign: "center" }}>点击开单</div>
                )}
              </div>
            );
          })}
        </div>
      </Content>

      <Modal
        title={timingEnabled ? `开始计时 · ${openModal?.name}` : `开单 · ${openModal?.name}`}
        open={!!openModal}
        onOk={handleOpen}
        confirmLoading={openSubmitting}
        cancelButtonProps={{ disabled: openSubmitting }}
        maskClosable={!openSubmitting}
        width={isMobile ? "92vw" : 420}
        style={{ top: isMobile ? 60 : 100 }}
        onCancel={() => {
          if (openSubmitting) return;
          setOpenModal(null);
          setRemark("");
        }}
      >
        {timingEnabled ? (
          <Typography.Paragraph>
            开单后开始计时，清台时按 ¥{storeCfg?.base_price}/{unitLabel(storeCfg?.billing_unit_minutes ?? 60)} 自动计费。
          </Typography.Paragraph>
        ) : (
          <>
            <Typography.Paragraph>实收价（留空则用基准价）</Typography.Paragraph>
            <InputNumber
              style={{ width: "100%" }}
              min={0}
              precision={2}
              value={actualPrice}
              onChange={(v) => setActualPrice(v)}
            />
          </>
        )}
        <Typography.Paragraph style={{ marginTop: 12 }}>备注（选填）</Typography.Paragraph>
        <Input.TextArea rows={2} value={remark} onChange={(e) => setRemark(e.target.value)} maxLength={500} />
      </Modal>

      <Modal
        title={`清台 · ${closeModal?.name}`}
        open={!!closeModal}
        onOk={handleClose}
        confirmLoading={closeSubmitting}
        cancelButtonProps={{ disabled: closeSubmitting }}
        maskClosable={!closeSubmitting}
        width={isMobile ? "92vw" : 420}
        style={{ top: isMobile ? 60 : 100 }}
        onCancel={() => {
          if (closeSubmitting) return;
          setCloseModal(null);
          setClosePrice(null);
        }}
      >
        <Typography.Paragraph>单号 {closeModal?.open_order_no}</Typography.Paragraph>
        {closeModal?.opened_at && (
          <Typography.Paragraph type="secondary">
            开台时间 {formatOpenTime(closeModal.opened_at)}，已用时 {formatElapsed(closeModal.opened_at)}
          </Typography.Paragraph>
        )}
        <Typography.Paragraph>原价：¥{closeModal?.base_price ?? "-"}</Typography.Paragraph>
        {(storeCfg?.cashier_allow_custom_price || me?.role === "ADMIN" || me?.role === "MANAGER") && (
          <>
            <Typography.Paragraph type="secondary">留空则按实收金额</Typography.Paragraph>
            <InputNumber
              style={{ width: "100%" }}
              min={0}
              precision={2}
              value={closePrice}
              onChange={(v) => setClosePrice(v)}
              placeholder={closeModal?.actual_price != null ? String(closeModal.actual_price) : undefined}
            />
          </>
        )}
        {closeModal?.remark ? (
          <Typography.Paragraph style={{ marginTop: 12 }}>
            开台备注：{closeModal.remark}
          </Typography.Paragraph>
        ) : (
          <Typography.Paragraph type="secondary" style={{ marginTop: 12 }}>
            开台备注：无
          </Typography.Paragraph>
        )}
      </Modal>
    </Layout>
  );
}
