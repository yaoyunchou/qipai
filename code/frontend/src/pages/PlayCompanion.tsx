import {
  Button,
  Card,
  DatePicker,
  Flex,
  Form,
  Input,
  InputNumber,
  Layout,
  Modal,
  Popconfirm,
  Select,
  Space,
  Statistic,
  Table,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  type PlayCompanionRecord,
  type PlayCompanionSummary,
  type TableBoardItem,
} from "../api/client";
import AppHeader from "../components/AppHeader";
import DirectionSwitch, { type DirectionOption } from "../components/DirectionSwitch";
import { useMe } from "../hooks/useMe";

const { Content } = Layout;
const { RangePicker } = DatePicker;

type AmountDirection = "WIN" | "LOSE";

type FormValues = {
  play_date: dayjs.Dayjs;
  table_id?: number | null;
  duration_hours?: number | null;
  amount_direction: AmountDirection;
  amount_abs: number;
  remark?: string;
};

const AMOUNT_DIRECTION_OPTIONS: DirectionOption[] = [
  { label: "赢", value: "WIN", tone: "red" },
  { label: "输", value: "LOSE", tone: "blue" },
];

const INCOME_COLOR = "#3f8600";
const LOSS_COLOR = "#cf1322";

/** 「赢/输」+ 正数 → 带符号金额（正数为赢，负数为输） */
function toSignedAmount(direction: AmountDirection, abs: number): number {
  const value = Math.abs(abs);
  return direction === "LOSE" ? -value : value;
}

/** 金额展示：+¥80.00 / -¥80.00 */
function signedMoney(value: string | number): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "¥0.00";
  const abs = Math.abs(n).toFixed(2);
  if (n > 0) return `+¥${abs}`;
  if (n < 0) return `-¥${abs}`;
  return "¥0.00";
}

