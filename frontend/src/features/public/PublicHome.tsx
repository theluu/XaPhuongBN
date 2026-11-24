import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import QRCode from "qrcode";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LogIn, Printer, Share2, X } from "lucide-react";
import { api } from "@/lib/api";
import { C, Card, Section, fmt } from "./charts";
import { CountUp, Gauge, Marquee, Reveal } from "./fx";
import { LangProvider, L, d as dl, date, dateTime, ind, n, period, t, unit, useLang } from "./i18n";
import { BanDo, ChiDao, CongTrinh, DanCu, DauTuCong, DichVuCong, KtxhCharts, NganSach, PhanAnh, PhucVu, ktxhCsv, type ChuyenMuc, type Diem, type PubCard } from "./sections";

/* ───────── Kiểu dữ liệu trang công khai ───────── */
export interface WardCard { id: number; ten: string; cap: string; slug: string | null; ten_mien: string[]; ten_co_quan: string[]; logo_url: string | null }
interface Snapshot {
  ky: string; gioi_thieu: string; tong_hop: PubCard[]; chi_tieu: PubCard[]; chuyen_muc?: ChuyenMuc; diem?: Diem[];
  ban_do?: { tam?: [number, number]; zoom?: number; tile_url?: string };
  thong_ke: { so_chi_tieu: number; da_xac_nhan: number; dat: number; nguy_co: number }; co_minh_hoa: boolean;
}
interface BanOut { id: number; ky: string; cong_bo_luc: string; nguoi_cong_bo: string; thong_ke: Snapshot["thong_ke"] | null; co_minh_hoa: boolean }
interface WardPage { don_vi: WardCard; ky_da_cong_bo: string[]; ban: (BanOut & { du_lieu: Snapshot }) | null }
interface WardListItem extends WardCard { ban_moi_nhat: BanOut | null; noi_bat: PubCard[] }
interface CompareRow { ten: string; slug: string; ky: string; chi_tieu_dat_pct: number | null; thu_ns_pct: number | null; giai_ngan_pct: number | null;
  tthc_dung_han_pct: number | null; pakn_dung_han_pct: number | null; dan_so: number | null; phuc_vu_diem: number | null; co_minh_hoa: boolean }

const ST: Record<string, { vi: string; en: string; color: string }> = {
  dat: { vi: "Đạt", en: "On target", color: "var(--xac-nhan)" },
  nguy_co: { vi: "Cần nỗ lực", en: "Needs effort", color: "var(--tam-thoi)" },
  chua_du_du_lieu: { vi: "Theo dõi", en: "Monitoring", color: "var(--muc-nhat)" },
  theo_doi: { vi: "Theo dõi", en: "Monitoring", color: "var(--muc-nhat)" },
  dang_cap_nhat: { vi: "Đang cập nhật", en: "Pending", color: "var(--thieu)" },
};
const ACCENT = ["#1d4ed8", "#0f766e", "#9f2026", "#a16207", "#6d28d9", "#0e7490"];

export function useHostWard() {
  return useQuery({ queryKey: ["cong-khai", "xac-dinh"], queryFn: () => api<{ don_vi: WardCard | null }>("/api/cong-khai/xac-dinh"), staleTime: Infinity });
}

/** Trang chủ khi chưa đăng nhập: tên miền phường → trang công khai của phường; tên miền chung → danh sách phường. */
export function PublicHome() {
  return <LangProvider><PublicInner /></LangProvider>;
}
function PublicInner() {
  const { slug } = useParams();
  const host = useHostWard();
  if (slug) return <WardPublic slug={slug} />;
  if (host.isLoading) return <Loading />;
  if (host.data?.don_vi?.slug) return <WardPublic slug={host.data.don_vi.slug} />;
  return <WardList />;
}
const Loading = () => <div className="flex min-h-screen items-center justify-center bg-nen text-muc-nhat" role="status">{t("Đang tải…")}</div>;

/* ───────── Đầu trang kiểu cổng thông tin điện tử cơ quan nhà nước ───────── */
function TrongDong({ className = "" }: { className?: string }) {
  const rays = Array.from({ length: 14 }, (_, i) => i * (360 / 14));
  return (
    <svg viewBox="-100 -100 200 200" aria-hidden className={className}>
      <g fill="none" stroke="currentColor">
        {[96, 86, 74, 62, 50, 38, 26].map((r, i) => <circle key={r} r={r} strokeWidth={i % 2 ? 0.8 : 1.6} strokeDasharray={i % 3 === 1 ? "2 3" : undefined} />)}
        {rays.map((a) => <path key={a} d="M0 -20 L4 -8 L0 -12 L-4 -8 Z" transform={`rotate(${a})`} fill="currentColor" />)}
        <polygon points="0,-16 4,-5 15,-5 6,2 9,13 0,6 -9,13 -6,2 -15,-5 -4,-5" fill="currentColor" />
        {Array.from({ length: 24 }, (_, i) => <circle key={i} r={2.2} cx={0} cy={-80} transform={`rotate(${i * 15})`} fill="currentColor" />)}
      </g>
    </svg>
  );
}

function Flag() {
  return (
    <svg viewBox="0 0 300 200" aria-hidden className="la-co h-full w-auto drop-shadow-[0_6px_12px_rgba(159,32,38,.35)]">
      <defs>
        <linearGradient id="co-bong" x1="0" x2="1">
          <stop offset="0" stopColor="#fff" stopOpacity=".0" /><stop offset=".35" stopColor="#fff" stopOpacity=".18" /><stop offset=".55" stopColor="#000" stopOpacity=".12" /><stop offset="1" stopColor="#fff" stopOpacity=".08" />
        </linearGradient>
      </defs>
      <path className="la-co-vai" d="M10 20 C 80 0, 150 40, 290 15 L 290 185 C 150 210, 80 170, 10 190 Z" fill="#da251d" />
      <polygon points="150,55 162,93 202,93 170,117 182,155 150,131 118,155 130,117 98,93 138,93" fill="#ffde00" />
      <path d="M10 20 C 80 0, 150 40, 290 15 L 290 185 C 150 210, 80 170, 10 190 Z" fill="url(#co-bong)" />
    </svg>
  );
}

