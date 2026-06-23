import {
  Button,
  Card,
  DatePicker,
  Form,
  Image,
  Input,
  InputNumber,
  Layout,
  Modal,
  Segmented,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import type { UploadFile } from "antd/es/upload";
import dayjs from "dayjs";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  downloadFile,
  type ApprovePermissionItem,
  type CategorySummary,
  type ExpenseClaimItem,
  type ExpenseReportSummary,
  type SelectableApprover,
} from "../api/client";
import AppHeader from "../components/AppHeader";
import { useMe } from "../hooks/useMe";

const { Content } = Layout;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

const ROLE_LABEL: Record<string, string> = {
  MANAGER: "经理",
  SHAREHOLDER: "股东",
  ADMIN: "超管",
};

const CATEGORY_LABEL: Record<string, string> = {
  FIXED: "固定支出",
  OPERATIONS: "营运支出",
  SANDBOX: "沙箱支出",
};

const CATEGORY_OPTIONS = [
  { label: "固定支出", value: "FIXED" },
  { label: "营运支出", value: "OPERATIONS" },
  { label: "沙箱支出", value: "SANDBOX" },
];

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  PENDING: { color: "orange", label: "待审批" },
  APPROVED: { color: "green", label: "已完成" },
  REJECTED: { color: "red", label: "已驳回" },
};

