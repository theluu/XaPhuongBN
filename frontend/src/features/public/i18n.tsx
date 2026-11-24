import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { formatDate as vnDate, formatDateTime as vnDateTime, formatNumber as vnNumber, formatPeriod as vnPeriod } from "@/lib/format";

export type Lang = "vi" | "en";
let LANG: Lang = "vi";
const KEY = "ioc-ngon-ngu";

function initial(): Lang {
  try {
    const q = new URLSearchParams(window.location.search).get("lang");
    if (q === "en" || q === "vi") return q;
    const s = window.localStorage.getItem(KEY);
    if (s === "en" || s === "vi") return s;
  } catch { /* trình duyệt chặn lưu trữ */ }
  return "vi";
}

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({ lang: "vi", setLang: () => undefined });

/** Ngôn ngữ trang công khai (Tiếng Việt / English). Đổi ngôn ngữ dựng lại toàn bộ cây con để mọi định dạng số, ngày cập nhật. */
export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, set] = useState<Lang>(initial);
  LANG = lang;
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const setLang = (l: Lang) => {
    try { window.localStorage.setItem(KEY, l); } catch { /* bỏ qua */ }
    set(l);
  };
  return <Ctx.Provider value={{ lang, setLang }}><div key={lang} className="contents">{children}</div></Ctx.Provider>;
}
export const useLang = () => useContext(Ctx);
export const isEn = () => LANG === "en";

