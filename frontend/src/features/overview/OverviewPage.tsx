import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { formatDate, formatNumber, formatPeriod } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import { usePeriod } from "@/lib/period";
import type { IndicatorCard } from "@/lib/types";
import { KpiTile } from "@/components/KpiTile";
import { MapLegend, ProjectMap, type MapFeature } from "@/components/ProjectMap";

interface AlertItem { id: number; tieu_de: string; mo_ta: string; muc_do: string; loai: string; trang_thai: string; link: string; can_cu?: string;
  ho_so: { nguoi_phu_trach: string; han: string } | null }
interface ScheduleRow { nhom: string; ten: string; don_vi: string | null; chu_ky: string; cap_nhat_cuoi: string | null; data_state: string;
  so_chi_tieu?: number; da_xac_nhan?: number; tam_thoi?: number; chua_co?: number }
export interface Overview {
  tenant: { ten: string }; ky: string; the_chi_so: IndicatorCard[]; nq01: { tong: number; dat: number; nguy_co: number; chua_du_du_lieu: number };
  can_chi_dao: AlertItem[]; xu_huong: { ky: string; thuc_hien: number | null; ke_hoach: number | null }[];
  ban_do: { features: MapFeature[]; lop: string[] }; lich_cap_nhat: ScheduleRow[]; do_day_du: { du_kien: number; co_so: number; ty_le_pct: number | null };
  bo_loc: { tdp: { id: number; ten: string }[]; don_vi: string[] };
}

const MUC: Record<string, string> = { cao: "Mức cao", trung_binh: "Mức trung bình", thap: "Mức thấp" };
const TT: Record<string, string> = { moi: "Mới", da_giao: "Đã giao", dang_xu_ly: "Đang xử lý", gia_han: "Gia hạn" };

function Zone({ title, children, className = "", note }: { title: string; children: React.ReactNode; className?: string; note?: string }) {
  const id = `z-${title.replace(/\s+/g, "-")}`;
  return (
    <section aria-labelledby={id} className={`khu p-4 ${className}`}>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 id={id} className="the-tieu-de">{title}</h2>
        {note && <span className="text-[13px] text-muc-nhat">{note}</span>}
      </div>
      {children}
    </section>
  );
}

function scheduleText(r: ScheduleRow): string {
  if (r.so_chi_tieu !== undefined) {
    if (r.chua_co) return `Còn ${r.chua_co} chỉ tiêu chưa có số`;
    if (r.tam_thoi) return `${r.tam_thoi} chỉ tiêu chờ xác nhận`;
    return `Đủ ${r.so_chi_tieu} chỉ tiêu đã xác nhận`;
  }
  return r.data_state === "chua_co_qua_han" ? "Quá hạn cập nhật" : `Cập nhật ${formatDate(r.cap_nhat_cuoi)}`;
}

