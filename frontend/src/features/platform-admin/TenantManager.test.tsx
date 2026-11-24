import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const calls: { path: string; method?: string; body: unknown }[] = [];
const T = [
  { id: 3, ma_dvhc: "P-VIETYEN", ten: "Phường Việt Yên", cap: "phuong", parent_id: 2, trang_thai: "hoat_dong", so_nguoi_dung: 7, so_chi_tieu: 27 },
  { id: 4, ma_dvhc: "P-NENH", ten: "Phường Nếnh", cap: "phuong", parent_id: 2, trang_thai: "hoat_dong", so_nguoi_dung: 7, so_chi_tieu: 27 },
  { id: 2, ma_dvhc: "T-BACNINH", ten: "Tỉnh Bắc Ninh", cap: "tinh", parent_id: 1, trang_thai: "hoat_dong", so_nguoi_dung: 0, so_chi_tieu: 0 },
];
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { method?: string; body?: unknown }) => {
    if (o?.method) {
      calls.push({ path, method: o.method, body: o.body });
      if (path.endsWith("/du-lieu-minh-hoa")) return Promise.resolve({ so_ban_ghi: 1200, tai_khoan: { chutich: "nenh.chutich" } });
      if (path.endsWith("/users")) return Promise.resolve({ id: 99, username: "nenh.moi", mat_khau_tam: "Tam-1@x" });
      return Promise.resolve({});
    }
    if (path === "/api/platform/tenants") return Promise.resolve(T);
    if (path === "/api/platform/tenants/4") return Promise.resolve({ ...T[1], ten_co_quan: ["ỦY BAN NHÂN DÂN PHƯỜNG NẾNH", "TRUNG TÂM"], ban_do: { tam: [21.238, 106.085], zoom: 14 },
      modules: { ngan_sach: "bat" }, tong_ban_ghi: 5000, ban_ghi_minh_hoa: 4800 });
    if (path === "/api/platform/tenants/4/users") return Promise.resolve([{ id: 11, username: "nenh.chutich", ho_ten: "Đào Thị Phương", chuc_danh: "Chủ tịch UBND", don_vi: "Phường Nếnh",
      email: null, trang_thai: "hoat_dong", roles: ["lanh_dao"], nhom: ["*"], co_2fa: false, bi_khoa: false, phai_doi_mat_khau: false, ly_do_thu_hoi: null }]);
    return Promise.resolve([]);
  },
  getToken: () => "t", ApiError: class extends Error {},
}));
const enterTenant = vi.hoisted(() => vi.fn((_id: number) => Promise.resolve()));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ me: { roles: ["quan_tri_nen_tang"], quyen: {}, phai_doi_mat_khau: false }, can: () => true, tenant: null, enterTenant }) }));

import { AdminPage } from "./AdminPage";

describe("Quản trị từng phường", () => {
  it("liệt kê 2 phường, mở quản trị Nếnh: sửa thông tin, thêm tài khoản, nạp dữ liệu minh họa", async () => {
    renderWithProviders(<AdminPage />);
    expect(await screen.findByText("Phường Việt Yên")).toBeInTheDocument();
    expect(screen.getByText("Phường Nếnh")).toBeInTheDocument();
    expect(screen.queryByText("T-BACNINH")).not.toBeInTheDocument(); // tỉnh không nằm trong danh sách xã/phường
    await userEvent.click(screen.getByRole("button", { name: "Quản trị Phường Nếnh" }));
    const panel = await screen.findByRole("region", { name: "Quản trị Phường Nếnh" });

    const name = await within(panel).findByLabelText("Tên đơn vị");
    await userEvent.clear(name);
    await userEvent.type(name, "Phường Nếnh mới");
    await userEvent.click(within(panel).getByRole("button", { name: "Lưu thông tin" }));
    expect(calls.at(-1)).toMatchObject({ path: "/api/platform/tenants/4", method: "PATCH", body: { ten: "Phường Nếnh mới", tam: [21.238, 106.085], parent_id: 2 } });

    await userEvent.click(within(panel).getByRole("tab", { name: "Tài khoản" }));
    expect(await within(panel).findByText("Đào Thị Phương")).toBeInTheDocument();
    const add = within(panel).getByRole("form", { name: "Thêm tài khoản" });
    await userEvent.type(within(add).getByLabelText("Tên đăng nhập"), "nenh.moi");
    await userEvent.type(within(add).getByLabelText("Họ tên"), "Cán bộ Mới");
    await userEvent.selectOptions(within(add).getByLabelText("Vai trò"), "nhap_lieu");
    await userEvent.click(within(add).getByLabelText("Ngân sách"));
    await userEvent.click(within(add).getByRole("button", { name: "Tạo tài khoản" }));
    expect(calls.at(-1)).toMatchObject({ path: "/api/platform/tenants/4/users", method: "POST", body: { username: "nenh.moi", role: "nhap_lieu", nhom: ["ngan_sach"] } });
    expect(await within(panel).findByText("Tam-1@x")).toBeInTheDocument();

    await userEvent.click(within(panel).getByRole("tab", { name: "Dữ liệu" }));
    expect(await within(panel).findByText("4.800")).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole("button", { name: "Nạp lại dữ liệu minh họa" }));
    expect(await within(panel).findByText(/Đã nạp 1.200 bản ghi/)).toBeInTheDocument();

    await userEvent.click(within(panel).getByRole("tab", { name: "Trạng thái" }));
    expect(within(panel).getByRole("button", { name: "Xóa đơn vị" })).toBeDisabled(); // phải tạm dừng trước

    await userEvent.click(within(panel).getByRole("button", { name: "Vào quản trị nội dung" }));
    expect(enterTenant).toHaveBeenCalledWith(4);
  });
});
