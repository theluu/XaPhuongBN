import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

vi.mock("@/components/ProjectMap", () => ({ ProjectMap: () => <div />, MapLegend: () => <div /> }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ tenant: null, can: () => true }) }));
const m = (kh: number, tt: number) => ({ id: 1, ngay: "2026-11-06", ke_hoach_pct: kh, thuc_te_pct: tt, cham: tt < kh, gpmb: "", vuong_mac: "", can_quyet_dinh: false, anh_keys: [], minh_chung_keys: [], trang_thai_xac_nhan: "da_xac_nhan" });
const works = [
  { id: 1, ma: "CT-02", ten: "Nhà văn hóa TDP số 8", don_vi_thuc_hien: "Cty A", ngay_ht: "2027-01-31", tre_han_ngay: null, chat_luong: "dat", camera_url: null, moi_nhat: m(40, 25), trang_thai: "dang_thi_cong", lat: 1, lng: 1 },
  { id: 2, ma: "CT-06", ten: "Cầu dân sinh", don_vi_thuc_hien: "Đội XD", ngay_ht: "2026-12-31", tre_han_ngay: null, chat_luong: null, camera_url: null, moi_nhat: null, trang_thai: "dang_thi_cong", lat: null, lng: null },
];
const summary = { so_cong_trinh: 2, so_cham: 1, so_tre_han: 0, so_can_quyet_dinh: 0, so_chua_cap_nhat: 1, chi_tieu_do_thi: [], diem_nghen: [] };
vi.mock("@/lib/api", () => ({ api: (p: string) => Promise.resolve(p.endsWith("summary") ? summary : p.endsWith("geojson") ? { features: [{ type: "Feature", geometry: { type: "Point", coordinates: [1, 1] }, properties: { ma: "CT-02" } }] } : works) }));

import { ConstructionPage } from "./ConstructionPage";

describe("Công trình", () => {
  it("thanh kế hoạch và thực tế, công trình không có vị trí được ghi chú", async () => {
    renderWithProviders(<ConstructionPage />);
    const t = await screen.findByRole("table", { name: "Tiến độ công trình" });
    const rows = within(t).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Chậm 15%");
    expect(rows[2]).toHaveTextContent("Chưa có báo cáo tiến độ");
    expect(screen.getByText(/1 công trình chưa có vị trí hợp lệ nên không hiển thị trên bản đồ/)).toBeInTheDocument();
  });
});
