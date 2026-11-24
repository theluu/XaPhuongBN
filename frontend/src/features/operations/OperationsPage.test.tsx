import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";
import { card, tenant } from "@/test/fixtures";

vi.mock("@/components/OpsMap", () => ({
  OpsMap: ({ points, onSelect }: { points: { key: string; ten: string }[]; onSelect: (k: string) => void }) => (
    <div data-testid="map">{points.map((p) => <button key={p.key} type="button" onClick={() => onSelect(p.key)}>điểm {p.ten}</button>)}</div>),
  OpsLegend: () => <div />, pointColor: () => "thuong",
}));
let roles = ["lanh_dao"];
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ can: () => true, tenant, me: { roles } }) }));

const item = (o: object) => ({ loai: "phan_anh", id: 1, ma: "PA-1", ten: "x", khan_cap: false, dia_diem: "Ngõ 5", tdp_ten: "Tổ dân phố số 1", don_vi: "Phòng Kinh tế, Hạ tầng và Đô thị",
  nguoi_phu_trach: null, trang_thai: "da_giao", trang_thai_ten: "Đã giao xử lý", han: "2026-11-01", qua_han_ngay: null, lat: 21.27, lng: 106.1, linh_vuc_ten: "Môi trường", moi: false, link: "/phan-anh?id=1", ...o });
const all = [item({ id: 1, ten: "Cây đổ chắn đường", khan_cap: true }), item({ id: 2, ten: "Đèn hỏng cả tuyến", qua_han_ngay: 5 }), item({ id: 3, ten: "Rác chưa có vị trí", lat: null, lng: null })];
const calls: Record<string, unknown>[] = [];
vi.mock("@/lib/api", () => ({
  api: (path: string, o?: { params?: Record<string, unknown> }) => {
    if (path === "/api/dieu-hanh/tong-quan") {
      calls.push(o?.params ?? {});
      const viec = o?.params?.loc === "qua_han" ? all.filter((x) => x.qua_han_ngay) : all;
      return Promise.resolve({ chi_so: { phan_anh_moi: 2, den_han_hom_nay: 1, qua_han: 1, canh_bao_mo: 3 }, viec, tong: viec.length, cap_nhat_luc: "2026-11-11T08:30:00Z",
        du_lieu_moi_nhat: "2026-11-11T08:00:00Z", bo_loc: { dia_ban_label: "Tổ dân phố", tdp: [{ id: 1, ten: "Tổ dân phố số 1" }] } });
    }
    if (path.startsWith("/api/phan-anh/")) return Promise.resolve({ ...all[1], tieu_de: "Đèn hỏng cả tuyến", linh_vuc_ten: "Hạ tầng", co_vi_tri: true, han_xu_ly: "2026-11-06", tien_do_pct: 30,
      don_vi_phu_trach_ten: "Phòng Kinh tế, Hạ tầng và Đô thị", dia_chi: "Đường A", lich_su: [{ luc: "2026-11-01T01:00:00Z", nguoi: "canbo1", hanh_dong: "tiep_nhan" }],
      quyen: { giao: true, cap_nhat: false, xac_nhan: false }, anh_keys: [] });
    if (path === "/api/overview") return Promise.resolve({ ky: "2026-10", nq01: { tong: 23, dat: 17, nguy_co: 4, chua_du_du_lieu: 2 },
      the_chi_so: [card({ ma: "NS-THU-DB", ten: "Thu ngân sách trên địa bàn" }), card({ ma: "DC-DAN-SO", ten: "Dân số" })] });
    if (path === "/api/dieu-hanh/danh-muc") return Promise.resolve({ cap: "phuong", dia_ban_label: "Tổ dân phố", dia_ban: [], phong_ban: [{ ma: "KTHTDT", ten: "Phòng Kinh tế, Hạ tầng và Đô thị" }], linh_vuc: [], nguon: [] });
    return Promise.resolve({});
  },
  getToken: () => "t", ApiError: class extends Error {},
}));

import { OperationsPage } from "./OperationsPage";

