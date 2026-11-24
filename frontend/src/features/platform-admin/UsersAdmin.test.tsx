import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const posts: { path: string; method?: string; body?: unknown }[] = [];
const users = [
  { id: 1, username: "canbo1", ho_ten: "Vũ Thị Giang", chuc_danh: "Chuyên viên", don_vi: "Trung tâm Phục vụ HCC", email: null, trang_thai: "hoat_dong", roles: ["nhap_lieu"], nhom: ["tthc_pakn"],
    co_2fa: false, bi_khoa: true, phai_doi_mat_khau: false, ly_do_thu_hoi: null },
  { id: 2, username: "pct2", ho_ten: "Đỗ Văn Minh", chuc_danh: "Phó Chủ tịch UBND", don_vi: "", email: null, trang_thai: "cho_duyet", roles: ["lanh_dao"], nhom: ["ktxh"],
    co_2fa: false, bi_khoa: false, phai_doi_mat_khau: true, ly_do_thu_hoi: null },
];
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { method?: string; body?: unknown }) => {
    if (o?.method) { posts.push({ path, method: o.method, body: o.body }); return Promise.resolve(path.endsWith("reset-password") ? { username: "canbo1", mat_khau_tam: "Tam-999@x" } : {}); }
    if (path === "/api/admin/users") return Promise.resolve(users);
    if (path === "/api/admin/roles") return Promise.resolve({ nhom: ["ngan_sach", "canh_bao"], vai_tro: [{ ma: "lanh_dao", ten: "Lãnh đạo", can_2fa: true, theo_nhom_giao: false, quyen: { ngan_sach: ["doc"], canh_bao: ["doc", "duyet", "nhap"] } }] });
    return Promise.resolve([]);
  },
  ApiError: class extends Error {},
}));

import { UsersAdmin } from "./UsersAdmin";
import { RoleMatrix } from "./RoleMatrix";

describe("Quản trị người dùng", () => {
  it("sửa vai trò và nhóm dữ liệu, cảnh báo sẽ đăng xuất", async () => {
    renderWithProviders(<UsersAdmin />);
    const row = (await screen.findByText("Vũ Thị Giang")).closest("tr")!;
    await userEvent.click(within(row).getByRole("button", { name: "Sửa quyền" }));
    const form = screen.getByRole("form", { name: "Sửa tài khoản canbo1" });
    await userEvent.selectOptions(within(form).getByLabelText("Vai trò"), "xac_nhan");
    await userEvent.click(within(form).getByLabelText("Ngân sách"));
    expect(within(form).getByText(/đăng xuất người dùng/)).toBeInTheDocument();
    await userEvent.click(within(form).getByRole("button", { name: "Lưu" }));
    expect(posts.at(-1)).toMatchObject({ path: "/api/admin/users/1", method: "PATCH", body: { role: "xac_nhan", nhom: ["tthc_pakn", "ngan_sach"] } });
  });

  it("tài khoản bị khóa có nút mở khóa; đặt lại mật khẩu hiện mật khẩu tạm một lần; chờ duyệt có nút phê duyệt", async () => {
    renderWithProviders(<UsersAdmin />);
    const row = (await screen.findByText("Vũ Thị Giang")).closest("tr")!;
    expect(within(row).getByText("Đang khóa")).toBeInTheDocument();
    await userEvent.click(within(row).getByRole("button", { name: "Mở khóa" }));
    expect(posts.at(-1)?.path).toBe("/api/admin/users/1/unlock");
    await userEvent.click(within(row).getByRole("button", { name: "Đặt lại mật khẩu" }));
    expect(await screen.findByText("Tam-999@x")).toBeInTheDocument();
    const pending = screen.getByText("Đỗ Văn Minh").closest("tr")!;
    await userEvent.click(within(pending).getByRole("button", { name: "Phê duyệt" }));
    expect(posts.at(-1)?.path).toBe("/api/users/2/approve");
  });

  it("ma trận phân quyền thể hiện xem/nhập/duyệt theo nhóm", async () => {
    renderWithProviders(<RoleMatrix />);
    const t = await screen.findByRole("table", { name: "Ma trận phân quyền" });
    const row = within(t).getByText("Lãnh đạo").closest("tr")!;
    expect(within(row).getAllByText("Duyệt")).toHaveLength(1);
    expect(within(row).getByText("Bắt buộc")).toBeInTheDocument();
  });
});
