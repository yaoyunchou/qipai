import {
  Button,
  Card,
  DatePicker,
  Drawer,
  Flex,
  Form,
  Input,
  InputNumber,
  Layout,
  Modal,
  Popconfirm,
  Segmented,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  type LoanBorrowerDetail,
  type LoanBorrowerSummary,
  type LoanRecord,
  type LoanSummary,
} from "../api/client";
import AppHeader from "../components/AppHeader";
import DirectionSwitch, { type DirectionOption } from "../components/DirectionSwitch";
import { useIsMobile } from "../hooks/useIsMobile";
import { useMe } from "../hooks/useMe";

const { Content } = Layout;
const { RangePicker } = DatePicker;

type AmountDirection = "LEND" | "REPAY";

type FormValues = {
  loan_date: dayjs.Dayjs;
  borrower: string;
  contact?: string | null;
  amount_direction: AmountDirection;
  amount_abs: number;
  remark?: string;
};

const AMOUNT_DIRECTION_OPTIONS: DirectionOption[] = [
  { label: "借钱", value: "LEND", tone: "blue" },
  { label: "还钱", value: "REPAY", tone: "red" },
];

const LEND_COLOR = "#cf1322";
const REPAY_COLOR = "#3f8600";

/** 「借出/还钱」+ 正数 → 带符号金额（正数为借出，负数为还钱） */
function toSignedAmount(direction: AmountDirection, abs: number): number {
  const value = Math.abs(abs);
  return direction === "REPAY" ? -value : value;
}

/** 金额展示：+¥500.00（借出）/ -¥200.00（还钱） */
function signedMoney(value: string | number): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "¥0.00";
  const abs = Math.abs(n).toFixed(2);
  if (n > 0) return `+¥${abs}`;
  if (n < 0) return `-¥${abs}`;
  return "¥0.00";
}

/** 余额展示：欠 ¥300.00 / 多还 ¥50.00 / 已结清 */
function balanceText(value: string | number) {
  const n = Number(value);
  if (!Number.isFinite(n) || n === 0) return { text: "已结清", color: undefined as string | undefined };
  if (n > 0) return { text: `欠 ¥${n.toFixed(2)}`, color: LEND_COLOR };
  return { text: `多还 ¥${Math.abs(n).toFixed(2)}`, color: REPAY_COLOR };
}

