import { screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";
import { card, me, nq01Cards, tenant } from "@/test/fixtures";

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ me, tenant, can: (q: string, n?: string) => q === "doc" || (n === "canh_bao") }),
}));

const apiMock = vi.fn();
vi.mock("@/lib/api", () => ({ api: (...a: unknown[]) => apiMock(...a), ApiError: class extends Error {} }));

import { Nq01Page } from "./Nq01Page";

beforeEach(() => {
  apiMock.mockReset();
  apiMock.mockImplementation((path: string) => {
    if (path === "/api/indicators") return Promise.resolve(nq01Cards);
    if (path.startsWith("/api/indicators/NQ01-12/series")) return Promise.resolve([
      { ky: "2026-08", gia_tri: 98.9, data_state: "da_xac_nhan", ke_hoach: 98.5 },
      { ky: "2026-09", gia_tri: null, data_state: "chua_co_qua_han", ke_hoach: 98.5 },
      { ky: "2026-10", gia_tri: 98.6, data_state: "da_xac_nhan", ke_hoach: 98.5 },
    ]);
    if (path === "/api/indicators/NQ01-12") return Promise.resolve({
      ...card({ lech_nguon: { phuong: 99.1, chuyen_nganh: 98.6, chenh: 0.5, chenh_pct: 0.5 } }),
      metadata: { dinh_nghia: "Tỷ lệ dân số có thẻ BHYT", cong_thuc: "Số người có thẻ / Dân số × 100", pham_vi_dia_ban: "Toàn phường",
                  don_vi_chu_quan: "Phòng Văn hóa – Xã hội", ky_cap_nhat: "thang", nguon_mac_dinh: "BHXH", dinh_dang: "so",
                  phan_loai_thong_tin: "noi_bo", ghi_chu: "", can_minh_chung: false },
      lich_su: [{ id: 10, version: 1, nguon_loai: "chuyen_nganh", gia_tri: 98.6, trang_thai: "da_xac_nhan", nguoi_xac_nhan: "PCT", ly_do: "", thoi_diem_dong_bo: null }],
    });
    return Promise.resolve([]);
  });
});

describe("Trang chỉ tiêu Nghị quyết", () => {
  it("lọc 'Chưa đủ dữ liệu' chỉ còn các chỉ tiêu thiếu số", async () => {
    renderWithProviders(<Nq01Page />);
    await screen.findByText("Tổ chức cơ sở Đảng hoàn thành tốt nhiệm vụ");
    await userEvent.click(screen.getByRole("tab", { name: /Chưa đủ dữ liệu/ }));
    const grid = screen.getByTestId("indicator-grid");
    expect(within(grid).getAllByRole("article")).toHaveLength(2);
    expect(within(grid).getByText("Tăng tổng giá trị sản phẩm bình quân")).toBeInTheDocument();
    expect(within(grid).getByText("Thu nhập bình quân đầu người")).toBeInTheDocument();
  });

  it("đếm số chỉ tiêu theo trạng thái trên các tab", async () => {
    renderWithProviders(<Nq01Page />);
    await screen.findByText("Tổ chức cơ sở Đảng hoàn thành tốt nhiệm vụ");
    expect(screen.getByRole("tab", { name: /Có nguy cơ/ })).toHaveTextContent("2");
    expect(screen.getByRole("tab", { name: /Tất cả/ })).toHaveTextContent("6");
  });

  it("danh sách cần đôn đốc gồm chỉ tiêu nguy cơ, thiếu số, số tạm thời và lệch nguồn", async () => {
    renderWithProviders(<Nq01Page />);
    const list = await screen.findByRole("list", { name: "Chỉ tiêu cần đôn đốc" });
    const items = within(list).getAllByRole("listitem").map((li) => li.textContent);
    expect(items).toHaveLength(5);
    expect(items.join(" ")).toContain("Số giữa các nguồn chưa thống nhất");
    expect(items.join(" ")).toContain("Chưa có số liệu kỳ Năm 2025");
    expect(items.join(" ")).toContain("Số tạm thời chờ xác nhận");
  });

  it("mở chi tiết thấy nguồn, người xác nhận, hai nguồn lệch và lịch sử", async () => {
    renderWithProviders(<Nq01Page />);
    await screen.findByText("Tổ chức cơ sở Đảng hoàn thành tốt nhiệm vụ");
    const grid = screen.getByTestId("indicator-grid");
    await userEvent.click(within(grid).getByRole("button", { name: "Tỷ lệ dân số tham gia BHYT" }));
    const dlg = await screen.findByRole("dialog");
    await waitFor(() => expect(within(dlg).getByText("Phó Chủ tịch UBND Hoàng Văn Đức")).toBeInTheDocument());
    expect(within(dlg).getByText("BHXH thành phố")).toBeInTheDocument();
    expect(within(dlg).getByText("Số liệu giữa các nguồn chưa thống nhất")).toBeInTheDocument();
    expect(within(dlg).getByText("Số người có thẻ / Dân số × 100")).toBeInTheDocument();
    expect(within(dlg).getByRole("table", { name: "Lịch sử số liệu" })).toBeInTheDocument();
  });
});
