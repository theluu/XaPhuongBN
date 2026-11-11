import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";
import { card } from "@/test/fixtures";

const pop = { ky: "2026-10", tong_dan_so: 51942, nam: 25888, nu: 26054, so_ho: 14632, nguong_an: 5, cho_phep_theo_tdp: true, is_sample: true,
  thap_tuoi: [{ nhom_tuoi: "0-4", nam: 1980, nu: 1860, nam_an: false, nu_an: false }, { nhom_tuoi: "85+", nam: null, nu: 9, nam_an: true, nu_an: false }],
  theo_tdp: [{ tdp_id: 1, ma_tdp: "TDP01", ten: "Tổ dân phố số 1", nhan_khau: 5090, an: false }, { tdp_id: 2, ma_tdp: "TDP02", ten: "Tổ dân phố số 2", nhan_khau: null, an: true }],
  bien_dong: [{ ky: "2026-10", dan_so: 51942, sinh: 55, tu: 21, chuyen_den: 106, chuyen_di: 75 }] };
vi.mock("@/lib/api", () => ({ api: (p: string) => Promise.resolve(p === "/api/population" ? pop : [card({ ma: "NQ01-10", ten: "Hộ nghèo", phan_he: "dan_cu" })]) }));

import { PopulationPage } from "./PopulationPage";

describe("Dân cư", () => {
  it("ô nhỏ hơn ngưỡng hiển thị <5, không phải 0", async () => {
    renderWithProviders(<PopulationPage />);
    const t = await screen.findByRole("table", { name: "Cơ cấu dân số theo nhóm tuổi" });
    const row = within(t).getAllByRole("row").find((r) => r.textContent?.includes("85+"))!;
    expect(row).toHaveTextContent("<5");
    const tdp = screen.getByRole("table", { name: "Dân số theo tổ dân phố" });
    expect(within(tdp).getAllByRole("row")[2]).toHaveTextContent("<5");
  });
  it("chỉ hiển thị số tổng hợp và nhắc nguyên tắc dữ liệu cá nhân", async () => {
    renderWithProviders(<PopulationPage />);
    expect((await screen.findAllByText("51.942")).length).toBeGreaterThan(0);
    expect(screen.getByText(/không hiển thị danh sách hay thông tin định danh cá nhân/)).toBeInTheDocument();
  });
});
