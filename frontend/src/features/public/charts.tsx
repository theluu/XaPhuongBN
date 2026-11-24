import type { ReactNode } from "react";
import { Download, type LucideIcon } from "lucide-react";
import { CountUp, Reveal } from "./fx";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { L, n } from "./i18n";

/** Bảng màu phân loại (thứ tự cố định, đã kiểm tra mù màu) — xem hướng dẫn dataviz. */
export const C = { blue: "#2a78d6", orange: "#eb6834", aqua: "#1baf7a", yellow: "#eda100", violet: "#6250d6", red: "#e34948", green: "#008300", gray: "#94a3b8" };
export const SERIES = [C.blue, C.orange, C.aqua, C.yellow, C.violet, C.red];
export const STATUS_C = { dat: "#15803d", nguy_co: "#d97706", dang_cap_nhat: "#94a3b8", theo_doi: "#2a78d6", qua_han: "#dc2626" };

export const fmt = (v: number | null | undefined, d?: number) =>
  v === null || v === undefined ? "—" : n(v, d ?? (Number.isInteger(v) || Math.abs(v) >= 100 ? 0 : 1));

/** Tải bảng số liệu của một chuyên mục dưới dạng CSV (mở được bằng Excel, có BOM UTF-8). */
export function downloadCsv(name: string, rows: (string | number | null | undefined)[][]) {
  const esc = (v: string | number | null | undefined) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const blob = new Blob(["\ufeff" + rows.map((r) => r.map(esc).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `${name}.csv` });
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
}
const short = (s: string, n = 22) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);
const AX = { fontSize: 11.5, fill: "var(--muc-nhat)" };
const TT = { contentStyle: { borderRadius: 10, border: "1px solid var(--vien-dam)", fontSize: 13, boxShadow: "0 6px 20px -6px rgba(15,42,77,.25)" } };

