import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Layout,
  Modal,
  Space,
  Select,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import { useCallback, useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, type TableBoardItem, type UserAccount } from "../api/client";
import AppHeader from "../components/AppHeader";
import { useIsMobile } from "../hooks/useIsMobile";
import { useMe } from "../hooks/useMe";

const { Content } = Layout;

type StoreConfig = {
  base_price: string;
  enable_timing: boolean;
  billing_unit_minutes: number;
  min_billing_units: number;
  cashier_allow_custom_price: boolean;
  cashier_allow_export: boolean;
  cashier_report_months: number | null;
  admin_report_days: number | null;
};

export default function AdminPage() {
  const { me, loading: meLoading } = useMe();
  const [form] = Form.useForm<StoreConfig>();
  const [cfg, setCfg] = useState<StoreConfig | null>(null);
  const [tables, setTables] = useState<TableBoardItem[]>([]);
  const [tableLoading, setTableLoading] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [addForm] = Form.useForm<{ name: string; sort_order: number }>();
  const [editOpen, setEditOpen] = useState(false);
  const [editForm] = Form.useForm<{ name: string; sort_order: number }>();
  const [editingTable, setEditingTable] = useState<TableBoardItem | null>(null);
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [userLoading, setUserLoading] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const [userForm] = Form.useForm<{
    username: string;
    password: string;
    display_name: string;
    role: UserAccount["role"];
  }>();

  const roleOptions = [
    { label: "收银员", value: "CASHIER" },
    { label: "门店经理", value: "MANAGER" },
    { label: "股东", value: "SHAREHOLDER" },
    { label: "超级管理员", value: "ADMIN" },
  ];

  const roleLabel = (role: UserAccount["role"]) =>
    roleOptions.find((r) => r.value === role)?.label ?? role;

  const isAdmin = me?.role === "ADMIN";
  const isMobile = useIsMobile();

  const loadConfig = useCallback(async () => {
    const c = await api<StoreConfig>("/api/v1/config/store");
    setCfg(c);
    form.setFieldsValue(c);
  }, [form]);

  const loadTables = useCallback(async () => {
    setTableLoading(true);
    try {
      const data = await api<TableBoardItem[]>("/api/v1/tables");
      setTables(data);
    } finally {
      setTableLoading(false);
    }
  }, []);

  const loadUsers = useCallback(async () => {
    setUserLoading(true);
    try {
      const data = await api<UserAccount[]>("/api/v1/users");
      setUsers(data);
    } finally {
      setUserLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!me || me.role === "SHAREHOLDER") return;
    loadConfig().catch((e) => message.error(e instanceof Error ? e.message : "加载配置失败"));
    if (isAdmin) {
      loadTables().catch((e) => message.error(e instanceof Error ? e.message : "加载台位失败"));
      loadUsers().catch((e) => message.error(e instanceof Error ? e.message : "加载用户失败"));
    }
  }, [me, isAdmin, loadConfig, loadTables, loadUsers]);

  const saveConfig = async (values: StoreConfig) => {
    try {
      await api("/api/v1/config/store", {
        method: "PUT",
        body: JSON.stringify({ ...values, enable_timing: false }),
      });
      message.success("配置已保存");
      loadConfig();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "保存失败");
    }
  };

  const addTable = async (values: { name: string; sort_order: number }) => {
    try {
      await api("/api/v1/tables", {
        method: "POST",
        body: JSON.stringify({ ...values, is_enabled: true }),
      });
      message.success("台位已添加");
      setAddOpen(false);
      addForm.resetFields();
      loadTables();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "添加失败");
    }
  };

  const toggleEnabled = async (row: TableBoardItem) => {
    try {
      await api(`/api/v1/tables/${row.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_enabled: !row.is_enabled }),
      });
      loadTables();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "更新失败");
    }
  };

  const openEditTable = (row: TableBoardItem) => {
    setEditingTable(row);
    editForm.setFieldsValue({ name: row.name, sort_order: row.sort_order });
    setEditOpen(true);
  };

  const saveEditTable = async (values: { name: string; sort_order: number }) => {
    if (!editingTable) return;
    try {
      await api(`/api/v1/tables/${editingTable.id}`, {
        method: "PATCH",
        body: JSON.stringify(values),
      });
      message.success("台位已更新");
      setEditOpen(false);
      setEditingTable(null);
      loadTables();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "更新失败");
    }
  };

  const addUser = async (values: {
    username: string;
    password: string;
    display_name: string;
    role: UserAccount["role"];
  }) => {
    try {
      await api("/api/v1/users", { method: "POST", body: JSON.stringify(values) });
      message.success("账号已创建");
      setUserOpen(false);
      userForm.resetFields();
      loadUsers();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "创建失败");
    }
  };

  const toggleUserEnabled = async (row: UserAccount) => {
    try {
      await api(`/api/v1/users/${row.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_enabled: !row.is_enabled }),
      });
      loadUsers();
    } catch (e) {
      message.error(e instanceof Error ? e.message : "更新失败");
    }
  };

  const resetUserPassword = (row: UserAccount) => {
    let pwd = "";
    Modal.confirm({
      title: `重置「${row.username}」密码`,
      content: (
        <Input.Password
          placeholder="新密码"
          onChange={(e) => {
            pwd = e.target.value;
          }}
        />
      ),
      onOk: async () => {
        if (pwd.length < 4) {
          message.error("密码至少 4 位");
          throw new Error("invalid");
        }
        await api(`/api/v1/users/${row.id}`, {
          method: "PATCH",
          body: JSON.stringify({ password: pwd }),
        });
        message.success("密码已重置");
        loadUsers();
      },
    });
  };

  const deleteUser = (row: UserAccount) => {
    Modal.confirm({
      title: `删除账号「${row.username}」？`,
      content: "删除后不可恢复。",
      onOk: async () => {
        await api(`/api/v1/users/${row.id}`, { method: "DELETE" });
        message.success("已删除");
        loadUsers();
      },
    });
  };

  const deleteTable = (row: TableBoardItem) => {
    Modal.confirm({
      title: `删除台位「${row.name}」？`,
      content: row.status === "OCCUPIED" ? "该台位占用中，无法删除。" : "删除后不可恢复。",
      okButtonProps: { disabled: row.status === "OCCUPIED" },
      onOk: async () => {
        await api(`/api/v1/tables/${row.id}`, { method: "DELETE" });
        message.success("已删除");
        loadTables();
      },
    });
  };

  if (meLoading) return null;
  if (me?.role === "SHAREHOLDER") return <Navigate to="/reports" replace />;

  const managerHub = (
    <Card>
      <Typography.Paragraph>门店经理后台入口，可前往：</Typography.Paragraph>
      <Space>
        <Link to="/floor">
          <Button type="primary">前台开单</Button>
        </Link>
        <Link to="/reports">
          <Button>营业报表</Button>
        </Link>
        <Link to="/orders">
          <Button>订单明细</Button>
        </Link>
      </Space>
      <Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>
        台位、基准价、账号等配置仅超级管理员可操作。
      </Typography.Paragraph>
    </Card>
  );

  const configTab = (
    <Card title="基准价与权限">
      {cfg && (
        <Form form={form} layout="vertical" onFinish={saveConfig} initialValues={cfg} disabled={!isAdmin}>
          <Form.Item name="base_price" label="全场基准价（元）" rules={[{ required: true }]}>
            <InputNumber min={0} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="cashier_allow_custom_price" label="收银员允许自定义改价" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="cashier_allow_export" label="收银员允许导出报表" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="cashier_report_months" label="收银员报表可查月数（留空=不限）">
            <InputNumber min={1} style={{ width: "100%" }} placeholder="不限" />
          </Form.Item>
          <Form.Item name="admin_report_days" label="超管报表日期筛选上限（天，留空=不限）">
            <InputNumber min={1} style={{ width: "100%" }} placeholder="不限" />
          </Form.Item>
          {isAdmin && (
            <Button type="primary" htmlType="submit">
              保存配置
            </Button>
          )}
        </Form>
      )}
    </Card>
  );

  const tablesTab = (
    <Card
      title="台位管理"
      extra={
        <Button type="primary" onClick={() => setAddOpen(true)}>
          新增台位
        </Button>
      }
    >
      {isMobile ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {tableLoading && <Typography.Text type="secondary">加载中…</Typography.Text>}
          {tables.map((row) => (
            <div
              key={row.id}
              style={{
                border: "1px solid #f0f0f0",
                borderRadius: 8,
                padding: "12px 14px",
                background: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
              }}
            >
              <div style={{ flex: 1 }}>
                <Typography.Text strong style={{ fontSize: 15 }}>{row.name}</Typography.Text>
                <div style={{ marginTop: 4, display: "flex", gap: 8, alignItems: "center" }}>
                  <Tag color={row.status === "IDLE" ? "green" : "red"} style={{ margin: 0 }}>
                    {row.status === "IDLE" ? "空闲" : "占用"}
                  </Tag>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>排序 {row.sort_order}</Typography.Text>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Switch size="small" checked={row.is_enabled} onChange={() => toggleEnabled(row)} />
                <Button type="link" size="small" style={{ padding: 0 }} onClick={() => openEditTable(row)}>编辑</Button>
                <Button type="link" danger size="small" style={{ padding: 0 }} onClick={() => deleteTable(row)}>删除</Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Table
          rowKey="id"
          loading={tableLoading}
          dataSource={tables}
          pagination={false}
          columns={[
            { title: "名称", dataIndex: "name" },
            { title: "排序", dataIndex: "sort_order", width: 80 },
            {
              title: "状态",
              width: 100,
              render: (_, row) => (
                <Tag color={row.status === "IDLE" ? "green" : "red"}>
                  {row.status === "IDLE" ? "空闲" : "占用"}
                </Tag>
              ),
            },
            {
              title: "启用",
              width: 80,
              render: (_, row) => (
                <Switch checked={row.is_enabled} onChange={() => toggleEnabled(row)} />
              ),
            },
            {
              title: "操作",
              width: 140,
              render: (_, row) => (
                <Space size={0}>
                  <Button type="link" size="small" onClick={() => openEditTable(row)}>编辑</Button>
                  <Button type="link" danger size="small" onClick={() => deleteTable(row)}>删除</Button>
                </Space>
              ),
            },
          ]}
        />
      )}
      <Modal title="新增台位" open={addOpen} onCancel={() => setAddOpen(false)} onOk={() => addForm.submit()}>
        <Form form={addForm} layout="vertical" onFinish={addTable} initialValues={{ sort_order: 0 }}>
          <Form.Item name="name" label="台位名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="如：1号桌" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title={`编辑台位 · ${editingTable?.name}`}
        open={editOpen}
        onCancel={() => {
          setEditOpen(false);
          setEditingTable(null);
        }}
        onOk={() => editForm.submit()}
      >
        <Form form={editForm} layout="vertical" onFinish={saveEditTable}>
          <Form.Item name="name" label="台位名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );

  const usersTab = (
    <Card
      title="账号管理"
      extra={
        <Button type="primary" onClick={() => setUserOpen(true)}>
          新建账号
        </Button>
      }
    >
      {isMobile ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {userLoading && <Typography.Text type="secondary">加载中…</Typography.Text>}
          {users.map((row) => (
            <div
              key={row.id}
              style={{
                border: "1px solid #f0f0f0",
                borderRadius: 8,
                padding: "12px 14px",
                background: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <Typography.Text strong style={{ fontSize: 15 }}>{row.display_name || row.username}</Typography.Text>
                <div style={{ marginTop: 4, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                  <Tag color="blue" style={{ margin: 0 }}>{roleLabel(row.role)}</Tag>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>@{row.username}</Typography.Text>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                <Switch
                  size="small"
                  checked={row.is_enabled}
                  disabled={row.id === me?.id}
                  onChange={() => toggleUserEnabled(row)}
                />
                <Button type="link" size="small" style={{ padding: 0 }} onClick={() => resetUserPassword(row)}>重置</Button>
                <Button
                  type="link"
                  danger
                  size="small"
                  style={{ padding: 0 }}
                  disabled={row.id === me?.id}
                  onClick={() => deleteUser(row)}
                >删除</Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Table
          rowKey="id"
          loading={userLoading}
          dataSource={users}
          pagination={false}
          columns={[
            { title: "用户名", dataIndex: "username" },
            { title: "显示名", dataIndex: "display_name" },
            { title: "角色", dataIndex: "role", render: (v: UserAccount["role"]) => roleLabel(v) },
            {
              title: "启用",
              width: 80,
              render: (_, row) => (
                <Switch
                  checked={row.is_enabled}
                  disabled={row.id === me?.id}
                  onChange={() => toggleUserEnabled(row)}
                />
              ),
            },
            {
              title: "操作",
              width: 160,
              render: (_, row) => (
                <Space size={0}>
                  <Button type="link" size="small" onClick={() => resetUserPassword(row)}>重置密码</Button>
                  <Button
                    type="link"
                    danger
                    size="small"
                    disabled={row.id === me?.id}
                    onClick={() => deleteUser(row)}
                  >删除</Button>
                </Space>
              ),
            },
          ]}
        />
      )}
      <Modal title="新建账号" open={userOpen} onCancel={() => setUserOpen(false)} onOk={() => userForm.submit()}>
        <Form
          form={userForm}
          layout="vertical"
          onFinish={addUser}
          initialValues={{ role: "CASHIER" as UserAccount["role"] }}
        >
          <Form.Item name="username" label="用户名" rules={[{ required: true, min: 2 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 4 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="display_name" label="显示名">
            <Input placeholder="留空则同用户名" />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={roleOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader title="后台管理" />
      <Content style={{ padding: isMobile ? 12 : 24, maxWidth: 960, margin: "0 auto", width: "100%" }}>
        {isAdmin ? (
          <Tabs
            items={[
              { key: "config", label: "门店配置", children: configTab },
              { key: "tables", label: "台位管理", children: tablesTab },
              { key: "users", label: "账号管理", children: usersTab },
            ]}
          />
        ) : (
          managerHub
        )}
      </Content>
    </Layout>
  );
}
