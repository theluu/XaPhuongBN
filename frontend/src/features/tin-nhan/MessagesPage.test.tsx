import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const calls: { path: string; method?: string; body?: unknown }[] = [];
const P = (id: number, ho_ten: string, chuc_danh: string) => ({ id, ho_ten, chuc_danh, don_vi: "Phường Việt Yên", username: `u${id}` });
const THREAD = { id: 7, tieu_de: "Thu tiền sử dụng đất chậm", loai: "viec", lien_ket_loai: "canh_bao", lien_ket_ten: "Thu tiền sử dụng đất chậm", lien_ket_url: "/canh-bao?id=3",
  thanh_vien: [P(1, "Lê Minh Châu", "Chủ tịch UBND"), P(2, "Phạm Thu Dung", "Kế toán")], phat_hanh_cong_van: true, tin: [
    { id: 1, nguoi_gui: P(2, "Phạm Thu Dung", "Kế toán"), cua_toi: false, noi_dung: "Phiên đấu giá lùi sang tháng 12", gui_luc: "2026-11-13T08:00:00Z", he_thong: false,
      tep: [{ key: "k1", ten: "bao-cao.pdf", content_type: "application/pdf", kich_thuoc: 20480 }], cong_van: null },
    { id: 2, nguoi_gui: P(1, "Lê Minh Châu", "Chủ tịch UBND"), cua_toi: true, noi_dung: "", gui_luc: "2026-11-13T09:00:00Z", he_thong: false, tep: [],
      cong_van: { id: 9, so_ky_hieu: "215/UBND-KT", trich_yeu: "Đôn đốc thu tiền sử dụng đất", loai: "cong_van", ngay_ban_hanh: "2026-11-13", han_thuc_hien: "2026-12-01", co_quan_ban_hanh: "UBND phường Việt Yên", nguoi_ky: "Lê Minh Châu" } }] };
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { method?: string; body?: unknown; form?: FormData }) => {
    if (o?.method) { calls.push({ path, method: o.method, body: o.body });
      if (path === "/api/tin-nhan/tep") return Promise.resolve({ key: "k9", ten: "cong-van.pdf", content_type: "application/pdf", kich_thuoc: 1000 });
      return Promise.resolve({ id: 7 }); }
    if (path === "/api/tin-nhan/hoi-thoai") return Promise.resolve([{ id: 7, tieu_de: "Thu tiền sử dụng đất chậm", loai: "viec", lien_ket_loai: "canh_bao", lien_ket_ten: "x", lien_ket_url: "/canh-bao?id=3",
      so_thanh_vien: 2, chua_doc: 1, cuoi: { nguoi: "Phạm Thu Dung", noi_dung: "Phiên đấu giá lùi", luc: "2026-11-13T08:00:00Z", he_thong: false }, cap_nhat_luc: "2026-11-13T08:00:00Z", is_sample: false }]);
    if (path === "/api/tin-nhan/nguoi-nhan") return Promise.resolve({ nguoi: [P(2, "Phạm Thu Dung", "Kế toán"), P(3, "Hoàng Văn Đức", "Phó Chủ tịch UBND")], phat_hanh_cong_van: true });
    if (path === "/api/tin-nhan/hoi-thoai/7") return Promise.resolve(THREAD);
    return Promise.resolve({ tong: 0 });
  },
  getToken: () => "t", ApiError: class extends Error {},
}));

import { MessagesPage } from "./MessagesPage";

describe("Tin nhắn nội bộ", () => {
  it("mở trao đổi gắn cảnh báo, thấy công văn và tệp; gửi tin kèm công văn", async () => {
    renderWithProviders(<MessagesPage />);
    const list = await screen.findByRole("list", { name: "Cuộc trao đổi" });
    expect(within(list).getByText("1")).toBeInTheDocument(); // chưa đọc
    await userEvent.click(within(list).getByRole("button", { name: /Thu tiền sử dụng đất chậm/ }));
    const th = await screen.findByRole("region", { name: /Trao đổi: Thu tiền sử dụng đất chậm/ });
    expect(within(th).getByRole("link", { name: /Cảnh báo: Thu tiền sử dụng đất chậm/ })).toHaveAttribute("href", "/canh-bao?id=3");
    expect(within(th).getByText(/Số 215\/UBND-KT/)).toBeInTheDocument();
    expect(within(th).getByRole("button", { name: /bao-cao.pdf/ })).toBeInTheDocument();
    const form = within(th).getByRole("form", { name: "Soạn tin" });
    await userEvent.click(within(form).getByRole("button", { name: "Gửi kèm công văn xử lý" }));
    await userEvent.type(within(form).getByLabelText("Số, ký hiệu"), "216/UBND-KT");
    expect(within(form).getByRole("button", { name: "Gửi" })).toBeDisabled(); // chưa có tệp công văn
    await userEvent.upload(within(form).getByLabelText("Chọn tệp"), new File(["%PDF-1.4"], "cong-van.pdf", { type: "application/pdf" }));
    await within(form).findByText("cong-van.pdf");
    await userEvent.type(within(form).getByLabelText("Nội dung tin nhắn"), "Đề nghị thực hiện ngay");
    await userEvent.click(within(form).getByRole("button", { name: "Gửi" }));
    expect(calls.at(-1)).toMatchObject({ path: "/api/tin-nhan/hoi-thoai/7/tin", method: "POST",
      body: { noi_dung: "Đề nghị thực hiện ngay", tep_keys: ["k9"], cong_van: { so_ky_hieu: "216/UBND-KT", trich_yeu: "V/v xử lý: Thu tiền sử dụng đất chậm", loai: "cong_van" } } });
  });
});
