import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const calls: { path: string; method?: string; body: unknown }[] = [];
const F = (name: string, label: string, kind = "text", extra = {}) => ({ name, label, kind, required: false, options: null, cat: null, ref: null, readonly: false, create_only: false, list: true, help: "", ...extra });
const SCHEMA = { key: "ngan_sach", ten: "Thu – chi ngân sách", nhom_phan_he: "Ngân sách", mo_ta: "Kỳ đã đối soát: sửa sẽ chuyển về Chờ đối soát", link: "/ngan-sach",
  co_minh_hoa: true, them: true, sua: true, xoa: true, xac_nhan: { truong: "trang_thai_doi_soat", khoa: ["da_doi_soat"], ve: "cho_doi_soat" },
  truong: [F("ky", "Kỳ", "ky", { required: true }), F("nhom_ma", "Nhóm thu/chi", "text", { required: true }), F("thuc_hien", "Thực hiện", "dec"),
    F("trang_thai_doi_soat", "Đối soát", "enum", { options: { cho_doi_soat: "Chờ đối soát", da_doi_soat: "Đã đối soát" }, readonly: true })] };
const ROWS = [{ id: 11, ky: "2026-09", nhom_ma: "THUE_CTN", thuc_hien: "1500000000", trang_thai_doi_soat: "da_doi_soat", is_sample: true },
  { id: 12, ky: "2026-10", nhom_ma: "LE_PHI", thuc_hien: "80000000", trang_thai_doi_soat: "cho_doi_soat", is_sample: false }];
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { method?: string; body?: unknown }) => {
    if (o?.method) { calls.push({ path, method: o.method, body: o.body }); return Promise.resolve(path.endsWith("/xoa") ? { da_xoa: 1 } : { id: 11, can_xac_nhan_lai: true }); }
    if (path === "/api/du-lieu") return Promise.resolve({ bo_du_lieu: [{ ...SCHEMA, so_ban_ghi: 2, so_minh_hoa: 1 }, { ...SCHEMA, key: "du_an", ten: "Dự án đầu tư công", nhom_phan_he: "Đầu tư công", so_ban_ghi: 9, so_minh_hoa: 9 }] });
    if (path === "/api/du-lieu/ngan_sach") return Promise.resolve({ schema: SCHEMA, rows: ROWS, tong: 2, trang: 1, co_trang: 50, lua_chon: { cat: {}, ref: {} } });
    return Promise.resolve({ schema: { ...SCHEMA, key: "du_an", ten: "Dự án đầu tư công" }, rows: [], tong: 0, trang: 1, co_trang: 50, lua_chon: { cat: {}, ref: {} } });
  },
  getToken: () => "t", ApiError: class extends Error {},
}));

import { DataAdminPage } from "./DataAdminPage";

describe("Quản lý dữ liệu", () => {
  it("liệt kê bộ dữ liệu theo phân hệ; sửa dòng đã đối soát cần lý do; xóa nhiều dòng có lý do", async () => {
    renderWithProviders(<DataAdminPage />);
    const nav = await screen.findByRole("navigation", { name: "Bộ dữ liệu" });
    expect(within(nav).getByText("Dự án đầu tư công")).toBeInTheDocument();
    const table = await screen.findByRole("table", { name: "Thu – chi ngân sách" });
    expect(within(table).getByText("Minh họa")).toBeInTheDocument();
    await userEvent.click(within(table).getByRole("button", { name: "Sửa bản ghi 11" }));
    const form = screen.getByRole("form", { name: "Sửa bản ghi 11" });
    expect(within(form).getByLabelText("Đối soát")).toBeDisabled();
    const th = within(form).getByLabelText("Thực hiện");
    await userEvent.clear(th);
    await userEvent.type(th, "1400000000");
    expect(within(form).getByRole("button", { name: "Lưu" })).toBeDisabled(); // thiếu lý do
    await userEvent.type(within(form).getByLabelText(/Lý do sửa/), "Sai số chốt");
    await userEvent.click(within(form).getByRole("button", { name: "Lưu" }));
    expect(calls.at(-1)).toMatchObject({ path: "/api/du-lieu/ngan_sach/11", method: "PUT", body: { data: { ky: "2026-09", nhom_ma: "THUE_CTN", thuc_hien: "1400000000" }, ly_do: "Sai số chốt" } });
    expect(await screen.findByText(/cần xác nhận\/đối soát lại/)).toBeInTheDocument();

    await userEvent.click(within(table).getByLabelText("Chọn tất cả"));
    await userEvent.click(screen.getByRole("button", { name: /Xóa \(2\)/ }));
    const confirm = screen.getByRole("form", { name: "Xác nhận xóa" });
    await userEvent.type(within(confirm).getByLabelText("Lý do xóa"), "Nhập trùng");
    await userEvent.click(within(confirm).getByRole("button", { name: "Xóa" }));
    expect(calls.at(-1)).toEqual({ path: "/api/du-lieu/ngan_sach/xoa", method: "POST", body: { ids: [11, 12], ly_do: "Nhập trùng" } });
  });
});
