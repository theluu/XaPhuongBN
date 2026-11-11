import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";

interface Src { id: number; ma: string; ten: string; loai: string; co_quan_cung_cap: string; nhom_du_lieu: string; trang_thai: string; phap_ly_chia_se: string;
  dung_chung: boolean; lan_dong_bo_cuoi: string | null; tong_api: number; so_api_ket_noi: number; so_api_tra_du_lieu: number;
  endpoints: { ma: string; ten: string; ket_noi: boolean; tra_du_lieu: boolean }[]; ghi_chu: string }

const TT: Record<string, [string, string]> = {
  hoat_dong: ["Hoạt động", "var(--xac-nhan)"], hoat_dong_mot_phan: ["Hoạt động một phần", "var(--tam-thoi)"], dang_ket_noi: ["Đang kết nối", "var(--thieu)"],
  khong_tra_du_lieu: ["Chưa trả dữ liệu", "var(--tam-thoi)"], loi: ["Gián đoạn", "var(--son)"],
};
const PL: Record<string, string> = { da_cho_phep: "Đã được phép chia sẻ", cho_phep_mot_phan: "Được phép chia sẻ một phần", chua_cho_phep: "Chưa được phép chia sẻ" };

export function SourcesPage() {
  const q = useQuery({ queryKey: ["sources"], queryFn: () => api<Src[]>("/api/sources") });
  return (
    <>
      <PageHeader title="Nguồn dữ liệu" desc="Ưu tiên API từ Kho dữ liệu dùng chung; nguồn chưa có API dùng tệp Excel/CSV theo biểu mẫu chuẩn hoặc biểu mẫu động. Hệ thống chỉ nhận số tổng hợp, bản ghi có thông tin định danh bị loại khi đồng bộ." />
      <div className="grid gap-3 lg:grid-cols-2">
        {(q.data ?? []).map((s) => {
          const [label, color] = TT[s.trang_thai] ?? [s.trang_thai, "var(--muc-nhat)"];
          const off = s.endpoints.filter((e) => !e.tra_du_lieu);
          return (
            <article key={s.id} className="khu rounded-md p-4">
              <div className="flex items-start gap-3">
                <div className="flex-1"><h2 className="font-semibold leading-snug">{s.ten}</h2><p className="text-[13px] text-muc-nhat">{s.co_quan_cung_cap}. {PL[s.phap_ly_chia_se]}{s.dung_chung ? ". Nguồn dùng chung của nền tảng" : ""}</p></div>
                <span className="shrink-0 text-[13.5px] font-medium" style={{ color }}>{label}</span>
              </div>
              {s.tong_api > 0 && <p className="mt-2 text-[14.5px]">{s.so_api_ket_noi}/{s.tong_api} API đã kết nối, {s.so_api_tra_du_lieu} API đang trả dữ liệu</p>}
              {off.length > 0 && <ul className="mt-1 text-[13px] text-muc-nhat">{off.map((e) => <li key={e.ma}>{e.ten}: chưa trả dữ liệu</li>)}</ul>}
              {s.ghi_chu && <p className="mt-1 text-[13px]">{s.ghi_chu}</p>}
              <p className="mt-2 text-[12.5px] text-muc-nhat">Đồng bộ lần cuối: {formatDate(s.lan_dong_bo_cuoi)}</p>
            </article>
          );
        })}
      </div>
    </>
  );
}
