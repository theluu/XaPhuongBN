export interface WorkItem {
  loai: "phan_anh" | "nhiem_vu" | "canh_bao";
  id: number; ma: string; ten: string; khan_cap: boolean; muc_do?: string;
  dia_diem: string; tdp_ten: string | null; don_vi: string | null; nguoi_phu_trach: string | null;
  trang_thai: string; trang_thai_ten: string; han: string | null; qua_han_ngay: number | null;
  lat: number | null; lng: number | null; linh_vuc_ten: string | null; moi: boolean; link: string;
}

export interface OpsOverview {
  chi_so: { phan_anh_moi: number; den_han_hom_nay: number; qua_han: number; canh_bao_mo: number };
  viec: WorkItem[]; tong: number; cap_nhat_luc: string; du_lieu_moi_nhat: string | null;
  pham_vi?: "tat_ca" | "cua_toi"; toi?: { ten: string; chuc_vu: string; don_vi_ten: string | null };
  bo_loc: { dia_ban_label: string; tdp: { id: number; ten: string }[] };
}

export interface HistoryRow { luc: string; nguoi: string; hanh_dong: string; ghi_chu?: string; han?: string; don_vi?: string; tien_do?: number; nguon?: string }

export interface FieldReport {
  id: number; ma: string; tieu_de: string; linh_vuc: string; linh_vuc_ten: string; khan_cap: boolean;
  tdp_id: number | null; tdp_ten: string | null; dia_chi: string; lat: number | null; lng: number | null; co_vi_tri: boolean;
  don_vi_phu_trach: string | null; don_vi_phu_trach_ten: string | null; nguoi_phu_trach: string | null;
  han_xu_ly: string | null; trang_thai: string; trang_thai_ten: string; qua_han_ngay: number | null; tien_do_pct: number;
  tiep_nhan_luc: string; cap_nhat_luc: string; is_sample: boolean;
  mo_ta?: string; nguon?: string; nguon_ten?: string; anh_keys?: string[]; chi_dao?: string; ket_qua?: string; anh_ket_qua_keys?: string[];
  hoan_thanh_luc?: string | null; lich_su?: HistoryRow[]; nguoi_gui_ten?: string | null; nguoi_gui_sdt?: string | null;
  quyen?: { giao: boolean; cap_nhat: boolean; xac_nhan: boolean };
}

export interface Catalogs {
  cap: string; dia_ban_label: string;
  dia_ban: { id: number; ma: string; ten: string; lat: number | null; lng: number | null }[];
  phong_ban: { ma: string; ten: string; loai?: string }[];
  linh_vuc: { ma: string; ten: string; chu_tri: string; han_ngay: number }[];
  nguon: { ma: string; ten: string }[];
}

export const HANH_DONG: Record<string, string> = {
  tiep_nhan: "Tiếp nhận phản ánh", xac_dinh_vi_tri: "Xác định địa điểm", giao_xu_ly: "Giao xử lý", cap_nhat_tien_do: "Cập nhật tiến độ",
  bao_cao_hoan_thanh: "Báo cáo hoàn thành", xac_nhan_hoan_thanh: "Xác nhận đã xử lý", tra_lai: "Trả lại xử lý tiếp", tu_choi: "Đóng: không thuộc thẩm quyền",
};