export function LangSwitch({ dark = false }: { dark?: boolean }) {
  const { lang, setLang } = useLang();
  const base = dark ? "text-white/70 hover:text-white" : "text-[#7a1a1a]/70 hover:text-[#b91c1c]";
  return (
    <div role="group" aria-label="Ngôn ngữ / Language" className={`inline-flex overflow-hidden rounded-full border ${dark ? "border-white/30" : "border-[#b91c1c]/30"} text-[12px] font-bold`}>
      {(["vi", "en"] as const).map((l) => (
        <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)}
                className={`px-2.5 py-1 ${lang === l ? "bg-[#b91c1c] text-white" : base}`}>{l === "vi" ? "VI" : "EN"}</button>
      ))}
    </div>
  );
}

function PortalHeader({ line1, line2, logo, nav, back, onShare }: {
  line1: string; line2: string; logo?: string | null; nav: { id: string; ten: string }[]; back?: boolean; onShare?: () => void;
}) {
  const today = new Date();
  const dateText = L(`Hôm nay, ngày ${today.getDate()} tháng ${today.getMonth() + 1} năm ${today.getFullYear()}`,
    today.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" }));
  return (
    <header className="khong-in-nen relative z-30">
      <div className="relative overflow-hidden bg-[linear-gradient(180deg,#fffaf1_0%,#fff3e1_100%)]">
        <TrongDong className="pointer-events-none absolute -left-24 top-1/2 h-[340px] w-[340px] -translate-y-1/2 text-[#e8b98a] opacity-40 sm:left-10" />
        <TrongDong className="pointer-events-none absolute left-1/2 top-1/2 hidden h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 text-[#f1caa0] opacity-25 lg:block" />
        <div className="relative mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 sm:gap-5 sm:px-8 sm:py-4">
          <img src={logo ?? "/brand/quoc-huy.svg"} alt={L("Quốc huy nước Cộng hòa xã hội chủ nghĩa Việt Nam", "National emblem of Viet Nam")} className="h-14 w-auto shrink-0 drop-shadow sm:h-20 lg:h-24" />
          <div className="min-w-0 flex-1">
            <p className="font-serif-gov text-[11px] font-bold uppercase tracking-[0.12em] text-[#b91c1c] sm:text-[15px] lg:text-[18px]">{L("Cổng số liệu công khai", "Open Data Portal")}</p>
            <p className="font-serif-gov text-[15px] font-bold uppercase leading-tight text-[#c8102e] [text-shadow:0_1px_0_#fff] sm:text-[24px] lg:text-[30px]">{line1}</p>
            {line2 && <p className="mt-0.5 truncate text-[10.5px] font-bold uppercase tracking-[0.1em] text-[#7a1a1a] sm:text-[12.5px]">{line2}</p>}
          </div>
          <div className="hidden h-20 shrink-0 md:block lg:h-24"><Flag /></div>
        </div>
      </div>
      <nav aria-label={L("Điều hướng chính", "Main navigation")} className="sticky top-0 z-40 bg-[linear-gradient(180deg,#d0121b_0%,#a50e15_100%)] shadow-[0_3px_10px_rgba(120,10,15,.35)]">
        <div className="mx-auto flex max-w-6xl items-center gap-1 px-2 sm:px-6">
          <div className="flex min-w-0 flex-1 overflow-x-auto [mask-image:linear-gradient(90deg,#000_88%,transparent)] [scrollbar-width:none]">
            {back && <Link to="/" className="nav-gov">{t("Các phường")}</Link>}
            <a href="#noi-dung" className="nav-gov">{t("Trang chủ")}</a>
            {nav.map((a) => <a key={a.id} href={`#${a.id}`} className="nav-gov">{a.ten}</a>)}
          </div>
          <div className="flex shrink-0 items-center gap-1.5 py-1.5 pl-2">
            {onShare && (
              <button type="button" onClick={onShare} className="khong-in grid h-8 w-8 place-items-center rounded-full text-white hover:bg-white/15" aria-label={t("Chia sẻ")} title={t("Chia sẻ")}><Share2 size={16} /></button>
            )}
            <button type="button" onClick={() => window.print()} className="khong-in hidden h-8 w-8 place-items-center rounded-full text-white hover:bg-white/15 sm:grid" aria-label={t("In / Lưu PDF")} title={t("In / Lưu PDF")}><Printer size={16} /></button>
            <LangSwitch dark />
            <Link to="/dang-nhap" className="khong-in inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1.5 text-[12.5px] font-bold text-[#a50e15] shadow hover:bg-[#fff3e1]">
              <LogIn size={14} aria-hidden /><span className="hidden sm:inline">{t("Đăng nhập")}</span><span className="sr-only sm:hidden">{t("Đăng nhập")}</span>
            </Link>
          </div>
        </div>
      </nav>
      <div className="border-b border-[#f0d9bf] bg-[#fffaf3]">
        <p className="mx-auto max-w-6xl px-4 py-1.5 text-[12px] italic text-[#7a1a1a] sm:px-8">{dateText}</p>
      </div>
    </header>
  );
}

const HERO = "relative overflow-hidden bg-[linear-gradient(115deg,#0f2a4d_0%,#0c2242_55%,#2a1d3d_100%)] text-white";
const Stripe = () => <div aria-hidden className="flex h-[3px]"><div className="w-[62%] bg-nhan-dien" /><div className="flex-1 bg-[var(--vang)]" /></div>;

function Value({ c, big }: { c: PubCard; big?: boolean }) {
  if (c.thuc_hien === null) return <span className={`${big ? "text-[22px]" : "text-[18px]"} font-bold text-muc-nhat`}>{t("Đang cập nhật")}</span>;
  const digits = Number.isInteger(c.thuc_hien) || Math.abs(c.thuc_hien) >= 100 ? 0 : 1;
  return (
    <span className="flex items-baseline gap-1.5">
      <span className={`${big ? "text-[30px] sm:text-[34px]" : "text-[24px]"} font-extrabold leading-none tracking-tight text-muc tabular-nums`}>{big ? <CountUp value={c.thuc_hien} digits={digits} /> : n(c.thuc_hien, digits)}</span>
      <span className="text-[13px] font-semibold text-muc-nhat">{unit(c.don_vi)}</span>
    </span>
  );
}

function Pill({ status }: { status: string }) {
  const s = ST[status] ?? ST.theo_doi;
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[11.5px] font-bold" style={{ color: s.color, background: `color-mix(in srgb, ${s.color} 11%, transparent)` }}>
      <span aria-hidden className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />{L(s.vi, s.en)}
    </span>
  );
}

