import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const row = (o: Record<string, unknown>) => ({ id: 1, ma_du_an: "DA-01", ten: "Dự án A", lop: 1, lop_ten: "", chu_dau_tu: "UBND phường", nguon_von: "NS_PHUONG",
  tong_muc_dt: 28e9, ke_hoach_von_nam: 12e9, lich_von_ky: 8.6e9, giai_ngan_luy_ke: 8.7e9, ty_le_giai_ngan_pct: 72.5, khoi_luong_pct: 70, cham_giai_ngan: false, ...o });
const summary = { ky: "2026-10", ty_le_giai_ngan_ns_phuong: 56.4, is_sample: true, theo_lop: {
  1: { ten: "Phường làm chủ đầu tư", so_du_an: 2, ke_hoach_von: 16e9, giai_ngan: 9e9, so_cham: 1, thieu_so_lieu: 0, tinh_vao_ty_le: true },
  2: { ten: "Cơ quan cấp thành phố làm chủ đầu tư, thi công trên địa bàn", so_du_an: 0, ke_hoach_von: null, giai_ngan: null, so_cham: 0, thieu_so_lieu: 0, tinh_vao_ty_le: false },
  3: { ten: "Dự án khác, chỉ theo dõi thông tin", so_du_an: 1, ke_hoach_von: null, giai_ngan: null, so_cham: 0, thieu_so_lieu: 1, tinh_vao_ty_le: false } } };
const list = [row({}), row({ id: 2, ma_du_an: "DA-02", ten: "Nhà văn hóa TDP 8", cham_giai_ngan: true, ty_le_giai_ngan_pct: 30 }),
  row({ id: 3, ma_du_an: "DA-08", ten: "Nhà ở xã hội", lop: 3, ke_hoach_von_nam: null, giai_ngan_luy_ke: null, ty_le_giai_ngan_pct: null })];
vi.mock("@/lib/api", () => ({ api: (p: string) => Promise.resolve(p.endsWith("summary") ? summary : list) }));

import { InvestmentPage } from "./InvestmentPage";

describe("Đầu tư công", () => {
  it("tỷ lệ giải ngân chỉ tính lớp 1, dự án chậm nằm trên đầu", async () => {
    renderWithProviders(<InvestmentPage />);
    expect(await screen.findByText("56,4%")).toBeInTheDocument();
    const rows = within(screen.getByRole("table", { name: "Danh sách dự án" })).getAllByRole("row");
    expect(rows[1]).toHaveTextContent("Nhà văn hóa TDP 8");
    expect(rows[1]).toHaveTextContent("Chậm so lịch vốn");
  });
  it("lớp 3 ghi chú không tính vào tỷ lệ giải ngân, thiếu số hiện gạch ngang", async () => {
    renderWithProviders(<InvestmentPage />);
    await userEvent.click(await screen.findByRole("tab", { name: /Lớp 3/ }));
    expect(screen.getByText("Chỉ theo dõi thông tin, không tính vào tỷ lệ giải ngân ngân sách phường.")).toBeInTheDocument();
    const r = within(screen.getByRole("table", { name: "Danh sách dự án" })).getAllByRole("row")[1];
    expect(r).toHaveTextContent("Chưa có số");
    expect(r.textContent).not.toMatch(/\b0%/);
  });
});
