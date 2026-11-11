import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { formatNumber, formatPeriod } from "@/lib/format";
import { usePeriod } from "@/lib/period";
import type { IndicatorCard } from "@/lib/types";
import { KpiTile } from "@/components/KpiTile";
import { PageHeader } from "@/components/PageHeader";

interface Pop {
  ky: string; tong_dan_so: number | null; nam: number | null; nu: number | null; so_ho: number | null; nguong_an: number; cho_phep_theo_tdp: boolean;
  thap_tuoi: { nhom_tuoi: string; nam: number | null; nu: number | null; nam_an: boolean; nu_an: boolean }[];
  theo_tdp: { tdp_id: number; ma_tdp: string; ten: string; nhan_khau: number | null; an: boolean }[] | null;
  bien_dong: { ky: string; dan_so: number | null; sinh: number | null; tu: number | null; chuyen_den: number | null; chuyen_di: number | null }[];
}

const cell = (v: number | null, an: boolean) => (an ? "<5" : formatNumber(v));

export function PopulationPage() {
  const { ky } = usePeriod();
  const q = useQuery({ queryKey: ["population", ky], queryFn: () => api<Pop>("/api/population", { params: { ky } }) });
  const inds = useQuery({ queryKey: ["indicators", "dan_cu", ky], queryFn: () => api<IndicatorCard[]>("/api/indicators", { params: { phan_he: "dan_cu", ky } }) });
  const d = q.data;
  return (
    <>
      <PageHeader title="Dân cư, an sinh và cơ cấu dân số"
        desc={`Số liệu thống kê tổng hợp kỳ ${formatPeriod(ky)} từ Kho dữ liệu dùng chung. Hệ thống không hiển thị danh sách hay thông tin định danh cá nhân; ô có dưới ${d?.nguong_an ?? 5} người được ẩn.`} />
      {!d ? <p className="text-muc-nhat">Đang tải…</p> : (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[["Dân số", d.tong_dan_so, "người"], ["Nam", d.nam, "người"], ["Nữ", d.nu, "người"], ["Số hộ", d.so_ho, "hộ"]].map(([t, v, u]) => (
              <div key={t as string} className={`khu rounded-md p-4 ${v === null ? "is-missing" : ""}`}>
                <div className="text-[14px] text-muc-nhat">{t}</div>
                <div className="font-so text-[40px] font-semibold leading-tight tabular">{formatNumber(v as number | null)}</div>
                <div className="text-[13px] text-muc-nhat">{u}</div>
              </div>
            ))}
          </div>
          <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
            <section className="khu rounded-md p-4">
              <h2 className="mb-2 font-semibold">Tháp dân số</h2>
              <ResponsiveContainer width="100%" height={420}>
                <BarChart layout="vertical" stackOffset="sign" data={[...d.thap_tuoi].reverse().map((r) => ({ ...r, namAm: r.nam === null ? null : -r.nam }))} margin={{ left: 8, right: 16 }}>
                  <CartesianGrid stroke="var(--vien)" horizontal={false} />
                  <XAxis type="number" tickFormatter={(v: number) => formatNumber(Math.abs(v))} tick={{ fontSize: 12, fill: "var(--muc-nhat)" }} />
                  <YAxis type="category" dataKey="nhom_tuoi" width={48} tick={{ fontSize: 12, fill: "var(--muc-nhat)" }} />
                  <Tooltip formatter={(v, n) => [v === null || v === undefined ? "Ẩn (<5)" : formatNumber(Math.abs(Number(v))), String(n)]}
                    contentStyle={{ background: "var(--be-mat)", border: "1px solid var(--vien)", borderRadius: 6, fontSize: 13 }} />
                  <Bar name="Nam" dataKey="namAm" stackId="a" fill="var(--muc)" isAnimationActive={false} />
                  <Bar name="Nữ" dataKey="nu" stackId="a" fill="var(--tam-thoi)" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </section>
            <section className="khu overflow-x-auto rounded-md">
              <table aria-label="Cơ cấu dân số theo nhóm tuổi" className="w-full text-[14px]">
                <caption className="px-4 pt-3 text-left font-semibold">Cơ cấu theo nhóm tuổi</caption>
                <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="px-4 py-1.5 font-medium">Nhóm tuổi</th><th className="text-right font-medium">Nam</th><th className="px-4 text-right font-medium">Nữ</th></tr></thead>
                <tbody>{d.thap_tuoi.map((r) => (
                  <tr key={r.nhom_tuoi} className="border-b border-vien"><td className="px-4 py-1">{r.nhom_tuoi}</td><td className="text-right tabular">{cell(r.nam, r.nam_an)}</td><td className="px-4 text-right tabular">{cell(r.nu, r.nu_an)}</td></tr>
                ))}</tbody>
              </table>
            </section>
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            <section className="khu overflow-x-auto rounded-md">
              <table aria-label="Biến động dân cư theo tháng" className="w-full text-[14px]">
                <caption className="px-4 pt-3 text-left font-semibold">Biến động theo tháng</caption>
                <thead><tr className="border-b border-vien text-left text-muc-nhat">
                  <th className="px-4 py-1.5 font-medium">Kỳ</th><th className="text-right font-medium">Dân số</th><th className="text-right font-medium">Sinh</th><th className="text-right font-medium">Tử</th>
                  <th className="text-right font-medium">Chuyển đến</th><th className="px-4 text-right font-medium">Chuyển đi</th></tr></thead>
                <tbody>{[...d.bien_dong].reverse().map((r) => (
                  <tr key={r.ky} className="border-b border-vien"><td className="px-4 py-1">{formatPeriod(r.ky)}</td><td className="text-right tabular">{formatNumber(r.dan_so)}</td>
                    <td className="text-right tabular">{formatNumber(r.sinh)}</td><td className="text-right tabular">{formatNumber(r.tu)}</td>
                    <td className="text-right tabular">{formatNumber(r.chuyen_den)}</td><td className="px-4 text-right tabular">{formatNumber(r.chuyen_di)}</td></tr>
                ))}</tbody>
              </table>
            </section>
            <section className="khu overflow-x-auto rounded-md">
              {d.theo_tdp ? (
                <table aria-label="Dân số theo tổ dân phố" className="w-full text-[14px]">
                  <caption className="px-4 pt-3 text-left font-semibold">Theo tổ dân phố</caption>
                  <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="px-4 py-1.5 font-medium">Tổ dân phố</th><th className="px-4 text-right font-medium">Nhân khẩu</th></tr></thead>
                  <tbody>{d.theo_tdp.map((r) => (
                    <tr key={r.tdp_id} className="border-b border-vien"><td className="px-4 py-1">{r.ten}</td><td className="px-4 text-right tabular">{cell(r.nhan_khau, r.an)}</td></tr>
                  ))}</tbody>
                </table>
              ) : <p className="p-4 text-[14px] text-muc-nhat">Nguồn dữ liệu chưa cho phép thống kê theo tổ dân phố.</p>}
            </section>
          </div>
          {(inds.data ?? []).length > 0 && (
            <section>
              <h2 className="mb-2 font-semibold">An sinh xã hội</h2>
              <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(260px,1fr))]">{(inds.data ?? []).map((c) => <KpiTile key={c.ma} card={c} />)}</div>
            </section>
          )}
        </div>
      )}
    </>
  );
}
