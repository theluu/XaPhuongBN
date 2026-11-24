import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Route, Routes } from "react-router-dom";
import { renderWithProviders } from "@/test/render";
import { PublicHome } from "./PublicHome";

const W = { id: 3, ten: "Phường Việt Yên", cap: "phuong", slug: "viet-yen", ten_mien: ["vietyen.example.vn"], ten_co_quan: ["ỦY BAN NHÂN DÂN PHƯỜNG VIỆT YÊN", "TRUNG TÂM"], logo_url: null };
const card = (ma: string, ten: string, thuc_hien: number | null, xn: boolean) => ({
  ma, ten, phan_he: "ktxh", ten_phan_he: "Kinh tế – xã hội", don_vi: "%", ky: "2026-10", ke_hoach: 10, muc_tieu: null, muc_so_sanh: 10, thuc_hien,
  hoan_thanh_pct: xn ? 80 : null, status: xn ? "nguy_co" : "dang_cap_nhat", nguon: "UBND", don_vi_cung_cap: "", thoi_diem_chot: null, da_xac_nhan: xn,
});
let host: unknown = { don_vi: null };
vi.mock("@/lib/api", () => ({
  api: (path: string) => {
    if (path === "/api/cong-khai/xac-dinh") return Promise.resolve(host);
    if (path === "/api/cong-khai") return Promise.resolve({ don_vi: [{ ...W, ban_moi_nhat: { id: 1, ky: "2026-10", cong_bo_luc: "2026-11-01T00:00:00Z", nguoi_cong_bo: "A", thong_ke: null, co_minh_hoa: true }, noi_bat: [] }] });
    if (path === "/api/cong-khai/viet-yen") return Promise.resolve({ don_vi: W, ky_da_cong_bo: ["2026-10"], ban: {
      id: 1, ky: "2026-10", cong_bo_luc: "2026-11-01T00:00:00Z", nguoi_cong_bo: "Chủ tịch", co_minh_hoa: true, thong_ke: null,
      du_lieu: { ky: "2026-10", gioi_thieu: "Giới thiệu", tong_hop: [], xu_huong_ngan_sach: [], co_minh_hoa: true,
        thong_ke: { so_chi_tieu: 2, da_xac_nhan: 1, dat: 0, nguy_co: 1 },
        chi_tieu: [card("A", "Tăng thu nội địa", 8, true), card("B", "Thu nhập bình quân", null, false)] } } });
    return Promise.reject(new Error(path));
  },
  ApiError: class extends Error {},
}));

describe("Trang công khai", () => {
  it("tên miền chung: liệt kê các phường", async () => {
    host = { don_vi: null };
    renderWithProviders(<PublicHome />);
    expect(await screen.findByRole("heading", { name: "Phường Việt Yên" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Đăng nhập/ }).length).toBeGreaterThan(0);
  });

  it("tên miền phường: chỉ số đã xác nhận hiện số, chưa xác nhận hiện Đang cập nhật, có nhãn bản demo", async () => {
    host = { don_vi: W };
    renderWithProviders(<Routes><Route path="/" element={<PublicHome />} /></Routes>);
    expect(await screen.findByText("Tăng thu nội địa")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getAllByText("Đang cập nhật").length).toBeGreaterThan(0);
    expect(screen.getByText(/Bản demo/)).toBeInTheDocument();
  });

  it("tiếng Anh: đổi ngôn ngữ hiện giao diện tiếng Anh và tên chỉ tiêu dịch", async () => {
    host = { don_vi: W };
    window.localStorage.setItem("ioc-ngon-ngu", "en");
    renderWithProviders(<Routes><Route path="/" element={<PublicHome />} /></Routes>);
    expect(await screen.findAllByText("Open Data Portal")).not.toHaveLength(0);
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
    window.localStorage.removeItem("ioc-ngon-ngu");
  });
});
