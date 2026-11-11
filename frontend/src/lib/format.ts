const nf = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 });

/** Thiếu số liệu → "—". Không bao giờ đổi thành 0. */
export function formatNumber(v: number | null | undefined, digits?: number): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (digits !== undefined) return new Intl.NumberFormat("vi-VN", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(v);
  return nf.format(v);
}

export function formatMoney(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (Math.abs(v) >= 1e9) return `${formatNumber(v / 1e9, 1)} tỷ`;
  if (Math.abs(v) >= 1e6) return `${formatNumber(v / 1e6, 0)} triệu`;
  return formatNumber(v);
}

const ROMAN = ["", "I", "II", "III", "IV"];

export function formatPeriod(ky: string): string {
  let m = ky.match(/^(\d{4})-Q([1-4])$/);
  if (m) return `Quý ${ROMAN[Number(m[2])]}/${m[1]}`;
  m = ky.match(/^(\d{4})-(\d{2})$/);
  if (m) return `Tháng ${Number(m[2])}/${m[1]}`;
  m = ky.match(/^(\d{4})-W(\d{2})$/);
  if (m) return `Tuần ${Number(m[2])}/${m[1]}`;
  if (/^\d{4}$/.test(ky)) return `Năm ${ky}`;
  return ky;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function currentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}
