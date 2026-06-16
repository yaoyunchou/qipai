import { Button, Card, Form, Input, message } from "antd";
import { useNavigate } from "react-router-dom";
import { api, setToken, type UserMe } from "../api/client";

export default function LoginPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  const onFinish = async (values: { username: string; password: string }) => {
    try {
      const { access_token } = await api<{ access_token: string }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(values),
      });
      setToken(access_token);
      const me = await api<UserMe>("/api/v1/auth/me");
      message.success(`欢迎，${me.display_name || me.username}`);
      navigate(me.home_path);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "登录失败");
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Card title="棋牌室开单系统" style={{ width: 360 }}>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input placeholder="admin" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password placeholder="admin123" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  );
}
