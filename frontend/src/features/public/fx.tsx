import { useEffect, useRef, useState, type ReactNode } from "react";
import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from "recharts";
import { L, n } from "./i18n";

const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** true khi phần tử đã vào khung nhìn (một lần). Không có IntersectionObserver (máy in, test) → hiện ngay. */
export function useInView<T extends Element>(margin = "0px 0px -60px 0px"): [React.RefObject<T>, boolean] {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(() => typeof IntersectionObserver === "undefined");
  useEffect(() => {
    if (seen || !ref.current) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { rootMargin: margin });
    io.observe(ref.current);
    const print = () => setSeen(true); // in/lưu PDF: dựng mọi biểu đồ chưa cuộn tới
    window.addEventListener("beforeprint", print);
    return () => { io.disconnect(); window.removeEventListener("beforeprint", print); };
  }, [seen, margin]);
  return [ref, seen];
}

/** Hiện dần + trượt lên khi cuộn tới; `lazy` = chỉ dựng nội dung (biểu đồ) khi đã thấy để hiệu ứng vẽ chạy đúng lúc. */
export function Reveal({ children, delay = 0, lazy = false, minH, className = "" }: { children: ReactNode; delay?: number; lazy?: boolean; minH?: number; className?: string }) {
  const [ref, seen] = useInView<HTMLDivElement>();
  return (
    <div ref={ref} className={`hien-dan ${seen ? "da-hien" : ""} ${className}`} style={{ transitionDelay: `${delay}ms`, minHeight: lazy && !seen ? minH : undefined }}>
      {!lazy || seen ? children : null}
    </div>
  );
}

/** Số chạy từ 0 tới giá trị khi xuất hiện. */
export function CountUp({ value, digits, suffix = "", ms = 1100 }: { value: number | null | undefined; digits?: number; suffix?: string; ms?: number }) {
  const [ref, seen] = useInView<HTMLSpanElement>();
  const d = digits ?? (value !== null && value !== undefined && (Number.isInteger(value) || Math.abs(value) >= 100) ? 0 : 1);
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!seen || value === null || value === undefined) return;
    if (reduced()) { setV(value); return; }
    let raf = 0; const t0 = performance.now();
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / ms);
      setV(value * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [seen, value, ms]);
  if (value === null || value === undefined) return <span ref={ref}>—</span>;
  const shown = typeof IntersectionObserver === "undefined" ? value : v;
  return <span ref={ref} className="tabular-nums">{n(shown, d)}{suffix}</span>;
}

/** Đồng hồ tròn phần trăm (0–100), màu theo ngưỡng do nơi gọi chọn. */
export function Gauge({ pct, label, sub, color }: { pct: number | null; label: string; sub?: string; color: string }) {
  const [ref, seen] = useInView<HTMLDivElement>();
  const v = pct === null ? 0 : Math.max(0, Math.min(100, pct));
  return (
    <div ref={ref} className="flex flex-col items-center text-center">
      <div className="relative h-[120px] w-[120px]">
        {seen && (
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart innerRadius="78%" outerRadius="100%" data={[{ v }]} startAngle={225} endAngle={-45} barSize={12}>
              <PolarAngleAxis type="number" domain={[0, 100]} tick={false} angleAxisId={0} />
              <RadialBar dataKey="v" cornerRadius={8} fill={color} background={{ fill: "rgba(255,255,255,.12)" }} angleAxisId={0} isAnimationActive={!reduced()} animationDuration={1200} />
            </RadialBarChart>
          </ResponsiveContainer>
        )}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[24px] font-extrabold leading-none text-white">{pct === null ? "—" : <CountUp value={pct} digits={1} />}</span>
          {pct !== null && <span className="text-[11px] font-bold text-white/70">%</span>}
        </div>
      </div>
      <p className="mt-1 text-[13px] font-bold leading-snug text-white">{label}</p>
      {sub && <p className="text-[11.5px] text-white/65">{sub}</p>}
    </div>
  );
}

/** Dải tin nổi bật chạy ngang (dừng khi rê chuột; tắt chạy khi người dùng giảm chuyển động). */
export function Marquee({ items }: { items: { text: string; tone?: "tot" | "canh_bao" | "thuong" }[] }) {
  if (!items.length) return null;
  const dot = { tot: "#4ade80", canh_bao: "#fbbf24", thuong: "#93c5fd" };
  const row = (hidden: boolean) => (
    <ul className="flex shrink-0 items-center gap-8 pr-8" aria-hidden={hidden || undefined}>
      {items.map((x, i) => (
        <li key={i} className="flex items-center gap-2 whitespace-nowrap text-[13px] font-semibold text-white/90">
          <span className="h-2 w-2 rounded-full" style={{ background: dot[x.tone ?? "thuong"], boxShadow: `0 0 10px ${dot[x.tone ?? "thuong"]}` }} />{x.text}
        </li>
      ))}
    </ul>
  );
  return (
    <div className="chay-ngang group relative overflow-hidden border-y border-white/10 bg-black/20 py-2.5" aria-label={L("Điểm tin số liệu", "Data highlights")}>
      <div className="chay-ngang-noi flex w-max group-hover:[animation-play-state:paused]">{row(false)}{row(true)}</div>
    </div>
  );
}
