import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumber, formatPeriod } from "@/lib/format";

export interface SeriesPoint { ky: string; gia_tri: number | null; ke_hoach: number | null; data_state?: string }

/** Diễn biến theo kỳ. Kỳ thiếu số để trống (không nối, không vẽ 0). */
export function SeriesChart({ data, unit, height = 220 }: { data: SeriesPoint[]; unit: string; height?: number }) {
  const hasPlan = data.some((d) => d.ke_hoach !== null);
  return (
    <figure>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
          <CartesianGrid stroke="var(--vien)" vertical={false} />
          <XAxis dataKey="ky" tickFormatter={formatPeriod} tick={{ fontSize: 12, fill: "var(--muc-nhat)" }} tickLine={false} axisLine={{ stroke: "var(--vien)" }} />
          <YAxis tick={{ fontSize: 12, fill: "var(--muc-nhat)" }} tickFormatter={(v) => formatNumber(v)} tickLine={false} axisLine={false} domain={["auto", "auto"]} width={52} />
          <Tooltip
            formatter={(v, name) => [v === null || v === undefined ? "Chưa có số" : `${formatNumber(Number(v))} ${unit}`, String(name)]}
            labelFormatter={(k) => formatPeriod(String(k))}
            contentStyle={{ background: "var(--be-mat)", border: "1px solid var(--vien)", borderRadius: 6, fontSize: 13 }}
          />
          {hasPlan && <Line name="Kế hoạch" dataKey="ke_hoach" stroke="var(--muc-nhat)" strokeDasharray="5 4" dot={false} strokeWidth={1.5} connectNulls={false} isAnimationActive={false} />}
          <Line name="Thực hiện" dataKey="gia_tri" stroke="var(--muc)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--muc)" }} connectNulls={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      <figcaption className="mt-1 flex gap-4 text-[12px] text-muc-nhat">
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-4 bg-muc" />Thực hiện</span>
        {hasPlan && <span className="flex items-center gap-1.5"><span className="h-0 w-4 border-t border-dashed border-muc-nhat" />Kế hoạch</span>}
        <span>Kỳ không có số để trống</span>
      </figcaption>
    </figure>
  );
}
