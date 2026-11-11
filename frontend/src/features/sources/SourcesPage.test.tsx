import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

vi.mock("@/lib/api", () => ({ api: () => Promise.resolve([
  { id: 1, ma: "KHO_DL_DAN_CU", ten: "Kho dữ liệu dùng chung — API dân cư", loai: "api", co_quan_cung_cap: "Công an thành phố", nhom_du_lieu: "dan_cu",
    trang_thai: "hoat_dong_mot_phan", phap_ly_chia_se: "cho_phep_mot_phan", dung_chung: true, lan_dong_bo_cuoi: null, tong_api: 12, so_api_ket_noi: 12, so_api_tra_du_lieu: 9,
    endpoints: [{ ma: "dan_toc", ten: "Nhân khẩu theo dân tộc", ket_noi: true, tra_du_lieu: false }], ghi_chu: "" },
]) }));

import { SourcesPage } from "./SourcesPage";

describe("Nguồn dữ liệu", () => {
  it("thể hiện số API đã kết nối và đang trả dữ liệu", async () => {
    renderWithProviders(<SourcesPage />);
    expect(await screen.findByText("12/12 API đã kết nối, 9 API đang trả dữ liệu")).toBeInTheDocument();
    expect(screen.getByText("Hoạt động một phần")).toBeInTheDocument();
    expect(screen.getByText(/Nhân khẩu theo dân tộc: chưa trả dữ liệu/)).toBeInTheDocument();
  });
});
