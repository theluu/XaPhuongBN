import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const QUALITY = "Đây là cảnh báo chất lượng dữ liệu, chưa kết luận chỉ tiêu không đạt.";
const alerts = [
  { id: 1, rule_ma: "CT_CHAM_KH", quy_tac: "Chỉ tiêu chậm so với kế hoạch kỳ", can_cu: "II.1", loai: "tien_do", nhom: "ktxh", muc_do: "trung_binh",
    tieu_de: "Tổ phó TDP là đảng viên: có nguy cơ không đạt", mo_ta: "Thực hiện 82,5", link: "/chi-tieu", ky: "2026-10", trang_thai: "moi", ghi_chu_chat_luong: null, phat_sinh_luc: "2026-11-11", ho_so: null },
  { id: 2, rule_ma: "CT_QUA_HAN_CAP_NHAT", quy_tac: "Chỉ tiêu quá hạn cập nhật", can_cu: "II.1", loai: "qua_han", nhom: "ktxh", muc_do: "thap",
    tieu_de: "Thu nhập bình quân: chưa có số liệu", mo_ta: "", link: "/chi-tieu", ky: "2026-10", trang_thai: "moi", ghi_chu_chat_luong: QUALITY, phat_sinh_luc: "2026-11-11", ho_so: null },
  { id: 3, rule_ma: "DA_QUA_HAN_MOC", quy_tac: "Dự án quá hạn mốc", can_cu: "II.4", loai: "tien_do", nhom: "dau_tu_cong", muc_do: "cao",
    tieu_de: "Thoát nước: quá hạn Nghiệm thu", mo_ta: "", link: "/dau-tu-cong/DA-03", ky: "2026-10", trang_thai: "da_giao", ghi_chu_chat_luong: null, phat_sinh_luc: "2026-11-11",
    ho_so: { id: 9, chi_dao: "Báo cáo tại giao ban", co_quan_xu_ly: "Ban QLDA", nguoi_phu_trach: "Hoàng Văn Đức", nguyen_nhan: "", hanh_dong: "", han: "2026-11-16", trang_thai: "da_giao", ket_qua: "", lich_su: [] } },
];
const calls: { path: string; body?: unknown }[] = [];
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { method?: string; body?: unknown }) => { if (o?.method) calls.push({ path, body: o.body }); return Promise.resolve(o?.method ? {} : alerts); },
  ApiError: class extends Error {},
}));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ can: () => true }) }));

import { AlertsBoard } from "./AlertsBoard";

describe("Cảnh báo và hồ sơ theo dõi", () => {
  it("5 cột trạng thái và tách cảnh báo chất lượng dữ liệu", async () => {
    renderWithProviders(<AlertsBoard />);
    for (const c of ["Mới", "Đã giao", "Đang xử lý", "Hoàn thành", "Gia hạn"]) expect(await screen.findByRole("region", { name: c })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: /Chất lượng dữ liệu/ }));
    const moi = screen.getByRole("region", { name: "Mới" });
    expect(within(moi).getByText("Thu nhập bình quân: chưa có số liệu")).toBeInTheDocument();
    expect(within(moi).queryByText(/Tổ phó TDP/)).not.toBeInTheDocument();
    expect(within(moi).getByText(QUALITY)).toBeInTheDocument();
  });

  it("giao việc từ cảnh báo cần đủ cơ quan, người phụ trách, hạn", async () => {
    renderWithProviders(<AlertsBoard />);
    await userEvent.click(await screen.findByRole("button", { name: /Tổ phó TDP là đảng viên/ }));
    const dlg = await screen.findByRole("dialog");
    const btn = within(dlg).getByRole("button", { name: "Giao xử lý" });
    expect(btn).toBeDisabled();
    await userEvent.type(within(dlg).getByLabelText("Cơ quan xử lý"), "Văn phòng Đảng ủy");
    await userEvent.type(within(dlg).getByLabelText("Người phụ trách"), "Trần Văn Bình");
    await userEvent.type(within(dlg).getByLabelText("Hạn xử lý"), "2026-11-25");
    expect(btn).toBeEnabled();
    await userEvent.click(btn);
    expect(calls.at(-1)).toEqual({ path: "/api/alerts/1/assign", body: { co_quan_xu_ly: "Văn phòng Đảng ủy", nguoi_phu_trach: "Trần Văn Bình", han: "2026-11-25", chi_dao: "" } });
  });

  it("đóng hồ sơ phải có kết quả xử lý", async () => {
    renderWithProviders(<AlertsBoard />);
    await userEvent.click(await screen.findByRole("button", { name: /Thoát nước: quá hạn Nghiệm thu/ }));
    const dlg = await screen.findByRole("dialog");
    expect(within(dlg).getByText("Hoàng Văn Đức")).toBeInTheDocument();
    expect(within(dlg).getByRole("button", { name: "Hoàn thành hồ sơ" })).toBeDisabled();
    await userEvent.type(within(dlg).getByLabelText("Kết quả xử lý"), "Đã nghiệm thu ngày 20/11");
    expect(within(dlg).getByRole("button", { name: "Hoàn thành hồ sơ" })).toBeEnabled();
  });
});
