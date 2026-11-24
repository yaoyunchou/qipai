import {
  Button,
  Card,
  DatePicker,
  Flex,
  Form,
  Input,
  InputNumber,
  Layout,
  Popconfirm,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type CompanionBalance, type CompanionLoanRecord } from "../api/client";
import AppHeader from "../components/AppHeader";
import { useMe } from "../hooks/useMe";

const { Content } = Layout;
const TIME_FORMAT = "YYYY-MM-DD HH:mm";

type FormValues = {
  companion_user_id?: number;
  occurred_at: dayjs.Dayjs;
  amount: number;
  remark?: string;
};

function money(value: string | number): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "¥0.00";
  return `¥${n.toFixed(2)}`;
}

export default function CompanionLoansPage() {
  const { me, loading: meLoading } = useMe();
  const [form] = Form.useForm<FormValues>();
  const [balances, setBalances] = useState<CompanionBalance[]>([]);
  const [records, setRecords] = useState<CompanionLoanRecord[]>([]);
  const [companionId, setCompanionId] = useState<number | undefined>();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const isCompanion = me?.role === "COMPANION";
  const canLend = !!me && ["SHAREHOLDER", "ADMIN"].includes(me.role);
  const canConfirmRepay = canLend;
  const isAdmin = me?.role === "ADMIN";

  const loadAll = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (!isCompanion && companionId) params.set("companion_user_id", String(companionId));
    const qs = params.toString();
    try {
      const [balanceRes, listRes] = await Promise.all([
        api<CompanionBalance[]>("/api/v1/companion-loans/balances"),
        api<CompanionLoanRecord[]>(`/api/v1/companion-loans${qs ? `?${qs}` : ""}`),
      ]);
      setBalances(balanceRes);
      setRecords(listRes);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [companionId, isCompanion]);

  useEffect(() => {
    if (meLoading) return;
    loadAll();
  }, [meLoading, loadAll]);

  const companionOptions = useMemo(
    () =>
      balances.map((c) => ({
        value: c.companion_user_id,
        label: c.display_name && c.display_name !== c.username ? `${c.username} ${c.display_name}` : c.username,
      })),
    [balances]
  );

  const shownBalances = companionId
    ? balances.filter((b) => b.companion_user_id === companionId)
    : balances;
  const lendTotal = shownBalances.reduce((sum, b) => sum + Number(b.lend_total), 0);
  const repayTotal = shownBalances.reduce((sum, b) => sum + Number(b.repay_total), 0);
  const pendingCount = shownBalances.reduce((sum, b) => sum + b.pending_count, 0);
  const balance = lendTotal - repayTotal;

  const submit = async (values: FormValues) => {
    setSubmitting(true);
    try {
      const path = canLend ? "/api/v1/companion-loans/lend" : "/api/v1/companion-loans/repay";
      await api(path, {
        method: "POST",
        body: JSON.stringify({
          companion_user_id: values.companion_user_id ?? null,
          occurred_at: values.occurred_at.format("YYYY-MM-DDTHH:mm:ss"),
          amount: values.amount,
          remark: values.remark ?? null,
        }),
      });
      message.success(canLend ? "放款已记下，等陪玩确认" : "还款已提交，等股东确认");
      form.resetFields();
      form.setFieldsValue({ occurred_at: dayjs() });
      loadAll();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  };

  const confirmRecord = async (id: number) => {
    try {
      await api(`/api/v1/companion-loans/${id}/confirm`, { method: "POST" });
      message.success("已确认");
      loadAll();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "确认失败");
    }
  };

  const removeRecord = async (id: number) => {
    try {
      await api(`/api/v1/companion-loans/${id}`, { method: "DELETE" });
      message.success("已删除");
      loadAll();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "删除失败");
    }
  };

  const columns: ColumnsType<CompanionLoanRecord> = [
    {
      title: "时间",
      dataIndex: "occurred_at",
      width: 150,
      render: (v: string) => dayjs(v).format(TIME_FORMAT),
    },
    {
      title: "陪玩",
      width: 140,
      render: (_, row) =>
        row.companion_name && row.companion_name !== row.companion_username
          ? `${row.companion_username} ${row.companion_name}`
          : row.companion_username,
    },
    {
      title: "类型",
      dataIndex: "direction",
      width: 90,
      render: (v: CompanionLoanRecord["direction"]) =>
        v === "LEND" ? <Tag color="blue">放款</Tag> : <Tag color="red">还款</Tag>,
    },
    {
      title: "金额",
      dataIndex: "amount",
      width: 110,
      align: "right",
      render: (v: string) => money(v),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 110,
      render: (v: CompanionLoanRecord["status"]) =>
        v === "CONFIRMED" ? <Tag color="green">已确认</Tag> : <Tag>待确认</Tag>,
    },
    { title: "备注", dataIndex: "remark", ellipsis: true, render: (v: string | null) => v || "-" },
    {
      title: "确认人",
      width: 120,
      render: (_, row) =>
        row.status === "CONFIRMED" ? row.confirmed_by_name || "-" : row.direction === "LEND" ? "待陪玩" : "待股东",
    },
    {
      title: "操作",
      width: 140,
      render: (_, row) => {
        const canConfirm =
          row.status === "PENDING" &&
          ((row.direction === "LEND" && isCompanion) || (row.direction === "REPAY" && canConfirmRepay));
        return (
          <Space size={0}>
            {canConfirm && (
              <Popconfirm title="确认后会计入欠款" onConfirm={() => confirmRecord(row.id)}>
                <Button type="link" size="small">
                  确认
                </Button>
              </Popconfirm>
            )}
            {isAdmin && (
              <Popconfirm title="删除后不可恢复" onConfirm={() => removeRecord(row.id)}>
                <Button type="link" size="small" danger>
                  删除
                </Button>
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  if (meLoading) return null;

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader title="陪玩借还" />
      <Content style={{ padding: 24, maxWidth: 1100, width: "100%", margin: "0 auto" }}>
        <Card title={canLend ? "记一笔放款" : "发起还款"} style={{ marginBottom: 16 }}>
          <Form form={form} layout="vertical" onFinish={submit} initialValues={{ occurred_at: dayjs() }}>
            <Flex wrap="wrap" gap={12}>
              {canLend && (
                <Form.Item
                  name="companion_user_id"
                  label="陪玩"
                  rules={[{ required: true, message: "请选择陪玩" }]}
                  style={{ flex: "1 1 180px", minWidth: 180 }}
                >
                  <Select
                    placeholder="工号或别名"
                    options={companionOptions.filter((opt) => balances.find((b) => b.companion_user_id === opt.value)?.is_enabled)}
                    showSearch
                    optionFilterProp="label"
                  />
                </Form.Item>
              )}
              <Form.Item
                name="occurred_at"
                label="时间"
                rules={[{ required: true, message: "请选择时间" }]}
                style={{ flex: "1 1 200px", minWidth: 200 }}
              >
                <DatePicker style={{ width: "100%" }} allowClear={false} showTime={{ format: "HH:mm" }} format={TIME_FORMAT} />
              </Form.Item>
              <Form.Item
                name="amount"
                label="金额"
                rules={[{ required: true, message: "请输入金额" }]}
                style={{ flex: "1 1 140px", minWidth: 140 }}
              >
                <InputNumber min={0.01} precision={2} prefix="¥" style={{ width: "100%" }} />
              </Form.Item>
            </Flex>
            <Form.Item name="remark" label="备注">
              <Input.TextArea rows={2} maxLength={500} showCount />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting}>
              {canLend ? "提交放款" : "提交还款"}
            </Button>
          </Form>
        </Card>

        <Card
          title={isCompanion ? "我的借还" : "陪玩借还"}
          extra={
            <Space wrap>
              {!isCompanion && (
                <Select
                  allowClear
                  placeholder="全部陪玩"
                  style={{ minWidth: 160 }}
                  options={companionOptions}
                  value={companionId}
                  onChange={(v) => setCompanionId(v)}
                  showSearch
                  optionFilterProp="label"
                />
              )}
              <Button onClick={loadAll} loading={loading}>
                刷新
              </Button>
            </Space>
          }
        >
          <Flex wrap="wrap" gap={12} style={{ marginBottom: 16 }}>
            <Card size="small" style={{ minWidth: 140 }}>
              <Statistic title="已确认放款" value={lendTotal} precision={2} prefix="¥" />
            </Card>
            <Card size="small" style={{ minWidth: 140 }}>
              <Statistic title="已确认还款" value={repayTotal} precision={2} prefix="¥" />
            </Card>
            <Card size="small" style={{ minWidth: 140 }}>
              <Statistic title="欠款" value={balance} precision={2} prefix="¥" valueStyle={{ color: balance > 0 ? "#cf1322" : undefined }} />
            </Card>
            <Card size="small" style={{ minWidth: 140 }}>
              <Statistic title="待确认" value={pendingCount} suffix="笔" />
            </Card>
          </Flex>
          <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
            欠款只算已确认的流水。放款要陪玩自己点确认，还款要股东或管理员点确认。
          </Typography.Paragraph>
          <Table
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={records}
            pagination={{ pageSize: 10, showSizeChanger: false }}
            scroll={{ x: 980 }}
          />
        </Card>
      </Content>
    </Layout>
  );
}
