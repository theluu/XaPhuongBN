import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const T = (du_toan: number, ke_hoach_ky: number | null, thuc_hien: number | null) => ({ du_toan, ke_hoach_ky, thuc_hien, uoc_th: null, ty_le_pct: thuc_hien && du_toan ? (thuc_hien * 100) / du_toan : null });
const data = {
  nam: 2026, ky: "2026-10",
  thu: { dia_ban: T(441e9, 344e9, 295.4e9), ns_phuong: T(117e9, 91.3e9, 75.7e9) },
  chi: {
    tong_hop: T(109e9, null, 70e9), theo_nhom: [{ nhom_ma: "CHI_SN_MT", ten: "Chi sự nghiệp môi trường", ...T(6e9, null, 6.4e9), vuot_du_toan: true }],
    theo_nhiem_vu: [
      { nhiem_vu: "NV_MOITRUONG", ten: "Vệ sinh môi trường", ...T(6e9, null, 6.4e9), vuot_du_toan: true },
      { nhiem_vu: "NV_BMAY", ten: "Hoạt động bộ máy", ...T(22e9, null, 17.8e9), vuot_du_toan: false },
    ],
  },
  nhom_thu: [{ nhom_ma: "TIEN_SDD", ten: "Tiền sử dụng đất", scope: "dia_ban", ...T(250e9, 195e9, 140e9), nguy_co: true, trang_thai_doi_soat: "cho_doi_soat", nguon_loai: "bao_cao_chot" }],
  xu_huong_thang: [{ ky: "2026-09", thu_dia_ban: 260e9, thu_ns_phuong: 66e9, chi: 60e9, ke_hoach_thu_dia_ban: 309e9 }],
  cho_doi_soat: true, lech_api_chot: [], ngay_chot_gan_nhat: "2026-11-04T00:00:00Z", co_du_lieu: true, is_sample: true,
};
vi.mock("@/lib/api", () => ({ api: () => Promise.resolve(data) }));

import { BudgetPage } from "./BudgetPage";

describe("Thu – chi ngân sách", () => {
  it("thu trên địa bàn và ngân sách phường hưởng là hai khối riêng, không có tổng gộp", async () => {
    renderWithProviders(<BudgetPage />);
    expect(await screen.findByRole("region", { name: "Thu ngân sách trên địa bàn" })).toHaveTextContent("295,4 tỷ");
    expect(screen.getByRole("region", { name: "Thu ngân sách phường được hưởng" })).toHaveTextContent("75,7 tỷ");
    expect(screen.queryByText(/Tổng thu/)).not.toBeInTheDocument();
  });
  it("đánh dấu chờ đối soát, khoản thu nguy cơ và chi vượt dự toán", async () => {
    renderWithProviders(<BudgetPage />);
    expect(await screen.findByText(/Số liệu kỳ này đang chờ đối soát/)).toBeInTheDocument();
    const thu = screen.getByRole("table", { name: "Thu theo nhóm khoản thu" });
    expect(within(thu).getByText("Tiền sử dụng đất")).toBeInTheDocument();
    expect(within(thu).getByText("Chậm tiến độ")).toBeInTheDocument();
    const chi = screen.getByRole("table", { name: "Chi theo nhiệm vụ" });
    expect(within(chi).getByText("Vượt dự toán")).toBeInTheDocument();
  });
});
