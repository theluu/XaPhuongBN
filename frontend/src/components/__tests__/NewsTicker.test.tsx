import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

vi.mock("@/lib/api", () => ({
  api: () => Promise.resolve({
    muc: [
      { loai: "thong_bao", id: 1, tieu_de: "Cảnh báo mưa lớn, trực ứng phó 24/24", lien_ket: "/phan-anh", muc_do: "khan" },
      { loai: "van_hanh", tieu_de: "3 nhiệm vụ chỉ đạo quá hạn", lien_ket: "/canh-bao", muc_do: "quan_trong" },
      { loai: "thong_bao", id: 2, tieu_de: "Bài trên Cổng TTĐT", lien_ket: "https://vietyen.bacninh.gov.vn/bai-1", muc_do: "thuong" },
    ],
    lien_ket: [{ ten: "Dịch vụ công quốc gia", url: "https://dichvucong.gov.vn" }], co_quyen_dang: true,
  }),
}));

import { DateLine, NewsTicker } from "../NewsTicker";

describe("Dải bản tin", () => {
  it("đọc được bằng trình đọc màn hình, có liên kết, tạm dừng, đăng thông báo, liên kết nhanh", async () => {
    renderWithProviders(<NewsTicker />);
    const region = await screen.findByRole("region", { name: "Bản tin điều hành" });
    const list = within(region).getByRole("list");
    expect(within(list).getByRole("link", { name: /KHẨN: Cảnh báo mưa lớn/ })).toHaveAttribute("href", "/phan-anh");
    expect(within(list).getByRole("link", { name: /Bài trên Cổng TTĐT/ })).toHaveAttribute("target", "_blank");
    await userEvent.click(screen.getByRole("button", { name: "Tạm dừng bản tin" }));
    expect(region).toHaveAttribute("data-dung", "1");
    expect(screen.getByRole("button", { name: "Chạy bản tin" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Đăng thông báo/ })).toHaveAttribute("href", "/quan-ly-du-lieu?bo=thong_bao");
    expect(within(screen.getByRole("navigation", { name: "Liên kết nhanh" })).getByRole("link", { name: /Dịch vụ công quốc gia/ })).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("dòng ngày giờ theo kiểu Cổng TTĐT", () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 10, 12, 8, 18));
    renderWithProviders(<DateLine />);
    expect(screen.getByText(/Thứ Năm, 12\/11\/2026 08:18/)).toBeInTheDocument();
    vi.useRealTimers();
  });
});
