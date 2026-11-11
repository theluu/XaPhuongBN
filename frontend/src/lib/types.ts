export type Status = "dat" | "nguy_co" | "chua_du_du_lieu" | "theo_doi";
export type DataState = "da_xac_nhan" | "tam_thoi" | "chua_co_qua_han";

export interface IndicatorCard {
  id: number;
  ma: string;
  ten: string;
  nhom: string;
  phan_he: string;
  bo: string[];
  don_vi: string;
  chieu: "tang_tot" | "giam_tot" | "dat_nguong" | "theo_doi";
  ky: string;
  ke_hoach: number | null;
  muc_tieu: number | null;
  muc_tieu_khoang: number[] | null;
  nguong_toan_tu: string | null;
  muc_tieu_2030: number | null;
  muc_so_sanh: number | null;
  thuc_hien: number | null;
  du_bao: number | null;
  hoan_thanh_pct: number | null;
  status: Status;
  data_state: DataState;
  ky_truoc: { ky: string; gia_tri: number | null; gop_tu?: string[] };
  cung_ky: { ky: string; gia_tri: number | null; gop_tu?: string[] };
  nguon: string;
  nguon_loai: string | null;
  don_vi_cung_cap: string;
  nguoi_xac_nhan: string | null;
  thoi_diem_chot: string | null;
  thoi_diem_dong_bo: string | null;
  lech_nguon: { phuong: number; chuyen_nganh: number; chenh: number; chenh_pct: number | null } | null;
  co_so_moi_cho_xac_nhan: boolean;
  is_sample: boolean;
  phan_loai_thong_tin: string;
  ky_cap_nhat: string;
  value_id: number | null;
  link?: string;
  ghi_chu?: string;
}

export interface TenantInfo {
  id: number;
  ma_dvhc: string;
  ten: string;
  cap: string;
  ten_co_quan: string[];
  logo_url: string | null;
  ban_do: { tam: [number, number]; zoom: number; tile_url?: string } | null;
  cho_phep_theo_tdp: boolean;
  modules: Record<string, "bat" | "dang_ket_noi" | "tat">;
}

export interface Me {
  id: number;
  username: string;
  ho_ten: string;
  chuc_danh: string;
  don_vi: string;
  tenant_id: number | null;
  phai_doi_mat_khau: boolean;
  roles: string[];
  quyen: Record<string, string[]>;
}
