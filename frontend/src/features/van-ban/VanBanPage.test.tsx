import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const VB = { id: 1, so_ky_hieu: "187/TB-UBND", ngay_ban_hanh: "2026-11-08", loai: "thong_bao", loai_ten: "Thông báo kết luận", co_quan_ban_hanh: "UBND phường Việt Yên",
  nguoi_ky: "Lê Minh Châu", trich_yeu: "Kết luận giao ban về thu ngân sách", file_key: "k1", lien_ket: "https://vietyen.bacninh.gov.vn/vb/1", han_thuc_hien: "2026-11-17",
  trang_thai: "con_hieu_luc", is_sample: false, tien_do: { tong: 2, hoan_thanh: 1, qua_han: 1 },
  nhiem_vu: [{ id: 5, tieu_de: "Thu tiền sử dụng đất chậm", co_quan_xu_ly: "Phòng Kinh tế", han: "2026-11-10", trang_thai: "dang_xu_ly", qua_han: true, alert_id: 9 }] };
const params: unknown[] = [];
vi.mock("@/lib/api", () => ({
  api: (_p: string, o?: { params?: Record<string, unknown> }) => { params.push(o?.params); return Promise.resolve({ van_ban: [VB], loai: { thong_bao: "Thông báo kết luận" }, co_quyen_sua: true }); },
  getToken: () => "t",
}));

import { RelatedDocs, VanBanPage } from "./VanBanPage";

describe("Văn bản chỉ đạo", () => {
  it("danh sách, tiến độ nhiệm vụ theo văn bản, tìm kiếm", async () => {
    renderWithProviders(<VanBanPage />);
    const a = await screen.findByRole("article", { name: "187/TB-UBND" });
    expect(within(a).getByText("1/2")).toBeInTheDocument();
    expect(within(a).getByText(/1 quá hạn/)).toBeInTheDocument();
    expect(within(a).getByRole("link", { name: "Thu tiền sử dụng đất chậm" })).toHaveAttribute("href", "/canh-bao?id=9");
    expect(within(a).getByRole("link", { name: /Bản đăng tải/ })).toHaveAttribute("rel", "noopener noreferrer");
    expect(within(a).getByRole("button", { name: /Tệp văn bản/ })).toBeInTheDocument();
    await userEvent.type(screen.getByPlaceholderText(/Số ký hiệu/), "ngân sách");
    await userEvent.click(screen.getByRole("button", { name: "Tìm" }));
    expect(params.at(-1)).toMatchObject({ q: "ngân sách", con_hieu_luc: "true" });
  });

  it("văn bản liên quan trong hồ sơ nhiệm vụ", async () => {
    renderWithProviders(<RelatedDocs caseId={5} />);
    expect(await screen.findByText("187/TB-UBND")).toBeInTheDocument();
    expect(params.at(-1)).toEqual({ nhiem_vu: 5 });
  });
});
