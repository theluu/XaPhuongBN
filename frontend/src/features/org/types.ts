import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Workload { dang_xu_ly: number; qua_han: number; viec: { loai: string; id: number; ten: string; han: string | null; qua_han_ngay: number | null; link: string }[] }
export interface OrgUnit { id: number; ma: string; ten: string; khoi: string; khoi_ten: string; cap_tren_ma: string | null; lanh_dao_phu_trach_ma: string | null;
  chuc_nang: string; dien_thoai: string | null; email: string | null; dia_chi: string | null; thu_tu: number; khoi_luong: Workload | null }
export interface StaffRow { id: number; ma: string; don_vi_ma: string; ho_ten: string; chuc_vu: string; cap: "truong" | "pho" | "thanh_vien"; dien_thoai: string | null;
  email: string | null; nhiem_vu: string; linh_vuc: string[]; dia_ban_ids: number[]; user_id: number | null; thu_tu: number; is_sample: boolean; khoi_luong: Workload | null }
export interface OrgData { ten_don_vi: string; cap: string; khoi: Record<string, string>; don_vi: OrgUnit[]; can_bo: StaffRow[]; dia_ban_label: string;
  dia_ban: { id: number; ma: string; ten: string; nguoi_dung_dau: string | null; dien_thoai: string | null; can_bo_phu_trach: string[] }[]; co_khoi_luong: boolean }

export function useOrg() {
  return useQuery({ queryKey: ["co-cau"], queryFn: () => api<OrgData>("/api/co-cau"), staleTime: 120_000 });
}

/** Người đứng đầu đơn vị (cấp trưởng, nếu không có thì cấp phó đầu tiên). */
export function headOf(d: OrgData, ma: string): StaffRow | undefined {
  const s = d.can_bo.filter((x) => x.don_vi_ma === ma);
  return s.find((x) => x.cap === "truong") ?? s.find((x) => x.cap === "pho");
}
