import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const inbox = [{ id: 5, indicator_id: 1, ma: "NQ01-15", ten: "Thu gom rác", nhom: "gd_yt_mt", don_vi: "%", ky_bao_cao: "2026-10", gia_tri: 97.5, du_bao: null,
  nguon: "Đơn vị môi trường", nguon_loai: "phuong", don_vi_cung_cap: "Phòng KT", thoi_diem_chot: "2026-11-05", trang_thai: "tam_thoi", version: 1, ly_do: "", minh_chung_keys: [], nguoi_nhap_id: 3, is_sample: true }];
const spec = { loai: "tthc", ten: "Hồ sơ TTHC", huong_dan: [], cot: [
  { ten: "Ngày", kieu: "ngay", bat_buoc: true, lua_chon: [], goi_y: "" }, { ten: "Bộ phận", kieu: "chu", bat_buoc: true, lua_chon: [], goi_y: "" },
  { ten: "Tiếp nhận", kieu: "so", bat_buoc: true, lua_chon: [], goi_y: "" }] };
const preview = { preview_id: 7, hop_le: 4, loi: [{ dong: 7, cot: "Mã chỉ tiêu", thong_bao: "Mã chỉ tiêu NQ01-99 không có trong danh mục" }], mau: [] };
vi.mock("@/lib/api", () => ({
  api: (path: string) => Promise.resolve(path === "/api/values/inbox" ? inbox : path.endsWith("/spec") ? spec : path.endsWith("/preview") ? preview
    : path === "/api/compliance" ? { tong: 0, dung_han: 0, cham: 0, thieu: 0, chua_den_han: 0, dung_han_pct: null, cham_pct: null, thieu_pct: null, theo_don_vi: [], chi_tiet: [] }
    : path === "/api/reminders" ? [] : []),
  getToken: () => "t", ApiError: class extends Error {},
}));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ can: () => true, me: { quyen: { "*": ["doc", "nhap", "duyet"] } } }) }));

import { DataEntryPage } from "./DataEntryPage";

describe("Nhập liệu và xác nhận", () => {
  it("từ chối số liệu phải ghi lý do", async () => {
    renderWithProviders(<DataEntryPage />);
    const row = (await screen.findByText("Thu gom rác")).closest("article")!;
    await userEvent.click(within(row).getByRole("button", { name: "Từ chối" }));
    const send = within(row).getByRole("button", { name: "Gửi từ chối" });
    expect(send).toBeDisabled();
    await userEvent.type(within(row).getByLabelText("Lý do từ chối"), "Sai kỳ chốt");
    expect(send).toBeEnabled();
  });

  it("tệp có lỗi thì không cho nhập vào hệ thống", async () => {
    renderWithProviders(<DataEntryPage />, "/nhap-lieu?tab=excel");
    await userEvent.upload(await screen.findByLabelText("Chọn tệp Excel hoặc CSV"), new File(["x"], "so_lieu.xlsx"));
    expect(await screen.findByText("Mã chỉ tiêu NQ01-99 không có trong danh mục")).toBeInTheDocument();
    expect(screen.getByText(/Dòng 7/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nhập vào hệ thống" })).toBeDisabled();
  });

  it("biểu mẫu trực tuyến sinh từ đặc tả cột", async () => {
    renderWithProviders(<DataEntryPage />, "/nhap-lieu?tab=bieu-mau&loai=tthc");
    expect(await screen.findByLabelText("Ngày *")).toHaveAttribute("type", "date");
    expect(screen.getByLabelText("Tiếp nhận *")).toHaveAttribute("inputmode", "decimal");
  });
});
