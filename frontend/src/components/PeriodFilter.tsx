import { formatPeriod } from "@/lib/format";
import { monthOptions, usePeriod } from "@/lib/period";

export function PeriodFilter() {
  const { ky, setKy } = usePeriod();
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muc-nhat">Kỳ báo cáo</span>
      <select value={ky} onChange={(e) => setKy(e.target.value)} className="o-nhap w-auto py-1.5">
        {monthOptions().map((m) => <option key={m} value={m}>{formatPeriod(m)}</option>)}
      </select>
    </label>
  );
}