export default function PlayCompanionPage() {
  const { me, loading: meLoading } = useMe();
  const [form] = Form.useForm<FormValues>();
  const [editForm] = Form.useForm<FormValues>();

  const [records, setRecords] = useState<PlayCompanionRecord[]>([]);
  const [tables, setTables] = useState<TableBoardItem[]>([]);
  const [summary, setSummary] = useState<PlayCompanionSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([
    dayjs().startOf("month"),
    dayjs(),
  ]);

  const [editOpen, setEditOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<PlayCompanionRecord | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);

  // 股东只读；收银员 / 经理 / 超管可录入
  const canEdit = !!me && ["CASHIER", "MANAGER", "ADMIN"].includes(me.role);
  const canViewList = canEdit;
  const isAdmin = me?.role === "ADMIN";

  const queryString = useCallback(() => {
    const params = new URLSearchParams();
    if (dateRange?.[0]) params.set("start", dateRange[0].format("YYYY-MM-DD"));
    if (dateRange?.[1]) params.set("end", dateRange[1].format("YYYY-MM-DD"));
    return params.toString();
  }, [dateRange]);

  const loadTables = useCallback(async () => {
    try {
      const data = await api<TableBoardItem[]>("/api/v1/tables/board");
      setTables(data);
    } catch {
      setTables([]);
    }
  }, []);

  const loadRecords = useCallback(async () => {
    const qs = queryString();
    setLoading(true);
    try {
      const [listRes, sumRes] = await Promise.allSettled([
        canViewList
          ? api<PlayCompanionRecord[]>(`/api/v1/play-companion?${qs}`)
          : Promise.resolve([] as PlayCompanionRecord[]),
        api<PlayCompanionSummary>(`/api/v1/play-companion/summary?${qs}`),
      ]);
      if (listRes.status === "fulfilled") setRecords(listRes.value);
      else message.error(listRes.reason instanceof Error ? listRes.reason.message : "加载失败");
      if (sumRes.status === "fulfilled") setSummary(sumRes.value);
    } finally {
      setLoading(false);
    }
  }, [canViewList, queryString]);

  useEffect(() => {
    if (meLoading) return;
    loadTables();
  }, [meLoading, loadTables]);

  useEffect(() => {
    if (meLoading) return;
    loadRecords();
  }, [meLoading, loadRecords]);

  const tableOptions = useMemo(
    () => tables.map((t) => ({ label: t.name, value: t.id })),
    [tables]
  );

  const submitRecord = async (values: FormValues) => {
    setSubmitting(true);
    try {
      await api<PlayCompanionRecord>("/api/v1/play-companion", {
        method: "POST",
        body: JSON.stringify({
          play_date: values.play_date.format("YYYY-MM-DD"),
          table_id: values.table_id ?? null,
          duration_hours: values.duration_hours ?? null,
          amount: toSignedAmount(values.amount_direction, values.amount_abs),
          remark: values.remark ?? null,
        }),
      });
      message.success("陪玩记录已保存");
      form.resetFields();
      form.setFieldsValue({ play_date: dayjs(), amount_direction: "WIN" });
      loadRecords();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  };

  const openEdit = (record: PlayCompanionRecord) => {
    setEditRecord(record);
    const signed = Number(record.amount);
    editForm.setFieldsValue({
      play_date: dayjs(record.play_date),
      table_id: record.table_id,
      duration_hours: record.duration_hours ? Number(record.duration_hours) : null,
      amount_direction: signed < 0 ? "LOSE" : "WIN",
      amount_abs: Math.abs(signed),
      remark: record.remark ?? undefined,
    });
    setEditOpen(true);
  };

  const submitEdit = async (values: FormValues) => {
    if (!editRecord) return;
    setEditSubmitting(true);
    try {
      await api<PlayCompanionRecord>(`/api/v1/play-companion/${editRecord.id}`, {
        method: "PUT",
        body: JSON.stringify({
          play_date: values.play_date.format("YYYY-MM-DD"),
          table_id: values.table_id ?? null,
          duration_hours: values.duration_hours ?? null,
          amount: toSignedAmount(values.amount_direction, values.amount_abs),
          remark: values.remark ?? null,
        }),
      });
      message.success("已更新");
      setEditOpen(false);
      loadRecords();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "更新失败");
    } finally {
      setEditSubmitting(false);
    }
  };

  const removeRecord = async (id: number) => {
    try {
      await api(`/api/v1/play-companion/${id}`, { method: "DELETE" });
      message.success("已删除");
      loadRecords();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "删除失败");
    }
  };

  if (meLoading) return null;

  const columns: ColumnsType<PlayCompanionRecord> = [
    {
      title: "日期",
      dataIndex: "play_date",
      width: 120,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD"),
    },
    {
      title: "台位",
      dataIndex: "table_name",
      width: 100,
      render: (v: string) => v || "-",
    },
    {
      title: "时长(小时)",
      dataIndex: "duration_hours",
      width: 100,
      render: (v: string | null) => (v ? Number(v).toString() : "-"),
    },
    {
      title: "金额",
      dataIndex: "amount",
      width: 110,
      align: "right",
      render: (v: string) => {
        const n = Number(v);
        const color = n > 0 ? INCOME_COLOR : n < 0 ? LOSS_COLOR : undefined;
        return <Typography.Text style={{ color, fontWeight: 500 }}>{signedMoney(v)}</Typography.Text>;
      },
    },
    { title: "备注", dataIndex: "remark", ellipsis: true, render: (v: string | null) => v || "-" },
    { title: "录入人", dataIndex: "created_by_name", width: 100, render: (v: string | null) => v || "-" },
    {
      title: "录入时间",
      dataIndex: "created_at",
      width: 150,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    ...(canEdit
      ? [
          {
            title: "操作",
            width: 130,
            render: (_: unknown, row: PlayCompanionRecord) => {
              const own = row.created_by === me?.id;
              if (!own && !isAdmin) return <Typography.Text type="secondary">-</Typography.Text>;
              return (
                <Space size={0}>
                  <Button type="link" size="small" onClick={() => openEdit(row)}>
                    编辑
                  </Button>
                  {isAdmin && (
                    <Popconfirm
                      title="确认删除这条陪玩记录？"
                      okText="删除"
                      okButtonProps={{ danger: true }}
                      cancelText="取消"
                      onConfirm={() => removeRecord(row.id)}
                    >
                      <Button type="link" danger size="small">
                        删除
                      </Button>
                    </Popconfirm>
                  )}
                </Space>
              );
            },
          },
        ]
      : []),
  ];

  const netTotal = Number(summary?.net_total ?? 0);
  const winTotal = Number(summary?.win_total ?? 0);
  const loseTotal = Number(summary?.lose_total ?? 0);
  const netColor = netTotal > 0 ? INCOME_COLOR : netTotal < 0 ? LOSS_COLOR : undefined;

  const summaryCards = (
    <Flex wrap="wrap" gap={16} style={{ marginBottom: 16 }}>
      <Card size="small" style={{ minWidth: 150 }}>
        <Statistic title="记录笔数" value={summary?.record_count ?? 0} />
      </Card>
      <Card size="small" style={{ minWidth: 150 }}>
        <Statistic
          title="赢合计"
          value={winTotal}
          prefix="+¥"
          precision={2}
          valueStyle={{ color: INCOME_COLOR }}
        />
      </Card>
      <Card size="small" style={{ minWidth: 150 }}>
        <Statistic
          title="输合计"
          value={loseTotal}
          prefix="-¥"
          precision={2}
          valueStyle={{ color: LOSS_COLOR }}
        />
      </Card>
      <Card size="small" style={{ minWidth: 160 }}>
        <Statistic
          title="净额（赢 - 输）"
          value={Math.abs(netTotal)}
          precision={2}
          prefix={netTotal < 0 ? "-¥" : netTotal > 0 ? "+¥" : "¥"}
          valueStyle={{ color: netColor, fontWeight: 600 }}
        />
      </Card>
      <Card size="small" style={{ minWidth: 150 }}>
        <Statistic
          title="合计时长"
          value={summary?.duration_total ?? "0"}
          suffix="小时"
          precision={1}
        />
      </Card>
    </Flex>
  );

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader title="陪玩记账" />
      <Content style={{ padding: 24, maxWidth: 1100, width: "100%", margin: "0 auto" }}>
        {canEdit && (
          <Card title="新增陪玩记录" style={{ marginBottom: 16 }}>
            <Form
              form={form}
              layout="vertical"
              onFinish={submitRecord}
              initialValues={{ play_date: dayjs(), amount_direction: "WIN" }}
            >
              <Flex wrap="wrap" gap={12}>
                <Form.Item
                  name="play_date"
                  label="日期"
                  rules={[{ required: true, message: "请选择日期" }]}
                  style={{ flex: "1 1 180px", minWidth: 180 }}
                >
                  <DatePicker style={{ width: "100%" }} allowClear={false} />
                </Form.Item>
                <Form.Item name="table_id" label="台位" style={{ flex: "1 1 160px", minWidth: 160 }}>
                  <Select
                    allowClear
                    placeholder="可不选"
                    options={tableOptions}
                    showSearch
                    optionFilterProp="label"
                  />
                </Form.Item>
                <Form.Item
                  name="duration_hours"
                  label="时长(小时)"
                  style={{ flex: "1 1 140px", minWidth: 140 }}
                >
                  <InputNumber min={0} step={0.5} precision={2} style={{ width: "100%" }} placeholder="如 2.5" />
                </Form.Item>
                <Form.Item
                  name="amount_direction"
                  label="输赢"
                  initialValue="WIN"
                  style={{ flex: "0 0 auto", minWidth: 110 }}
                >
                  <DirectionSwitch options={AMOUNT_DIRECTION_OPTIONS} />
                </Form.Item>
                <Form.Item
                  name="amount_abs"
                  label="金额"
                  rules={[
                    { required: true, message: "请输入金额" },
                    {
                      validator: (_, value) =>
                        value === undefined || value === null || Number(value) > 0
                          ? Promise.resolve()
                          : Promise.reject(new Error("金额需大于 0，输请切换到「输」")),
                    },
                  ]}
                  style={{ flex: "1 1 140px", minWidth: 140 }}
                >
                  <InputNumber min={0.01} precision={2} prefix="¥" style={{ width: "100%" }} />
                </Form.Item>
              </Flex>
              <Form.Item name="remark" label="备注">
                <Input.TextArea rows={2} maxLength={500} showCount placeholder="例如：3 号桌缺一人，安排陪玩 2 小时" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={submitting}>
                保存记录
              </Button>
            </Form>
          </Card>
        )}

        <Card
          title={canEdit ? "陪玩明细" : "陪玩汇总"}
          extra={
            <Space wrap>
              <RangePicker
                value={dateRange}
                onChange={(v) => setDateRange(v ?? [null, null])}
                allowEmpty={[true, true]}
              />
              <Button onClick={loadRecords} loading={loading}>
                刷新
              </Button>
            </Space>
          }
        >
          {summaryCards}
          {canEdit ? (
            <Table
              rowKey="id"
              loading={loading}
              columns={columns}
              dataSource={records}
              pagination={{ pageSize: 10, showSizeChanger: false }}
              scroll={{ x: 860 }}
            />
          ) : (
            <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
              当前账号为股东角色，仅可查看陪玩汇总数据，明细由收银员 / 经理 / 超管录入。
            </Typography.Paragraph>
          )}
        </Card>
      </Content>

      <Modal
        title="编辑陪玩记录"
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={() => editForm.submit()}
        okText="保存"
        confirmLoading={editSubmitting}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" onFinish={submitEdit}>
          <Form.Item
            name="play_date"
            label="日期"
            rules={[{ required: true, message: "请选择日期" }]}
          >
            <DatePicker style={{ width: "100%" }} allowClear={false} />
          </Form.Item>
          <Form.Item name="table_id" label="台位">
            <Select allowClear placeholder="可不选" options={tableOptions} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="duration_hours" label="时长(小时)">
            <InputNumber min={0} step={0.5} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="amount_direction" label="输赢" initialValue="WIN">
            <DirectionSwitch options={AMOUNT_DIRECTION_OPTIONS} />
          </Form.Item>
          <Form.Item
            name="amount_abs"
            label="金额"
            rules={[
              { required: true, message: "请输入金额" },
              {
                validator: (_, value) =>
                  value === undefined || value === null || Number(value) > 0
                    ? Promise.resolve()
                    : Promise.reject(new Error("金额需大于 0，输请切换到「输」")),
              },
            ]}
          >
            <InputNumber min={0.01} precision={2} prefix="¥" style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} maxLength={500} showCount />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}
