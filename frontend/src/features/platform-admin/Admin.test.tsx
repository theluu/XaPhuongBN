import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const posts: { path: string; body: unknown }[] = [];
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { method?: string; body?: unknown }) => {
    if (o?.method) { posts.push({ path, body: o.body }); return Promise.resolve(path.endsWith("onboard") ? { tenant_id: 9, so_chi_tieu: 27, so_tdp: 6, lanh_dao: "ct_demo", mat_khau_tam: "Tam-123@abc" } : { da_xoa: 3 }); }
    if (path === "/api/platform/tenants") return Promise.resolve([{ id: 3, ma_dvhc: "P-VIETYEN", ten: "Phường Việt Yên", cap: "phuong", trang_thai: "hoat_dong", so_nguoi_dung: 8, so_chi_tieu: 27 }]);
    if (path === "/api/platform/packs") return Promise.resolve([{ ma: "phuong_do_thi", ten: "Phường đô thị", phien_ban: 1, so_chi_tieu: 27 }]);
    return Promise.resolve([]);
  },
  getToken: () => "t", ApiError: class extends Error {},
}));
let roles = ["quan_tri_nen_tang"];
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ me: { roles, quyen: {}, phai_doi_mat_khau: false }, can: () => true, tenant: null }) }));

import { AdminPage } from "./AdminPage";

describe("Quản trị nền tảng", () => {
  it("khởi tạo đơn vị mới qua 5 bước", async () => {
    roles = ["quan_tri_nen_tang"];
    renderWithProviders(<AdminPage />);
    expect(await screen.findByText("Phường Việt Yên")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Khởi tạo đơn vị mới" }));
    const w = screen.getByRole("form", { name: "Khởi tạo đơn vị" });
    expect(within(w).getByText("Bước 1/5: Đơn vị hành chính")).toBeInTheDocument();
    await userEvent.type(within(w).getByLabelText("Mã đơn vị hành chính"), "P-DEMO2");
    await userEvent.type(within(w).getByLabelText("Tên đơn vị"), "Phường Demo 2");
    await userEvent.click(within(w).getByRole("button", { name: "Tiếp tục" }));
    expect(within(w).getByText("Bước 2/5: Gói mẫu")).toBeInTheDocument();
    await userEvent.click(await within(w).findByLabelText(/Phường đô thị/));
    await userEvent.click(within(w).getByRole("button", { name: "Tiếp tục" }));
    await userEvent.clear(within(w).getByLabelText("Số tổ dân phố"));
    await userEvent.type(within(w).getByLabelText("Số tổ dân phố"), "6");
    await userEvent.click(within(w).getByRole("button", { name: "Tiếp tục" }));
    await userEvent.type(within(w).getByLabelText("Tên đăng nhập"), "ct_demo");
    await userEvent.type(within(w).getByLabelText("Họ tên"), "Nguyễn Văn Demo");
    await userEvent.type(within(w).getByLabelText("Chức danh"), "Chủ tịch UBND");
    await userEvent.click(within(w).getByRole("button", { name: "Tiếp tục" }));
    expect(within(w).getByText("Bước 5/5: Xác nhận")).toBeInTheDocument();
    await userEvent.click(within(w).getByRole("button", { name: "Khởi tạo" }));
    expect(await screen.findByText("Tam-123@abc")).toBeInTheDocument();
    expect(posts.at(-1)).toEqual({ path: "/api/platform/onboard", body: { ma_dvhc: "P-DEMO2", ten: "Phường Demo 2", cap: "phuong", pack: "phuong_do_thi", so_tdp: 6,
      lanh_dao: { username: "ct_demo", ho_ten: "Nguyễn Văn Demo", chuc_danh: "Chủ tịch UBND" } } });
  });
});

describe("Quản trị đơn vị", () => {
  it("xóa dữ liệu minh họa phải gõ đúng cụm xác nhận", async () => {
    roles = ["quan_tri_don_vi"];
    renderWithProviders(<AdminPage />, "/quan-tri?tab=cau-hinh");
    const btn = await screen.findByRole("button", { name: "Xóa dữ liệu minh họa" });
    expect(btn).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Gõ XÓA DỮ LIỆU MINH HỌA/), "XÓA DỮ LIỆU MINH HỌA");
    expect(btn).toBeEnabled();
  });
});