export default function LoansPage() {
  const { me, loading: meLoading } = useMe();
  const isMobile = useIsMobile();
  const [form] = Form.useForm<FormValues>();
  const [editForm] = Form.useForm<FormValues>();

  const [records, setRecords] = useState<LoanRecord[]>([]);
  const [summary, setSummary] = useState<LoanSummary | null>(null);
  const [borrowers, setBorrowers] = useState<LoanBorrowerSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([
    dayjs().startOf("month"),
    dayjs(),
  ]);
  const [onlyPending, setOnlyPending] = useState(true);
  const [keyword, setKeyword] = useState("");

  const [editOpen, setEditOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<LoanRecord | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);

  const [repayOpen, setRepayOpen] = useState(false);
  /** 还款目标：客人 + 参考金额 + 备注提示（不依赖某条完整记录） */
  const [repayTarget, setRepayTarget] = useState<{
    borrower: string;
    contact: string | null;
    defaultAmount: number;
    hint?: string;
  } | null>(null);
  const [repaySubmitting, setRepaySubmitting] = useState(false);
  const [repayForm] = Form.useForm<{ repay_date: dayjs.Dayjs; amount_abs: number; remark?: string }>();

  const [lendOpen, setLendOpen] = useState(false);
  const [lendTarget, setLendTarget] = useState<{ borrower: string; contact: string | null } | null>(null);
  const [lendSubmitting, setLendSubmitting] = useState(false);
  const [lendForm] = Form.useForm<{ loan_date: dayjs.Dayjs; amount_abs: number; remark?: string }>();

  // 客人总账详情抽屉
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailBorrower, setDetailBorrower] = useState<string>("");
  const [detail, setDetail] = useState<LoanBorrowerDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

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

  const loadAll = useCallback(async () => {
    const qs = queryString();
    const borrowerParams = new URLSearchParams(qs);
    if (onlyPending) borrowerParams.set("only_pending", "true");
    const listParams = new URLSearchParams(qs);
    if (keyword.trim()) listParams.set("borrower", keyword.trim());

    setLoading(true);
    try {
      const [listRes, sumRes, borrowerRes] = await Promise.allSettled([
        canViewList
          ? api<LoanRecord[]>(`/api/v1/loans?${listParams.toString()}`)
          : Promise.resolve([] as LoanRecord[]),
        api<LoanSummary>(`/api/v1/loans/summary?${qs}`),
        api<LoanBorrowerSummary[]>(`/api/v1/loans/borrowers?${borrowerParams.toString()}`),
      ]);
      if (listRes.status === "fulfilled") setRecords(listRes.value);
      else message.error(listRes.reason instanceof Error ? listRes.reason.message : "加载失败");
      if (sumRes.status === "fulfilled") setSummary(sumRes.value);
      if (borrowerRes.status === "fulfilled") setBorrowers(borrowerRes.value);
    } finally {
      setLoading(false);
    }
  }, [canViewList, keyword, onlyPending, queryString]);

  useEffect(() => {
    if (meLoading) return;
    loadAll();
  }, [meLoading, loadAll]);

  const loadDetail = useCallback(async (name: string) => {
    if (!name.trim()) return;
    setDetailLoading(true);
    try {
      const data = await api<LoanBorrowerDetail>(
        `/api/v1/loans/borrowers/detail?borrower=${encodeURIComponent(name.trim())}`
      );
      setDetail(data);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载客人详情失败");
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  /** 打开某个客人的总账详情：看全部流水，余额按全部历史算 */
  const openDetail = (name: string) => {
    setDetailBorrower(name);
    setDetail(null);
    setDetailOpen(true);
    loadDetail(name);
  };

  const submitRecord = async (values: FormValues) => {
    setSubmitting(true);
    try {
      await api<LoanRecord>("/api/v1/loans", {
        method: "POST",
        body: JSON.stringify({
          loan_date: values.loan_date.format("YYYY-MM-DD"),
          borrower: values.borrower,
          contact: values.contact ?? null,
          amount: toSignedAmount(values.amount_direction, values.amount_abs),
          remark: values.remark ?? null,
        }),
      });
      message.success("借钱记录已保存");
      form.resetFields();
      form.setFieldsValue({ loan_date: dayjs(), amount_direction: "LEND" });
      loadAll();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  };

  /** 打开「还钱」弹窗：客人锁定，默认金额可指定（余额或某笔借出额） */
  const openRepayForBorrower = (
    borrower: string,
    balance: number,
    contact: string | null,
    hintPrefix = "当前未还余额"
  ) => {
    setRepayTarget({
      borrower,
      contact,
      defaultAmount: balance,
      hint: `${hintPrefix} ¥${balance.toFixed(2)}`,
    });
    repayForm.setFieldsValue({
      repay_date: dayjs(),
      amount_abs: balance,
      remark: undefined,
    });
    setRepayOpen(true);
  };

  /** 从客人总账继续借钱：客人锁定，金额由当场填写 */
  const openLendForBorrower = (borrower: string, contact: string | null) => {
    setLendTarget({ borrower, contact });
    lendForm.setFieldsValue({
      loan_date: dayjs(),
      amount_abs: undefined,
      remark: undefined,
    });
    setLendOpen(true);
  };

  const submitLend = async (values: { loan_date: dayjs.Dayjs; amount_abs: number; remark?: string }) => {
    if (!lendTarget) return;
    setLendSubmitting(true);
    try {
      await api<LoanRecord>("/api/v1/loans", {
        method: "POST",
        body: JSON.stringify({
          loan_date: values.loan_date.format("YYYY-MM-DD"),
          borrower: lendTarget.borrower,
          contact: lendTarget.contact ?? null,
          amount: Math.abs(values.amount_abs),
          remark: values.remark ?? null,
        }),
      });
      message.success(`已记录 ${lendTarget.borrower} 借钱`);
      setLendOpen(false);
      setLendTarget(null);
      loadAll();
      if (detailOpen && detailBorrower) loadDetail(detailBorrower);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "借钱记录保存失败");
    } finally {
      setLendSubmitting(false);
    }
  };

  /** 从「客人总账」行尾点「还钱」：弹框交互，默认金额为当前未还余额 */
  const quickRepay = (row: LoanBorrowerSummary) => {
    const balance = Number(row.balance);
    if (balance > 0) openRepayForBorrower(row.borrower, balance, null);
  };

  /** 从明细某一笔借出打开「还钱」弹窗：客人锁定，金额默认该行金额 */
  const openRepay = (record: LoanRecord) => {
    const borrowed = Math.abs(Number(record.amount));
    openRepayForBorrower(
      record.borrower,
      borrowed,
      record.contact ?? null,
      `这笔借出（${dayjs(record.loan_date).format("YYYY-MM-DD")}）`
    );
  };

  const submitRepay = async (values: {
    repay_date: dayjs.Dayjs;
    amount_abs: number;
    remark?: string;
  }) => {
    if (!repayTarget) return;
    setRepaySubmitting(true);
    try {
      await api<LoanRecord>("/api/v1/loans", {
        method: "POST",
        body: JSON.stringify({
          loan_date: values.repay_date.format("YYYY-MM-DD"),
          borrower: repayTarget.borrower,
          contact: repayTarget.contact ?? null,
          amount: -Math.abs(values.amount_abs),
          remark: values.remark ?? null,
        }),
      });
      message.success(`已记录 ${repayTarget.borrower} 还款`);
      setRepayOpen(false);
      setRepayTarget(null);
      loadAll();
      if (detailOpen && detailBorrower) loadDetail(detailBorrower);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "还款记录保存失败");
    } finally {
      setRepaySubmitting(false);
    }
  };

  const openEdit = (record: LoanRecord) => {
    setEditRecord(record);
    const signed = Number(record.amount);
    editForm.setFieldsValue({
      loan_date: dayjs(record.loan_date),
      borrower: record.borrower,
      contact: record.contact ?? undefined,
      amount_direction: signed < 0 ? "REPAY" : "LEND",
      amount_abs: Math.abs(signed),
      remark: record.remark ?? undefined,
    });
    setEditOpen(true);
  };

  const submitEdit = async (values: FormValues) => {
    if (!editRecord) return;
    setEditSubmitting(true);
    try {
      await api<LoanRecord>(`/api/v1/loans/${editRecord.id}`, {
        method: "PUT",
        body: JSON.stringify({
          loan_date: values.loan_date.format("YYYY-MM-DD"),
          borrower: values.borrower,
          contact: values.contact ?? null,
          amount: toSignedAmount(values.amount_direction, values.amount_abs),
          remark: values.remark ?? null,
        }),
      });
      message.success("已更新");
      setEditOpen(false);
      loadAll();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "更新失败");
    } finally {
      setEditSubmitting(false);
    }
  };

  const removeRecord = async (id: number) => {
    try {
      await api(`/api/v1/loans/${id}`, { method: "DELETE" });
      message.success("已删除");
      loadAll();
      if (detailOpen && detailBorrower) loadDetail(detailBorrower);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "删除失败");
    }
  };

  const amountRules = useMemo(
    () => [
      { required: true, message: "请输入金额" },
      {
        validator: (_: unknown, value: number | undefined | null) =>
          value === undefined || value === null || Number(value) > 0
            ? Promise.resolve()
            : Promise.reject(new Error("金额需大于 0，还钱请切换到「还钱」")),
      },
    ],
    []
  );

  if (meLoading) return null;

  const columns: ColumnsType<LoanRecord> = [
    {
      title: "日期",
      dataIndex: "loan_date",
      width: 110,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD"),
    },
    { title: "客人", dataIndex: "borrower", width: 120, ellipsis: true },
    {
      title: "联系方式",
      dataIndex: "contact",
      width: 130,
      render: (v: string | null) => v || "-",
    },
    {
      title: "类型",
      dataIndex: "amount",
      width: 80,
      render: (v: string) => {
        const n = Number(v);
        return n < 0 ? <Tag color="green">还钱</Tag> : <Tag color="red">借出</Tag>;
      },
    },
    {
      title: "金额",
      dataIndex: "amount",
      width: 120,
      align: "right",
      render: (v: string) => {
        const n = Number(v);
        const color = n < 0 ? REPAY_COLOR : LEND_COLOR;
        return (
          <Typography.Text style={{ color, fontWeight: 500 }}>{signedMoney(v)}</Typography.Text>
        );
      },
    },
    {
      title: "备注",
      dataIndex: "remark",
      ellipsis: true,
      render: (v: string | null) => v || "-",
    },
    {
      title: "录入人",
      dataIndex: "created_by_name",
      width: 100,
      render: (v: string | null) => v || "-",
    },
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
            width: 190,
            fixed: isMobile ? undefined : ("right" as const),
            render: (_: unknown, row: LoanRecord) => {
              const own = row.created_by === me?.id;
              if (!own && !isAdmin) return <Typography.Text type="secondary">-</Typography.Text>;
              const isLend = Number(row.amount) > 0;
              return (
                <Space size={0}>
                  {isLend && (
                    <Button type="link" size="small" onClick={() => openRepay(row)}>
                      还钱
                    </Button>
                  )}
                  <Button type="link" size="small" onClick={() => openEdit(row)}>
                    编辑
                  </Button>
                  {isAdmin && (
                    <Popconfirm
                      title="确认删除这条借钱记录？"
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

  const borrowerColumns: ColumnsType<LoanBorrowerSummary> = [
    {
      title: "客人",
      dataIndex: "borrower",
      width: isMobile ? undefined : 140,
      ellipsis: true,
      render: (v: string) => (
        <Button
          type="link"
          size="small"
          style={{ padding: 0, fontWeight: 500 }}
          onClick={() => openDetail(v)}
        >
          {v}
        </Button>
      ),
    },
    // 手机上不展示借出/已还拆分，只留最关键的两列，避免横向挤压
    ...(isMobile
      ? []
      : [
          {
            title: "借出合计",
            dataIndex: "lent_total",
            width: 120,
            align: "right" as const,
            render: (v: string) => (
              <Typography.Text style={{ color: LEND_COLOR }}>
                ¥{Number(v).toFixed(2)}
              </Typography.Text>
            ),
          },
          {
            title: "已还合计",
            dataIndex: "repaid_total",
            width: 120,
            align: "right" as const,
            render: (v: string) => (
              <Typography.Text style={{ color: REPAY_COLOR }}>
                ¥{Number(v).toFixed(2)}
              </Typography.Text>
            ),
          },
        ]),
    {
      title: "未还余额",
      dataIndex: "balance",
      width: isMobile ? undefined : 140,
      align: "right",
      render: (v: string) => {
        const { text, color } = balanceText(v);
        return (
          <Typography.Text style={{ color, fontWeight: 600 }}>{text}</Typography.Text>
        );
      },
    },
    ...(isMobile
      ? []
      : [
          {
            title: "笔数",
            dataIndex: "record_count",
            width: 70,
            align: "right" as const,
          },
          {
            title: "最近一次",
            dataIndex: "last_date",
            width: 110,
            render: (v: string) => dayjs(v).format("YYYY-MM-DD"),
          },
        ]),
    ...(canEdit
      ? [
          {
            title: "操作",
            width: isMobile ? undefined : 150,
            fixed: isMobile ? undefined : ("right" as const),
            render: (_: unknown, row: LoanBorrowerSummary) => (
              <Space size={0}>
                {/* 手机上点客人名即可看明细，这里只保留「还钱」节省横向空间 */}
                {!isMobile && (
                  <Button type="link" size="small" onClick={() => openDetail(row.borrower)}>
                    明细
                  </Button>
                )}
                {Number(row.balance) > 0 && (
                  <Button type="link" size="small" onClick={() => quickRepay(row)}>
                    还钱
                  </Button>
                )}
              </Space>
            ),
          },
        ]
      : [
          {
            title: "操作",
            width: 90,
            fixed: "right" as const,
            render: (_: unknown, row: LoanBorrowerSummary) => (
              <Button type="link" size="small" onClick={() => openDetail(row.borrower)}>
                明细
              </Button>
            ),
          },
        ]),
  ];

  const lentTotal = Number(summary?.lent_total ?? 0);
  const repaidTotal = Number(summary?.repaid_total ?? 0);
  const balanceTotal = Number(summary?.balance_total ?? 0);
  const balanceInfo = balanceText(balanceTotal);

  const summaryCards = (
    <Flex wrap="wrap" gap={16} style={{ marginBottom: 16 }}>
      <Card size="small" style={{ minWidth: 150 }}>
        <Statistic title="记录笔数" value={summary?.record_count ?? 0} />
      </Card>
      <Card size="small" style={{ minWidth: 160 }}>
        <Statistic
          title="借出合计"
          value={lentTotal}
          prefix="¥"
          precision={2}
          valueStyle={{ color: LEND_COLOR }}
        />
      </Card>
      <Card size="small" style={{ minWidth: 160 }}>
        <Statistic
          title="已还合计"
          value={repaidTotal}
          prefix="¥"
          precision={2}
          valueStyle={{ color: REPAY_COLOR }}
        />
      </Card>
      <Card size="small" style={{ minWidth: 180 }}>
        <Statistic
          title="未还余额（借出 - 已还）"
          value={Math.abs(balanceTotal)}
          precision={2}
          prefix={balanceTotal < 0 ? "-¥" : "¥"}
          valueStyle={{ color: balanceInfo.color, fontWeight: 600 }}
        />
      </Card>
    </Flex>
  );

  const repayHint = (
    <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
      当前账号为股东角色，仅可查看借钱汇总与客人欠款余额，明细由收银员 / 经理 / 超管录入。
    </Typography.Paragraph>
  );

  const recordFormItems = (
    <>
      <Flex wrap="wrap" gap={12}>
        <Form.Item
          name="loan_date"
          label="日期"
          rules={[{ required: true, message: "请选择日期" }]}
          style={{ flex: "1 1 180px", minWidth: 180 }}
        >
          <DatePicker style={{ width: "100%" }} allowClear={false} />
        </Form.Item>
        <Form.Item
          name="borrower"
          label="客人"
          rules={[
            { required: true, message: "请填写客人姓名" },
            { max: 64, message: "最多 64 个字" },
          ]}
          style={{ flex: "1 1 180px", minWidth: 180 }}
        >
          <Input placeholder="如：张哥 / 3 号桌老李" maxLength={64} />
        </Form.Item>
        <Form.Item
          name="contact"
          label="联系方式"
          style={{ flex: "1 1 180px", minWidth: 180 }}
        >
          <Input placeholder="手机号 / 微信，选填" maxLength={64} />
        </Form.Item>
        <Form.Item
          name="amount_direction"
          label="类型"
          initialValue="LEND"
          style={{ flex: "0 0 auto", minWidth: 130 }}
        >
          <DirectionSwitch options={AMOUNT_DIRECTION_OPTIONS} />
        </Form.Item>
        <Form.Item
          name="amount_abs"
          label="金额"
          rules={amountRules}
          style={{ flex: "1 1 150px", minWidth: 150 }}
        >
          <InputNumber min={0.01} precision={2} prefix="¥" style={{ width: "100%" }} />
        </Form.Item>
      </Flex>
      <Form.Item name="remark" label="备注">
        <Input.TextArea
          rows={2}
          maxLength={500}
          showCount
          placeholder="例如：打牌临时借 500，说晚上还"
        />
      </Form.Item>
    </>
  );

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader title="借钱还钱" />
      <Content
        style={{
          padding: isMobile ? 12 : 24,
          maxWidth: 1200,
          width: "100%",
          margin: "0 auto",
        }}
      >
        {canEdit && (
          <Card title="新增借还记录" style={{ marginBottom: 16 }}>
            <Form
              form={form}
              layout="vertical"
              onFinish={submitRecord}
              initialValues={{ loan_date: dayjs(), amount_direction: "LEND" }}
            >
              {recordFormItems}
              <Button type="primary" htmlType="submit" loading={submitting}>
                保存记录
              </Button>
            </Form>
          </Card>
        )}

        <Card
          title={canEdit ? "借还明细" : "借还汇总"}
          extra={
            <Space wrap>
              <RangePicker
                value={dateRange}
                onChange={(v) => setDateRange(v ?? [null, null])}
                allowEmpty={[true, true]}
              />
              <Button onClick={loadAll} loading={loading}>
                刷新
              </Button>
            </Space>
          }
        >
          {summaryCards}
          {canEdit ? (
            <Tabs
              items={[
                {
                  key: "borrowers",
                  label: `客人总账（${borrowers.length}）`,
                  children: (
                    <>
                      <Flex wrap="wrap" gap={8} align="center" style={{ marginBottom: 12 }}>
                        <Segmented
                          value={onlyPending ? "PENDING" : "ALL"}
                          onChange={(v) => setOnlyPending(v === "PENDING")}
                          options={[
                            { label: "只看还欠着", value: "PENDING" },
                            { label: "全部客人", value: "ALL" },
                          ]}
                        />
                        <Typography.Text type="secondary">
                          一人一账，点客人名或「明细」查看该人的每笔借还流水
                        </Typography.Text>
                      </Flex>
                      <Table
                        rowKey="borrower"
                        loading={loading}
                        columns={borrowerColumns}
                        dataSource={borrowers}
                        pagination={{ pageSize: 10, showSizeChanger: false }}
                        scroll={isMobile ? undefined : { x: 860 }}
                      />
                    </>
                  ),
                },
                {
                  key: "records",
                  label: `全部流水（${records.length}）`,
                  children: (
                    <>
                      <Flex wrap="wrap" gap={8} align="center" style={{ marginBottom: 12 }}>
                        <Input.Search
                          allowClear
                          placeholder="按客人筛选"
                          value={keyword}
                          onChange={(e) => setKeyword(e.target.value)}
                          onSearch={() => loadAll()}
                          style={{ width: 220 }}
                        />
                        <Typography.Text type="secondary">
                          所有客人的借出 / 还钱流水，按日期倒序
                        </Typography.Text>
                      </Flex>
                      <Table
                        rowKey="id"
                        loading={loading}
                        columns={columns}
                        dataSource={records}
                        pagination={{ pageSize: 10, showSizeChanger: false }}
                        scroll={{ x: 1000 }}
                      />
                    </>
                  ),
                },
              ]}
            />
          ) : (
            <>
              <Table
                rowKey="borrower"
                loading={loading}
                columns={borrowerColumns.filter((c) => c.title !== "操作")}
                dataSource={borrowers}
                pagination={{ pageSize: 10, showSizeChanger: false }}
                scroll={isMobile ? undefined : { x: 700 }}
                style={{ marginBottom: 12 }}
              />
              {repayHint}
            </>
          )}
        </Card>
      </Content>

      <Drawer
        title={detail ? `客人总账 · ${detail.borrower}` : `客人总账 · ${detailBorrower}`}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        width="min(720px, 100vw)"
        destroyOnClose
        extra={
          canEdit && detail ? (
            <Space>
              <Button
                type="primary"
                onClick={() =>
                  openLendForBorrower(detail.borrower, detail.records[0]?.contact ?? null)
                }
              >
                借钱
              </Button>
              {Number(detail.balance) > 0 && (
                <Button
                  danger
                  onClick={() =>
                    openRepayForBorrower(
                      detail.borrower,
                      Number(detail.balance),
                      detail.records[0]?.contact ?? null
                    )
                  }
                >
                  还钱
                </Button>
              )}
            </Space>
          ) : null
        }
      >
        <div style={{ minHeight: 200 }}>
          {detailLoading || !detail ? (
            <Typography.Text type="secondary">加载中…</Typography.Text>
          ) : (
            <>
              {/* 移动端用 Flex 卡片自动换行，避免 Descriptions 在窄屏被压成竖排文字 */}
              <Flex wrap="wrap" gap={8} style={{ marginBottom: 16 }}>
                <Card size="small" style={{ flex: "1 1 130px", minWidth: 130 }}>
                  <Statistic
                    title="借出合计"
                    value={Number(detail.lent_total)}
                    precision={2}
                    prefix="¥"
                    valueStyle={{ color: LEND_COLOR, fontSize: 18 }}
                  />
                </Card>
                <Card size="small" style={{ flex: "1 1 130px", minWidth: 130 }}>
                  <Statistic
                    title="已还合计"
                    value={Number(detail.repaid_total)}
                    precision={2}
                    prefix="¥"
                    valueStyle={{ color: REPAY_COLOR, fontSize: 18 }}
                  />
                </Card>
                <Card size="small" style={{ flex: "1 1 130px", minWidth: 130 }}>
                  <Statistic
                    title="未还余额"
                    value={Math.abs(Number(detail.balance))}
                    precision={2}
                    prefix={Number(detail.balance) < 0 ? "-¥" : "¥"}
                    valueStyle={{
                      color: balanceText(detail.balance).color,
                      fontSize: 18,
                      fontWeight: 600,
                    }}
                  />
                </Card>
              </Flex>
              <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
                共 {detail.record_count} 笔流水，按日期倒序（余额按全部历史计算，不受上方日期筛选影响）
              </Typography.Paragraph>
              <Table
                rowKey="id"
                size="small"
                loading={detailLoading}
                dataSource={detail.records}
                pagination={false}
                scroll={isMobile ? undefined : { x: 620 }}
                columns={[
                  {
                    title: "日期",
                    dataIndex: "loan_date",
                    width: isMobile ? 96 : 110,
                    render: (v: string) =>
                      isMobile ? dayjs(v).format("MM-DD") : dayjs(v).format("YYYY-MM-DD"),
                  },
                  {
                    title: "类型",
                    dataIndex: "amount",
                    width: isMobile ? 64 : 80,
                    render: (v: string) =>
                      Number(v) < 0 ? <Tag color="green">还钱</Tag> : <Tag color="red">借出</Tag>,
                  },
                  {
                    title: "金额",
                    dataIndex: "amount",
                    width: isMobile ? 104 : 120,
                    align: "right",
                    render: (v: string) => (
                      <Typography.Text
                        style={{
                          color: Number(v) < 0 ? REPAY_COLOR : LEND_COLOR,
                          fontWeight: 500,
                        }}
                      >
                        {signedMoney(v)}
                      </Typography.Text>
                    ),
                  },
                  // 手机上不展示这两列，避免横向溢出；要看得转桌面端
                  ...(isMobile
                    ? []
                    : [
                        {
                          title: "备注",
                          dataIndex: "remark",
                          ellipsis: true,
                          render: (v: string | null) => v || "-",
                        },
                        {
                          title: "录入时间",
                          dataIndex: "created_at",
                          width: 140,
                          render: (v: string) => dayjs(v).format("MM-DD HH:mm"),
                        },
                      ]),
                ]}
              />
            </>
          )}
        </div>
      </Drawer>

      <Modal
        title={lendTarget ? `继续借钱 · ${lendTarget.borrower}` : "继续借钱"}
        open={lendOpen}
        onCancel={() => {
          setLendOpen(false);
          setLendTarget(null);
        }}
        onOk={() => lendForm.submit()}
        okText="保存借钱"
        confirmLoading={lendSubmitting}
        destroyOnClose
      >
        <Form form={lendForm} layout="vertical" onFinish={submitLend}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
            记在「{lendTarget?.borrower}」名下，作为一笔新的借出。原来的流水不动，未还余额按全部记录重算。
          </Typography.Paragraph>
          <Form.Item
            name="loan_date"
            label="借钱日期"
            rules={[{ required: true, message: "请选择日期" }]}
          >
            <DatePicker style={{ width: "100%" }} allowClear={false} />
          </Form.Item>
          <Form.Item
            name="amount_abs"
            label="借钱金额"
            rules={[
              { required: true, message: "请输入借钱金额" },
              {
                validator: (_, value) =>
                  value === undefined || value === null || Number(value) > 0
                    ? Promise.resolve()
                    : Promise.reject(new Error("金额需大于 0")),
              },
            ]}
          >
            <InputNumber min={0.01} precision={2} prefix="¥" style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} maxLength={500} showCount placeholder="例如：又借了一笔" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={repayTarget ? `记录还钱 · ${repayTarget.borrower}` : "记录还钱"}
        open={repayOpen}
        onCancel={() => {
          setRepayOpen(false);
          setRepayTarget(null);
        }}
        onOk={() => repayForm.submit()}
        okText="保存还款"
        confirmLoading={repaySubmitting}
        destroyOnClose
      >
        <Form form={repayForm} layout="vertical" onFinish={submitRepay}>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
            {repayTarget?.hint}。还款会作为一条独立记录计入「{repayTarget?.borrower}
            」名下，余额按客人汇总抵扣。</Typography.Paragraph>
          <Form.Item
            name="repay_date"
            label="还钱日期"
            rules={[{ required: true, message: "请选择日期" }]}
          >
            <DatePicker style={{ width: "100%" }} allowClear={false} />
          </Form.Item>
          <Form.Item
            name="amount_abs"
            label="还钱金额"
            rules={[
              { required: true, message: "请输入还款金额" },
              {
                validator: (_, value) =>
                  value === undefined || value === null || Number(value) > 0
                    ? Promise.resolve()
                    : Promise.reject(new Error("金额需大于 0")),
              },
            ]}
          >
            <InputNumber min={0.01} precision={2} prefix="¥" style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} maxLength={500} showCount placeholder="例如：当场还清 / 先还一部分" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="编辑借还记录"
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={() => editForm.submit()}
        okText="保存"
        confirmLoading={editSubmitting}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" onFinish={submitEdit}>
          <Form.Item
            name="loan_date"
            label="日期"
            rules={[{ required: true, message: "请选择日期" }]}
          >
            <DatePicker style={{ width: "100%" }} allowClear={false} />
          </Form.Item>
          <Form.Item
            name="borrower"
            label="客人"
            rules={[{ required: true, message: "请填写客人姓名" }]}
          >
            <Input maxLength={64} />
          </Form.Item>
          <Form.Item name="contact" label="联系方式">
            <Input placeholder="选填" maxLength={64} />
          </Form.Item>
          <Form.Item name="amount_direction" label="类型" initialValue="LEND">
            <DirectionSwitch options={AMOUNT_DIRECTION_OPTIONS} />
          </Form.Item>
          <Form.Item name="amount_abs" label="金额" rules={amountRules}>
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