export function Section({ id, title, desc, tag, children, csv }: { id: string; title: string; desc?: string; tag?: string; children: ReactNode;
  csv?: () => (string | number | null | undefined)[][] }) {
  return (
    <section id={id} aria-labelledby={`h-${id}`} className="scroll-mt-16">
      <Reveal className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-4">
        <div className="w-full min-w-0 border-l-4 border-[#c8102e] pl-3 sm:flex-1">
          <h2 id={`h-${id}`} className="text-[21px] font-extrabold leading-tight tracking-tight text-muc sm:text-[24px]">{title}</h2>
          {desc && <p className="mt-1 text-[13.5px] leading-relaxed text-muc-nhat">{desc}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2 pl-4 sm:shrink-0 sm:pl-0">
          {tag && <span className="rounded-full bg-[color-mix(in_srgb,var(--chinh)_10%,transparent)] px-3 py-1 text-[12.5px] font-bold text-[var(--chinh)]">{tag}</span>}
          {csv && (
            <button type="button" onClick={() => downloadCsv(id, csv())} className="khong-in inline-flex items-center gap-1.5 rounded-full border border-[var(--vien-dam)] bg-[var(--be-mat)] px-3 py-1 text-[12.5px] font-semibold text-muc hover:border-[var(--chinh)] hover:text-[var(--chinh)]">
              <Download size={13} aria-hidden />{L("Tải CSV", "CSV")}<span className="sr-only">{` – ${title}`}</span>
            </button>
          )}
        </div>
      </Reveal>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}

export interface Kpi { label: string; value?: string; num?: number | null; digits?: number; suffix?: string; sub?: string; color?: string; icon?: LucideIcon }
export function Kpis({ items }: { items: Kpi[] }) {
  return (
    <div className={`grid grid-cols-2 gap-3 ${items.length >= 5 ? "lg:grid-cols-5" : "lg:grid-cols-4"} max-lg:[&>*:last-child:nth-child(odd)]:col-span-2`}>
      {items.map((k, i) => {
        const c = k.color ?? SERIES[i % SERIES.length];
        const Icon = k.icon;
        return (
          <Reveal key={k.label} delay={i * 70}>
            <div className="khu the-noi relative h-full overflow-hidden p-4 pt-5" style={{ background: `linear-gradient(135deg, color-mix(in srgb, ${c} 9%, var(--be-mat)) 0%, var(--be-mat) 60%)` }}>
              <div aria-hidden className="absolute inset-x-0 top-0 h-1" style={{ background: c }} />
              {Icon && <span aria-hidden className="absolute right-3 top-4 flex h-9 w-9 items-center justify-center rounded-xl" style={{ background: `color-mix(in srgb, ${c} 14%, transparent)`, color: c }}><Icon size={18} /></span>}
              <p className="pr-10 text-[11.5px] font-bold uppercase tracking-wider text-muc-nhat">{k.label}</p>
              <p className="mt-1 text-[24px] font-extrabold leading-tight tracking-tight text-muc tabular-nums sm:text-[28px]">
                {k.num !== undefined ? <CountUp value={k.num} digits={k.digits} suffix={k.suffix} /> : k.value}
              </p>
              {k.sub && <p className="mt-0.5 text-[12px] text-muc-nhat">{k.sub}</p>}
            </div>
          </Reveal>
        );
      })}
    </div>
  );
}

export function Card({ title, desc, unit, children, className = "" }: { title: string; desc?: string; unit?: string; children: ReactNode; className?: string }) {
  return (
    <Reveal lazy minH={260} className={`khu the-noi min-w-0 p-4 sm:p-5 ${className}`}>
      <div className="mb-3 flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="the-tieu-de text-[15.5px] font-extrabold text-muc">{title}</h3>
          {desc && <p className="mt-0.5 text-[12.5px] text-muc-nhat">{desc}</p>}
        </div>
        {unit && <span className="shrink-0 rounded-full bg-[var(--be-mat-2)] px-2.5 py-0.5 text-[11.5px] font-semibold text-muc-nhat">{unit}</span>}
      </div>
      {children}
    </Reveal>
  );
}

/** Thanh ngang: một hoặc nhiều chuỗi (cùng đơn vị), có chú giải khi ≥ 2 chuỗi. */
export function HBars({ data, keys, unit = "", stacked = false, max, height }: {
  data: object[]; keys: { key: string; name: string; color: string }[]; unit?: string; stacked?: boolean; max?: number; height?: number;
}) {
  const h = height ?? Math.max(160, data.length * (keys.length > 1 && !stacked ? 40 : 34) + 40);
  const narrow = typeof window !== "undefined" && window.innerWidth < 640;
  return (
    <div style={{ height: h }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }} barCategoryGap="22%">
          <CartesianGrid stroke="var(--vien)" horizontal={false} />
          <XAxis type="number" tick={AX} tickLine={false} axisLine={false} domain={max ? [0, max] : [0, "auto"]} />
          <YAxis type="category" dataKey="ten" width={narrow ? 104 : 150} tick={AX} tickLine={false} axisLine={false} tickFormatter={(s: string) => short(s, narrow ? 16 : 24)} />
          <Tooltip {...TT} cursor={{ fill: "rgba(42,120,214,.06)" }} formatter={(v, n) => [`${fmt(Number(v))}${unit ? ` ${unit}` : ""}`, String(n)]} />
          {keys.length > 1 && <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 12.5, paddingTop: 6 }} />}
          {keys.map((k, i) => (
            <Bar key={k.key} dataKey={k.key} name={k.name} fill={k.color} stackId={stacked ? "s" : undefined}
                 radius={stacked ? (i === keys.length - 1 ? [0, 4, 4, 0] : 0) : [0, 4, 4, 0]} maxBarSize={22} animationDuration={900} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Cột đứng theo thời gian / nhóm, cùng một trục. */
export function VBars({ data, xKey, keys, unit = "", stacked = false, height = 240, xFmt }: {
  data: object[]; xKey: string; keys: { key: string; name: string; color: string }[]; unit?: string; stacked?: boolean; height?: number; xFmt?: (v: string) => string;
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }} barCategoryGap="24%">
          <CartesianGrid stroke="var(--vien)" vertical={false} />
          <XAxis dataKey={xKey} tick={AX} tickLine={false} tickFormatter={xFmt} interval={0} />
          <YAxis tick={AX} tickLine={false} axisLine={false} width={48} />
          <Tooltip {...TT} cursor={{ fill: "rgba(42,120,214,.06)" }} formatter={(v, n) => [`${fmt(Number(v))}${unit ? ` ${unit}` : ""}`, String(n)]}
                   labelFormatter={(l) => (xFmt ? xFmt(String(l)) : String(l))} />
          {keys.length > 1 && <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 12.5, paddingTop: 6 }} />}
          {keys.map((k, i) => (
            <Bar key={k.key} dataKey={k.key} name={k.name} fill={k.color} stackId={stacked ? "s" : undefined}
                 radius={stacked ? (i === keys.length - 1 ? [4, 4, 0, 0] : 0) : [4, 4, 0, 0]} maxBarSize={30} animationDuration={900} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Vành khuyên + chú giải có số và tỷ lệ (nhận diện không chỉ dựa vào màu). */
export function Donut({ data, center, unit }: { data: { ten: string; so: number; color: string }[]; center: string; unit: string }) {
  const total = data.reduce((a, b) => a + b.so, 0);
  const shown = data.filter((d) => d.so > 0);
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div className="relative h-[190px] w-[190px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={shown} dataKey="so" nameKey="ten" innerRadius={58} outerRadius={88} paddingAngle={shown.length > 1 ? 2 : 0} stroke="var(--be-mat)" strokeWidth={2} animationDuration={900}>
              {shown.map((d) => <Cell key={d.ten} fill={d.color} />)}
            </Pie>
            <Tooltip {...TT} formatter={(v, n) => [`${fmt(Number(v))} ${unit}`, String(n)]} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[24px] font-extrabold leading-none text-muc tabular-nums">{center}</span>
          <span className="mt-1 text-[12px] text-muc-nhat">{unit}</span>
        </div>
      </div>
      <ul className="w-full min-w-0 flex-1 space-y-2">
        {data.map((d) => (
          <li key={d.ten} className="flex items-start gap-2 text-[13px]">
            <span aria-hidden className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: d.color }} />
            <span className="min-w-0 flex-1 leading-snug text-muc">{d.ten}</span>
            <span className="font-bold text-muc tabular-nums">{fmt(d.so)}</span>
            <span className="w-12 text-right text-muc-nhat tabular-nums">{total ? `${fmt((d.so * 100) / total, 0)}%` : ""}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Thanh tiến độ ngang có nhãn — dùng cho danh sách ngắn (độ phủ, tiến độ). */
export function Meter({ label, pct, sub, color = C.blue }: { label: string; pct: number | null; sub?: string; color?: string }) {
  const w = pct === null ? 0 : Math.max(0, Math.min(100, pct));
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2 text-[12.5px]">
        <span className="min-w-0 truncate font-semibold text-muc">{label}</span>
        <span className="shrink-0 font-bold text-muc tabular-nums">{pct === null ? L("Đang cập nhật", "Pending") : `${fmt(pct, 1)}%`}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-[var(--be-mat-2)]" role="progressbar" aria-label={label} aria-valuenow={w} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full transition-[width] duration-1000 ease-out" style={{ width: `${w}%`, background: `linear-gradient(90deg, color-mix(in srgb, ${color} 70%, white), ${color})` }} />
      </div>
      {sub && <p className="mt-1 text-[11.5px] text-muc-nhat">{sub}</p>}
    </div>
  );
}
