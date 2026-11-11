import type { IndicatorCard, Me, TenantInfo } from "@/lib/types";

export const tenant: TenantInfo = {
  id: 1, ma_dvhc: "P-VIETYEN", ten: "Phường Việt Yên", cap: "phuong",
  ten_co_quan: ["ĐẢNG ỦY – UBND PHƯỜNG VIỆT YÊN", "Hệ thống điều hành số phường"], logo_url: null,
  ban_do: { tam: [21.27, 106.1], zoom: 14 }, cho_phep_theo_tdp: true,
  modules: { ktxh: "bat", dan_cu: "bat", ngan_sach: "dang_ket_noi", dau_tu_cong: "bat", cong_trinh: "bat", tthc_pakn: "bat", gd_yt_mt: "bat" },
};

export const me: Me = {
  id: 7, username: "chutich", ho_ten: "Lê Minh Châu", chuc_danh: "Chủ tịch UBND", don_vi: "UBND", tenant_id: 1,
  phai_doi_mat_khau: false, roles: ["lanh_dao"], quyen: { "*": ["doc"], canh_bao: ["doc", "nhap", "duyet"] },
};

export function card(over: Partial<IndicatorCard> = {}): IndicatorCard {
  return {
    id: 1, ma: "NQ01-12", ten: "Tỷ lệ dân số tham gia BHYT", nhom: "gd_yt_mt", phan_he: "gd_yt_mt", bo: ["NQ01"],
    don_vi: "%", chieu: "tang_tot", ky: "2026-10", ke_hoach: 98.5, muc_tieu: null, muc_tieu_khoang: null,
    nguong_toan_tu: null, muc_tieu_2030: 99.8, muc_so_sanh: 98.5, thuc_hien: 98.6, du_bao: null, hoan_thanh_pct: 100.1,
    status: "dat", data_state: "da_xac_nhan", ky_truoc: { ky: "2026-09", gia_tri: 98.5 }, cung_ky: { ky: "2025-10", gia_tri: 97.9 },
    nguon: "BHXH thành phố", nguon_loai: "chuyen_nganh", don_vi_cung_cap: "Bảo hiểm xã hội",
    nguoi_xac_nhan: "Phó Chủ tịch UBND Hoàng Văn Đức", thoi_diem_chot: "2026-11-05T00:00:00Z",
    thoi_diem_dong_bo: "2026-11-06T00:00:00Z", lech_nguon: null, co_so_moi_cho_xac_nhan: false, is_sample: true,
    phan_loai_thong_tin: "noi_bo", ky_cap_nhat: "thang", value_id: 10, ...over,
  };
}

export const nq01Cards: IndicatorCard[] = [
  card({ id: 1, ma: "NQ01-01a", ten: "Tổ chức cơ sở Đảng hoàn thành tốt nhiệm vụ", status: "dat", ky: "2025", thuc_hien: 92.3 }),
  card({ id: 2, ma: "NQ01-03b", ten: "Tổ phó tổ dân phố là đảng viên", status: "nguy_co", ky: "2025", thuc_hien: 82.5 }),
  card({ id: 3, ma: "NQ01-06", ten: "Tăng tổng giá trị sản phẩm bình quân", status: "chua_du_du_lieu", data_state: "chua_co_qua_han", thuc_hien: null, hoan_thanh_pct: null, ky: "2025" }),
  card({ id: 4, ma: "NQ01-09", ten: "Thu nhập bình quân đầu người", status: "chua_du_du_lieu", data_state: "chua_co_qua_han", thuc_hien: null, hoan_thanh_pct: null, ky: "2025" }),
  card({ id: 5, ma: "NQ01-12", lech_nguon: { phuong: 99.1, chuyen_nganh: 98.6, chenh: 0.5, chenh_pct: 0.5 } }),
  card({ id: 6, ma: "NQ01-15", ten: "Thu gom, xử lý rác thải sinh hoạt", status: "nguy_co", data_state: "tam_thoi", thuc_hien: 97.5, nguoi_xac_nhan: null }),
];
