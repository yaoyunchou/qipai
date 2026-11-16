import { Button, DatePicker, Layout, Modal, Select, Space, Table, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useCallback, useEffect, useState } from "react";
import { api, type OrderItem } from "../api/client";
import AppHeader from "../components/AppHeader";
import { useMe } from "../hooks/useMe";

const { Content } = Layout;
const { RangePicker } = DatePicker;

export default function OrdersPage() {
  const { me, loading: meLoading } = useMe();
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"ALL" | "OPEN" | "CLOSED">("ALL");
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  const [resetting, setResetting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "200" });
      if (status !== "ALL") params.set("status", status);
      if (dateRange?.[0]) params.set("start", dateRange[0].format("YYYY-MM-DD"));
      if (dateRange?.[1]) params.set("end", dateRange[1].format("YYYY-MM-DD"));
      const data = await api<OrderItem[]>(`/api/v1/orders?${params}`);
      setOrders(data);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [status, dateRange]);

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  const resetOperations = () => {
    Modal.confirm({
      title: "运营数据重置",
      content:
        "将清除所有订单、报销单、陪玩记录、借钱记录、基准价变更记录及报销附件，账号、台位、门店配置与审批授权将保留。此操作不可恢复，确认继续？",
      okText: "确认重置",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        setResetting(true);
        try {
          const res = await api<{
            deleted_orders: number;
            deleted_expense_claims: number;
            deleted_price_logs: number;
            deleted_play_companion: number;
            deleted_loan_records: number;
          }>("/api/v1/orders/reset-operations", { method: "POST" });
          message.success(
            `已清除：订单 ${res.deleted_orders} 条、报销 ${res.deleted_expense_claims} 条、陪玩 ${res.deleted_play_companion} 条、借还 ${res.deleted_loan_records} 条、基准价记录 ${res.deleted_price_logs} 条`
          );
          load();
        } catch (e) {
          message.error(e instanceof Error ? e.message : "重置失败");
          throw e;
        } finally {
          setResetting(false);
        }
      },
    });
  };

  if (meLoading) return null;

  const columns: ColumnsType<OrderItem> = [
    { title: "单号", dataIndex: "order_no", width: 140 },
    { title: "台位", dataIndex: "table_name", width: 80 },
    { title: "原价", dataIndex: "base_price", width: 80, render: (v) => `¥${v}` },
    { title: "实收", dataIndex: "actual_price", width: 80, render: (v) => `¥${v}` },
    {
      title: "状态",
      dataIndex: "status",
      width: 80,
      render: (v: OrderItem["status"]) => (
        <Tag color={v === "OPEN" ? "orange" : "default"}>{v === "OPEN" ? "进行中" : "已归档"}</Tag>
      ),
    },
    { title: "开单人", dataIndex: "opened_by_name", width: 100 },
    {
      title: "开单时间",
      dataIndex: "opened_at",
      width: 160,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "清台时间",
      dataIndex: "closed_at",
      width: 160,
      render: (v: string | null) => (v ? dayjs(v).format("YYYY-MM-DD HH:mm") : "-"),
    },
    { title: "备注", dataIndex: "remark", ellipsis: true },
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader title="订单明细" />
      <Content style={{ padding: 24 }}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Select
            value={status}
            style={{ width: 120 }}
            onChange={setStatus}
            options={[
              { label: "全部", value: "ALL" },
              { label: "进行中", value: "OPEN" },
              { label: "已归档", value: "CLOSED" },
            ]}
          />
          <RangePicker value={dateRange} onChange={(v) => setDateRange(v)} allowClear />
          {me?.role === "ADMIN" && (
            <Button danger loading={resetting} onClick={resetOperations}>
              运营数据重置
            </Button>
          )}
        </Space>
        <Table rowKey="id" loading={loading} columns={columns} dataSource={orders} scroll={{ x: 960 }} />
      </Content>
    </Layout>
  );
}
