import { Button, Layout, Space, Typography } from "antd";
import { Link, useNavigate } from "react-router-dom";
import { clearToken } from "../api/client";
import { useMe } from "../hooks/useMe";

const { Header } = Layout;

type AppHeaderProps = {
  title: string;
};

export default function AppHeader({ title }: AppHeaderProps) {
  const navigate = useNavigate();
  const { me } = useMe();

  const showFloor = me?.role !== "SHAREHOLDER";
  const showOrders = me?.role !== "SHAREHOLDER";
  const showAdmin = me?.role === "ADMIN" || me?.role === "MANAGER";

  return (
    <Header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", color: "#fff" }}>
      <Typography.Title level={4} style={{ color: "#fff", margin: 0 }}>
        {title}
      </Typography.Title>
      <Space>
        {showFloor && (
          <Link to="/floor" style={{ color: "#fff" }}>
            开单
          </Link>
        )}
        {showOrders && (
          <Link to="/orders" style={{ color: "#fff" }}>
            订单
          </Link>
        )}
        <Link to="/reports" style={{ color: "#fff" }}>
          报表
        </Link>
        {showAdmin && (
          <Link to="/admin" style={{ color: "#fff" }}>
            {me?.role === "ADMIN" ? "后台配置" : "后台"}
          </Link>
        )}
        <Button
          size="small"
          onClick={() => {
            clearToken();
            navigate("/login");
          }}
        >
          退出
        </Button>
      </Space>
    </Header>
  );
}