/** ▲▼ so với kỳ trước và cùng kỳ (chỉ khi cả hai số đều đã xác nhận). */
function Deltas({ c }: { c: PubCard }) {
  if (!c.so_sanh || c.thuc_hien === null) return null;
  const items = ([["ky_truoc", "so với kỳ trước"], ["cung_ky", "so với cùng kỳ"]] as const)
    .map(([k, label]) => ({ label, v: c.so_sanh?.[k].gia_tri, ky: c.so_sanh?.[k].ky }))
    .filter((x) => x.v !== null && x.v !== undefined && x.v !== 0);
  if (!items.length) return null;
  const good = (dv: number) => (c.chieu === "giam_tot" ? dv <= 0 : dv >= 0);
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11.5px]">
      {items.map((x) => {
        const dv = (c.thuc_hien as number) - (x.v as number);
        const p = (dv * 100) / Math.abs(x.v as number);
        return (
          <span key={x.label} title={`${period(x.ky ?? "")}: ${n(x.v)}`} className={good(dv) ? "text-[#15803d]" : "text-[#dc2626]"}>
            <b>{dv >= 0 ? "▲" : "▼"} {n(Math.abs(p), 1)}%</b> <span className="text-muc-nhat">{t(x.label)}</span>
          </span>
        );
      })}
    </div>
  );
}

function KpiCard({ c, i }: { c: PubCard; i: number }) {
  const a = ACCENT[i % ACCENT.length];
  return (
    <Reveal delay={i * 80} className="h-full">
      <div className="khu the-noi relative flex h-full flex-col gap-2 overflow-hidden p-4 pt-5" style={{ background: `linear-gradient(140deg, color-mix(in srgb, ${a} 10%, var(--be-mat)) 0%, var(--be-mat) 65%)` }}>
        <div aria-hidden className="absolute inset-x-0 top-0 h-1" style={{ background: a }} />
        <p className="text-[13px] font-semibold leading-snug text-muc-nhat">{dl(c.ten)}</p>
        <Value c={c} big />
        {c.ghi_chu && c.thuc_hien !== null && <p className="text-[12px] text-muc-nhat">{L(c.ghi_chu, "")}</p>}
        {c.ky_so_lieu && c.thuc_hien !== null && <p className="text-[12px] italic text-muc-nhat">{L("Số liệu", "Figures for")} {period(c.ky_so_lieu)}</p>}
        <div className="mt-auto pt-1"><Pill status={c.status} /></div>
      </div>
    </Reveal>
  );
}

/** Bảng chi tiết chỉ tiêu: lọc theo lĩnh vực; máy tính = hàng bảng, điện thoại/máy tính bảng = thẻ xếp dọc (không ô trống). */
function IndicatorTable({ cards, groups }: { cards: PubCard[]; groups: [string, PubCard[]][] }) {
  const [g, setG] = useState<string>("*");
  const rows = g === "*" ? cards : cards.filter((c) => c.ten_phan_he === g);
  const tabs: [string, string, number][] = [["*", L("Tất cả", "All"), cards.length], ...groups.map(([k, cs]) => [k, dl(k), cs.length] as [string, string, number])];
  const ref = (c: PubCard) => c.ke_hoach ?? c.muc_so_sanh ?? c.muc_tieu;
  return (
    <Reveal className="khu overflow-hidden">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-[var(--vien)] p-4 sm:px-5">
        <h3 className="the-tieu-de mr-auto text-[15.5px] font-extrabold text-muc">{t("Chi tiết")} {cards.length} {unit("chỉ tiêu")}</h3>
        <div role="tablist" aria-label={L("Lọc theo lĩnh vực", "Filter by area")} className="-mx-1 flex max-w-full gap-1.5 overflow-x-auto px-1 pb-0.5 [scrollbar-width:none]">
          {tabs.map(([k, ten, nn]) => (
            <button key={k} role="tab" type="button" aria-selected={g === k} onClick={() => setG(k)}
                    className={`shrink-0 rounded-full border px-3 py-1 text-[12.5px] font-semibold transition ${g === k ? "border-[#a50e15] bg-[#a50e15] text-white" : "border-[var(--vien-dam)] bg-[var(--be-mat)] text-muc hover:border-[#a50e15]"}`}>
              {ten} <span className={g === k ? "text-white/80" : "text-muc-nhat"}>({nn})</span>
            </button>
          ))}
        </div>
      </div>
      <div className="hidden grid-cols-[minmax(0,2.3fr)_120px_120px_minmax(0,1.5fr)_118px] gap-4 bg-[var(--be-mat-2)] px-5 py-2.5 text-[11.5px] font-bold uppercase tracking-wider text-muc-nhat lg:grid" aria-hidden>
        <span>{L("Chỉ tiêu", "Indicator")}</span><span className="text-right">{L("Thực hiện", "Actual")}</span><span className="text-right">{t("Mục tiêu")}</span>
        <span>{L("Tiến độ · so sánh", "Progress · comparison")}</span><span>{L("Đánh giá", "Status")}</span>
      </div>
      <ul className="divide-y divide-[var(--vien)]">
        {rows.map((c, i) => {
          const r = ref(c);
          const p = c.hoan_thanh_pct === null ? null : Math.max(0, Math.min(100, c.hoan_thanh_pct));
          const s = ST[c.status] ?? ST.theo_doi;
          return (
            <li key={c.ma} className="hien-dan da-hien grid gap-x-4 gap-y-2 px-4 py-3.5 transition-colors hover:bg-[color-mix(in_srgb,var(--chinh)_3%,transparent)] sm:px-5 lg:grid-cols-[minmax(0,2.3fr)_120px_120px_minmax(0,1.5fr)_118px] lg:items-center"
                style={{ transitionDelay: `${Math.min(i, 12) * 25}ms` }}>
              <div className="flex min-w-0 items-start gap-2.5">
                <span aria-hidden className="mt-1 h-8 w-1 shrink-0 rounded-full" style={{ background: s.color }} />
                <div className="min-w-0 flex-1">
                  <p className="text-[14px] font-semibold leading-snug text-muc">{ind(c.ma, c.ten)}</p>
                  <p className="mt-0.5 text-[11.5px] leading-snug text-muc-nhat">
                    {g === "*" && <span className="font-semibold">{dl(c.ten_phan_he)} · </span>}{t("Nguồn")}: {c.nguon || c.don_vi_cung_cap || "UBND"}{c.thoi_diem_chot ? ` · ${t("chốt")} ${date(c.thoi_diem_chot)}` : ""}
                  </p>
                </div>
                <span className="lg:hidden"><Pill status={c.status} /></span>
              </div>
              <div className="grid grid-cols-2 gap-3 pl-3.5 lg:contents">
                <div className="lg:text-right">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muc-nhat lg:hidden">{L("Thực hiện", "Actual")}</p>
                  {c.thuc_hien === null ? <p className="text-[14px] font-semibold text-muc-nhat">{t("Đang cập nhật")}</p>
                    : <p className="text-[18px] font-extrabold leading-tight text-muc tabular-nums">{n(c.thuc_hien, Number.isInteger(c.thuc_hien) || Math.abs(c.thuc_hien) >= 100 ? 0 : 1)} <span className="text-[12px] font-semibold text-muc-nhat">{unit(c.don_vi)}</span></p>}
                </div>
                <div className="lg:text-right">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muc-nhat lg:hidden">{t("Mục tiêu")}</p>
                  <p className="text-[14px] font-semibold text-muc tabular-nums">{r === null ? "—" : <>{n(r)} <span className="text-[12px] text-muc-nhat">{unit(c.don_vi)}</span></>}</p>
                </div>
              </div>
              <div className="min-w-0 pl-3.5 lg:pl-0">
                {p !== null ? (
                  <div className="flex items-center gap-2">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-[var(--be-mat-2)]" role="progressbar" aria-valuenow={p} aria-valuemin={0} aria-valuemax={100} aria-label={`${t("Mức hoàn thành")} ${ind(c.ma, c.ten)}`}>
                      <div className="h-full rounded-full" style={{ width: `${p}%`, background: `linear-gradient(90deg, color-mix(in srgb, ${s.color} 65%, white), ${s.color})` }} />
                    </div>
                    <span className="w-14 shrink-0 text-right text-[12.5px] font-bold text-muc tabular-nums">{n(c.hoan_thanh_pct, 1)}%</span>
                  </div>
                ) : <p className="text-[12px] text-muc-nhat">{c.thuc_hien === null ? L("Chờ số liệu được xác nhận", "Awaiting confirmed data") : L("Chỉ tiêu theo dõi, không đặt mục tiêu", "Monitored, no target set")}</p>}
                <div className="mt-1"><Deltas c={c} /></div>
              </div>
              <div className="hidden lg:block"><Pill status={c.status} /></div>
            </li>
          );
        })}
      </ul>
    </Reveal>
  );
}

