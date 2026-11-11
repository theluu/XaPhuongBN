import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { formatDate, formatMoney, formatNumber, formatPeriod } from "@/lib/format";
import { usePeriod } from "@/lib/period";
import { PageHeader } from "@/components/PageHeader";
import { Progress } from "@/components/Progress";

interface Totals { du_toan: number | null; ke_hoach_ky: number | null; thuc_hien: number | null; uoc_th: number | null; ty_le_pct: number | null }
interface Budget {
  nam: number; ky: string; thu: { dia_ban: Totals; ns_phuong: Totals };
  chi: { tong_hop: Totals; theo_nhom: (Totals & { nhom_ma: string; ten: string; vuot_du_toan: boolean })[]; theo_nhiem_vu: (Totals & { nhiem_vu: string; ten: string; vuot_du_toan: boolean })[] };
  nhom_thu: (Totals & { nhom_ma: string; ten: string; scope: string; nguy_co: boolean; trang_thai_doi_soat: string })[];
  xu_huong_thang: { ky: string; thu_dia_ban: number | null; thu_ns_phuong: number | null; chi: number | null; ke_hoach_thu_dia_ban: number | null }[];
  cho_doi_soat: boolean; lech_api_chot: { nhom_ma: string; scope: string; api: number; bao_cao_chot: number; chenh_pct: number }[];
  ngay_chot_gan_nhat: string | null; co_du_lieu: boolean;
}

const SCOPE: Record<string, string> = { dia_ban: "Trên địa bàn", ns_phuong: "NS phường hưởng" };

function RevenueBlock({ title, t, note }: { title: string; t: Totals; note: string }) {
  return (
    <section aria-label={title} className="khu rounded-md p-4">
      <h2 className="text-[16px] font-semibold">{title}</h2>
      <p className="mb-3 text-[13px] text-muc-nhat">{note}</p>
      <div className="flex items-baseline gap-2">
        <span className="font-so text-[44px] font-semibold leading-none tabular">{formatMoney(t.thuc_hien)}</span>
        <span className="text-[14px] text-muc-nhat">lũy kế</span>
      </div>
      <div className="my-3"><Progress value={t.thuc_hien} mark={t.ke_hoach_ky} max={t.du_toan} label={`${title}: thực hiện so với dự toán năm, vạch đứng là kế hoạch kỳ`} /></div>
      <dl className="grid grid-cols-2 gap-y-1 text-[14px] sm:grid-cols-4">
        <div><dt className="nhan">Dự toán năm</dt><dd className="tabular font-medium">{formatMoney(t.du_toan)}</dd></div>
        <div><dt className="nhan">Kế hoạch kỳ</dt><dd className="tabular font-medium">{formatMoney(t.ke_hoach_ky)}</dd></div>
        <div><dt className="nhan">Đạt so dự toán</dt><dd className="tabular font-medium">{t.ty_le_pct === null ? "—" : `${formatNumber(t.ty_le_pct, 1)}%`}</dd></div>
        <div><dt className="nhan">Ước thực hiện năm</dt><dd className="tabular font-medium">{formatMoney(t.uoc_th)}</dd></div>
      </dl>
    </section>
  );
}