const APPROVER_STATUS: Record<string, string> = {
  PENDING: "待处理",
  APPROVED: "已通过",
  REJECTED: "已驳回",
  SKIPPED: "不参与",
};

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function ExpensesPage() {
  const { me } = useMe();
  const [form] = Form.useForm();
  const [actionForm] = Form.useForm<{ comment: string }>();
  const [submitting, setSubmitting] = useState(false);
  const [selectableApprovers, setSelectableApprovers] = useState<SelectableApprover[]>([]);
  const [myClaims, setMyClaims] = useState<ExpenseClaimItem[]>([]);
  const [pendingClaims, setPendingClaims] = useState<ExpenseClaimItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<ExpenseClaimItem | null>(null);
  const [actionOpen, setActionOpen] = useState(false);
  const [actionType, setActionType] = useState<"approve" | "reject">("approve");
  const [actionClaimId, setActionClaimId] = useState<number | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  const [period, setPeriod] = useState<"day" | "week" | "month">("day");
  const [anchorDate, setAnchorDate] = useState(dayjs());
  const [reportData, setReportData] = useState<ExpenseReportSummary | null>(null);
  const [exporting, setExporting] = useState(false);

  const [permissions, setPermissions] = useState<ApprovePermissionItem[]>([]);
  const [permLoading, setPermLoading] = useState(false);
  const [permSaving, setPermSaving] = useState(false);

  const [editOpen, setEditOpen] = useState(false);
  const [editClaim, setEditClaim] = useState<ExpenseClaimItem | null>(null);
  const [editForm] = Form.useForm();
  const [editFileList, setEditFileList] = useState<UploadFile[]>([]);
  const [editSubmitting, setEditSubmitting] = useState(false);

  const canManagePerm = me?.role === "ADMIN";
  const canExportReport = me?.role !== "SHAREHOLDER";

  const loadApprovers = useCallback(async () => {
    try {
      const data = await api<SelectableApprover[]>("/api/v1/expenses/selectable-approvers");
      setSelectableApprovers(data);
    } catch {
      setSelectableApprovers([]);
    }
  }, []);

  const loadLists = useCallback(async () => {
    setListLoading(true);
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (dateRange?.[0]) params.set("start", dateRange[0].format("YYYY-MM-DD"));
      if (dateRange?.[1]) params.set("end", dateRange[1].format("YYYY-MM-DD"));
      const [mine, pending] = await Promise.all([
        api<ExpenseClaimItem[]>(`/api/v1/expenses?scope=mine&${params}`),
        api<ExpenseClaimItem[]>(`/api/v1/expenses?scope=pending&${params}`),
      ]);
      setMyClaims(mine);
      setPendingClaims(pending);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载失败");
    } finally {
      setListLoading(false);
    }
  }, [dateRange]);

  const loadReport = useCallback(async () => {
    try {
      const data = await api<ExpenseReportSummary>(
        `/api/v1/expenses/reports/summary?period=${period}&start=${anchorDate.format("YYYY-MM-DD")}`
      );
      setReportData(data);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "报表加载失败");
    }
  }, [period, anchorDate]);

  const loadPermissions = useCallback(async () => {
    if (!canManagePerm) return;
    setPermLoading(true);
    try {
      const data = await api<ApprovePermissionItem[]>("/api/v1/expenses/approve-permissions");
      setPermissions(data);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载授权失败");
    } finally {
      setPermLoading(false);
    }
  }, [canManagePerm]);

  useEffect(() => {
    loadApprovers();
    loadLists();
  }, [loadApprovers, loadLists]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  useEffect(() => {
    loadPermissions();
  }, [loadPermissions]);


  const openDetail = async (id: number) => {
    try {
      const data = await api<ExpenseClaimItem>(`/api/v1/expenses/${id}`);
      setDetail(data);
      setDetailOpen(true);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "加载详情失败");
    }
  };

  const submitClaim = async (values: {
    amount: number;
    remark?: string;
    approver_ids: number[];
  }) => {
    setSubmitting(true);
    try {
      const attachments = await Promise.all(
        fileList
          .filter((f) => f.originFileObj)
          .map(async (f) => ({
            filename: f.name,
            content_type: f.type || "image/jpeg",
            data_base64: await fileToBase64(f.originFileObj as File),
          }))
      );
      await api<ExpenseClaimItem>("/api/v1/expenses", {
        method: "POST",
        body: JSON.stringify({ ...values, attachments }),
      });
      message.success("报销已提交，等待审批");
      form.resetFields();
      setFileList([]);
      loadLists();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const openAction = (claimId: number, type: "approve" | "reject") => {
    setActionClaimId(claimId);
    setActionType(type);
    actionForm.resetFields();
    setActionOpen(true);
  };

  const submitAction = async (values: { comment: string }) => {
    if (!actionClaimId) return;
    try {
      const path =
        actionType === "approve"
          ? `/api/v1/expenses/${actionClaimId}/approve`
          : `/api/v1/expenses/${actionClaimId}/reject`;
      await api(path, { method: "POST", body: JSON.stringify(values) });
      message.success(actionType === "approve" ? "已通过" : "已驳回");
      setActionOpen(false);
      loadLists();
      if (detail?.id === actionClaimId) openDetail(actionClaimId);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "操作失败");
    }
  };

  const skipApproval = async (claimId: number) => {
    try {
      await api(`/api/v1/expenses/${claimId}/skip`, { method: "POST" });
      message.success("已标记为不参与");
      loadLists();
      if (detail?.id === claimId) openDetail(claimId);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "操作失败");
    }
  };

  const savePermissions = async () => {
    setPermSaving(true);
    try {
      const user_ids = permissions.filter((p) => p.can_approve).map((p) => p.user_id);
      const data = await api<ApprovePermissionItem[]>("/api/v1/expenses/approve-permissions", {
        method: "PUT",
        body: JSON.stringify({ user_ids }),
      });
      setPermissions(data);
      loadApprovers();
      message.success("审批授权已保存");
    } catch (e) {
      message.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setPermSaving(false);
    }
  };

  const openEdit = (claim: ExpenseClaimItem) => {
    setEditClaim(claim);
    editForm.setFieldsValue({
      amount: parseFloat(claim.amount),
      remark: claim.remark,
      category: claim.category,
    });
    setEditFileList([]);
    setEditOpen(true);
  };

  const submitEdit = async (values: { amount: number; remark?: string; approver_ids: number[] }) => {
    if (!editClaim) return;
    setEditSubmitting(true);
    try {
      const attachments = await Promise.all(
        editFileList
          .filter((f) => f.originFileObj)
          .map(async (f) => ({
            filename: f.name,
            content_type: f.type || "image/jpeg",
            data_base64: await fileToBase64(f.originFileObj as File),
          }))
      );
      await api<ExpenseClaimItem>(`/api/v1/expenses/${editClaim.id}`, {
        method: "PUT",
        body: JSON.stringify({ ...values, attachments }),
      });
      message.success("已重新提交，等待审批");
      setEditOpen(false);
      loadLists();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "提交失败");
    } finally {
      setEditSubmitting(false);
    }
  };

  const deleteClaim = (claimId: number) => {
    Modal.confirm({
      title: "确认删除",
      content: "删除后无法恢复，确认删除该报销单吗？",
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          await api(`/api/v1/expenses/${claimId}`, { method: "DELETE" });
          message.success("已删除");
          loadLists();
        } catch (e) {
          message.error(e instanceof Error ? e.message : "删除失败");
        }
      },
    });
  };

  const handleExport = async () => {    setExporting(true);
    try {
      await downloadFile(
        `/api/v1/expenses/reports/export?period=${period}&start=${anchorDate.format("YYYY-MM-DD")}`,
        `expense_${period}_${anchorDate.format("YYYY-MM-DD")}.xlsx`
      );
      message.success("导出成功");
    } catch (e) {
      message.error(e instanceof Error ? e.message : "导出失败");
    } finally {
      setExporting(false);
    }
  };

  const claimColumns = [
    { title: "单号", dataIndex: "claim_no", width: 150 },
    {
      title: "申请人",
      dataIndex: "applicant_name",
      width: 100,
      render: (v: string | null, row: ExpenseClaimItem) => v || `#${row.applicant_id}`,
    },
    { title: "金额", dataIndex: "amount", width: 90, render: (v: string) => `¥${v}` },
    {
      title: "分类",
      dataIndex: "category",
      width: 90,
      render: (v: string) => CATEGORY_LABEL[v] || v,
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 90,
      render: (v: string) => {
        const t = STATUS_TAG[v] || { color: "default", label: v };
        return <Tag color={t.color}>{t.label}</Tag>;
      },
    },
    {
      title: "提交时间",
      dataIndex: "submitted_at",
      width: 150,
      render: (v: string) => dayjs(v).format("YYYY-MM-DD HH:mm"),
    },
    { title: "备注", dataIndex: "remark", ellipsis: true },
    {
      title: "操作",
      width: 240,
      render: (_: unknown, row: ExpenseClaimItem) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => openDetail(row.id)}>
            详情
          </Button>
          {row.status === "PENDING" &&
            row.approvers.some(
              (a) => a.approver_id === me?.id && a.status === "PENDING"
            ) && (
              <>
                <Button type="link" size="small" onClick={() => openAction(row.id, "approve")}>
                  通过
                </Button>
                <Button type="link" danger size="small" onClick={() => openAction(row.id, "reject")}>
                  驳回
                </Button>
                <Button type="link" size="small" onClick={() => skipApproval(row.id)}>
                  不参与
                </Button>
              </>
            )}
          {row.status === "REJECTED" && row.applicant_id === me?.id && (
            <>
              <Button type="link" size="small" onClick={() => openEdit(row)}>
                编辑重提
              </Button>
              <Button type="link" danger size="small" onClick={() => deleteClaim(row.id)}>
                删除
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  const createTab = (
    <Card title="新建报销">
      <Form form={form} layout="vertical" onFinish={submitClaim} style={{ maxWidth: 520 }}>
        <Form.Item name="amount" label="报销金额" rules={[{ required: true, message: "请输入金额" }]}>
          <InputNumber min={0.01} precision={2} prefix="¥" style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="category" label="报销分类" rules={[{ required: true, message: "请选择分类" }]} initialValue="FIXED">
          <Select options={CATEGORY_OPTIONS} />
        </Form.Item>
        <Form.Item name="remark" label="备注">
          <TextArea rows={3} maxLength={500} showCount placeholder="费用说明（选填）" />
        </Form.Item>
        <Form.Item label="审批人">
          {selectableApprovers.length === 0 ? (
            <Typography.Text type="warning">暂无审批人，请联系超管配置审批授权</Typography.Text>
          ) : (
            <Space wrap>
              {selectableApprovers.map((a) => (
                <Tag key={a.id} color="blue">
                  {a.display_name}（{ROLE_LABEL[a.role] || a.role}）
                </Tag>
              ))}
            </Space>
          )}
        </Form.Item>
        <Form.Item label="附件/图片（最多5张，单张≤3MB）">
          <Upload
            listType="picture-card"
            fileList={fileList}
            accept="image/*"
            beforeUpload={() => false}
            onChange={({ fileList: fl }) => setFileList(fl.slice(0, 5))}
          >
            {fileList.length < 5 && "+ 上传"}
          </Upload>
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={submitting} disabled={selectableApprovers.length === 0}>
          提交报销
        </Button>
      </Form>
    </Card>
  );

  const listTab = (
    <Card
      title="我的报销"
      extra={
        <RangePicker
          value={dateRange}
          onChange={(v) => setDateRange(v)}
          allowEmpty={[true, true]}
        />
      }
    >
      <Table
        rowKey="id"
        loading={listLoading}
        dataSource={myClaims}
        columns={claimColumns.filter((c) => c.title !== "申请人")}
        pagination={{ pageSize: 10 }}
        scroll={{ x: 800 }}
      />
    </Card>
  );

  const pendingTab = (
    <Card title="待我审批">
      <Table
        rowKey="id"
        loading={listLoading}
        dataSource={pendingClaims}
        columns={claimColumns}
        pagination={{ pageSize: 10 }}
        scroll={{ x: 900 }}
      />
    </Card>
  );

  const reportTab = (
    <Card title="报销报表（仅统计已完成）">
      <Space wrap style={{ marginBottom: 16 }}>
        <Segmented
          options={[
            { label: "日报", value: "day" },
            { label: "周报", value: "week" },
            { label: "月报", value: "month" },
          ]}
          value={period}
          onChange={(v) => setPeriod(v as "day" | "week" | "month")}
        />
        <DatePicker
          value={anchorDate}
          onChange={(d) => d && setAnchorDate(d)}
          allowClear={false}
          picker={period === "month" ? "month" : period === "week" ? "week" : "date"}
        />
        {canExportReport && (
          <Button loading={exporting} onClick={handleExport}>
            导出 Excel
          </Button>
        )}
      </Space>
      {reportData && (
        <>
          <Space size={48}>
            <Statistic title="已完成笔数" value={reportData.claim_count} />
            <Statistic title="报销总金额" value={reportData.amount_total} prefix="¥" precision={2} />
          </Space>
          {reportData.by_category.length > 0 && (
          <Table
            size="small"
            style={{ marginTop: 16, maxWidth: 480 }}
            rowKey="category"
            pagination={false}
            dataSource={reportData.by_category}
            columns={[
              {
                title: "分类",
                dataIndex: "category",
                render: (v: string) => CATEGORY_LABEL[v] || v,
              },
              { title: "笔数", dataIndex: "claim_count" },
              {
                title: "金额",
                dataIndex: "amount_total",
                render: (v: string) => `¥${parseFloat(v).toFixed(2)}`,
              },
            ]}
          />
        )}
        </>
      )}
    </Card>
  );

  const permTab = (
    <Card
      title="审批授权"
      extra={
        <Button type="primary" loading={permSaving} onClick={savePermissions}>
          保存授权
        </Button>
      }
    >
      <Typography.Paragraph type="secondary">
        勾选后可被选为报销审批人。仅超管可配置。
      </Typography.Paragraph>
      <Table
        rowKey="user_id"
        loading={permLoading}
        dataSource={permissions}
        pagination={false}
        columns={[
          { title: "用户名", dataIndex: "username" },
          { title: "显示名", dataIndex: "display_name" },
          {
            title: "角色",
            dataIndex: "role",
            render: (v: string) => ROLE_LABEL[v] || v,
          },
          {
            title: "可审批",
            render: (_, row) => (
              <Switch
                checked={row.can_approve}
                onChange={(checked) =>
                  setPermissions((prev) =>
                    prev.map((p) =>
                      p.user_id === row.user_id ? { ...p, can_approve: checked } : p
                    )
                  )
                }
              />
            ),
          },
        ]}
      />
    </Card>
  );

  const tabItems = [
    { key: "create", label: "新建报销", children: createTab },
    { key: "mine", label: "我的报销", children: listTab },
    { key: "pending", label: "待我审批", children: pendingTab },
    { key: "report", label: "报销报表", children: reportTab },
    ...(canManagePerm ? [{ key: "perm", label: "审批授权", children: permTab }] : []),
  ];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader title="报销审批" />
      <Content style={{ padding: 24 }}>
        <Tabs items={tabItems} />
      </Content>

      <Modal
        title={`报销详情 ${detail?.claim_no || ""}`}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={640}
      >
        {detail && (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <div>
              <Typography.Text type="secondary">申请人：</Typography.Text>
              {detail.applicant_name}
            </div>
            <div>
              <Typography.Text type="secondary">金额：</Typography.Text>¥{detail.amount}
            </div>
            <div>
              <Typography.Text type="secondary">状态：</Typography.Text>
              <Tag color={STATUS_TAG[detail.status]?.color}>{STATUS_TAG[detail.status]?.label}</Tag>
            </div>
            <div>
              <Typography.Text type="secondary">申请备注：</Typography.Text>
              {detail.remark || "无"}
            </div>
            <div>
              <Typography.Text type="secondary">提交时间：</Typography.Text>
              {dayjs(detail.submitted_at).format("YYYY-MM-DD HH:mm")}
            </div>
            {detail.attachments.length > 0 && (
              <div>
                <Typography.Text type="secondary">附件：</Typography.Text>
                <Image.PreviewGroup>
                  <Space wrap>
                    {detail.attachments.map((a) => (
                      <Image
                        key={a.id}
                        width={80}
                        height={80}
                        style={{ objectFit: "cover" }}
                        src={
                          a.data_base64.startsWith("data:")
                            ? a.data_base64
                            : `data:${a.content_type};base64,${a.data_base64}`
                        }
                      />
                    ))}
                  </Space>
                </Image.PreviewGroup>
              </div>
            )}
            <div>
              <Typography.Text strong>审批记录</Typography.Text>
              <Table
                size="small"
                rowKey="id"
                pagination={false}
                style={{ marginTop: 8 }}
                dataSource={detail.approvers}
                columns={[
                  { title: "审批人", dataIndex: "approver_name" },
                  {
                    title: "状态",
                    dataIndex: "status",
                    render: (v: string) => APPROVER_STATUS[v] || v,
                  },
                  { title: "意见", dataIndex: "comment", ellipsis: true },
                  {
                    title: "时间",
                    dataIndex: "acted_at",
                    render: (v: string | null) => (v ? dayjs(v).format("YYYY-MM-DD HH:mm") : "-"),
                  },
                ]}
              />
            </div>
          </Space>
        )}
      </Modal>

      <Modal
        title={actionType === "approve" ? "审批通过" : "审批驳回"}
        open={actionOpen}
        onCancel={() => setActionOpen(false)}
        onOk={() => actionForm.submit()}
      >
        <Form form={actionForm} layout="vertical" onFinish={submitAction}>
          <Form.Item
            name="comment"
            label="审批意见"
            rules={[{ required: true, message: "请填写审批意见" }]}
          >
            <TextArea rows={3} maxLength={500} showCount />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="编辑重提报销单"
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={() => editForm.submit()}
        okText="重新提交"
        confirmLoading={editSubmitting}
        width={560}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" onFinish={submitEdit}>
          <Form.Item name="amount" label="报销金额" rules={[{ required: true, message: "请输入金额" }]}>
            <InputNumber min={0.01} precision={2} prefix="¥" style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="category" label="报销分类" rules={[{ required: true, message: "请选择分类" }]}>
            <Select options={CATEGORY_OPTIONS} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <TextArea rows={3} maxLength={500} showCount placeholder="费用说明（选填）" />
          </Form.Item>
          <Form.Item label="审批人">
            {selectableApprovers.length === 0 ? (
              <Typography.Text type="warning">暂无审批人，请联系超管配置审批授权</Typography.Text>
            ) : (
              <Space wrap>
                {selectableApprovers.map((a) => (
                  <Tag key={a.id} color="blue">
                    {a.display_name}（{ROLE_LABEL[a.role] || a.role}）
                  </Tag>
                ))}
              </Space>
            )}
          </Form.Item>
          <Form.Item label="附件/图片（最多5张，单张≤3MB，不上传则清空原附件）">
            <Upload
              listType="picture-card"
              fileList={editFileList}
              accept="image/*"
              beforeUpload={() => false}
              onChange={({ fileList: fl }) => setEditFileList(fl.slice(0, 5))}
            >
              {editFileList.length < 5 && "+ 上传"}
            </Upload>
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}
