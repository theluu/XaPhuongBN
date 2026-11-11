import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";
import { card } from "@/test/fixtures";

vi.mock("@/lib/api", () => ({
  api: (path: string) => Promise.resolve(path === "/api/programs" ? [
    { id: 1, ma: "NV-01", ten: "Nhiệm vụ trọng tâm số 1 – chờ phường cung cấp", mo_ta: "", don_vi_chu_tri: "", trang_thai: "dang_thuc_hien",
      tien_do: { tong: 0, dat: 0, nguy_co: 0, chua_du_du_lieu: 0, ty_le_dat_pct: null }, chi_tieu: [] },
    { id: 2, ma: "NV-02", ten: "Phát triển đô thị", mo_ta: "", don_vi_chu_tri: "UBND", trang_thai: "dang_thuc_hien",
      tien_do: { tong: 2, dat: 1, nguy_co: 1, chua_du_du_lieu: 0, ty_le_dat_pct: 50 }, chi_tieu: [card({ ma: "A" }), card({ ma: "B", status: "nguy_co" })] },
  ] : [
    { id: 1, ma: "KB-01", ten: "Điều hành các chỉ tiêu kinh tế - xã hội", la_bo_sung: false, trang_thai: "hoat_dong", so_chi_tieu: 10, rule_codes: ["CT_CHAM_KH"], layout: {}, mo_ta: "", indicator_ids: [] },
    { id: 2, ma: "KB-BS-01", ten: "Kịch bản bổ sung số 1 – chờ phường cung cấp", la_bo_sung: true, trang_thai: "cho_cau_hinh", so_chi_tieu: 0, rule_codes: [], layout: {}, mo_ta: "", indicator_ids: [] },
  ]),
}));

import { ProgramsPage } from "./ProgramsPage";
import { ScenariosPage } from "./ScenariosPage";

describe("Nhiệm vụ trọng tâm", () => {
  it("nhiệm vụ chưa có chỉ tiêu ghi rõ đang chờ cấu hình, không hiện 0%", async () => {
    renderWithProviders(<ProgramsPage />);
    expect(await screen.findByText("Nhiệm vụ trọng tâm số 1 – chờ phường cung cấp")).toBeInTheDocument();
    expect(screen.getByText("Chưa gắn chỉ tiêu theo dõi")).toBeInTheDocument();
    expect(screen.getByText("1/2 chỉ tiêu đạt")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });
});

describe("Kịch bản điều hành", () => {
  it("phân biệt kịch bản đang dùng và kịch bản chờ cấu hình", async () => {
    renderWithProviders(<ScenariosPage />);
    expect(await screen.findByText("Điều hành các chỉ tiêu kinh tế - xã hội")).toBeInTheDocument();
    expect(screen.getByText("Đang áp dụng")).toBeInTheDocument();
    expect(screen.getByText("Chờ cấu hình")).toBeInTheDocument();
    expect(screen.getByText("Kịch bản bổ sung")).toBeInTheDocument();
  });
});
