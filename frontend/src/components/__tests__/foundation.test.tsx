import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { formatNumber, formatPeriod } from "@/lib/format";
import { GovHeader } from "@/components/GovHeader";
import { KpiTile } from "@/components/KpiTile";
import { ProvenanceStamp } from "@/components/ProvenanceStamp";
import { SampleBanner } from "@/components/SampleBanner";
import { ModuleConnectingState } from "@/components/ModuleConnectingState";
import type { IndicatorCard, TenantInfo } from "@/lib/types";

const tenant: TenantInfo = {
  id: 1, ma_dvhc: "P", ten: "Phường Việt Yên", cap: "phuong",
  ten_co_quan: ["ĐẢNG ỦY – UBND PHƯỜNG VIỆT YÊN", "Hệ thống điều hành số phường"],
  logo_url: null, ban_do: null, cho_phep_theo_tdp: true, modules: {},
};

export const card = (over: Partial<IndicatorCard> = {}): IndicatorCard => ({
  id: 1, ma: "NQ01-12", ten: "Tỷ lệ dân số tham gia BHYT", nhom: "gd_yt_mt", phan_he: "gd_yt_mt", bo: ["NQ01"],
  don_vi: "%", chieu: "tang_tot", ky: "2026-10", ke_hoach: 98.5, muc_tieu: null, muc_tieu_khoang: null,
  nguong_toan_tu: null, muc_tieu_2030: 99.8, muc_so_sanh: 98.5, thuc_hien: 98.6, du_bao: null, hoan_thanh_pct: 100.1,
  status: "dat", data_state: "da_xac_nhan", ky_truoc: { ky: "2026-09", gia_tri: 98.5 }, cung_ky: { ky: "2025-10", gia_tri: 97.9 },
  nguon: "BHXH thành phố", nguon_loai: "chuyen_nganh", don_vi_cung_cap: "Bảo hiểm xã hội",
  nguoi_xac_nhan: "Phó Chủ tịch UBND Hoàng Văn Đức", thoi_diem_chot: "2026-11-05T00:00:00Z",
  thoi_diem_dong_bo: "2026-11-06T00:00:00Z", lech_nguon: null, co_so_moi_cho_xac_nhan: false, is_sample: true,
  phan_loai_thong_tin: "noi_bo", ky_cap_nhat: "thang", value_id: 10, ...over,
});

describe("định dạng số", () => {
  it("không bao giờ đổi thiếu số thành 0", () => {
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
    expect(formatNumber(0)).toBe("0");
  });
  it("theo chuẩn Việt Nam", () => {
    expect(formatNumber(1234.5)).toBe("1.234,5");
    expect(formatNumber(98.6)).toBe("98,6");
  });
  it("hiển thị kỳ dễ đọc", () => {
    expect(formatPeriod("2026-10")).toBe("Tháng 10/2026");
    expect(formatPeriod("2026-Q3")).toBe("Quý III/2026");
    expect(formatPeriod("2025")).toBe("Năm 2025");
  });
});

describe("GovHeader", () => {
  it("dùng Quốc huy khi đơn vị không có logo", () => {
    render(<GovHeader tenant={tenant} />);
    const img = screen.getByAltText("Quốc huy nước Cộng hòa xã hội chủ nghĩa Việt Nam");
    expect(img).toHaveAttribute("src", "/brand/quoc-huy.svg");
    expect(screen.getByText("ĐẢNG ỦY – UBND PHƯỜNG VIỆT YÊN")).toBeInTheDocument();
  });
  it("dùng logo đơn vị nếu có", () => {
    render(<GovHeader tenant={{ ...tenant, logo_url: "/api/files/abc" }} />);
    expect(screen.getByAltText("Biểu trưng Phường Việt Yên")).toHaveAttribute("src", "/api/files/abc");
  });
});

describe("KpiTile", () => {
  it("thiếu số hiển thị gạch ngang và vân chéo, không hiển thị 0", () => {
    const { container } = render(<KpiTile card={card({ thuc_hien: null, status: "chua_du_du_lieu", data_state: "chua_co_qua_han", hoan_thanh_pct: null })} />);
    const value = screen.getByTestId("kpi-value");
    expect(value).toHaveTextContent("—");
    expect(value.textContent).not.toMatch(/\b0\b/);
    expect(container.querySelector(".is-missing")).not.toBeNull();
  });
  it("hiển thị giá trị, kỳ và trạng thái", () => {
    render(<KpiTile card={card()} />);
    expect(screen.getByTestId("kpi-value")).toHaveTextContent("98,6");
    expect(screen.getByText("Tháng 10/2026")).toBeInTheDocument();
    expect(screen.getByText("Đạt")).toBeInTheDocument();
  });
});

describe("ProvenanceStamp", () => {
  it("đã xác nhận: dấu đặc", () => {
    render(<ProvenanceStamp card={card()} />);
    expect(screen.getByTestId("stamp")).toHaveAttribute("data-kind", "da_xac_nhan");
    expect(screen.getByLabelText(/Đã xác nhận/)).toBeInTheDocument();
  });
  it("tạm thời: dấu nét đứt", () => {
    render(<ProvenanceStamp card={card({ data_state: "tam_thoi", nguoi_xac_nhan: null })} />);
    expect(screen.getByTestId("stamp")).toHaveAttribute("data-kind", "tam_thoi");
    expect(screen.getByLabelText("Tạm thời – chờ xác nhận")).toBeInTheDocument();
  });
  it("chưa có số: không có dấu", () => {
    render(<ProvenanceStamp card={card({ data_state: "chua_co_qua_han", thuc_hien: null })} />);
    expect(screen.getByTestId("stamp")).toHaveAttribute("data-kind", "chua_co");
  });
  it("lệch nguồn: dấu viền kép", () => {
    render(<ProvenanceStamp card={card({ lech_nguon: { phuong: 99.1, chuyen_nganh: 98.6, chenh: 0.5, chenh_pct: 0.5 } })} />);
    expect(screen.getByTestId("stamp")).toHaveAttribute("data-kind", "lech_nguon");
  });
});

describe("SampleBanner và ModuleConnectingState", () => {
  it("cảnh báo dữ liệu minh họa", () => {
    render(<SampleBanner show />);
    expect(screen.getByRole("status")).toHaveTextContent("Dữ liệu minh họa – không phải số liệu chính thức");
  });
  it("không hiện khi không có dữ liệu minh họa", () => {
    const { container } = render(<SampleBanner show={false} />);
    expect(container).toBeEmptyDOMElement();
  });
  it("phân hệ đang kết nối", () => {
    render(<ModuleConnectingState title="Ngân sách" sources={[{ ten: "Kho bạc", trang_thai: "dang_ket_noi" }]} />);
    expect(screen.getByText("Đang kết nối nguồn dữ liệu")).toBeInTheDocument();
    expect(screen.getByText(/Kho bạc/)).toBeInTheDocument();
  });
});
