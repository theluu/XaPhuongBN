import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";
import { card, tenant } from "@/test/fixtures";

const calls: { path: string; params?: Record<string, unknown> }[] = [];
const overview = {
  tenant: { ten: "Phường Việt Yên" }, ky: "2026-10", the_chi_so: [card({ ma: "NS-THU-DB", ten: "Thu ngân sách trên địa bàn" })],
  nq01: { tong: 23, dat: 17, nguy_co: 4, chua_du_du_lieu: 2 },
  can_chi_dao: [{ id: 1, tieu_de: "9 phản ánh kiến nghị quá hạn xử lý", mo_ta: "", muc_do: "cao", loai: "tien_do", trang_thai: "moi", link: "", ho_so: null }],
  xu_huong: [], ban_do: { features: [], lop: [] }, lich_cap_nhat: [], do_day_du: { du_kien: 1, co_so: 1, ty_le_pct: 100 }, bo_loc: { tdp: [], don_vi: [] },
};
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { params?: Record<string, unknown> }) => { calls.push({ path, params: o?.params });
    return Promise.resolve(path === "/api/overview" ? overview : [card({ ma: "NQ01-03b", ten: "Tổ phó TDP là đảng viên", status: "nguy_co" })]); },
  getToken: () => "t",
}));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ tenant, can: () => true, me: { ho_ten: "A" } }) }));

import { PresentationMode } from "./PresentationMode";

describe("Trình chiếu giao ban", () => {
  it("chỉ lấy số liệu tổng hợp (chế độ trình chiếu) và chuyển trang bằng phím", async () => {
    renderWithProviders(<PresentationMode />);
    expect(await screen.findByRole("heading", { level: 2, name: /Tổng quan/ })).toBeInTheDocument();
    expect(calls.find((c) => c.path === "/api/overview")?.params?.che_do).toBe("trinh_chieu");
    expect(document.documentElement.dataset.theme).toBe("dark");
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(await screen.findByRole("heading", { level: 2, name: "Chỉ tiêu có nguy cơ" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(await screen.findByRole("heading", { level: 2, name: "Việc cần chỉ đạo" })).toBeInTheDocument();
    expect(screen.getByText("9 phản ánh kiến nghị quá hạn xử lý")).toBeInTheDocument();
  });
});
