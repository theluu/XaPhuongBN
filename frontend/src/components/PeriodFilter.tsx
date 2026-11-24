import { formatPeriod } from "@/lib/format";
import { monthOptions, usePeriod } from "@/lib/period";

/** Bộ lọc thời gian trên thanh đầu trang (nền navy). */
export function PeriodFilter({ onDark = false }: { onDark?: boolean }) {
  const { ky, setKy } = usePeriod();
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className={onDark ? "text-white/75" : "text-muc-nhat"}>Kỳ báo cáo</span>
      <select value={ky} onChange={(e) => setKy(e.target.value)} className="o-nhap w-auto py-1 text-muc">
        {monthOptions().map((m) => <option key={m} value={m}>{formatPeriod(m)}</option>)}
      </select>
    </label>
  );
}
