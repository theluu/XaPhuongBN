import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const calls: string[] = [];
const now = new Date().toISOString();
const ITEMS = [
  { id: 1, loai: "giao_viec", tieu_de: "Bạn được giao xử lý: Thu tiền sử dụng đất chậm", noi_dung: "Hạn 20/11/2026", lien_ket: "/canh-bao?id=3", muc_do: "quan_trong", tao_luc: now, da_doc: false },
  { id: 2, loai: "cong_van", tieu_de: "Lê Minh Châu gửi công văn số 215/UBND-KT", noi_dung: "Đôn đốc thu", lien_ket: "/tin-nhan?id=7", muc_do: "khan", tao_luc: now, da_doc: false },
  { id: 3, loai: "ket_qua", tieu_de: "Nhiệm vụ đã hoàn thành", noi_dung: "", lien_ket: "/canh-bao", muc_do: "thuong", tao_luc: "2026-11-01T08:00:00Z", da_doc: true },
];
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { method?: string }) => {
    if (o?.method) { calls.push(path); return Promise.resolve({ ok: true }); }
    if (path === "/api/noti/dem") return Promise.resolve({ chua_doc: 2, moi_nhat: ITEMS[0] });
    return Promise.resolve({ chua_doc: 2, muc: ITEMS });
  },
}));
const nav = vi.fn();
vi.mock("react-router-dom", async (orig) => ({ ...(await orig<typeof import("react-router-dom")>()), useNavigate: () => nav }));

import { NotificationBell } from "../NotificationBell";

describe("Chuông thông báo", () => {
  it("số chưa đọc, bảng thông báo theo nhóm, mở thông báo → đánh dấu đọc và chuyển trang", async () => {
    renderWithProviders(<NotificationBell />);
    const bell = await screen.findByRole("button", { name: "Thông báo, 2 chưa đọc" });
    await userEvent.click(bell);
    const panel = screen.getByRole("dialog", { name: "Thông báo" });
    expect(await within(panel).findByText("2 mới")).toBeInTheDocument();
    expect(within(panel).getByRole("region", { name: "Hôm nay" })).toBeInTheDocument();
    expect(within(panel).getByRole("region", { name: "Trước đó" })).toBeInTheDocument();
    expect(within(panel).getByText("KHẨN")).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole("button", { name: /Chưa đọc\. Giao việc: Bạn được giao xử lý/ }));
    expect(calls).toContain("/api/noti/1/doc");
    expect(nav).toHaveBeenCalledWith("/canh-bao?id=3");
    expect(screen.queryByRole("dialog", { name: "Thông báo" })).not.toBeInTheDocument();
    await userEvent.click(bell);
    await userEvent.click(within(screen.getByRole("dialog", { name: "Thông báo" })).getByRole("button", { name: /Đánh dấu đã đọc tất cả/ }));
    expect(calls).toContain("/api/noti/doc-het");
  });
});