describe("Tổng quan điều hành", () => {
  it("dải chỉ tiêu trọng tâm gọn dưới khối điều hành, dẫn sang báo cáo đầy đủ", async () => {
    roles = ["lanh_dao"];
    renderWithProviders(<OperationsPage />);
    const zone = await screen.findByRole("region", { name: /Chỉ tiêu trọng tâm/ });
    expect(await within(zone).findByText("Thu ngân sách trên địa bàn")).toBeInTheDocument();
    expect(within(zone).getByText("17 đạt")).toBeInTheDocument();
    expect(within(zone).getByRole("link", { name: "Xem báo cáo đầy đủ" })).toHaveAttribute("href", "/bao-cao");
  });

  it("lãnh đạo mặc định xem toàn đơn vị; cán bộ chuyên môn mặc định Việc của tôi", async () => {
    roles = ["lanh_dao"];
    const { unmount } = renderWithProviders(<OperationsPage />);
    expect(await screen.findByRole("radio", { name: "Toàn đơn vị" })).toHaveAttribute("aria-checked", "true");
    expect(calls.at(-1)).toMatchObject({ pham_vi: "tat_ca" });
    unmount();
    roles = ["nhap_lieu"];
    renderWithProviders(<OperationsPage />);
    expect(await screen.findByRole("radio", { name: "Việc của tôi" })).toHaveAttribute("aria-checked", "true");
    expect(calls.at(-1)).toMatchObject({ pham_vi: "cua_toi" });
    await userEvent.click(screen.getByRole("radio", { name: "Toàn đơn vị" }));
    expect(calls.at(-1)).toMatchObject({ pham_vi: "tat_ca" });
    roles = ["lanh_dao"];
  });

  it("hàng chỉ số, danh sách 60% và bản đồ 40%; khẩn cấp lên đầu", async () => {
    renderWithProviders(<OperationsPage />);
    expect(await screen.findByRole("button", { name: /Việc quá hạn\s*1/ })).toBeInTheDocument();
    const rows = within(screen.getByRole("table", { name: "Việc cần xử lý" })).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("Cây đổ chắn đường");
    expect(rows[0]).toHaveTextContent("Khẩn cấp");
    expect(rows[1]).toHaveTextContent("Quá hạn 5 ngày");
    expect(rows[2]).toHaveTextContent("Chưa có vị trí trên bản đồ");
    expect(screen.getByRole("region", { name: "Bản đồ địa bàn" })).toBeInTheDocument();
    expect(screen.getByText(/Cập nhật lúc/)).toBeInTheDocument();
  });

  it("bấm Việc quá hạn thì lọc danh sách: thấy việc, địa điểm, đơn vị, đã quá hạn bao lâu", async () => {
    renderWithProviders(<OperationsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /Việc quá hạn/ }));
    expect(calls.at(-1)).toMatchObject({ loc: "qua_han" });
    const table = await screen.findByRole("table", { name: "Việc cần xử lý" });
    await within(table).findByText("Đèn hỏng cả tuyến");
    expect(within(table).queryByText("Cây đổ chắn đường")).not.toBeInTheDocument();
    const row = within(table).getAllByRole("row")[1];
    expect(row).toHaveTextContent("Ngõ 5");
    expect(row).toHaveTextContent("Phòng Kinh tế, Hạ tầng và Đô thị");
    expect(row).toHaveTextContent("Quá hạn 5 ngày");
  });

  it("bấm điểm trên bản đồ chọn dòng và mở khung chi tiết có lịch sử, nút giao việc theo quyền", async () => {
    renderWithProviders(<OperationsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "điểm Đèn hỏng cả tuyến" }));
    const row = screen.getByRole("row", { selected: true });
    expect(row).toHaveTextContent("Đèn hỏng cả tuyến");
    const panel = await screen.findByRole("complementary", { name: "Chi tiết phản ánh" });
    expect(await within(panel).findByText("Tiếp nhận phản ánh")).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: /Giao lại/ })).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: "Cập nhật tiến độ" })).not.toBeInTheDocument();
  });
});
