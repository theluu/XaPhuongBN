import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const item = (id: number, ngay: string, gio: string, nd: string, extra = {}) => ({ id, ngay, gio_bat_dau: gio, gio_ket_thuc: null, noi_dung: nd, chu_tri: "Lê Minh Châu",
  dia_diem: "Phòng họp tầng 2", thanh_phan: "Các Phó Chủ tịch", don_vi_chuan_bi: "Văn phòng", loai: "hop", loai_ten: "Họp", trang_thai: "chinh_thuc", trang_thai_ten: "Chính thức",
  ghi_chu: "", is_sample: false, ...extra });
const days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"].map((thu, i) => ({ ngay: `2026-11-${String(9 + i).padStart(2, "0")}`, thu, muc: [] as unknown[] }));
days[0].muc = [item(1, "2026-11-09", "07:30", "Giao ban đầu tuần")];
days[3].muc = [item(2, "2026-11-12", "08:00", "Hội nghị trực tuyến"), item(3, "2026-11-12", "15:00", "Đối thoại hộ dân", { trang_thai: "hoan", trang_thai_ten: "Hoãn" })];
const seen: unknown[] = [];
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { params?: Record<string, unknown> }) => {
    seen.push(o?.params);
    if (path === "/api/lich-cong-tac/hom-nay") return Promise.resolve([days[3].muc[0]]);
    return Promise.resolve({ tu: "2026-11-09", den: "2026-11-15", tuan_so: 46, hom_nay: "2026-11-12", co_quyen_sua: true, ngay: days });
  },
}));

import { LichHomNay, LichPage } from "./LichPage";

describe("Lịch công tác", () => {
  it("lịch tuần theo ngày, đánh dấu hôm nay, lịch hoãn, chuyển tuần", async () => {
    renderWithProviders(<LichPage />);
    const t = await screen.findByRole("table", { name: "Lịch công tác tuần" });
    expect(within(t).getByText("Giao ban đầu tuần")).toBeInTheDocument();
    expect(within(t).getByText(/Hôm nay/)).toBeInTheDocument();
    expect(within(t).getByText("Hoãn")).toBeInTheDocument();
    expect(within(t).getAllByText("Không có lịch").length).toBe(5);
    expect(screen.getByRole("link", { name: /Cập nhật lịch/ })).toHaveAttribute("href", "/quan-ly-du-lieu?bo=lich_cong_tac");
    await userEvent.click(screen.getByRole("button", { name: /Tuần sau/ }));
    expect(seen.at(-1)).toEqual({ tuan: "2026-11-16" });
  });

  it("thẻ lịch hôm nay trên trang chủ", async () => {
    renderWithProviders(<LichHomNay />);
    expect(await screen.findByText("Hội nghị trực tuyến")).toBeInTheDocument();
    expect(screen.getByText(/Chủ trì: Lê Minh Châu/)).toBeInTheDocument();
  });
});
