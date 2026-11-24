import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const puts: unknown[] = [];
const viec = (ma: string, xong = false) => ({ ma, ten: `Việc ${ma}`, xong, goi_y: ma === "nguon_nguoi" ? "16 đầu mối, 14 đầu mối có người liên hệ" : null });
const D = {
  bat_dau: "2026-10-22", ngay_thu: 21, nguong_dung_han: 80, dat: 1, con_du_lieu_minh_hoa: true, co_quyen_sua: true,
  lo_trinh: [
    { ma: "GD1", tu_ngay: 1, den_ngay: 15, ten: "Thống nhất phạm vi", tu: "2026-10-22", den: "2026-11-05", hien_tai: false, qua_han: true, viec: [viec("pham_vi", true), viec("nguon_nguoi")] },
    { ma: "GD2", tu_ngay: 16, den_ngay: 45, ten: "Dữ liệu mẫu và dashboard lõi", tu: null, den: null, hien_tai: true, qua_han: false, viec: [viec("chuan_hoa")] },
  ],
  tieu_chi: [
    { ma: "TC1", ten: "Có màn hình tổng quan và dashboard lõi", ket_qua: "chua_dat", chi_tiet: ["Ngân sách: 0 bản ghi thật"], can_lam: ["Nhập số liệu thật nhóm Ngân sách"], link: "/nguon-du-lieu" },
    { ma: "TC2", ten: "100% chỉ tiêu có lý lịch", ket_qua: "dat", chi_tiet: ["12 số liệu thật"], can_lam: [], link: "/chi-tieu" },
  ],
  ho_so: [{ ma: "i", ten: "Kế hoạch thực hiện Nghị quyết 01-NQ/ĐU", trang_thai: "chua_co", ghi_chu: "", goi_y: null }],
  su_dung: { so_ngay: 30, so_dang_nhap: 42, so_nguoi_dung_hoat_dong: 9, so_thao_tac_du_lieu: 130, theo_vai_tro: [{ role: "lanh_dao", so_nguoi: 2 }] },
};
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { method?: string; body?: unknown }) => {
    if (o?.method) { puts.push(o.body); return Promise.resolve({ ok: true }); }
    return Promise.resolve(path === "/api/thi-diem" ? D : []);
  },
  ApiError: class extends Error {},
}));

import { PilotPage } from "./PilotPage";

describe("Thí điểm và nghiệm thu", () => {
  it("hiện tiêu chí, lộ trình có giai đoạn hiện tại, cập nhật việc và hồ sơ", async () => {
    renderWithProviders(<PilotPage />);
    expect(await screen.findByText(/đạt 1\/2/)).toBeInTheDocument();
    expect(screen.getByText("Chưa đạt")).toBeInTheDocument();
    expect(screen.getByText(/Nhập số liệu thật nhóm Ngân sách/)).toBeInTheDocument();
    const gd2 = screen.getByRole("article", { name: "Dữ liệu mẫu và dashboard lõi" });
    expect(within(gd2).getByText("Đang thực hiện")).toBeInTheDocument();
    expect(within(screen.getByRole("article", { name: "Thống nhất phạm vi" })).getByText("Quá hạn")).toBeInTheDocument();
    expect(screen.getByText(/16 đầu mối, 14 đầu mối có người liên hệ/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /Việc nguon_nguoi/ }));
    expect(puts.at(-1)).toEqual({ viec: { nguon_nguoi: true } });
    await userEvent.selectOptions(screen.getByLabelText("Trạng thái hồ sơ i"), "da_co");
    expect(puts.at(-1)).toEqual({ ho_so: { i: { trang_thai: "da_co", ghi_chu: "" } } });
    expect(screen.getByText("42")).toBeInTheDocument();
  });
});
