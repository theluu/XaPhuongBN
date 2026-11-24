import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/render";

const unit = (ma: string, ten: string, khoi: string) => ({ id: ma.length, ma, ten, khoi, khoi_ten: khoi, cap_tren_ma: "UBND", lanh_dao_phu_trach_ma: null, chuc_nang: "",
  dien_thoai: null, email: null, dia_chi: null, thu_tu: 0, khoi_luong: null });
const st = (id: number, dv: string, ho_ten: string, chuc_vu: string, cap: string) => ({ id, ma: `S${id}`, don_vi_ma: dv, ho_ten, chuc_vu, cap, dien_thoai: "0900 111 222", email: null,
  nhiem_vu: "", linh_vuc: [], dia_ban_ids: [], user_id: null, thu_tu: id, is_sample: true, khoi_luong: { dang_xu_ly: 3, qua_han: 1, viec: [] } });
const org = {
  ten_don_vi: "P", cap: "phuong", khoi: { chuyen_mon: "Cơ quan chuyên môn thuộc UBND", truc_thuoc: "Đơn vị trực thuộc UBND" }, co_khoi_luong: true, dia_ban_label: "Tổ dân phố", dia_ban: [],
  don_vi: [unit("KTHTDT", "Phòng Kinh tế, Hạ tầng và Đô thị", "chuyen_mon"), unit("VHXH", "Phòng Văn hóa – Xã hội", "chuyen_mon"), unit("HCC", "Trung tâm Phục vụ hành chính công", "truc_thuoc")],
  can_bo: [st(1, "KTHTDT", "Trần Thị Bích", "Phó Trưởng phòng", "pho"), st(2, "KTHTDT", "Nguyễn Văn An", "Trưởng phòng", "truong"), st(3, "VHXH", "Mai Thị Thu", "Trưởng phòng", "truong")],
};
vi.mock("@/lib/api", () => ({ api: () => Promise.resolve(org), ApiError: class extends Error {} }));

import { AssigneePicker, type Assignee } from "./AssigneePicker";

let last: Assignee | null = null;
function Harness({ nhom }: { nhom?: string }) {
  const [v, setV] = useState<Assignee>({ unitMa: "", unitTen: "", nguoi: "" });
  last = v;
  return <AssigneePicker value={v} onChange={setV} nhom={nhom} />;
}

describe("Chọn người được giao", () => {
  it("gợi ý đơn vị theo lĩnh vực, tự điền trưởng đơn vị, hiện điện thoại và khối lượng việc", async () => {
    renderWithProviders(<Harness nhom="dau_tu_cong" />);
    expect(await screen.findByText(/Gợi ý theo lĩnh vực/)).toBeInTheDocument();
    expect(last).toEqual({ unitMa: "KTHTDT", unitTen: "Phòng Kinh tế, Hạ tầng và Đô thị", nguoi: "Nguyễn Văn An" });
    expect(screen.getByText(/đang xử lý 3 việc, 1 quá hạn/)).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Người phụ trách"), "Trần Thị Bích");
    expect(last?.nguoi).toBe("Trần Thị Bích");
    await userEvent.selectOptions(screen.getByLabelText("Đơn vị xử lý"), "VHXH");
    expect(last).toEqual({ unitMa: "VHXH", unitTen: "Phòng Văn hóa – Xã hội", nguoi: "Mai Thị Thu" });
  });

  it("chỉ chọn được cán bộ của đơn vị đã chọn; có thể nhập người khác", async () => {
    renderWithProviders(<Harness />);
    await screen.findByRole("option", { name: "Trung tâm Phục vụ hành chính công" });
    await userEvent.selectOptions(screen.getByLabelText("Đơn vị xử lý"), "HCC");
    expect(screen.getByText(/chưa có cán bộ trong danh bạ/)).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Người phụ trách"), "Người khác (nhập tên)…");
    await userEvent.type(screen.getByLabelText("Họ tên người phụ trách"), "Đỗ Thị Mai");
    expect(last?.nguoi.trim()).toBe("Đỗ Thị Mai");
  });
});
