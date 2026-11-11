import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";
import { card } from "@/test/fixtures";

vi.mock("@/components/ProjectMap", () => ({ ProjectMap: () => <div data-testid="map" />, MapLegend: () => <div /> }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ can: () => true, tenant: null }) }));

const overview = {
  tenant: { ten: "Phường Việt Yên", ten_co_quan: ["ĐẢNG ỦY – UBND PHƯỜNG VIỆT YÊN", "Hệ thống điều hành số phường"] },
  ky: "2026-10", che_do: "lam_viec", co_du_lieu_minh_hoa: true, modules: {},
  the_chi_so: [
    { ...card({ ma: "NS-THU-DB", ten: "Thu ngân sách trên địa bàn", thuc_hien: 295.4, don_vi: "tỷ đồng", status: "nguy_co" }), link: "/ngan-sach", ghi_chu: "Dự toán năm 441 tỷ đồng" },
    { ...card({ ma: "DC-DAN-SO", ten: "Dân số", thuc_hien: 51942, don_vi: "người", status: "theo_doi", chieu: "theo_doi" }), link: "/dan-cu", ghi_chu: "" },
  ],
  nq01: { tong: 23, dat: 17, nguy_co: 4, chua_du_du_lieu: 2 },
  can_chi_dao: [{ id: 1, tieu_de: "9 phản ánh kiến nghị quá hạn xử lý", mo_ta: "Mã: PA-1", muc_do: "cao", loai: "tien_do", trang_thai: "moi", link: "/hanh-chinh", ho_so: null, can_cu: "II.6" }],
  xu_huong: [{ ky: "2026-09", thuc_hien: 260, ke_hoach: 300 }, { ky: "2026-10", thuc_hien: 295, ke_hoach: 344 }],
  ban_do: { type: "FeatureCollection", features: [], lop: ["du_an", "cong_trinh"] },
  lich_cap_nhat: [
    { nhom: "ngan_sach", ten: "Thu, chi ngân sách", don_vi: null, chu_ky: "Tuần/tháng", dieu_kien: "", cap_nhat_cuoi: "2026-11-04", data_state: "da_xac_nhan" },
    { nhom: "gd_yt_mt", ten: "Giáo dục, y tế, môi trường", don_vi: "Trung tâm Y tế", chu_ky: "Tháng/quý", dieu_kien: "", so_chi_tieu: 3, da_xac_nhan: 1, tam_thoi: 1, chua_co: 1, data_state: "chua_co_qua_han", cap_nhat_cuoi: null },
  ],
  do_day_du: { du_kien: 27, co_so: 25, ty_le_pct: 92.6 },
  bo_loc: { tdp: [{ id: 1, ten: "Tổ dân phố số 1" }], don_vi: ["Văn phòng"] },
};

vi.mock("@/lib/api", () => ({ api: () => Promise.resolve(overview) }));

import { OverviewPage } from "./OverviewPage";

describe("Tổng quan", () => {
  it("có đủ 4 khu theo Dự thảo IV.1", async () => {
    renderWithProviders(<OverviewPage />);
    expect(await screen.findByRole("region", { name: "Chỉ tiêu trọng tâm" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Việc cần chỉ đạo trong tuần" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Xu hướng và bản đồ" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Lịch cập nhật và xác nhận dữ liệu" })).toBeInTheDocument();
  });

  it("ô chỉ số dẫn sang phân hệ và có tóm tắt Nghị quyết", async () => {
    renderWithProviders(<OverviewPage />);
    const zone = await screen.findByRole("region", { name: "Chỉ tiêu trọng tâm" });
    expect(within(zone).getAllByRole("article")).toHaveLength(2);
    expect(within(zone).getByText("Dự toán năm 441 tỷ đồng")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /17.*đạt/ })).toHaveAttribute("href", "/chi-tieu");
  });

  it("lịch cập nhật hiển thị trạng thái chưa có số", async () => {
    renderWithProviders(<OverviewPage />);
    const zone = await screen.findByRole("region", { name: "Lịch cập nhật và xác nhận dữ liệu" });
    expect(within(zone).getByText("Còn 1 chỉ tiêu chưa có số")).toBeInTheDocument();
    expect(within(zone).getByText("Trung tâm Y tế")).toBeInTheDocument();
  });

  it("việc cần chỉ đạo có mức độ và dẫn tới phân hệ", async () => {
    renderWithProviders(<OverviewPage />);
    const zone = await screen.findByRole("region", { name: "Việc cần chỉ đạo trong tuần" });
    expect(within(zone).getByRole("link", { name: /9 phản ánh kiến nghị quá hạn/ })).toHaveAttribute("href", "/canh-bao?id=1");
    expect(within(zone).getByText("Mức cao")).toBeInTheDocument();
  });
});
