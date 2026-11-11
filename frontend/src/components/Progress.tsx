/** Thanh tiến độ thực hiện so với mốc (kế hoạch kỳ). Thiếu số → vân gạch, không vẽ 0. */
export function Progress({ value, mark, max, label }: { value: number | null; mark?: number | null; max: number | null; label: string }) {
  if (value === null || !max) return <div className="is-missing h-2.5 rounded-full" role="img" aria-label={`${label}: chưa có số liệu`} />;
  const pct = Math.min(100, (value * 100) / max);
  const mk = mark ? Math.min(100, (mark * 100) / max) : null;
  const behind = mark !== null && mark !== undefined && value < mark;
  return (
    <div className="relative h-2.5 rounded-full bg-nen" role="img" aria-label={label}>
      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: behind ? "var(--tam-thoi)" : "var(--xac-nhan)" }} />
      {mk !== null && <div className="absolute -top-1 h-[18px] w-0.5 bg-muc" style={{ left: `${mk}%` }} title="Mốc kế hoạch kỳ" />}
    </div>
  );
}