function DemoBadge() {
  return <span className="inline-flex items-center rounded-full bg-[var(--vang)] px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-[#3b2a00]">{t("Bản demo · số liệu minh họa")}</span>;
}

function Footer({ lines }: { lines: string[] }) {
  return (
    <footer className="mt-12 bg-[linear-gradient(180deg,#a50e15_0%,#7f0b10_100%)] text-white/85">
      <div aria-hidden className="h-1 bg-[var(--vang)]" />
      <div className="mx-auto grid max-w-6xl gap-4 px-5 py-7 text-[13px] sm:grid-cols-[1fr_auto] sm:items-center sm:px-8">
        <div className="flex items-start gap-3">
          <img src="/brand/quoc-huy.svg" alt="" className="h-12 w-auto" />
          <div>
            <p className="font-bold uppercase text-white">{lines[0]}</p>
            <p className="mt-1 max-w-3xl">{t("Số liệu trên trang do đơn vị xác nhận và công bố theo kỳ. Thông tin nội bộ chỉ xem được khi đăng nhập.")}</p>
          </div>
        </div>
        <Link to="/dang-nhap" className="khong-in shrink-0 rounded-full border border-white/40 px-4 py-2 text-center font-semibold text-white hover:bg-white/10">{t("Đăng nhập hệ thống")}</Link>
      </div>
    </footer>
  );
}

