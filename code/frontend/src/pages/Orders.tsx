import { DatePicker, Layout, Select, Space, Table, Tag, message } from "antd";
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
        </Space>
        <Table rowKey="id" loading={loading} columns={columns} dataSource={orders} scroll={{ x: 960 }} />
      </Content>
    </Layout>
  );
}
