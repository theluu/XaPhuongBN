import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { formatDate, formatMoney, formatNumber } from "@/lib/format";
import { usePeriod } from "@/lib/period";
import { PageHeader } from "@/components/PageHeader";
import { Progress } from "@/components/Progress";
import type { ProjectRow } from "./InvestmentPage";

interface Detail extends ProjectRow {
  lop_ten: string; don_vi_phu_trach: string; dia_diem: string; ngay_ht_ke_hoach: string | null;
  moc: { loai: string; loai_ten: string; han: string; ngay_thuc_te: string | null; qua_han: boolean }[];
  vuong_mac: { id: number; noi_dung: string; nguyen_nhan: string; trach_nhiem: string; huong_xu_ly: string; can_quyet_dinh: boolean; han: string | null; trang_thai: string }[];
}

export function ProjectDetail() {
  const { ma = "" } = useParams();
  const { ky } = usePeriod();
  const q = useQuery({ queryKey: ["project", ma, ky], queryFn: () => api<Detail>(`/api/projects/${encodeURIComponent(ma)}`, { params: { ky } }) });
  const d = q.data;
  if (q.isError) return <p className="text-son">Không tìm thấy dự án {ma}.</p>;
  if (!d) return <p className="text-muc-nhat">Đang tải…</p>;
  return (
    <>
      <Link to="/dau-tu-cong" className="text-[14px] text-muc-nhat hover:underline">Đầu tư công</Link>
      <PageHeader title={d.ten} desc={`${d.ma_du_an}. Lớp ${d.lop}: ${d.lop_ten}. Chủ đầu tư: ${d.chu_dau_tu}.`} />
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <section className="khu rounded-md p-4">
          <h2 className="mb-3 font-semibold">Vốn và giải ngân</h2>
          <dl className="grid grid-cols-2 gap-y-2 text-[14px]">
            <div><dt className="nhan">Tổng mức đầu tư</dt><dd className="tabular font-medium">{formatMoney(d.tong_muc_dt)}</dd></div>
            <div><dt className="nhan">Kế hoạch vốn năm</dt><dd className="tabular font-medium">{formatMoney(d.ke_hoach_von_nam)}</dd></div>
            <div><dt className="nhan">Lịch vốn đến kỳ</dt><dd className="tabular font-medium">{formatMoney(d.lich_von_ky)}</dd></div>
            <div><dt className="nhan">Đã giải ngân</dt><dd className="tabular font-medium">{formatMoney(d.giai_ngan_luy_ke)} ({d.ty_le_giai_ngan_pct === null ? "—" : `${formatNumber(d.ty_le_giai_ngan_pct, 1)}%`})</dd></div>
            <div><dt className="nhan">Khối lượng thực hiện</dt><dd className="tabular font-medium">{d.khoi_luong_pct === null ? "—" : `${formatNumber(d.khoi_luong_pct)}%`}</dd></div>
            <div><dt className="nhan">Hoàn thành theo kế hoạch</dt><dd className="font-medium">{formatDate(d.ngay_ht_ke_hoach)}</dd></div>
          </dl>
          <div className="mt-3"><Progress value={d.giai_ngan_luy_ke} mark={d.lich_von_ky} max={d.ke_hoach_von_nam} label="Giải ngân so với kế hoạch vốn năm" /></div>
        </section>
        <section className="khu rounded-md p-4">
          <h2 className="mb-3 font-semibold">Mốc tiến độ</h2>
          <ol className="space-y-2 text-[14px]">
            {d.moc.map((m) => (
              <li key={m.loai} className="flex items-center gap-3">
                <span aria-hidden className="h-3 w-3 rounded-full border-2" style={{ borderColor: m.ngay_thuc_te ? "var(--xac-nhan)" : m.qua_han ? "var(--son)" : "var(--thieu)", background: m.ngay_thuc_te ? "var(--xac-nhan)" : "transparent" }} />
                <span className="w-28 font-medium">{m.loai_ten}</span>
                <span className="text-muc-nhat">Hạn {formatDate(m.han)}</span>
                <span className={m.qua_han ? "font-medium text-son" : ""}>{m.ngay_thuc_te ? `Xong ${formatDate(m.ngay_thuc_te)}` : m.qua_han ? "Quá hạn" : "Chưa đến hạn"}</span>
              </li>
            ))}
          </ol>
        </section>
      </div>
      <section className="mt-4">
        <h2 className="mb-2 font-semibold">Vướng mắc</h2>
        {d.vuong_mac.length === 0 && <p className="text-[14px] text-muc-nhat">Không có vướng mắc được báo cáo.</p>}
        <div className="grid gap-3 lg:grid-cols-2">
          {d.vuong_mac.map((v) => (
            <article key={v.id} className={`khu rounded-md p-4 ${v.can_quyet_dinh ? "border-l-[3px] border-l-son" : ""}`}>
              <h3 className="font-semibold">{v.noi_dung}</h3>
              {v.can_quyet_dinh && <p className="text-[13px] font-medium text-son">Cần lãnh đạo quyết định</p>}
              <dl className="mt-2 grid grid-cols-[8rem_1fr] gap-y-1 text-[14px]">
                <dt className="nhan">Nguyên nhân</dt><dd>{v.nguyen_nhan || "—"}</dd>
                <dt className="nhan">Trách nhiệm</dt><dd>{v.trach_nhiem || "—"}</dd>
                <dt className="nhan">Hướng xử lý</dt><dd>{v.huong_xu_ly || "—"}</dd>
                <dt className="nhan">Hạn</dt><dd>{formatDate(v.han)}</dd>
              </dl>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}
