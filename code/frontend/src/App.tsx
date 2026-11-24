import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api/client";
import { UserProvider } from "./context/UserContext";
import { useMe } from "./hooks/useMe";
import AdminPage from "./pages/Admin";
import CompanionLoansPage from "./pages/CompanionLoans";
import ExpensesPage from "./pages/Expenses";
import FloorPage from "./pages/Floor";
import LoginPage from "./pages/Login";
import LoansPage from "./pages/Loans";
import OrdersPage from "./pages/Orders";
import PlayCompanionPage from "./pages/PlayCompanion";
import ReportsPage from "./pages/Reports";

function RoleGate({ allow, children }: { allow: string[]; children: React.ReactNode }) {
  const { me, loading } = useMe();
  if (!getToken()) return <Navigate to="/login" replace />;
  if (loading || !me) return null;
  if (!allow.includes(me.role)) return <Navigate to={me.home_path || "/login"} replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/floor"
          element={
            <RoleGate allow={["CASHIER", "MANAGER", "SHAREHOLDER", "ADMIN"]}>
              <FloorPage />
            </RoleGate>
          }
        />
        <Route
          path="/reports"
          element={
            <RoleGate allow={["CASHIER", "MANAGER", "SHAREHOLDER", "ADMIN"]}>
              <ReportsPage />
            </RoleGate>
          }
        />
        <Route
          path="/orders"
          element={
            <RoleGate allow={["CASHIER", "MANAGER", "SHAREHOLDER", "ADMIN"]}>
              <OrdersPage />
            </RoleGate>
          }
        />
        <Route
          path="/expenses"
          element={
            <RoleGate allow={["CASHIER", "MANAGER", "SHAREHOLDER", "ADMIN"]}>
              <ExpensesPage />
            </RoleGate>
          }
        />
        <Route
          path="/play-companion"
          element={
            <RoleGate allow={["CASHIER", "MANAGER", "SHAREHOLDER", "ADMIN"]}>
              <PlayCompanionPage />
            </RoleGate>
          }
        />
        <Route
          path="/companion-loans"
          element={
            <RoleGate allow={["ADMIN", "SHAREHOLDER", "COMPANION"]}>
              <CompanionLoansPage />
            </RoleGate>
          }
        />
        <Route
          path="/loans"
          element={
            <RoleGate allow={["CASHIER", "MANAGER", "SHAREHOLDER", "ADMIN"]}>
              <LoansPage />
            </RoleGate>
          }
        />
        <Route
          path="/admin"
          element={
            <RoleGate allow={["MANAGER", "ADMIN"]}>
              <AdminPage />
            </RoleGate>
          }
        />
        <Route path="/config" element={<Navigate to="/admin" replace />} />
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "")}>
      <UserProvider>
        <AppRoutes />
      </UserProvider>
    </BrowserRouter>
  );
}
