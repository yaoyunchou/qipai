import { CloseOutlined, MenuOutlined } from "@ant-design/icons";
import { Layout, Typography } from "antd";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { clearToken } from "../api/client";
import { useUser } from "../context/UserContext";
import { useIsMobile } from "../hooks/useIsMobile";
import { useMe } from "../hooks/useMe";

const { Header } = Layout;

type AppHeaderProps = {
  title: string;
};

export default function AppHeader({ title }: AppHeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { me } = useMe();
  const { setMe } = useUser();
  const isMobile = useIsMobile();
  const [menuOpen, setMenuOpen] = useState(false);

  const showFloor = me?.role !== "SHAREHOLDER";
  const showOrders = me?.role !== "SHAREHOLDER";
  const showAdmin = me?.role === "ADMIN" || me?.role === "MANAGER";

  const logout = () => {
    clearToken();
    setMe(null);
    navigate("/login");
  };

  const navLinks = [
    showFloor && { to: "/floor", label: "前台开单" },
    showOrders && { to: "/orders", label: "订单明细" },
    { to: "/reports", label: "营业报表" },
    showAdmin && { to: "/admin", label: me?.role === "ADMIN" ? "后台配置" : "后台" },
  ].filter(Boolean) as { to: string; label: string }[];

  if (isMobile) {
    return (
      <>
        {/* 移动端顶部 Navbar */}
        <Header
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 16px",
            height: 52,
            lineHeight: "52px",
            position: "sticky",
            top: 0,
            zIndex: 200,
          }}
        >
          <Typography.Title level={5} style={{ color: "#fff", margin: 0, fontSize: 16 }}>
            {title}
          </Typography.Title>

          {/* 汉堡按钮 */}
          <button
            onClick={() => setMenuOpen((v) => !v)}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: "#fff",
              fontSize: 20,
              padding: "4px 6px",
              display: "flex",
              alignItems: "center",
              lineHeight: 1,
            }}
            aria-label="菜单"
          >
            {menuOpen ? <CloseOutlined /> : <MenuOutlined />}
          </button>
        </Header>

        {/* 折叠菜单 */}
        <div
          style={{
            position: "fixed",
            top: 52,
            left: 0,
            right: 0,
            zIndex: 199,
            background: "#002140",
            overflow: "hidden",
            maxHeight: menuOpen ? 400 : 0,
            transition: "max-height 0.25s ease",
            boxShadow: menuOpen ? "0 4px 12px rgba(0,0,0,0.25)" : "none",
          }}
        >
          {navLinks.map(({ to, label }) => {
            const active = location.pathname === to;
            return (
              <Link
                key={to}
                to={to}
                onClick={() => setMenuOpen(false)}
                style={{
                  display: "block",
                  padding: "14px 20px",
                  color: active ? "#1890ff" : "rgba(255,255,255,0.85)",
                  fontSize: 15,
                  borderLeft: active ? "3px solid #1890ff" : "3px solid transparent",
                  background: active ? "rgba(24,144,255,0.08)" : "transparent",
                  textDecoration: "none",
                }}
              >
                {label}
              </Link>
            );
          })}
          <div
            onClick={() => { setMenuOpen(false); logout(); }}
            style={{
              padding: "14px 20px",
              color: "rgba(255,255,255,0.5)",
              fontSize: 15,
              cursor: "pointer",
              borderTop: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            退出登录
          </div>
        </div>

        {/* 点击空白关闭菜单 */}
        {menuOpen && (
          <div
            onClick={() => setMenuOpen(false)}
            style={{ position: "fixed", inset: 0, zIndex: 198 }}
          />
        )}
      </>
    );
  }

  // 桌面端
  return (
    <Header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 24px" }}>
      <Typography.Title level={4} style={{ color: "#fff", margin: 0 }}>
        {title}
      </Typography.Title>
      <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
        {navLinks.map(({ to, label }) => (
          <Link key={to} to={to} style={{ color: location.pathname === to ? "#1890ff" : "#fff" }}>
            {label}
          </Link>
        ))}
        <span
          onClick={logout}
          style={{
            color: "#fff",
            fontSize: 13,
            opacity: 0.75,
            cursor: "pointer",
            border: "1px solid rgba(255,255,255,0.3)",
            borderRadius: 4,
            padding: "2px 10px",
          }}
        >
          退出
        </span>
      </div>
    </Header>
  );
}