/* ───────── Định dạng theo ngôn ngữ ───────── */
export function n(v: number | null | undefined, digits?: number): string {
  if (LANG === "vi") return vnNumber(v, digits);
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return new Intl.NumberFormat("en-US", digits !== undefined ? { maximumFractionDigits: digits, minimumFractionDigits: digits } : { maximumFractionDigits: 2 }).format(v);
}
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function period(ky: string): string {
  if (LANG === "vi") return vnPeriod(ky);
  let m = ky.match(/^(\d{4})-Q([1-4])$/);
  if (m) return `Q${m[2]} ${m[1]}`;
  m = ky.match(/^(\d{4})-(\d{2})$/);
  if (m) return `${MONTHS[Number(m[2]) - 1]} ${m[1]}`;
  if (/^\d{4}$/.test(ky)) return `Year ${ky}`;
  return ky;
}
export const monthTick = (k: string) => (LANG === "vi" ? `T${Number(k.slice(5))}` : MONTHS[Number(k.slice(5)) - 1]);
export function date(iso: string | null | undefined): string {
  if (LANG === "vi" || !iso) return vnDate(iso);
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}
export function dateTime(iso: string | null | undefined): string {
  if (LANG === "vi" || !iso) return vnDateTime(iso);
  return new Date(iso).toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

/* ───────── Chữ giao diện: t("tiếng Việt") → bản tiếng Anh nếu có ───────── */
const UI: Record<string, string> = {
  "Cổng số liệu công khai": "Open Data Portal", "Kỳ công bố": "Reporting period", "Công bố": "Published", "Đăng nhập": "Sign in",
  "Đăng nhập hệ thống": "Staff sign-in", "Các phường": "All wards", "Trang chủ": "Home", "Bản demo · số liệu minh họa": "Demo · illustrative data",
  "Chỉ tiêu công khai": "Public indicators", "Đã xác nhận": "Confirmed", "Đạt kế hoạch": "On target", "Cần nỗ lực": "Needs effort",
  "Chỉ số điều hành chính": "Key performance gauges", "Chỉ tiêu đạt kế hoạch": "Indicators on target", "Thu NSNN / dự toán": "Revenue vs. budget",
  "Giải ngân đầu tư công": "Public investment disbursed", "Hồ sơ TTHC đúng hạn": "Applications on time", "Phản ánh xử lý đúng hạn": "Feedback resolved on time",
  "Số liệu nổi bật": "Highlights", "Các chỉ số tổng hợp chính của phường": "Main aggregate figures of the ward",
  "Tổng hợp": "Summary", "Kinh tế – xã hội": "Socio-economic", "Ngân sách": "Budget", "Dịch vụ công": "Public services",
  "Phản ánh kiến nghị": "Citizen feedback", "Đầu tư công": "Public investment", "Công trình": "Construction", "Dân cư": "Population",
  "Bản đồ": "Map", "Chỉ đạo – điều hành": "Governance & directives", "Chỉ số phục vụ": "Service index",
  "Đang cập nhật": "Pending", "Đạt": "On target", "Theo dõi": "Monitoring", "Mục tiêu": "Target", "Nguồn": "Source", "chốt": "closed",
  "Mức hoàn thành": "Completion", "so với kỳ trước": "vs. previous period", "so với cùng kỳ": "vs. same period last year",
  "Đơn vị chưa công bố số liệu kỳ nào": "No period has been published yet",
  "Số liệu sẽ hiển thị sau khi lãnh đạo đơn vị xác nhận và công bố.": "Figures appear after the ward leadership confirms and publishes them.",
  "Không tìm thấy trang công khai của đơn vị": "Public page not found", "Về trang chủ": "Back to home", "Thử lại": "Try again",
  "Không tải được dữ liệu. Vui lòng thử lại.": "Could not load data. Please try again.", "Đang tải…": "Loading…",
  "Bỏ qua đến nội dung chính": "Skip to main content", "Chia sẻ": "Share", "In / Lưu PDF": "Print / Save PDF", "Tải CSV": "Download CSV",
  "Sao chép liên kết": "Copy link", "Đã sao chép": "Copied", "Quét mã để mở trang trên điện thoại": "Scan to open on your phone", "Đóng": "Close",
  "Chi tiết": "Details", "chỉ tiêu": "indicators", "Tháng": "Monthly", "Quý": "Quarterly",
  "Số liệu trên trang do đơn vị xác nhận và công bố theo kỳ. Thông tin nội bộ chỉ xem được khi đăng nhập.":
    "Figures on this page are confirmed and published by the ward each period. Internal information requires sign-in.",
  "Chỉ số chưa được xác nhận trong kỳ hiển thị “Đang cập nhật”. Số liệu chính thức theo văn bản báo cáo của UBND phường.":
    "Figures not yet confirmed for the period are shown as “Pending”. Official figures follow the ward People's Committee reports.",
  "Cổng số liệu công khai các xã, phường": "Open data portal of communes and wards", "Số liệu đã xác nhận.": "Confirmed figures.",
  "Công khai theo kỳ.": "Published every period.", "Đã công bố": "Published", "Chưa công bố": "Not published", "Xem trang công khai": "Open public page",
  "Mỗi phường có trang riêng, hiển thị các chỉ tiêu lãnh đạo phường đã duyệt công khai. Cán bộ đăng nhập để vào hệ thống điều hành nội bộ.":
    "Each ward has its own page showing the indicators its leadership approved for publication. Staff sign in to access the internal operations system.",
  "So sánh các phường": "Ward comparison", "Bản công bố mới nhất của từng phường": "Latest published period of each ward",
  "Chỉ tiêu đạt": "Indicators on target", "Thu NS / dự toán": "Revenue / budget", "Giải ngân": "Disbursement", "TTHC đúng hạn": "Applications on time",
  "PAKN đúng hạn": "Feedback on time", "Điểm phục vụ": "Service score", "Dân số": "Population", "Kỳ": "Period", "Phường": "Ward",
};
export const t = (s: string) => (LANG === "en" ? UI[s] ?? s : s);

/* ───────── Nhãn dữ liệu từ máy chủ (tên lĩnh vực, trạng thái, phòng ban, đơn vị đo…) ───────── */
const DATA: Record<string, string> = {
  "Dân số": "Population", "Kinh tế – xã hội": "Socio-economic", "Giáo dục, y tế, môi trường": "Education, health & environment", "Ngân sách": "Budget",
  "Đầu tư công": "Public investment", "Dân cư": "Population", "Hành chính công": "Public administration", "Công trình": "Construction", "Khác": "Other",
  "Mới phát hiện": "Newly detected", "Đã giao xử lý": "Assigned", "Đang xử lý": "In progress", "Gia hạn": "Extended", "Hoàn thành": "Completed",
  "Mức cao": "High", "Mức trung bình": "Medium", "Mức thấp": "Low", "Rất hài lòng": "Very satisfied", "Hài lòng": "Satisfied",
  "Bình thường": "Neutral", "Chưa hài lòng": "Unsatisfied", "Không hài lòng": "Very unsatisfied", "Chưa đánh giá": "Not rated",
  "Đã giải quyết": "Resolved", "Mới tiếp nhận": "Received", "Quá hạn": "Overdue",
  "Vệ sinh môi trường": "Sanitation", "Trật tự đô thị": "Urban order", "Hạ tầng": "Infrastructure", "An ninh trật tự": "Public security",
  "Đất đai, xây dựng": "Land & construction",
  "Công khai, minh bạch": "Openness & transparency", "Tiến độ giải quyết": "Processing timeliness", "Dịch vụ công trực tuyến": "Online public services",
  "Mức độ hài lòng": "Satisfaction", "Số hóa hồ sơ": "Record digitisation",
  "Phòng Kinh tế, Hạ tầng và Đô thị": "Economic, Infrastructure & Urban Dept.", "Văn phòng HĐND và UBND": "Office of People's Council & Committee",
  "Phòng Văn hóa – Xã hội": "Culture & Social Affairs Dept.", "Bộ phận Một cửa": "One-stop shop", "Công an phường": "Ward police",
  "Ban Quản lý dự án": "Project Management Board", "Bộ phận Tài chính – Kế toán": "Finance & Accounting", "Văn hóa – Xã hội": "Culture & Social Affairs",
  "Địa chính – Xây dựng": "Land & Construction", "Chưa phân công": "Unassigned",
  "Phường làm chủ đầu tư": "Ward is investor", "Cơ quan cấp thành phố làm chủ đầu tư, thi công trên địa bàn": "City agency is investor, built in ward",
  "Giao thông": "Transport", "Công trình công cộng": "Public facilities", "Thoát nước": "Drainage", "Chỉnh trang đô thị": "Urban upgrading",
  "Trường học": "School", "Thủy lợi": "Irrigation",
  "Thu ngân sách trên địa bàn": "State revenue collected in the ward", "Thu ngân sách phường được hưởng": "Revenue retained by the ward",
  "Giải ngân đầu tư công": "Public investment disbursement", "Hồ sơ TTHC giải quyết đúng hạn": "Administrative applications on time",
  "Phản ánh kiến nghị quá hạn": "Overdue citizen feedback", "Hồ sơ TTHC giải quyết đúng hạn (30 ngày)": "Applications resolved on time (30 days)",
  "Tiền sử dụng đất": "Land use fees", "Thuế công thương nghiệp ngoài quốc doanh": "Non-state business tax", "Thuế thu nhập cá nhân": "Personal income tax",
  "Thu khác ngân sách": "Other revenue", "Phí, lệ phí": "Fees and charges", "Thuế sử dụng đất phi nông nghiệp": "Non-agricultural land tax",
  "Chi đầu tư phát triển": "Development investment", "Chi quản lý hành chính": "Administration", "Chi sự nghiệp giáo dục": "Education",
  "Chi sự nghiệp môi trường": "Environment", "Chi đảm bảo xã hội": "Social welfare",
};
const IND: Record<string, string> = {
  "NQ01-05a": "Growth of total state revenue in the ward", "NQ01-05b": "Growth of domestic revenue (excl. land fees)", "NQ01-06": "Growth of average output value",
  "NQ01-07a": "General urban plan completed", "NQ01-07b": "Detailed planning coverage", "NQ01-08a": "Road land per capita", "NQ01-08b": "Streets with lighting",
  "NQ01-09": "Income per capita", "NQ01-10": "Poor households (multidimensional standard)", "NQ01-11": "Schools meeting national standard level 2",
  "NQ01-12": "Health insurance coverage", "NQ01-14": "Population with clean water", "NQ01-15": "Household waste collected & treated",
  "NQ01-16": "Urban wastewater treated to standard", "DT-CX": "Public green space per capita", "DT-TRUONG": "Number of schools",
  "DT-LOP": "Number of classes", "DT-HS": "Number of pupils",
};
const UNIT: Record<string, string> = {
  "người": "people", "hộ": "households", "trường": "schools", "lớp": "classes", "học sinh": "pupils", "phản ánh": "reports", "hồ sơ": "applications",
  "tỷ đồng": "VND bn", "tỷ": "bn", "%/năm": "%/yr", "có/không": "yes/no", "m²/người": "m²/person", "triệu đồng/người/năm": "VND m/person/yr",
  "chỉ tiêu": "indicators", "dự án": "projects", "công trình": "works", "vấn đề": "issues", "nhiệm vụ": "tasks", "điểm": "points",
};
export function d(s: string | null | undefined): string {
  if (!s) return "";
  if (LANG === "vi") return s;
  if (DATA[s]) return DATA[s];
  const m = s.match(/^Tổ dân phố số (\d+)$/);
  if (m) return `Residential group ${m[1]}`;
  return s;
}
export const ind = (ma: string, ten: string) => (LANG === "en" ? IND[ma] ?? ten : ten);
export const unit = (u: string) => (LANG === "en" ? UNIT[u] ?? u : u);
/** Chuỗi song ngữ tại chỗ: L("tiếng Việt", "English"). */
export const L = (vi: string, en: string) => (LANG === "en" ? en : vi);
