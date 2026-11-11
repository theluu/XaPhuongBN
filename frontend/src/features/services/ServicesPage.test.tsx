import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const agg = (o = {}) => ({ tiep_nhan: 100, giai_quyet: 90, dung_han: 88, qua_han: 2, truc_tuyen: 60, dung_han_pct: 97.8, truc_tuyen_pct: 60, co_so_tam_thoi: false, ...o });
const tthc = { tong: agg({ co_so_tam_thoi: true }), theo_ky: [{ ky: "2026-11", ...agg({ co_so_tam_thoi: true }) }], theo_bo_phan: [{ bo_phan: "Một cửa", ...agg() }],
  co_so_tam_thoi: true, nguon: ["bieu_mau"], is_sample: true };
const pakn = { tong: 80, theo_trang_thai: { tiep_nhan: 0, dang_xu_ly: 19, qua_han: 9, hoan_thanh: 61 }, ty_le_da_tra_loi_pct: 76.3, ty_le_dung_han_pct: 90, hai_long_tb: 4.5, theo_linh_vuc: [], is_sample: true };
const urge = [{ ma: "PAKN-1", loai_viec: "moi_truong", linh_vuc: "moi_truong", ngay_nhan: "2026-10-01", han_xu_ly: "2026-10-08", con_lai_ngay_lam_viec: -24, muc: "qua_han", trang_thai: "dang_xu_ly" }];
const post = vi.fn(() => Promise.resolve({}));
vi.mock("@/lib/api", () => ({
  api: (p: string, o?: { method?: string }) => o?.method === "POST" ? post() : Promise.resolve(p.includes("tthc") ? tthc : p.includes("can-don-doc") ? urge : pakn),
  ApiError: class extends Error {},
}));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ can: () => true }) }));

import { ServicesPage } from "./ServicesPage";

describe("Hành chính công – PAKN", () => {
  it("số tạm thời được gắn nhãn và nêu lý do nhập biểu mẫu", async () => {
    renderWithProviders(<ServicesPage />);
    expect(await screen.findByText(/có số liệu tạm thời chờ xác nhận/i)).toBeInTheDocument();
    expect(screen.getByText(/gián đoạn từ 01\/6\/2026/)).toBeInTheDocument();
    expect(screen.getByText("PAKN-1")).toBeInTheDocument();
    expect(screen.getByText("Quá hạn 24 ngày làm việc")).toBeInTheDocument();
  });
  it("biểu mẫu TTHC chặn số giải quyết lớn hơn tiếp nhận", async () => {
    renderWithProviders(<ServicesPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Nhập số liệu TTHC" }));
    await userEvent.type(screen.getByLabelText("Bộ phận"), "Một cửa");
    await userEvent.clear(screen.getByLabelText("Tiếp nhận"));
    await userEvent.type(screen.getByLabelText("Tiếp nhận"), "5");
    await userEvent.clear(screen.getByLabelText("Giải quyết"));
    await userEvent.type(screen.getByLabelText("Giải quyết"), "6");
    expect(screen.getByText("Số đã giải quyết không được lớn hơn số tiếp nhận")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lưu số liệu" })).toBeDisabled();
    expect(post).not.toHaveBeenCalled();
  });
});