export function OverviewPage() {
  const { ky, tdp, setTdp } = usePeriod();
  const { tenant } = useAuth();
  const [donVi, setDonVi] = useState("");
  const q = useQuery({ queryKey: ["overview", ky, tdp, donVi], queryFn: () => api<Overview>("/api/overview", { params: { ky, tdp: tdp || undefined, don_vi: donVi || undefined } }) });
  const d = q.data;
  if (!d) return <p className="text-muc-nhat">{q.isError ? "Không tải được dữ liệu tổng quan." : "Đang tải tổng quan…"}</p>;
  const center: [number, number] = d.ban_do.features[0] ? [d.ban_do.features[0].geometry.coordinates[1], d.ban_do.features[0].geometry.coordinates[0]] : [21.2725, 106.0975];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1">
          <h1 className="text-[22px] font-bold leading-tight">Báo cáo tổng hợp {d.tenant.ten}</h1>
          <p className="text-[15px] text-muc-nhat">Số liệu kỳ {formatPeriod(d.ky)}. Độ đầy đủ dữ liệu chỉ tiêu: {d.do_day_du.ty_le_pct === null ? "—" : `${formatNumber(d.do_day_du.ty_le_pct)}%`} ({d.do_day_du.co_so}/{d.do_day_du.du_kien}).</p>
        </div>
        {d.bo_loc.don_vi.length > 0 && (
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muc-nhat">Đơn vị cung cấp</span>
            <select className="o-nhap w-auto py-1.5" value={donVi} onChange={(e) => setDonVi(e.target.value)}>
              <option value="">Tất cả đơn vị</option>
              {d.bo_loc.don_vi.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
          </label>
        )}
        {d.bo_loc.tdp.length > 0 && (
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muc-nhat">Tổ dân phố</span>
            <select className="o-nhap w-auto py-1.5" value={tdp} onChange={(e) => setTdp(e.target.value)}>
              <option value="">Toàn phường</option>
              {d.bo_loc.tdp.map((t) => <option key={t.id} value={t.id}>{t.ten}</option>)}
            </select>
          </label>
        )}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <Zone title="Chỉ tiêu trọng tâm" note="Bấm vào ô để mở phân hệ">
          <Link to="/chi-tieu" className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-1 rounded border border-vien bg-nen px-3 py-2 text-[14px] hover:bg-be-mat-2">
            <span className="font-semibold">Nghị quyết 01-NQ/ĐU: {d.nq01.tong} chỉ tiêu</span>
            <span style={{ color: "var(--xac-nhan)" }}>{d.nq01.dat} đạt</span>
            <span style={{ color: "var(--tam-thoi)" }}>{d.nq01.nguy_co} có nguy cơ</span>
            <span className="text-thieu">{d.nq01.chua_du_du_lieu} chưa đủ dữ liệu</span>
          </Link>
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(230px,1fr))]">
            {d.the_chi_so.map((c) => <KpiTile key={c.ma} card={c} />)}
          </div>
        </Zone>

        <Zone title="Việc cần chỉ đạo trong tuần" className="border-t-[3px] border-t-son">
          <ol className="divide-y divide-[var(--vien)]">
            {d.can_chi_dao.slice(0, 6).map((a) => (
              <li key={a.id} className="py-2.5">
                <Link to={`/canh-bao?id=${a.id}`} className="text-[14.5px] font-medium leading-snug hover:underline">{a.tieu_de}</Link>
                <div className="mt-0.5 flex flex-wrap gap-x-3 text-[12.5px] text-muc-nhat">
                  <span style={{ color: a.muc_do === "cao" ? "var(--son)" : undefined }}>{MUC[a.muc_do]}</span>
                  <span>{TT[a.trang_thai] ?? a.trang_thai}</span>
                  {a.ho_so && <span>Phụ trách: {a.ho_so.nguoi_phu_trach}, hạn {formatDate(a.ho_so.han)}</span>}
                </div>
              </li>
            ))}
            {d.can_chi_dao.length === 0 && <li className="py-2 text-[14px] text-muc-nhat">Không có việc cần chỉ đạo trong tuần.</li>}
          </ol>
          <Link to="/canh-bao" className="mt-2 inline-block text-[14px] font-medium underline">
            {d.can_chi_dao.length > 6 ? `Xem tất cả (${d.can_chi_dao.length} việc)` : "Xem tất cả cảnh báo và hồ sơ"}
          </Link>
        </Zone>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
        <Zone title="Xu hướng và bản đồ">
          <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
            <div>
              {d.ban_do.lop.length ? (
                <>
                  <ProjectMap features={d.ban_do.features} center={center} tileUrl={tenant?.ban_do?.tile_url} />
                  <MapLegend items={[{ loai: "du_an", ten: "Dự án đầu tư công" }, { loai: "cong_trinh", ten: "Công trình đang thi công" }]} />
                </>
              ) : <p className="text-[14px] text-muc-nhat">Bạn chưa được cấp quyền xem lớp bản đồ dự án, công trình.</p>}
            </div>
            <div>
              <h3 className="mb-1 the-tieu-de">Thu ngân sách trên địa bàn, lũy kế (tỷ đồng)</h3>
              {d.xu_huong.length ? (
                <ResponsiveContainer width="100%" height={260}>
                  <ComposedChart data={d.xu_huong} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid stroke="var(--vien)" vertical={false} />
                    <XAxis dataKey="ky" tickFormatter={(k: string) => `T${Number(k.slice(5))}`} tick={{ fontSize: 12, fill: "var(--muc-nhat)" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 12, fill: "var(--muc-nhat)" }} tickLine={false} axisLine={false} />
                    <Tooltip formatter={(v, n) => [v === null || v === undefined ? "Chưa có số" : `${formatNumber(Number(v))} tỷ`, String(n)]} labelFormatter={(k) => formatPeriod(String(k))}
                      contentStyle={{ background: "var(--be-mat)", border: "1px solid var(--vien)", borderRadius: 6, fontSize: 13 }} />
                    <Bar name="Thực hiện" dataKey="thuc_hien" fill="var(--muc)" radius={[2, 2, 0, 0]} isAnimationActive={false} />
                    <Line name="Kế hoạch tiến độ" dataKey="ke_hoach" stroke="var(--tam-thoi)" strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : <p className="text-[14px] text-muc-nhat">Chưa có số liệu ngân sách hoặc bạn chưa được cấp quyền xem.</p>}
            </div>
          </div>
        </Zone>

        <Zone title="Lịch cập nhật và xác nhận dữ liệu">
          <ul className="divide-y divide-[var(--vien)] text-[14px]">
            {d.lich_cap_nhat.map((r) => (
              <li key={`${r.nhom}-${r.don_vi ?? ""}`} className="flex items-start gap-3 py-2">
                <span aria-hidden className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${r.data_state === "chua_co_qua_han" ? "is-missing border border-thieu" : ""}`}
                  style={{ background: r.data_state === "da_xac_nhan" ? "var(--xac-nhan)" : r.data_state === "tam_thoi" ? "var(--tam-thoi)" : undefined }} />
                <div className="min-w-0 flex-1">
                  <div className="font-medium">{r.ten}</div>
                  {r.don_vi && <div className="text-[12.5px] text-muc-nhat">{r.don_vi}</div>}
                  <div className="text-[12.5px] text-muc-nhat">Chu kỳ: {r.chu_ky}</div>
                </div>
                <span className={`shrink-0 text-right text-[13px] ${r.data_state === "chua_co_qua_han" ? "text-son" : "text-muc-nhat"}`}>{scheduleText(r)}</span>
              </li>
            ))}
          </ul>
        </Zone>
      </div>
    </div>
  );
}
