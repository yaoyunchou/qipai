import { Button, Card, DatePicker, Layout, Segmented, Space, Statistic, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import { api, downloadFile, type ReportSummary, type StoreConfigBrief } from "../api/client";
import AppHeader from "../components/AppHeader";
import { useMe } from "../hooks/useMe";

const { Content } = Layout;

export default function ReportsPage() {
  const { me } = useMe();
  const [period, setPeriod] = useState<"day" | "week" | "month">("day");
  const [anchorDate, setAnchorDate] = useState(dayjs());
  const [data, setData] = useState<ReportSummary | null>(null);
  const [exporting, setExporting] = useState(false);
  const [storeCfg, setStoreCfg] = useState<StoreConfigBrief | null>(null);

  const startParam = anchorDate.format("YYYY-MM-DD");

  const canExport = useMemo(() => {
    if (!me) return false;
    if (me.role === "MANAGER" || me.role === "SHAREHOLDER" || me.role === "ADMIN") return true;
    if (me.role === "CASHIER") return storeCfg?.cashier_allow_export ?? false;
    return false;
  }, [me, storeCfg]);

  useEffect(() => {
    api<StoreConfigBrief>("/api/v1/config/store")
      .then((c) => setStoreCfg(c))
      .catch(() => {});
  }, []);

  useEffect(() => {
    api<ReportSummary>(`/api/v1/reports/summary?period=${period}&start=${startParam}`)
      .then(setData)
      .catch((e) => message.error(e instanceof Error ? e.message : "加载失败"));
  }, [period, startParam]);

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadFile(
        `/api/v1/reports/export?period=${period}&start=${startParam}`,
        `report_${period}_${startParam}.xlsx`
      );
      message.success("导出成功");
    } catch (e) {
      message.error(e instanceof Error ? e.message : "导出失败");
    } finally {
      setExporting(false);
    }
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <AppHeader title="营业报表" />
      <Content style={{ padding: 24 }}>
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
          {canExport && (
            <Button loading={exporting} onClick={handleExport}>
              导出 Excel
            </Button>
          )}
        </Space>
        {data && (
          <Card title={`${data.start_date} ~ ${data.end_date}`}>
            <Space size="large" wrap>
              <Statistic title="开单量" value={data.order_count} />
              <Statistic title="原价营收" value={data.base_price_total} prefix="¥" />
              <Statistic title="实收营收" value={data.actual_price_total} prefix="¥" />
            </Space>
            {me?.role === "SHAREHOLDER" && (
              <p style={{ marginTop: 16, color: "#888" }}>股东仅查看汇总数据，订单明细不可见。</p>
            )}
          </Card>
        )}
      </Content>
    </Layout>
  );
}