/* ───────── Chia sẻ: mã QR, sao chép liên kết, Facebook ───────── */
function ShareDialog({ open, onOpenChange, title }: { open: boolean; onOpenChange: (o: boolean) => void; title: string }) {
  const url = typeof window !== "undefined" ? window.location.href.split("#")[0] : "";
  const [qr, setQr] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => { if (open) QRCode.toDataURL(url, { width: 480, margin: 1, color: { dark: "#7f0b10", light: "#ffffff" } }).then(setQr).catch(() => setQr(null)); }, [open, url]);
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px]" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,380px)] -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-[var(--be-mat)] p-5 shadow-2xl">
          <div className="mb-3 flex items-center gap-2">
            <Dialog.Title className="flex-1 text-[17px] font-extrabold text-muc">{t("Chia sẻ")}</Dialog.Title>
            <Dialog.Close className="grid h-8 w-8 place-items-center rounded-full hover:bg-[var(--be-mat-2)]" aria-label={t("Đóng")}><X size={18} /></Dialog.Close>
          </div>
          <Dialog.Description className="mb-3 text-[13px] text-muc-nhat">{title}</Dialog.Description>
          <div className="mx-auto w-56 rounded-xl border-4 border-[#a50e15] bg-white p-2">
            {qr ? <img src={qr} alt={t("Quét mã để mở trang trên điện thoại")} className="h-auto w-full" /> : <div className="aspect-square animate-pulse bg-[var(--be-mat-2)]" />}
          </div>
          <p className="mt-2 text-center text-[12.5px] text-muc-nhat">{t("Quét mã để mở trang trên điện thoại")}</p>
          <div className="mt-4 flex gap-2">
            <input readOnly value={url} className="o-nhap min-w-0 flex-1 text-[12.5px]" aria-label="URL" onFocus={(e) => e.currentTarget.select()} />
            <button type="button" className="btn-chinh shrink-0" onClick={() => navigator.clipboard?.writeText(url).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); })}>
              {copied ? t("Đã sao chép") : t("Sao chép liên kết")}
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {qr && <a href={qr} download="ma-qr-cong-so-lieu.png" className="btn-phu flex-1">{L("Tải mã QR", "Download QR")}</a>}
            <a href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`} target="_blank" rel="noreferrer" className="btn-phu flex-1">Facebook</a>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/* ───────── Trang công khai của một phường ───────── */
function WardPublic({ slug }: { slug: string }) {
  const [ky, setKy] = useState<string | undefined>();
  const [share, setShare] = useState(false);
  const q = useQuery({ queryKey: ["cong-khai", slug, ky], queryFn: () => api<WardPage>(`/api/cong-khai/${encodeURIComponent(slug)}`, { params: { ky } }), retry: 1,
    staleTime: 0, refetchOnMount: "always", refetchOnWindowFocus: true, refetchInterval: 5 * 60_000 });
  const host = useHostWard();
  const onMain = !host.data?.don_vi;
  const snap = q.data?.ban?.du_lieu;
  const cm: ChuyenMuc = snap?.chuyen_muc ?? {};
  const groups = useMemo(() => {
    const m = new Map<string, PubCard[]>();
    for (const c of snap?.chi_tieu ?? []) m.set(c.ten_phan_he, [...(m.get(c.ten_phan_he) ?? []), c]);
    return [...m.entries()];
  }, [snap]);
  useEffect(() => {
    if (q.data?.don_vi) document.title = `${L("Cổng số liệu công khai", "Open Data Portal")} – ${q.data.don_vi.ten}`;
  }, [q.data]);

  if (q.isLoading) return <Loading />;
  if (q.isError || !q.data) {
    const notFound = (q.error as { status?: number } | null)?.status === 404;
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-nen p-8 text-center" role="alert">
        <p className="text-lg font-bold text-muc">{notFound ? t("Không tìm thấy trang công khai của đơn vị") : t("Không tải được dữ liệu. Vui lòng thử lại.")}</p>
        <div className="flex gap-2">
          {!notFound && <button type="button" className="btn-chinh px-4 py-2" onClick={() => q.refetch()}>{t("Thử lại")}</button>}
          <Link to="/" className="btn-phu px-4 py-2">{t("Về trang chủ")}</Link>
        </div>
      </div>
    );
  }
  const w = q.data.don_vi;
  const ban = q.data.ban;
  const anchors = [
    ...(snap?.tong_hop.length ? [{ id: "tong-hop", ten: t("Tổng hợp") }] : []),
    ...(snap?.chi_tieu.length ? [{ id: "ktxh", ten: t("Kinh tế – xã hội") }] : []),
    ...(cm.chi_dao ? [{ id: "chi-dao", ten: t("Chỉ đạo – điều hành") }] : []),
    ...(cm.phuc_vu ? [{ id: "phuc-vu", ten: t("Chỉ số phục vụ") }] : []),
    ...(cm.ngan_sach ? [{ id: "ngan-sach", ten: t("Ngân sách") }] : []),
    ...(cm.dich_vu_cong ? [{ id: "dich-vu-cong", ten: t("Dịch vụ công") }] : []),
    ...(cm.phan_anh ? [{ id: "phan-anh", ten: t("Phản ánh kiến nghị") }] : []),
    ...(cm.dau_tu_cong ? [{ id: "dau-tu-cong", ten: t("Đầu tư công") }] : []),
    ...(cm.cong_trinh ? [{ id: "cong-trinh", ten: t("Công trình") }] : []),
    ...(cm.dan_cu ? [{ id: "dan-cu", ten: t("Dân cư") }] : []),
    ...(snap?.ban_do?.tam ? [{ id: "ban-do", ten: t("Bản đồ") }] : []),
  ];
  const datCount = snap?.chi_tieu.filter((c) => c.status === "dat").length ?? 0;
  const gauges = snap ? [
    { label: t("Chỉ tiêu đạt kế hoạch"), pct: snap.chi_tieu.length ? (datCount * 100) / snap.chi_tieu.length : null, sub: `${datCount}/${snap.chi_tieu.length} ${unit("chỉ tiêu")}`, color: "#4ade80" },
    ...(cm.ngan_sach ? [{ label: t("Thu NSNN / dự toán"), pct: cm.ngan_sach.thu_dia_ban.ty_le_pct, sub: L(`Lũy kế ${period(cm.ngan_sach.ky)}`, `YTD ${period(cm.ngan_sach.ky)}`), color: "#60a5fa" }] : []),
    ...(cm.dau_tu_cong ? [{ label: t("Giải ngân đầu tư công"), pct: cm.dau_tu_cong.ty_le_pct, sub: `${cm.dau_tu_cong.so_du_an} ${unit("dự án")}`, color: "#fbbf24" }] : []),
    ...(cm.dich_vu_cong ? [{ label: t("Hồ sơ TTHC đúng hạn"), pct: cm.dich_vu_cong.tong.dung_han_pct, sub: `${n(cm.dich_vu_cong.tong.tiep_nhan, 0)} ${unit("hồ sơ")}`, color: "#34d399" }] : []),
    ...(cm.phan_anh ? [{ label: t("Phản ánh xử lý đúng hạn"), pct: cm.phan_anh.ty_le_dung_han_pct, sub: `${cm.phan_anh.tong} ${unit("phản ánh")}`, color: "#c4b5fd" }] : []),
    ...(cm.phuc_vu ? [{ label: L("Điểm phục vụ người dân", "Service index score"), pct: (cm.phuc_vu.tong_diem * 100) / (cm.phuc_vu.toi_da || 100), sub: cm.phuc_vu.xep_hang ? L(`Xếp hạng #${cm.phuc_vu.xep_hang}`, `Rank #${cm.phuc_vu.xep_hang}`) : period(cm.phuc_vu.ky), color: "#f9a8d4" }] : []),
  ] : [];
  const tin: { text: string; tone?: "tot" | "canh_bao" | "thuong" }[] = [];
  if (snap) {
    for (const c of snap.chi_tieu.filter((x) => x.status === "dat" && x.hoan_thanh_pct !== null).slice(0, 4)) tin.push({ text: `${ind(c.ma, c.ten)}: ${n(c.thuc_hien, Number.isInteger(c.thuc_hien) ? 0 : 1)} ${unit(c.don_vi)} — ${L("đạt", "")} ${n(c.hoan_thanh_pct, 1)}% ${L("kế hoạch", "of target")}`, tone: "tot" });
    if (cm.ngan_sach) tin.push({ text: L(`Thu NSNN trên địa bàn lũy kế ${period(cm.ngan_sach.ky)}: ${n(cm.ngan_sach.thu_dia_ban.thuc_hien)} tỷ đồng (${n(cm.ngan_sach.thu_dia_ban.ty_le_pct, 1)}% dự toán)`, `State revenue YTD ${period(cm.ngan_sach.ky)}: VND ${n(cm.ngan_sach.thu_dia_ban.thuc_hien)} bn (${n(cm.ngan_sach.thu_dia_ban.ty_le_pct, 1)}% of budget)`) });
    if (cm.phuc_vu) tin.push({ text: L(`Chỉ số phục vụ người dân ${period(cm.phuc_vu.ky)}: ${n(cm.phuc_vu.tong_diem, 1)}/${n(cm.phuc_vu.toi_da, 0)} điểm`, `Service index ${period(cm.phuc_vu.ky)}: ${n(cm.phuc_vu.tong_diem, 1)}/${n(cm.phuc_vu.toi_da, 0)} points`), tone: "tot" });
    if (cm.dich_vu_cong) tin.push({ text: L(`${n(cm.dich_vu_cong.tong.tiep_nhan, 0)} hồ sơ TTHC tiếp nhận, ${n(cm.dich_vu_cong.tong.dung_han_pct, 1)}% giải quyết đúng hạn`, `${n(cm.dich_vu_cong.tong.tiep_nhan, 0)} applications received, ${n(cm.dich_vu_cong.tong.dung_han_pct, 1)}% resolved on time`), tone: "tot" });
    if (cm.chi_dao) tin.push({ text: L(`${cm.chi_dao.hoan_thanh}/${cm.chi_dao.da_giao} việc lãnh đạo giao đã hoàn thành`, `${cm.chi_dao.hoan_thanh}/${cm.chi_dao.da_giao} assigned tasks completed`) });
    if (cm.dau_tu_cong) tin.push({ text: L(`Giải ngân đầu tư công đạt ${n(cm.dau_tu_cong.ty_le_pct, 1)}% kế hoạch vốn ${n(cm.dau_tu_cong.ke_hoach_von)} tỷ đồng`, `Public investment disbursed ${n(cm.dau_tu_cong.ty_le_pct, 1)}% of VND ${n(cm.dau_tu_cong.ke_hoach_von)} bn plan`) });
    if (cm.phan_anh) tin.push({ text: L(`${cm.phan_anh.tong} phản ánh của người dân, mức hài lòng ${n(cm.phan_anh.hai_long_tb, 1)}/5`, `${cm.phan_anh.tong} citizen reports, satisfaction ${n(cm.phan_anh.hai_long_tb, 1)}/5`) });
    if (cm.dan_cu) tin.push({ text: L(`Dân số ${n(cm.dan_cu.tong_dan_so, 0)} người, ${n(cm.dan_cu.so_ho, 0)} hộ`, `Population ${n(cm.dan_cu.tong_dan_so, 0)}, ${n(cm.dan_cu.so_ho, 0)} households`) });
    for (const c of snap.chi_tieu.filter((x) => x.status === "nguy_co").slice(0, 2)) tin.push({ text: `${t("Cần nỗ lực")}: ${ind(c.ma, c.ten)} (${n(c.hoan_thanh_pct, 1)}%)`, tone: "canh_bao" });
  }
  const kys = q.data.ky_da_cong_bo;
  const kyGroups = [
    { label: L("Theo tháng", "Monthly"), items: kys.filter((k) => /^\d{4}-\d{2}$/.test(k)) },
    { label: L("Theo quý", "Quarterly"), items: kys.filter((k) => /-Q\d$/.test(k)) },
    { label: L("Theo năm", "Yearly"), items: kys.filter((k) => /^\d{4}$/.test(k)) },
  ].filter((g) => g.items.length);

  return (
    <div className="flex min-h-screen flex-col bg-nen">
      <a href="#noi-dung" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:font-bold focus:text-[#a50e15] focus:shadow-lg">{t("Bỏ qua đến nội dung chính")}</a>
      <PortalHeader line1={w.ten_co_quan[0] ?? w.ten} line2={w.ten_co_quan[1] ?? ""} logo={w.logo_url} nav={anchors} back={onMain} onShare={() => setShare(true)} />
      <ShareDialog open={share} onOpenChange={setShare} title={`${t("Cổng số liệu công khai")} – ${w.ten}`} />

      <section className={`${HERO} pb-0`} id="noi-dung" tabIndex={-1}>
        <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="hao-quang absolute -left-24 top-10 h-80 w-80 rounded-full bg-[#2a78d6] opacity-50 blur-[90px]" />
          <div className="hao-quang absolute -right-16 top-40 h-96 w-96 rounded-full bg-[#9f2026] opacity-40 blur-[110px]" style={{ animationDelay: "-6s" }} />
          <div className="absolute inset-0 bg-[radial-gradient(rgba(255,255,255,.07)_1px,transparent_1px)] [background-size:22px_22px]" />
        </div>
        <Stripe />
        <div className="relative mx-auto max-w-6xl px-5 pt-7 sm:px-8">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[11.5px] font-bold uppercase tracking-[0.16em] text-white/70">{t("Cổng số liệu công khai")}</p>
            {ban?.co_minh_hoa && <DemoBadge />}
          </div>
          <h1 className="mt-2 text-[30px] font-extrabold leading-[1.1] tracking-tight sm:text-[44px]">{w.ten}</h1>
          {snap?.gioi_thieu && <p className="mt-3 max-w-3xl text-[14.5px] leading-relaxed text-white/80">{L(snap.gioi_thieu, "Socio-economic, budget, public investment and public service figures confirmed and published by the ward People's Committee every period.")}</p>}
          {ban && (
            <div className="mt-6 flex flex-wrap items-end gap-x-6 gap-y-3">
              <label className="text-[12px] font-semibold uppercase tracking-wider text-white/70">{t("Kỳ công bố")}
                <select className="mt-1 block rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-[14px] font-bold normal-case tracking-normal text-white"
                        value={ky ?? ban.ky} onChange={(e) => setKy(e.target.value)}>
                  {kyGroups.map((g) => (
                    <optgroup key={g.label} label={g.label} className="text-muc">
                      {g.items.map((k) => <option key={k} value={k} className="text-muc">{period(k)}</option>)}
                    </optgroup>
                  ))}
                </select>
              </label>
              <div className="text-[13px]">
                <p className="flex items-center gap-2 font-semibold text-white" aria-live="polite">
                  <span aria-hidden className="relative flex h-2.5 w-2.5"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#4ade80] opacity-70 motion-reduce:hidden" /><span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#4ade80]" /></span>
                  {L("Dữ liệu mới nhất · cập nhật lúc", "Latest data · updated at")} {dateTime(new Date(q.dataUpdatedAt || Date.now()).toISOString())}
                </p>
                <p className="mt-0.5 text-[12px] text-white/60">{L(`Số liệu kỳ ${period(ban.ky)} được công bố ${dateTime(ban.cong_bo_luc)}`, `${period(ban.ky)} figures published ${dateTime(ban.cong_bo_luc)}`)}{ban.nguoi_cong_bo ? ` · ${ban.nguoi_cong_bo}` : ""}</p>
              </div>
            </div>
          )}
          {snap && (
            <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {([[t("Chỉ tiêu công khai"), snap.thong_ke.so_chi_tieu], [t("Đã xác nhận"), snap.thong_ke.da_xac_nhan], [t("Đạt kế hoạch"), snap.thong_ke.dat], [t("Cần nỗ lực"), snap.thong_ke.nguy_co]] as const).map(([k, v]) => (
                <div key={k} className="rounded-xl border border-white/10 bg-white/[0.06] px-4 py-3">
                  <dt className="text-[12px] font-semibold text-white/70">{k}</dt>
                  <dd className="mt-0.5 text-[26px] font-extrabold tabular-nums"><CountUp value={Number(v)} digits={0} /></dd>
                </div>
              ))}
            </dl>
          )}
          {gauges.length > 0 && (
            <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.05] p-4 backdrop-blur-sm sm:p-5">
              <p className="mb-3 text-[11.5px] font-bold uppercase tracking-[0.16em] text-white/70">{t("Chỉ số điều hành chính")}</p>
              <div className="grid grid-cols-2 gap-x-3 gap-y-5 sm:grid-cols-3 lg:grid-cols-6">
                {gauges.map((g) => <Gauge key={g.label} pct={g.pct} label={g.label} sub={g.sub} color={g.color} />)}
              </div>
            </div>
          )}
        </div>
        <div className="relative mt-8 khong-in"><Marquee items={tin} /></div>
      </section>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pt-8 sm:px-8">
        {!ban || !snap ? (
          <div className="khu p-8 text-center">
            <p className="text-lg font-bold text-muc">{t("Đơn vị chưa công bố số liệu kỳ nào")}</p>
            <p className="mt-1 text-muc-nhat">{t("Số liệu sẽ hiển thị sau khi lãnh đạo đơn vị xác nhận và công bố.")}</p>
          </div>
        ) : (
          <div className="flex flex-col gap-12">
            {snap.tong_hop.length > 0 && (
              <Section id="tong-hop" title={t("Số liệu nổi bật")} desc={t("Các chỉ số tổng hợp chính của phường")} tag={period(snap.ky)}>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5 sm:max-lg:[&>*:last-child:nth-child(odd)]:col-span-2">{snap.tong_hop.map((c, i) => <KpiCard key={c.ma} c={c} i={i} />)}</div>
              </Section>
            )}
            {snap.chi_tieu.length > 0 && (
              <Section id="ktxh" title={`${t("Kinh tế – xã hội")} ${snap.ky.slice(0, 4)}`} desc={L("Tiến độ và mức độ hoàn thành các chỉ tiêu Nghị quyết, kế hoạch phát triển", "Progress and completion of resolution and development-plan targets")}
                       tag={period(snap.ky)} csv={() => ktxhCsv(snap.chi_tieu)}>
                <KtxhCharts cards={snap.chi_tieu} ky={snap.ky} />
                <IndicatorTable cards={snap.chi_tieu} groups={groups} />
              </Section>
            )}
            {cm.chi_dao && <ChiDao d={cm.chi_dao} />}
            {cm.phuc_vu && <PhucVu d={cm.phuc_vu} />}
            {cm.ngan_sach && <NganSach d={cm.ngan_sach} />}
            {cm.dich_vu_cong && <DichVuCong d={cm.dich_vu_cong} />}
            {cm.phan_anh && <PhanAnh d={cm.phan_anh} />}
            {cm.dau_tu_cong && <DauTuCong d={cm.dau_tu_cong} ky={snap.ky} />}
            {cm.cong_trinh && <CongTrinh d={cm.cong_trinh} />}
            {cm.dan_cu && <DanCu d={cm.dan_cu} />}
            {snap.ban_do?.tam && <BanDo cm={cm} diem={snap.diem ?? []} center={snap.ban_do.tam} zoom={snap.ban_do.zoom} tileUrl={snap.ban_do.tile_url} />}
            <p className="text-[12.5px] text-muc-nhat">{t("Chỉ số chưa được xác nhận trong kỳ hiển thị “Đang cập nhật”. Số liệu chính thức theo văn bản báo cáo của UBND phường.")}</p>
          </div>
        )}
      </main>
      <Footer lines={w.ten_co_quan} />
    </div>
  );
}

