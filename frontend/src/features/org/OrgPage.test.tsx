import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const wl = (n: number, q: number) => ({ dang_xu_ly: n, qua_han: q, viec: n ? [{ loai: "phan_anh", id: 5, ten: "Đèn hỏng cả tuyến", han: "2026-11-01", qua_han_ngay: q ? 3 : null, link: "/phan-anh?id=5" }] : [] });
const u = (ma: string, ten: string, khoi: string, o: object = {}) => ({ id: ma.length, ma, ten, khoi, khoi_ten: khoi, cap_tren_ma: null, lanh_dao_phu_trach_ma: null, chuc_nang: "",
  dien_thoai: null, email: null, dia_chi: null, thu_tu: 0, khoi_luong: wl(0, 0), ...o });
const p = (id: number, ma: string, dv: string, ho_ten: string, chuc_vu: string, cap: string, o: object = {}) => ({ id, ma, don_vi_ma: dv, ho_ten, chuc_vu, cap, dien_thoai: `0900 000 00${id}`,
  email: null, nhiem_vu: "", linh_vuc: [], dia_ban_ids: [], user_id: null, thu_tu: id, is_sample: true, khoi_luong: wl(0, 0), ...o });
const data = {
  ten_don_vi: "Phường Việt Yên", cap: "phuong", khoi: {}, co_khoi_luong: true, dia_ban_label: "Tổ dân phố",
  don_vi: [u("DU", "Đảng ủy phường Việt Yên", "dang"), u("HDND", "Hội đồng nhân dân phường Việt Yên", "hdnd"), u("UBND", "Ủy ban nhân dân phường Việt Yên", "ubnd"),
    u("MTTQ", "Ủy ban MTTQ Việt Nam phường Việt Yên", "mttq"),
    u("KTHTDT", "Phòng Kinh tế, Hạ tầng và Đô thị", "chuyen_mon", { cap_tren_ma: "UBND", lanh_dao_phu_trach_ma: "PCT1", khoi_luong: wl(4, 1), dien_thoai: "0222 3874 105", chuc_nang: "Quy hoạch, xây dựng" }),
    u("VHXH", "Phòng Văn hóa – Xã hội", "chuyen_mon", { cap_tren_ma: "UBND", lanh_dao_phu_trach_ma: "PCT2" })],
  can_bo: [p(1, "CT", "UBND", "Lê Minh Châu", "Chủ tịch UBND", "truong", { nhiem_vu: "Phụ trách chung" }), p(2, "PCT1", "UBND", "Hoàng Văn Đức", "Phó Chủ tịch UBND", "pho", { nhiem_vu: "Phụ trách kinh tế, đô thị" }),
    p(3, "PCT2", "UBND", "Ngô Thị Lan", "Phó Chủ tịch UBND", "pho"), p(4, "TPKT", "KTHTDT", "Nguyễn Văn An", "Trưởng phòng Kinh tế, Hạ tầng và Đô thị", "truong", { khoi_luong: wl(1, 1), nhiem_vu: "Hạ tầng, xây dựng" }),
    p(5, "BT", "DU", "Trần Văn Bình", "Bí thư Đảng ủy", "truong")],
  dia_ban: [{ id: 1, ma: "TDP01", ten: "Tổ dân phố số 1", nguoi_dung_dau: "Nguyễn Văn Thành", dien_thoai: "0912 300 450", can_bo_phu_trach: ["TPKT"] }],
};
vi.mock("@/lib/api", () => ({ api: () => Promise.resolve(data), ApiError: class extends Error {} }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ can: () => false, tenant: null }) }));

import { OrgPage } from "./OrgPage";

describe("Cơ cấu tổ chức", () => {
  it("sơ đồ: Đảng ủy, HĐND, UBND (lãnh đạo → cụm đơn vị phụ trách), MTTQ và tổ dân phố", async () => {
    renderWithProviders(<OrgPage />);
    const ubnd = await screen.findByRole("region", { name: "Ủy ban nhân dân phường Việt Yên" });
    expect(screen.getByRole("region", { name: "Đảng ủy phường Việt Yên" })).toHaveTextContent("Trần Văn Bình");
    const pct1 = within(ubnd).getByText("Hoàng Văn Đức").closest("div.flex-col") as HTMLElement;
    expect(within(pct1).getByText("Phòng Kinh tế, Hạ tầng và Đô thị")).toBeInTheDocument();
    expect(within(pct1).queryByText("Phòng Văn hóa – Xã hội")).not.toBeInTheDocument();
    expect(within(pct1).getByText("4 việc · 1 quá hạn")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Tổ dân phố (1)" })).toHaveTextContent("Cán bộ theo dõi: Nguyễn Văn An");
  });

  it("bấm đơn vị mở chi tiết: lãnh đạo phụ trách, cán bộ, số điện thoại gọi được, việc đang xử lý", async () => {
    renderWithProviders(<OrgPage />);
    await userEvent.click(await screen.findByRole("button", { name: /Phòng Kinh tế, Hạ tầng và Đô thị/ }));
    const panel = screen.getByRole("complementary", { name: "Chi tiết Phòng Kinh tế, Hạ tầng và Đô thị" });
    expect(panel).toHaveTextContent("Lãnh đạo phụ trách: Hoàng Văn Đức");
    expect(within(panel).getByRole("link", { name: "0900 000 004" })).toHaveAttribute("href", "tel:0900000004");
    expect(within(panel).getAllByRole("link", { name: "Đèn hỏng cả tuyến" })[0]).toHaveAttribute("href", "/phan-anh?id=5");
    expect(within(panel).queryByRole("button", { name: /Thêm cán bộ/ })).not.toBeInTheDocument(); // không có quyền quản trị
  });

  it("danh bạ: tìm theo lĩnh vực phụ trách và lọc người đang có việc", async () => {
    renderWithProviders(<OrgPage />, "/co-cau-to-chuc?tab=danh-ba");
    const t = await screen.findByRole("table", { name: "Danh bạ và phân công" });
    expect(within(t).getAllByRole("row")).toHaveLength(6);
    await userEvent.type(screen.getByPlaceholderText(/Tìm theo tên/), "kinh tế");
    expect(within(t).getAllByRole("row").map((r) => r.textContent).join()).toContain("Hoàng Văn Đức");
    await userEvent.clear(screen.getByPlaceholderText(/Tìm theo tên/));
    await userEvent.click(screen.getByLabelText("Chỉ người đang có việc"));
    expect(within(t).getAllByRole("row")).toHaveLength(2);
    expect(t).toHaveTextContent("Nguyễn Văn An");
  });
});
