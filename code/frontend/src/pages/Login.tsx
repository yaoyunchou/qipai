import { Button, Card, Checkbox, Form, Input, message } from "antd";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken, type UserMe } from "../api/client";
import { useUser } from "../context/UserContext";

const USERNAME_KEY = "qipai_remember_username";

export default function LoginPage() {
  const navigate = useNavigate();
  const { setMe } = useUser();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem(USERNAME_KEY);
    if (saved) {
      form.setFieldsValue({ username: saved, remember: true });
    }
  }, [form]);

  const onFinish = async (values: { username: string; password: string; remember?: boolean }) => {
    if (loading) return;
    setLoading(true);
    try {
      const { access_token } = await api<{ access_token: string }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username: values.username, password: values.password }),
      });
      if (values.remember) {
        localStorage.setItem(USERNAME_KEY, values.username);
      } else {
        localStorage.removeItem(USERNAME_KEY);
      }
      setToken(access_token);
      const me = await api<UserMe>("/api/v1/auth/me");
      setMe(me);
      message.success(`欢迎，${me.display_name || me.username}`);
      navigate(me.home_path);
    } catch (e) {
      message.error(e instanceof Error ? e.message : "登录失败");
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <Card title="棋牌室开单系统" style={{ width: 360 }}>
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input placeholder="admin" autoFocus autoComplete="username" onPressEnter={() => form.submit()} />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password placeholder="admin123" autoComplete="current-password" onPressEnter={() => form.submit()} />
          </Form.Item>
          <Form.Item name="remember" valuePropName="checked">
            <Checkbox>记住账号</Checkbox>
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading} disabled={loading}>
            登录
          </Button>
        </Form>
      </Card>
    </div>
  );
}
