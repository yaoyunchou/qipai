const TOKEN_KEY = "qipai_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error((data as { detail?: string }).detail || res.statusText);
  }
  return data as T;
}

export type UserMe = {
  id: number;
  username: string;
  display_name: string;
  role: string;
  home_path: string;
};

export type TableBoardItem = {
  id: number;
  name: string;
  sort_order: number;
  is_enabled: boolean;
  status: "IDLE" | "OCCUPIED";
  open_order_id: number | null;
  open_order_no: string | null;
  base_price: string | null;
  actual_price: string | null;
  remark: string | null;
  opened_at: string | null;
  billing_minutes: number | null;
  enable_timing: boolean;
  billing_unit_minutes: number;
  unit_price: string | null;
};

export type ReportSummary = {
  period: string;
  start_date: string;
  end_date: string;
  order_count: number;
  base_price_total: string;
  actual_price_total: string;
};

export type OrderItem = {
  id: number;
  order_no: string;
  table_id: number;
  table_name: string | null;
  base_price: string;
  actual_price: string;
  billing_minutes: number | null;
  status: "OPEN" | "CLOSED";
  remark: string | null;
  opened_by: number;
  opened_by_name: string | null;
  opened_at: string;
  closed_by: number | null;
  closed_at: string | null;
};

export type StoreConfigBrief = {
  cashier_allow_export: boolean;
};

export type SelectableApprover = {
  id: number;
  display_name: string;
  role: string;
};

export type ExpenseApproverRecord = {
  id: number;
  approver_id: number;
  approver_name: string | null;
  status: "PENDING" | "APPROVED" | "REJECTED" | "SKIPPED";
  comment: string | null;
  acted_at: string | null;
};

export type ExpenseAttachment = {
  id: number;
  filename: string;
  content_type: string;
  data_base64: string;
};

export type ExpenseClaimItem = {
  id: number;
  claim_no: string;
  applicant_id: number;
  applicant_name: string | null;
  amount: string;
  remark: string | null;
  category: "FIXED" | "OPERATIONS" | "SANDBOX";
  status: "PENDING" | "APPROVED" | "REJECTED";
  submitted_at: string;
  attachments: ExpenseAttachment[];
  approvers: ExpenseApproverRecord[];
};

export type CategorySummary = {
  category: "FIXED" | "OPERATIONS" | "SANDBOX";
  claim_count: number;
  amount_total: string;
};

export type ExpenseReportSummary = {
  period: string;
  start_date: string;
  end_date: string;
  claim_count: number;
  amount_total: string;
  by_category: CategorySummary[];
};

export type ApprovePermissionItem = {
  user_id: number;
  username: string;
  display_name: string;
  role: string;
  can_approve: boolean;
};

export type UserAccount = {
  id: number;
  username: string;
  display_name: string;
  role: "CASHIER" | "MANAGER" | "SHAREHOLDER" | "ADMIN";
  is_enabled: boolean;
};

export async function downloadFile(path: string, filename = "download.xlsx") {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { headers });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error((data as { detail?: string }).detail || res.statusText);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
