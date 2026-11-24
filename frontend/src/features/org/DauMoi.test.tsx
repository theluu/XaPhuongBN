import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const calls: { path: string; method?: string; body: unknown }[] = [];
const DATA = {
  vai_tro: { chu_tri: "Chủ trì", phoi_hop: "Phối hợp", cung_cap: "Cung cấp số liệu", xac_nhan: "Xác nhận" },
  cap: { phuong: "Phường", thanh_pho: "Thành phố", chuyen_nganh: "Cơ quan chuyên ngành", chu_dau_tu: "Chủ đầu tư" },
  phieu: {}, nhom: ["chung", "ngan_sach", "dan_cu"], cua_toi: ["THUE"],
  dau_moi: [
    { id: 1, ma: "STC", ten: "Sở Tài chính", cap: "chuyen_nganh", cap_ten: "Cơ quan chuyên ngành", noi_dung: "Xác nhận phạm vi và số liệu ngân sách",
      trach_nhiem: [{ nhom: "ngan_sach", vai_tro: "chu_tri", vai_tro_ten: "Chủ trì", noi_dung: "Thống nhất biểu mẫu, đối soát" }], phieu_nguon: [{ ma: "B", ten: "Thu, chi ngân sách" }],
      chi_tieu: ["NQ01-05a"], nguon: [], nguoi_lien_he: "Lê Văn Hùng", chuc_vu: "Trưởng phòng", dien_thoai: "0222 3822 455", email: null,
      tai_khoan: [{ id: 7, username: "sotaichinh", ho_ten: "Lê Văn Hùng", chuc_danh: "", trang_thai: "hoat_dong", roles: ["chuyen_nganh"], nhom: ["ngan_sach"] }],
      thu_tu: 0, viec_tre: [], so_qua_han: 0 },
    { id: 2, ma: "THUE", ten: "Cơ quan Thuế", cap: "chuyen_nganh", cap_ten: "Cơ quan chuyên ngành", noi_dung: "",
      trach_nhiem: [{ nhom: "ngan_sach", vai_tro: "cung_cap", vai_tro_ten: "Cung cấp số liệu", noi_dung: "Số thu NSNN" }], phieu_nguon: [], chi_tieu: [], nguon: [],
      nguoi_lien_he: "", chuc_vu: "", dien_thoai: null, email: null, tai_khoan: [], thu_tu: 1,
      viec_tre: [{ ma: "NQ01-05a", ten: "Tăng tổng thu", ky: "2026-Q3", han: "2026-10-20", con_lai_ngay: -5, muc: "qua_han" }], so_qua_han: 1 },
  ],
};
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { method?: string; body?: unknown }) => {
    if (o?.method) { calls.push({ path, method: o.method, body: o.body }); return Promise.resolve({}); }
    if (path === "/api/dau-moi") return Promise.resolve(DATA);
    if (path === "/api/admin/users") return Promise.resolve([{ id: 7, username: "sotaichinh", ho_ten: "Lê Văn Hùng", chuc_danh: "", trang_thai: "hoat_dong", roles: [], nhom: [] },
      { id: 8, username: "khobac", ho_ten: "Phạm Thị Hương", chuc_danh: "", trang_thai: "hoat_dong", roles: [], nhom: [] }]);
    return Promise.resolve([]);
  },
  ApiError: class extends Error {},
}));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ can: () => true, me: { roles: ["quan_tri_don_vi"] } }) }));

import { DauMoiTab, MyResponsibility } from "./DauMoi";

describe("Đầu mối và trách nhiệm", () => {
  it("ma trận, thẻ đầu mối có liên hệ, tài khoản; sửa và gắn thêm tài khoản", async () => {
    renderWithProviders(<DauMoiTab />);
    const m = await screen.findByRole("table", { name: "Ma trận trách nhiệm" });
    expect(within(m).getAllByText("CT").length).toBeGreaterThan(0);
    const card = screen.getByRole("article", { name: "Sở Tài chính" });
    expect(within(card).getByText("0222 3822 455")).toBeInTheDocument();
    expect(within(card).getByText("sotaichinh")).toBeInTheDocument();
    expect(screen.getByRole("article", { name: "Cơ quan Thuế" })).toHaveTextContent("Đầu mối của bạn");
    expect(screen.getByText("1 kỳ quá hạn nộp")).toBeInTheDocument();
    await userEvent.click(within(card).getByRole("button", { name: "Sửa" }));
    const f = await screen.findByRole("form", { name: "Sửa đầu mối Sở Tài chính" });
    await userEvent.click(await within(f).findByLabelText(/Phạm Thị Hương/));
    await userEvent.click(within(f).getByRole("button", { name: "Lưu" }));
    expect(calls.at(-1)).toMatchObject({ path: "/api/dau-moi/STC", method: "PUT", body: { ma: "STC", user_ids: [7, 8], chi_tieu: ["NQ01-05a"] } });
  });

  it("trang chủ hiện trách nhiệm của tài khoản đầu mối", async () => {
    renderWithProviders(<MyResponsibility />);
    expect(await screen.findByText("Bạn là đầu mối của Cơ quan Thuế")).toBeInTheDocument();
    expect(screen.getByText(/1 kỳ số liệu cần nộp, 1 quá hạn/)).toBeInTheDocument();
  });
});