/** Môi trường thật (HTTPS) → mở tên miền riêng của phường; máy phát triển → đường dẫn /p/<mã>. */
function wardHref(w: WardCard): string {
  return w.ten_mien[0] && window.location.protocol === "https:" ? `https://${w.ten_mien[0]}` : `/p/${w.slug}`;
}

/* ───────── Tên miền chung: danh sách phường + so sánh ───────── */
function Compare({ rows }: { rows: CompareRow[] }) {
  if (rows.length < 2) return null;
  const metrics = [
    { key: "chi_tieu_dat_pct", ten: t("Chỉ tiêu đạt") }, { key: "thu_ns_pct", ten: t("Thu NS / dự toán") }, { key: "giai_ngan_pct", ten: t("Giải ngân") },
    { key: "tthc_dung_han_pct", ten: t("TTHC đúng hạn") }, { key: "pakn_dung_han_pct", ten: t("PAKN đúng hạn") }, { key: "phuc_vu_diem", ten: t("Điểm phục vụ") },
  ] as const;
  const data = metrics.map((m) => ({ ten: m.ten, ...Object.fromEntries(rows.map((r) => [r.ten, r[m.key]])) }));
  const colors = [C.blue, C.orange, C.aqua, C.violet, C.yellow];
  return (
    <Section id="so-sanh" title={t("So sánh các phường")} desc={t("Bản công bố mới nhất của từng phường")}
             csv={() => [[t("Phường"), t("Kỳ"), ...metrics.map((m) => m.ten), t("Dân số")], ...rows.map((r) => [r.ten, r.ky, ...metrics.map((m) => r[m.key]), r.dan_so])]}>
      <Card title={L("Các chỉ số chính (%, điểm)", "Key measures (%, points)")} unit="%">
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }} barCategoryGap="22%">
              <CartesianGrid stroke="var(--vien)" vertical={false} />
              <XAxis dataKey="ten" tick={{ fontSize: 11.5, fill: "var(--muc-nhat)" }} tickLine={false} interval={0} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11.5, fill: "var(--muc-nhat)" }} tickLine={false} axisLine={false} width={40} />
              <Tooltip contentStyle={{ borderRadius: 10, fontSize: 13 }} formatter={(v, nm) => [fmt(Number(v), 1), String(nm)]} />
              <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 12.5 }} />
              {rows.map((r, i) => <Bar key={r.slug} dataKey={r.ten} fill={colors[i % colors.length]} radius={[4, 4, 0, 0]} maxBarSize={26} animationDuration={900} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <Reveal className="khu overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-[13.5px]">
          <thead><tr>{[t("Phường"), t("Kỳ"), ...metrics.map((m) => m.ten), t("Dân số")].map((h) => <th key={h} className="px-3 py-2.5">{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.slug} className="border-t border-[var(--vien)]">
                <td className="px-3 py-2.5 font-bold text-muc"><a href={wardHref({ ...r, id: 0, cap: "", ten_mien: [], ten_co_quan: [], logo_url: null })} className="hover:text-[var(--chinh)]">{r.ten}</a></td>
                <td className="px-3 py-2.5 text-muc-nhat">{period(r.ky)}</td>
                {metrics.map((m) => <td key={m.key} className="px-3 py-2.5 tabular-nums">{fmt(r[m.key], 1)}</td>)}
                <td className="px-3 py-2.5 tabular-nums">{fmt(r.dan_so, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Reveal>
    </Section>
  );
}

function WardList() {
  const q = useQuery({ queryKey: ["cong-khai", "ds"], queryFn: () => api<{ don_vi: WardListItem[]; so_sanh?: CompareRow[] }>("/api/cong-khai") });
  const [share, setShare] = useState(false);
  const lines = [L("Nền tảng điều hành số xã, phường", "Digital governance platform for communes and wards"), L("Trung tâm điều hành thông minh", "Intelligent operations centre")];
  useEffect(() => { document.title = t("Cổng số liệu công khai các xã, phường"); }, []);
  const ds = q.data?.don_vi ?? [];
  return (
    <div className="flex min-h-screen flex-col bg-nen">
      <a href="#noi-dung" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:font-bold focus:text-[#a50e15] focus:shadow-lg">{t("Bỏ qua đến nội dung chính")}</a>
      <PortalHeader line1={lines[0]} line2={lines[1]} nav={[{ id: "cac-phuong", ten: t("Các phường") }, ...((q.data?.so_sanh?.length ?? 0) > 1 ? [{ id: "so-sanh", ten: t("So sánh các phường") }] : [])]} onShare={() => setShare(true)} />
      <ShareDialog open={share} onOpenChange={setShare} title={t("Cổng số liệu công khai các xã, phường")} />
      <section className={`${HERO} pb-28 sm:pb-32`} id="noi-dung" tabIndex={-1}>
        <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="hao-quang absolute -left-24 top-10 h-80 w-80 rounded-full bg-[#2a78d6] opacity-50 blur-[90px]" />
          <div className="hao-quang absolute -right-16 top-24 h-96 w-96 rounded-full bg-[#9f2026] opacity-40 blur-[110px]" style={{ animationDelay: "-6s" }} />
        </div>
        <Stripe />
        <div className="relative mx-auto max-w-6xl px-5 pt-8 sm:px-8">
          <p className="text-[11.5px] font-bold uppercase tracking-[0.16em] text-white/70">{t("Cổng số liệu công khai các xã, phường")}</p>
          <h1 className="mt-3 max-w-3xl text-[32px] font-extrabold leading-[1.08] tracking-tight sm:text-[48px]">
            {t("Số liệu đã xác nhận.")}<br /><span className="text-[var(--vang)]">{t("Công khai theo kỳ.")}</span>
          </h1>
          <p className="mt-4 max-w-2xl text-[14.5px] leading-relaxed text-white/80 sm:text-[16px]">{t("Mỗi phường có trang riêng, hiển thị các chỉ tiêu lãnh đạo phường đã duyệt công khai. Cán bộ đăng nhập để vào hệ thống điều hành nội bộ.")}</p>
        </div>
      </section>
      <main className="relative z-10 mx-auto -mt-20 flex w-full max-w-6xl flex-1 flex-col gap-12 px-4 sm:-mt-24 sm:px-8">
        {q.isLoading ? <div className="khu p-6 text-muc-nhat">{t("Đang tải…")}</div> : q.isError ? (
          <div className="khu flex flex-wrap items-center gap-3 p-6" role="alert"><span className="text-muc">{t("Không tải được dữ liệu. Vui lòng thử lại.")}</span>
            <button type="button" className="btn-chinh" onClick={() => q.refetch()}>{t("Thử lại")}</button></div>
        ) : (
          <div id="cac-phuong" className="grid scroll-mt-16 grid-cols-1 gap-4 md:grid-cols-2">
            {ds.map((w, i) => (
              <Reveal key={w.id} delay={i * 90}>
                <a href={wardHref(w)} className="khu the-noi group flex h-full flex-col gap-4 p-5 sm:p-6">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <img src={w.logo_url ?? "/brand/quoc-huy.svg"} alt="" className="h-12 w-auto shrink-0" />
                      <div className="min-w-0">
                        <p className="chu-nho-hoa">{w.ban_moi_nhat ? `${t("Đã công bố")} ${period(w.ban_moi_nhat.ky)}` : t("Chưa công bố")}</p>
                        <h2 className="mt-0.5 text-[22px] font-extrabold text-muc">{w.ten}</h2>
                        {w.ten_mien[0] && <p className="truncate text-[12.5px] text-muc-nhat">{w.ten_mien[0]}</p>}
                      </div>
                    </div>
                    {w.ban_moi_nhat?.co_minh_hoa && <DemoBadge />}
                  </div>
                  {w.noi_bat.length > 0 && (
                    <dl className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                      {w.noi_bat.map((c) => (
                        <div key={c.ma} className="rounded-xl bg-[var(--be-mat-2)] px-3 py-2.5">
                          <dt className="line-clamp-2 text-[12px] font-semibold text-muc-nhat">{dl(c.ten)}</dt>
                          <dd className="mt-1 text-[18px] font-extrabold text-muc tabular-nums">{c.thuc_hien === null ? "—" : `${fmt(c.thuc_hien)} ${unit(c.don_vi)}`}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  <span className="mt-auto text-[14px] font-bold text-[var(--chinh)]">{t("Xem trang công khai")} <span aria-hidden className="inline-block transition group-hover:translate-x-1">→</span></span>
                </a>
              </Reveal>
            ))}
          </div>
        )}
        <Compare rows={q.data?.so_sanh ?? []} />
      </main>
      <Footer lines={lines} />
    </div>
  );
}