export function BudgetPage() {
  const { ky } = usePeriod();
  const q = useQuery({ queryKey: ["budget", ky], queryFn: () => api<Budget>("/api/budget/summary", { params: { ky } }) });
  const d = q.data;
  return (
    <>
      <PageHeader title="Thu – chi ngân sách" desc={`Số liệu lũy kế đến hết ${formatPeriod(ky)}. Thu trên địa bàn và thu ngân sách phường được hưởng là hai phạm vi khác nhau, không cộng gộp.`} />
      {!d ? <p className="text-muc-nhat">Đang tải…</p> : (
        <div className="space-y-4">
          {d.cho_doi_soat && (
            <p role="status" className="rounded border border-[var(--tam-thoi)] bg-be-mat px-3 py-2 text-[14px]">
              Số liệu kỳ này đang chờ đối soát với Sở Tài chính/Kho bạc. Lần chốt gần nhất: {formatDate(d.ngay_chot_gan_nhat)}.
            </p>
          )}
          <div className="grid gap-4 lg:grid-cols-2">
            <RevenueBlock title="Thu ngân sách trên địa bàn" t={d.thu.dia_ban} note="Toàn bộ số thu NSNN phát sinh trên địa bàn phường" />
            <RevenueBlock title="Thu ngân sách phường được hưởng" t={d.thu.ns_phuong} note="Phần ngân sách phường được hưởng theo phân cấp" />
          </div>

          <section className="khu rounded-md p-4">
            <h2 className="mb-2 text-[16px] font-semibold">Diễn biến thu lũy kế theo tháng</h2>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={d.xu_huong_thang.map((x) => ({ ...x, a: x.thu_dia_ban && x.thu_dia_ban / 1e9, b: x.thu_ns_phuong && x.thu_ns_phuong / 1e9, k: x.ke_hoach_thu_dia_ban && x.ke_hoach_thu_dia_ban / 1e9 }))}
                margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--vien)" vertical={false} />
                <XAxis dataKey="ky" tickFormatter={formatPeriod} tick={{ fontSize: 12, fill: "var(--muc-nhat)" }} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "var(--muc-nhat)" }} tickLine={false} axisLine={false} unit=" tỷ" width={64} />
                <Tooltip formatter={(v, n) => [v === null || v === undefined ? "Chưa có số" : `${formatNumber(Number(v), 1)} tỷ đồng`, String(n)]} labelFormatter={(k) => formatPeriod(String(k))}
                  contentStyle={{ background: "var(--be-mat)", border: "1px solid var(--vien)", borderRadius: 6, fontSize: 13 }} />
                <Line name="Thu trên địa bàn" dataKey="a" stroke="var(--muc)" strokeWidth={2.5} dot={{ r: 2.5 }} connectNulls={false} isAnimationActive={false} />
                <Line name="Kế hoạch tiến độ (trên địa bàn)" dataKey="k" stroke="var(--tam-thoi)" strokeDasharray="5 4" strokeWidth={1.8} dot={false} isAnimationActive={false} />
                <Line name="NS phường hưởng" dataKey="b" stroke="var(--xac-nhan)" strokeWidth={2} dot={{ r: 2 }} connectNulls={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section className="khu overflow-x-auto rounded-md">
            <table aria-label="Thu theo nhóm khoản thu" className="w-full text-[14px]">
              <caption className="px-4 pt-3 text-left text-[16px] font-semibold">Thu theo nhóm khoản thu</caption>
              <thead><tr className="border-b border-vien text-left text-muc-nhat">
                <th className="px-4 py-2 font-medium">Nhóm</th><th className="font-medium">Phạm vi</th><th className="text-right font-medium">Dự toán</th>
                <th className="text-right font-medium">Kế hoạch kỳ</th><th className="text-right font-medium">Thực hiện</th><th className="text-right font-medium">% dự toán</th><th className="px-4 font-medium">Tình trạng</th>
              </tr></thead>
              <tbody>
                {d.nhom_thu.map((n) => (
                  <tr key={`${n.nhom_ma}-${n.scope}`} className="border-b border-vien">
                    <td className="px-4 py-2">{n.ten}</td><td>{SCOPE[n.scope]}</td>
                    <td className="text-right tabular">{formatMoney(n.du_toan)}</td><td className="text-right tabular">{formatMoney(n.ke_hoach_ky)}</td>
                    <td className="text-right tabular">{formatMoney(n.thuc_hien)}</td><td className="text-right tabular">{n.ty_le_pct === null ? "—" : `${formatNumber(n.ty_le_pct, 1)}%`}</td>
                    <td className="px-4">{n.nguy_co ? <span style={{ color: "var(--tam-thoi)" }}>Chậm tiến độ</span> : n.ke_hoach_ky === null ? <span className="text-muc-nhat">Chưa có kế hoạch kỳ</span> : "Đúng tiến độ"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="khu overflow-x-auto rounded-md">
            <table aria-label="Chi theo nhiệm vụ" className="w-full text-[14px]">
              <caption className="px-4 pt-3 text-left text-[16px] font-semibold">Chi ngân sách phường theo nhiệm vụ</caption>
              <thead><tr className="border-b border-vien text-left text-muc-nhat">
                <th className="px-4 py-2 font-medium">Nhiệm vụ</th><th className="text-right font-medium">Dự toán</th><th className="text-right font-medium">Thực chi</th>
                <th className="w-56 px-4 font-medium">So với dự toán</th><th className="px-4 font-medium">Tình trạng</th>
              </tr></thead>
              <tbody>
                {d.chi.theo_nhiem_vu.map((n) => (
                  <tr key={n.nhiem_vu} className="border-b border-vien">
                    <td className="px-4 py-2">{n.ten}</td><td className="text-right tabular">{formatMoney(n.du_toan)}</td><td className="text-right tabular">{formatMoney(n.thuc_hien)}</td>
                    <td className="px-4"><Progress value={n.thuc_hien} max={n.du_toan} label={`${n.ten}: thực chi so với dự toán`} /></td>
                    <td className="px-4">{n.vuot_du_toan ? <span className="font-medium text-son">Vượt dự toán</span> : "Trong dự toán"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {d.lech_api_chot.length > 0 && (
            <section className="khu rounded-md border-[var(--tam-thoi)] p-4">
              <h2 className="font-semibold">Số liệu API lệch báo cáo đã chốt</h2>
              <p className="mb-2 text-[13px] text-muc-nhat">Đây là cảnh báo chất lượng dữ liệu, cần lập biên bản giải trình trước khi chốt đối soát kỳ.</p>
              <ul className="text-[14px]">{d.lech_api_chot.map((l) => <li key={l.nhom_ma + l.scope}>{l.nhom_ma} ({SCOPE[l.scope]}): API {formatMoney(l.api)}, báo cáo chốt {formatMoney(l.bao_cao_chot)}, chênh {formatNumber(l.chenh_pct)}%</li>)}</ul>
            </section>
          )}
        </div>
      )}
    </>
  );
}
