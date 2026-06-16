import { Card, Input, InputNumber, Layout, Modal, Space, Tag, Typography, message } from "antd";
import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { api, type TableBoardItem } from "../api/client";
import AppHeader from "../components/AppHeader";
import { useMe } from "../hooks/useMe";

const { Content } = Layout;

type StoreConfig = {
  enable_timing: boolean;
  billing_unit_minutes: number;
  base_price: string;
  cashier_allow_custom_price: boolean;
};

function formatDuration(openedAt: string) {
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
  const [tables, setTables] = useState<TableBoardItem[]>([]);
  const [storeCfg, setStoreCfg] = useState<StoreConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [tick, setTick] = useState(0);
  const [openModal, setOpenModal] = useState<TableBoardItem | null>(null);
  const [closeModal, setCloseModal] = useState<TableBoardItem | null>(null);
  const [actualPrice, setActualPrice] = useState<number | null>(null);
  const [remark, setRemark] = useState("");
  const [closePrice, setClosePrice] = useState<number | null>(null);

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
    if (!tables.some((t) => t.status === "OCCUPIED" && t.enable_timing)) return;
    const timer = window.setInterval(() => setTick((n) => n + 1), 1000);
    return () => window.clearInterval(timer);
  }, [tables, tick]);

  const handleOpen = async () => {
    if (!openModal) return;
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
    }
  };

  const handleClose = async () => {
    if (!closeModal?.open_order_id) return;
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
    }
  };

  const openCloseModal = (t: TableBoardItem) => {
    setCloseModal(t);
    setClosePrice(t.actual_price != null ? Number(t.actual_price) : null);
  };

  if (meLoading) return null;
  if (me?.role === "SHAREHOLDER") return <Navigate to="/reports" replace />;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader title="前台开单" />
      <Content style={{ padding: 16 }}>
        {timingEnabled && storeCfg && (
          <Typography.Paragraph type="secondary" style={{ marginBottom: 12 }}>
            计时计费：¥{storeCfg.base_price}/{unitLabel(storeCfg.billing_unit_minutes)}，清台自动结算
          </Typography.Paragraph>
        )}
        <Space wrap size={[12, 12]}>
          {tables.map((t) => (
            <Card
              key={t.id}
              loading={loading}
              style={{
                width: 156,
                borderColor: t.status === "IDLE" ? "#52c41a" : "#ff4d4f",
                borderWidth: 2,
              }}
              onClick={() => {
                if (t.status === "IDLE") {
                  setActualPrice(null);
                  setRemark("");
                  setOpenModal(t);
                } else {
                  openCloseModal(t);
                }
              }}
            >
              <Typography.Text strong>{t.name}</Typography.Text>
              <br />
              <Tag color={t.status === "IDLE" ? "green" : "red"}>
                {t.status === "IDLE" ? "空闲" : "占用"}
              </Tag>
              {t.status === "OCCUPIED" && t.enable_timing && t.opened_at && (
                <div style={{ marginTop: 6, fontSize: 12 }}>
                  <div>{formatDuration(t.opened_at)}</div>
                  <div>预估 ¥{t.actual_price}</div>
                </div>
              )}
              {t.status === "OCCUPIED" && !t.enable_timing && t.actual_price && (
                <div style={{ marginTop: 6 }}>¥{t.actual_price}</div>
              )}
            </Card>
          ))}
        </Space>
      </Content>

      <Modal
        title={timingEnabled ? `开始计时 · ${openModal?.name}` : `开单 · ${openModal?.name}`}
        open={!!openModal}
        onOk={handleOpen}
        onCancel={() => {
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
        onCancel={() => {
          setCloseModal(null);
          setClosePrice(null);
        }}
      >
        <Typography.Paragraph>单号 {closeModal?.open_order_no}</Typography.Paragraph>
        {closeModal?.enable_timing && closeModal.opened_at && (
          <Typography.Paragraph>
            已用时 {formatDuration(closeModal.opened_at)}
            {closeModal.billing_minutes != null && `，计费 ${closeModal.billing_minutes} 分钟`}
          </Typography.Paragraph>
        )}
        <Typography.Paragraph>
          实收金额：¥{closeModal?.actual_price ?? "-"}
        </Typography.Paragraph>
        {(storeCfg?.cashier_allow_custom_price || me?.role === "ADMIN" || me?.role === "MANAGER") && (
          <>
            <Typography.Paragraph type="secondary">可手动改价（留空则按自动计费）</Typography.Paragraph>
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
      </Modal>
    </Layout>
  );
}
