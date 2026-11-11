import type { DataState, Status } from "./types";

export const STATUS_LABEL: Record<Status, string> = {
  dat: "Đạt",
  nguy_co: "Có nguy cơ",
  chua_du_du_lieu: "Chưa đủ dữ liệu",
  theo_doi: "Theo dõi",
};
export const STATUS_COLOR: Record<Status, string> = {
  dat: "var(--xac-nhan)",
  nguy_co: "var(--tam-thoi)",
  chua_du_du_lieu: "var(--thieu)",
  theo_doi: "var(--muc-nhat)",
};
export const DATA_STATE_LABEL: Record<DataState, string> = {
  da_xac_nhan: "Đã xác nhận",
  tam_thoi: "Tạm thời – chờ xác nhận",
  chua_co_qua_han: "Chưa có hoặc quá hạn cập nhật",
};
export const PHAN_HE: { key: string; ten: string; path: string }[] = [
  { key: "ktxh", ten: "Chỉ tiêu KT-XH & Nghị quyết", path: "/chi-tieu" },
  { key: "dan_cu", ten: "Dân cư – an sinh", path: "/dan-cu" },
  { key: "ngan_sach", ten: "Thu – chi ngân sách", path: "/ngan-sach" },
  { key: "dau_tu_cong", ten: "Đầu tư công", path: "/dau-tu-cong" },
  { key: "cong_trinh", ten: "Công trình – đô thị", path: "/cong-trinh" },
  { key: "tthc_pakn", ten: "Hành chính công – PAKN", path: "/hanh-chinh" },
  { key: "gd_yt_mt", ten: "Giáo dục – Y tế – Môi trường", path: "/chat-luong-song" },
];
