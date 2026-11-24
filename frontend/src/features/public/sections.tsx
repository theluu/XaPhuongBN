import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CircleMarker, MapContainer, Tooltip as MapTip } from "react-leaflet";
import { AlertTriangle, Award, Banknote, Building2, CheckCircle2, ClipboardList, Clock, Coins, Database, FileCheck2, FileInput, Globe, HardHat, Home, Landmark,
  ListChecks, MessageSquare, PiggyBank, Smile, Target, TrendingUp, Trophy, Users, Wallet } from "lucide-react";
import { MapTiles } from "@/components/MapTiles";
import { Reveal } from "./fx";
import { C, Card, Donut, HBars, Kpis, Meter, SERIES, STATUS_C, Section, VBars, fmt } from "./charts";
import { L, d as dl, date, ind, monthTick as T, n, period, unit } from "./i18n";

/* ───────── Kiểu dữ liệu chuyên mục (khớp backend cong_khai/service.py) ───────── */
interface Tot { du_toan: number | null; thuc_hien: number | null; ty_le_pct: number | null }
interface Co { ten: string; thuc_hien: number | null; du_toan: number | null; ty_le_pct: number | null }
interface TthcRow { tiep_nhan: number; giai_quyet: number; dung_han: number; qua_han: number; truc_tuyen: number; dung_han_pct: number | null; truc_tuyen_pct: number | null }
interface Cnt { ma?: string | number; ten: string; so: number }
export interface ChuyenMuc {
  chi_dao?: { tong_van_de: number; da_giao: number; hoan_thanh: number; qua_han: number; theo_trang_thai: Cnt[]; theo_linh_vuc: Cnt[]; theo_muc_do: Cnt[];
    theo_don_vi: { ten: string; hoan_thanh: number; dang_xu_ly: number; qua_han: number }[];
    nhiem_vu_trong_tam: { ten: string; don_vi: string; trang_thai: string; so_chi_tieu: number; tien_do_pct: number | null }[] };
  phuc_vu?: { ky: string; tong_diem: number; toi_da: number; xep_hang: number | null; tong_don_vi: number | null; nguon: string;
    tieu_chi: { ten: string; diem: number; toi_da: number; ty_le_pct: number | null }[]; xu_huong: { ky: string; tong_diem: number }[] };
  ngan_sach?: { ky: string; thu_dia_ban: Tot; thu_ns_phuong: Tot; chi: Tot; co_cau_thu: Co[]; co_cau_chi: Co[]; xu_huong: { ky: string; thu: number | null; ke_hoach: number | null; chi: number | null }[] };
  dich_vu_cong?: { tu: string; den: string; tong: TthcRow; theo_thang: (TthcRow & { ky: string })[]; theo_bo_phan: (TthcRow & { ten: string })[]; co_so_tam_thoi: boolean };
  phan_anh?: { tu: string; den: string; tong: number; theo_trang_thai: Cnt[]; theo_linh_vuc: { ten: string; tong: number; qua_han: number }[];
    ty_le_dung_han_pct: number | null; ty_le_da_tra_loi_pct: number | null; hai_long_tb: number | null; hai_long?: Cnt[]; theo_tdp?: Cnt[] };
  dau_tu_cong?: { so_du_an: number; ke_hoach_von: number; giai_ngan: number; ty_le_pct: number | null;
    du_an: { ten: string; lop: number; lop_ten: string; chu_dau_tu: string; ke_hoach_von: number | null; giai_ngan: number | null; ty_le_pct: number | null; khoi_luong_pct: number | null;
      tong_muc_dt: number | null; ngay_ht: string | null; lat?: number | null; lng?: number | null }[] };
  cong_trinh?: { so_cong_trinh: number; dung_tien_do: number; cham: number; theo_loai: { ten: string; so: number }[];
    cong_trinh: { ten: string; loai: string; trang_thai: string; ke_hoach_pct: number | null; thuc_te_pct: number | null; ngay: string | null; ngay_ht: string | null; lat?: number | null; lng?: number | null }[] };
  dan_cu?: { ky: string; tong_dan_so: number; nam: number; nu: number; so_ho: number; thap_tuoi: { nhom_tuoi: string; nam: number | null; nu: number | null }[];
    bien_dong: { ky: string; dan_so: number | null; sinh: number | null; tu: number | null; chuyen_den: number | null; chuyen_di: number | null }[] };
}
export interface PubCard {
  ma: string; ten: string; phan_he: string | null; ten_phan_he: string; don_vi: string; ky: string; ke_hoach: number | null; muc_tieu: number | null;
  muc_so_sanh: number | null; thuc_hien: number | null; hoan_thanh_pct: number | null; status: string; nguon: string; don_vi_cung_cap: string;
  thoi_diem_chot: string | null; ghi_chu?: string; chieu?: string; da_xac_nhan: boolean; ky_so_lieu?: string | null;
  so_sanh?: { ky_truoc: { ky: string; gia_tri: number | null }; cung_ky: { ky: string; gia_tri: number | null } } | null;
}
export interface Diem { loai: string; ten: string; lat: number | null; lng: number | null }

const AX = { fontSize: 11.5, fill: "var(--muc-nhat)" };
const TT = { contentStyle: { borderRadius: 10, border: "1px solid var(--vien-dam)", fontSize: 13 } };
const range = (tu: string, den: string) => `${date(tu)} – ${date(den)}`;
const pct = (a: number, b: number) => (b ? (a * 100) / b : null);

/** Mức hoàn thành 5 nhóm (giống cách báo cáo của các phường). */
export function bucket(c: PubCard): { key: string; ten: string; color: string } {
  if (c.status === "dang_cap_nhat" || c.thuc_hien === null) return { key: "cho", ten: L("Chưa có số liệu kỳ này", "No data this period"), color: "#94a3b8" };
  if (c.status === "dat") return { key: "dat", ten: L("Đạt / vượt", "On / above target"), color: "#15803d" };
  const p = c.hoan_thanh_pct;
  if (p === null) return { key: "td", ten: L("Theo dõi (không đặt mục tiêu)", "Monitored (no target)"), color: C.blue };
  if (p >= 60) return { key: "60", ten: L("Đang thực hiện từ 60%", "In progress ≥ 60%"), color: "#65a30d" };
  if (p >= 40) return { key: "40", ten: L("Hoàn thành 40–59%", "Completion 40–59%"), color: "#d97706" };
  return { key: "0", ten: L("Hoàn thành dưới 40%", "Completion < 40%"), color: "#dc2626" };
}

/* ───────── Kinh tế – xã hội ───────── */
export function KtxhCharts({ cards, ky }: { cards: PubCard[]; ky: string }) {
  if (!cards.length) return null;
  const groups = [...new Set(cards.map((c) => c.ten_phan_he))];
  const by = (g: string) => cards.filter((c) => c.ten_phan_he === g);
  const avg = groups.map((g) => {
    const xs = by(g).map((c) => c.hoan_thanh_pct).filter((x): x is number => x !== null);
    return { ten: dl(g), value: xs.length ? Math.round((xs.reduce((a, b) => a + Math.min(b, 150), 0) / xs.length) * 10) / 10 : null };
  }).filter((x) => x.value !== null);
  const bs = cards.map(bucket);
  const kinds = [...new Map(bs.map((b) => [b.key, b])).values()];
  const order = ["dat", "60", "40", "0", "td", "cho"];
  kinds.sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key));
  const stack = groups.map((g) => {
    const row: Record<string, string | number> = { ten: dl(g) };
    for (const k of kinds) row[k.key] = by(g).filter((c) => bucket(c).key === k.key).length;
    return row;
  });
  const dat = bs.filter((b) => b.key === "dat").length;
  const tot = bs.filter((b) => b.key === "60").length;
  const xn = cards.filter((c) => c.da_xac_nhan).length;
  return (
    <>
      <Kpis items={[
        { label: L("Tổng số chỉ tiêu", "Total indicators"), num: cards.length, sub: L(`${groups.length} lĩnh vực`, `${groups.length} areas`), color: C.blue, icon: Target },
        { label: L("Đạt hoặc vượt", "On / above target"), value: `${dat}/${cards.length}`, sub: L(`${fmt(pct(dat, cards.length), 1)}% tổng số chỉ tiêu`, `${fmt(pct(dat, cards.length), 1)}% of all`), color: STATUS_C.dat, icon: CheckCircle2 },
        { label: L("Tiến độ từ 60%", "Progress ≥ 60%"), num: tot, sub: L("Chưa đạt nhưng đang đúng hướng", "Not yet met, on track"), color: "#65a30d", icon: TrendingUp },
        { label: L("Có số liệu xác nhận", "Confirmed data"), num: pct(xn, cards.length), digits: 1, suffix: "%", sub: L(`${xn}/${cards.length} chỉ tiêu kỳ ${period(ky)}`, `${xn}/${cards.length} indicators, ${period(ky)}`), color: C.violet, icon: Database },
      ]} />
      <div className="grid gap-4 lg:grid-cols-[1.25fr_1fr]">
        <Card title={L("Tiến độ trung bình theo lĩnh vực", "Average progress by area")} desc={L("Mức hoàn thành bình quân của các chỉ tiêu có số liệu", "Mean completion of indicators with data")} unit="%">
          <HBars data={avg} keys={[{ key: "value", name: L("Hoàn thành bình quân", "Mean completion"), color: C.blue }]} unit="%" />
        </Card>
        <Card title={L("Cơ cấu mức hoàn thành", "Completion structure")} desc={L("Phân nhóm toàn bộ chỉ tiêu theo tiến độ", "All indicators grouped by progress")} unit={`${cards.length} ${unit("chỉ tiêu")}`}>
          <Donut center={String(cards.length)} unit={unit("chỉ tiêu")} data={kinds.map((k) => ({ ten: k.ten, so: bs.filter((b) => b.key === k.key).length, color: k.color }))} />
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {avg.length >= 3 && (
          <Card title={L("Bức tranh hoàn thành theo lĩnh vực", "Completion profile by area")} desc={L("Mức hoàn thành bình quân (%) — càng phủ rộng càng tốt", "Mean completion (%) — wider is better")} unit="%">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={avg.map((a) => ({ ...a, value: Math.min(120, a.value ?? 0) }))} outerRadius="70%">
                  <PolarGrid stroke="var(--vien-dam)" />
                  <PolarAngleAxis dataKey="ten" tick={{ fontSize: 11.5, fill: "var(--muc)" }} />
                  <PolarRadiusAxis angle={90} domain={[0, 120]} tick={{ fontSize: 10, fill: "var(--muc-nhat)" }} />
                  <Radar name={L("Hoàn thành bình quân", "Mean completion")} dataKey="value" stroke={C.blue} fill={C.blue} fillOpacity={0.28} strokeWidth={2} dot={{ r: 3 }} animationDuration={900} />
                  <Tooltip {...TT} formatter={(v) => [`${fmt(Number(v), 1)}%`, L("Hoàn thành bình quân", "Mean completion")]} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        )}
        <Card title={L("Phân bổ tiến độ theo lĩnh vực", "Progress distribution by area")} desc={L("Số chỉ tiêu trong từng nhóm tiến độ", "Indicators per progress group")} unit={unit("chỉ tiêu")}>
          <HBars stacked data={stack} keys={kinds.map((k) => ({ key: k.key, name: k.ten, color: k.color }))} unit={unit("chỉ tiêu")} />
        </Card>
      </div>
      <Card title={L("Tỷ lệ có số liệu theo lĩnh vực", "Data coverage by area")} desc={L("Chỉ tiêu đã có số liệu được xác nhận trong kỳ", "Indicators with confirmed data this period")}>
        <div className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
          {groups.map((g, i) => {
            const t = by(g).length; const ok = by(g).filter((c) => c.da_xac_nhan).length;
            return <Meter key={g} label={dl(g)} pct={pct(ok, t)} sub={L(`${ok}/${t} chỉ tiêu có số liệu`, `${ok}/${t} with data`)} color={SERIES[i % SERIES.length]} />;
          })}
        </div>
      </Card>
    </>
  );
}
export const ktxhCsv = (cards: PubCard[]) => [
  [L("Mã", "Code"), L("Chỉ tiêu", "Indicator"), L("Lĩnh vực", "Area"), L("Kỳ", "Period"), L("Thực hiện", "Actual"), L("Đơn vị", "Unit"), L("Kế hoạch", "Plan"),
    L("Hoàn thành (%)", "Completion (%)"), L("Kỳ trước", "Previous"), L("Cùng kỳ", "Same period last year"), L("Nguồn", "Source")],
  ...cards.map((c) => [c.ma, ind(c.ma, c.ten), dl(c.ten_phan_he), c.ky, c.thuc_hien, unit(c.don_vi), c.ke_hoach ?? c.muc_so_sanh, c.hoan_thanh_pct,
    c.so_sanh?.ky_truoc.gia_tri, c.so_sanh?.cung_ky.gia_tri, c.nguon]),
];

/* ───────── Chỉ đạo – điều hành ───────── */
export function ChiDao({ d }: { d: NonNullable<ChuyenMuc["chi_dao"]> }) {
  const sc: Record<string, string> = { moi: C.yellow, da_giao: C.blue, dang_xu_ly: C.violet, gia_han: C.orange, hoan_thanh: C.aqua };
  const mc: Record<string, string> = { cao: C.red, trung_binh: C.yellow, thap: C.blue };
  return (
    <Section id="chi-dao" title={L("Chỉ đạo – điều hành", "Governance & directives")}
             desc={L("Vấn đề hệ thống tự phát hiện và việc lãnh đạo giao xử lý — chỉ công bố số lượng tổng hợp", "Issues detected and tasks assigned by leadership — aggregate counts only")}
             tag={L("Số liệu tổng hợp", "Aggregates")}
             csv={() => [[L("Đơn vị", "Unit"), L("Hoàn thành", "Completed"), L("Đang xử lý", "In progress"), L("Quá hạn", "Overdue")],
               ...d.theo_don_vi.map((x) => [dl(x.ten), x.hoan_thanh, x.dang_xu_ly, x.qua_han])]}>
      <Kpis items={[
        { label: L("Vấn đề được phát hiện", "Issues detected"), num: d.tong_van_de, color: C.blue, icon: ClipboardList },
        { label: L("Đã giao xử lý", "Assigned"), num: d.da_giao, color: C.violet, icon: ListChecks },
        { label: L("Hoàn thành", "Completed"), num: d.hoan_thanh, sub: d.da_giao ? L(`${fmt(pct(d.hoan_thanh, d.da_giao), 1)}% việc đã giao`, `${fmt(pct(d.hoan_thanh, d.da_giao), 1)}% of assigned`) : undefined, color: C.aqua, icon: CheckCircle2 },
        { label: L("Quá hạn", "Overdue"), num: d.qua_han, color: C.red, icon: AlertTriangle },
      ]} />
      <div className="grid gap-4 lg:grid-cols-[1fr_1.25fr]">
        <Card title={L("Cơ cấu trạng thái xử lý", "Status breakdown")} unit={`${d.tong_van_de} ${unit("vấn đề")}`}>
          <Donut center={String(d.tong_van_de)} unit={unit("vấn đề")} data={d.theo_trang_thai.map((x) => ({ ten: dl(x.ten), so: x.so, color: sc[String(x.ma)] ?? C.gray }))} />
        </Card>
        <Card title={L("Tiến độ theo đơn vị xử lý", "Progress by responsible unit")} desc={L("Hoàn thành, đang xử lý và quá hạn", "Completed, in progress and overdue")} unit={unit("nhiệm vụ")}>
          <HBars stacked data={d.theo_don_vi.map((x) => ({ ...x, ten: dl(x.ten) }))} unit={unit("nhiệm vụ")}
                 keys={[{ key: "hoan_thanh", name: L("Hoàn thành", "Completed"), color: C.aqua }, { key: "dang_xu_ly", name: L("Đang xử lý", "In progress"), color: C.blue },
                   { key: "qua_han", name: L("Quá hạn", "Overdue"), color: C.red }]} />
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={L("Vấn đề theo lĩnh vực", "Issues by area")} unit={unit("vấn đề")}>
          <HBars data={d.theo_linh_vuc.map((x) => ({ ten: dl(x.ten), so: x.so }))} keys={[{ key: "so", name: L("Vấn đề", "Issues"), color: C.violet }]} unit={unit("vấn đề")} />
        </Card>
        <Card title={L("Mức độ ưu tiên", "Priority level")} unit={unit("vấn đề")}>
          <Donut center={String(d.tong_van_de)} unit={unit("vấn đề")} data={d.theo_muc_do.map((x) => ({ ten: dl(x.ten), so: x.so, color: mc[String(x.ma)] ?? C.gray }))} />
        </Card>
      </div>
      {d.nhiem_vu_trong_tam.length > 0 && (
        <Card title={L("Nhiệm vụ, chương trình trọng tâm", "Key programmes")} desc={L("Tiến độ bình quân các chỉ tiêu gắn với từng nhiệm vụ", "Mean progress of linked indicators")}>
          <div className="grid gap-x-6 gap-y-4 md:grid-cols-2">
            {d.nhiem_vu_trong_tam.map((x, i) => <Meter key={x.ten} label={x.ten} pct={x.tien_do_pct} color={SERIES[i % SERIES.length]}
              sub={L(`${x.so_chi_tieu} chỉ tiêu${x.don_vi ? ` · ${x.don_vi}` : ""}`, `${x.so_chi_tieu} indicators${x.don_vi ? ` · ${x.don_vi}` : ""}`)} />)}
          </div>
        </Card>
      )}
    </Section>
  );
}

/* ───────── Bộ chỉ số phục vụ người dân ───────── */
export function PhucVu({ d }: { d: NonNullable<ChuyenMuc["phuc_vu"]> }) {
  return (
    <Section id="phuc-vu" title={L("Chỉ số phục vụ người dân, doanh nghiệp", "Citizen & business service index")}
             desc={L("Điểm thành phần và xu hướng chất lượng phục vụ (Bộ chỉ số theo Quyết định 766/QĐ-TTg)", "Component scores and trend (index under Decision 766/QĐ-TTg)")}
             tag={period(d.ky)} csv={() => [[L("Tiêu chí", "Criterion"), L("Điểm", "Score"), L("Tối đa", "Max"), "%"], ...d.tieu_chi.map((x) => [dl(x.ten), x.diem, x.toi_da, x.ty_le_pct])]}>
      <Kpis items={[
        { label: L("Tổng điểm", "Total score"), value: `${fmt(d.tong_diem, 1)}/${fmt(d.toi_da, 0)}`, color: C.blue, icon: Award },
        { label: L("Xếp hạng", "Ranking"), value: d.xep_hang ? `#${d.xep_hang}` : "—", sub: d.tong_don_vi ? L(`trên ${d.tong_don_vi} xã, phường`, `of ${d.tong_don_vi} communes/wards`) : undefined, color: C.yellow, icon: Trophy },
        { label: L("Số tiêu chí", "Criteria"), num: d.tieu_chi.length, color: C.violet, icon: ListChecks },
        { label: L("Tỷ lệ điểm đạt", "Score ratio"), num: pct(d.tong_diem, d.toi_da), digits: 1, suffix: "%", color: C.aqua, icon: Target },
      ]} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={L("Điểm theo tiêu chí", "Score by criterion")} desc={L("Tỷ lệ đạt so với điểm tối đa của từng tiêu chí", "Share of the maximum for each criterion")} unit="%">
          <HBars data={d.tieu_chi.map((x) => ({ ten: dl(x.ten), value: x.ty_le_pct }))} max={100} keys={[{ key: "value", name: L("Tỷ lệ đạt", "Achieved"), color: C.blue }]} unit="%" />
        </Card>
        <Card title={L("Xu hướng tổng điểm", "Total score trend")} unit={L("thang 100", "out of 100")}>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={d.xu_huong} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
                <defs><linearGradient id="g-pv" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.orange} stopOpacity={0.4} /><stop offset="100%" stopColor={C.orange} stopOpacity={0.02} /></linearGradient></defs>
                <CartesianGrid stroke="var(--vien)" vertical={false} />
                <XAxis dataKey="ky" tickFormatter={T} tick={AX} tickLine={false} />
                <YAxis tick={AX} tickLine={false} axisLine={false} width={40} domain={[(m: number) => Math.max(0, Math.floor(m - 5)), 100]} />
                <Tooltip {...TT} formatter={(v) => [fmt(Number(v), 1), L("Tổng điểm", "Total score")]} labelFormatter={(k) => period(String(k))} />
                <Area dataKey="tong_diem" stroke={C.orange} strokeWidth={2.5} fill="url(#g-pv)" dot={{ r: 3, fill: C.orange }} animationDuration={900} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
      <p className="text-[12px] text-muc-nhat">{L("Nguồn", "Source")}: {d.nguon}</p>
    </Section>
  );
}

/* ───────── Ngân sách ───────── */
function Delta({ cur, prev, label }: { cur: number | null | undefined; prev: number | null | undefined; label: string }) {
  if (cur === null || cur === undefined || prev === null || prev === undefined || !prev) return null;
  const p = ((cur - prev) * 100) / Math.abs(prev);
  const up = p >= 0;
  return <span className={`inline-flex items-center gap-0.5 font-bold ${up ? "text-[#15803d]" : "text-[#dc2626]"}`}>{up ? "▲" : "▼"} {fmt(Math.abs(p), 1)}% <span className="font-normal text-muc-nhat">{label}</span></span>;
}

export function NganSach({ d }: { d: NonNullable<ChuyenMuc["ngan_sach"]> }) {
  const co = (xs: Co[]) => xs.filter((x) => x.thuc_hien !== null).sort((a, b) => (b.thuc_hien ?? 0) - (a.thuc_hien ?? 0))
    .map((x) => ({ ten: dl(x.ten), thuc_hien: x.thuc_hien, con_lai: x.du_toan !== null && x.thuc_hien !== null ? Math.max(0, Math.round((x.du_toan - x.thuc_hien) * 100) / 100) : null }));
  const ty = unit("tỷ");
  const last = d.xu_huong.at(-1); const prev = d.xu_huong.at(-2);
  const mth = (a?: number | null, b?: number | null) => (a !== null && a !== undefined && b !== null && b !== undefined ? a - b : null);
  return (
    <Section id="ngan-sach" title={L("Thu – chi ngân sách", "Budget revenue & expenditure")} desc={L("Số liệu đã đối soát với Kho bạc Nhà nước, lũy kế từ đầu năm", "Reconciled with the State Treasury, year to date")}
             tag={L(`Lũy kế đến ${period(d.ky)}`, `YTD to ${period(d.ky)}`)}
             csv={() => [[L("Tháng", "Month"), L("Thu trên địa bàn (tỷ)", "Revenue (bn)"), L("Kế hoạch thu (tỷ)", "Revenue plan (bn)"), L("Chi (tỷ)", "Spending (bn)")],
               ...d.xu_huong.map((x) => [x.ky, x.thu, x.ke_hoach, x.chi])]}>
      <Kpis items={[
        { label: L("Thu NSNN trên địa bàn", "State revenue in ward"), num: d.thu_dia_ban.thuc_hien, suffix: ` ${ty}`, sub: L(`${fmt(d.thu_dia_ban.ty_le_pct, 1)}% dự toán ${fmt(d.thu_dia_ban.du_toan)} tỷ`, `${fmt(d.thu_dia_ban.ty_le_pct, 1)}% of ${fmt(d.thu_dia_ban.du_toan)} bn budget`), color: C.blue, icon: Landmark },
        { label: L("Thu ngân sách phường", "Ward budget revenue"), num: d.thu_ns_phuong.thuc_hien, suffix: ` ${ty}`, sub: L(`${fmt(d.thu_ns_phuong.ty_le_pct, 1)}% dự toán ${fmt(d.thu_ns_phuong.du_toan)} tỷ`, `${fmt(d.thu_ns_phuong.ty_le_pct, 1)}% of ${fmt(d.thu_ns_phuong.du_toan)} bn budget`), color: C.aqua, icon: PiggyBank },
        { label: L("Chi ngân sách phường", "Ward spending"), num: d.chi.thuc_hien, suffix: ` ${ty}`, sub: L(`${fmt(d.chi.ty_le_pct, 1)}% dự toán ${fmt(d.chi.du_toan)} tỷ`, `${fmt(d.chi.ty_le_pct, 1)}% of ${fmt(d.chi.du_toan)} bn budget`), color: C.orange, icon: Wallet },
        { label: L("Tỷ lệ thu đạt dự toán", "Revenue vs. budget"), num: d.thu_dia_ban.ty_le_pct, digits: 1, suffix: "%", sub: L("Thu trên địa bàn so với dự toán năm", "Ward revenue vs. annual budget"), color: C.violet, icon: TrendingUp },
      ]} />
      {last && prev && (
        <Reveal className="flex flex-wrap gap-x-6 gap-y-1 rounded-xl bg-[var(--be-mat)] px-4 py-2.5 text-[13px] shadow-[var(--bong-nho)]">
          <span className="font-semibold text-muc">{L(`Thu riêng ${period(last.ky)}`, `Revenue in ${period(last.ky)}`)}: {fmt(mth(last.thu, prev.thu))} {ty}</span>
          <Delta cur={mth(last.thu, prev.thu)} prev={d.xu_huong.length > 2 ? mth(prev.thu, d.xu_huong.at(-3)?.thu) : null} label={L("so với tháng trước", "vs. previous month")} />
          <span className="font-semibold text-muc">{L(`Chi riêng ${period(last.ky)}`, `Spending in ${period(last.ky)}`)}: {fmt(mth(last.chi, prev.chi))} {ty}</span>
        </Reveal>
      )}
      <Card title={L("Thu, chi theo tháng (lũy kế)", "Monthly revenue & spending (cumulative)")} desc={L("Thu trên địa bàn, chi ngân sách phường và kế hoạch thu theo tiến độ", "Ward revenue, ward spending and revenue plan")} unit={unit("tỷ đồng")}>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={d.xu_huong} margin={{ top: 8, right: 8, left: -8, bottom: 0 }} barGap={2}>
              <defs>
                <linearGradient id="g-thu" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.blue} /><stop offset="100%" stopColor={C.blue} stopOpacity={0.55} /></linearGradient>
                <linearGradient id="g-chi" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.orange} /><stop offset="100%" stopColor={C.orange} stopOpacity={0.55} /></linearGradient>
              </defs>
              <CartesianGrid stroke="var(--vien)" vertical={false} />
              <XAxis dataKey="ky" tickFormatter={T} tick={AX} tickLine={false} />
              <YAxis tick={AX} tickLine={false} axisLine={false} width={48} />
              <Tooltip {...TT} formatter={(v, nm) => [v === null || v === undefined ? "—" : `${fmt(Number(v))} ${ty}`, String(nm)]} labelFormatter={(k) => period(String(k))} />
              <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 12.5, paddingTop: 6 }} />
              <Bar name={L("Thu trên địa bàn", "Ward revenue")} dataKey="thu" fill="url(#g-thu)" radius={[4, 4, 0, 0]} maxBarSize={22} animationDuration={900} />
              <Bar name={L("Chi ngân sách phường", "Ward spending")} dataKey="chi" fill="url(#g-chi)" radius={[4, 4, 0, 0]} maxBarSize={22} animationDuration={900} />
              <Line name={L("Kế hoạch thu", "Revenue plan")} dataKey="ke_hoach" stroke={C.violet} strokeWidth={2} strokeDasharray="5 4" dot={false} animationDuration={900} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={L("Cơ cấu thu trên địa bàn", "Revenue structure")} desc={L("Đã thu và phần còn lại so với dự toán năm", "Collected vs. remaining annual budget")} unit={unit("tỷ đồng")}>
          <HBars stacked data={co(d.co_cau_thu)} keys={[{ key: "thuc_hien", name: L("Đã thu", "Collected"), color: C.blue }, { key: "con_lai", name: L("Còn lại theo dự toán", "Remaining"), color: "#cbd5e1" }]} unit={ty} />
        </Card>
        <Card title={L("Chi ngân sách theo nhóm", "Spending by group")} desc={L("Đã chi và phần còn lại so với dự toán năm", "Spent vs. remaining annual budget")} unit={unit("tỷ đồng")}>
          <HBars stacked data={co(d.co_cau_chi)} keys={[{ key: "thuc_hien", name: L("Đã chi", "Spent"), color: C.orange }, { key: "con_lai", name: L("Còn lại theo dự toán", "Remaining"), color: "#cbd5e1" }]} unit={ty} />
        </Card>
      </div>
    </Section>
  );
}

/* ───────── Dịch vụ công ───────── */
export function DichVuCong({ d }: { d: NonNullable<ChuyenMuc["dich_vu_cong"]> }) {
  const t = d.tong;
  const hs = unit("hồ sơ");
  return (
    <Section id="dich-vu-cong" title={L("Dịch vụ công", "Public services")} desc={L("Tiếp nhận và giải quyết hồ sơ thủ tục hành chính tại phường", "Administrative applications received and resolved")}
             tag={range(d.tu, d.den)}
             csv={() => [[L("Tháng", "Month"), L("Tiếp nhận", "Received"), L("Giải quyết", "Resolved"), L("Đúng hạn", "On time"), L("Quá hạn", "Overdue"), L("Trực tuyến", "Online")],
               ...d.theo_thang.map((x) => [x.ky, x.tiep_nhan, x.giai_quyet, x.dung_han, x.qua_han, x.truc_tuyen])]}>
      <Kpis items={[
        { label: L("Hồ sơ tiếp nhận", "Applications received"), num: t.tiep_nhan, color: C.blue, icon: FileInput },
        { label: L("Đã giải quyết", "Resolved"), num: t.giai_quyet, sub: L(`${fmt(pct(t.giai_quyet, t.tiep_nhan), 1)}% số tiếp nhận`, `${fmt(pct(t.giai_quyet, t.tiep_nhan), 1)}% of received`), color: C.aqua, icon: FileCheck2 },
        { label: L("Đúng hạn", "On time"), num: t.dung_han_pct, digits: 1, suffix: "%", sub: L(`${fmt(t.qua_han)} hồ sơ quá hạn`, `${fmt(t.qua_han)} overdue`), color: STATUS_C.dat, icon: Clock },
        { label: L("Nộp trực tuyến", "Submitted online"), num: t.truc_tuyen_pct, digits: 1, suffix: "%", sub: `${fmt(t.truc_tuyen)} ${hs}`, color: C.violet, icon: Globe },
      ]} />
      <div className="grid gap-4 lg:grid-cols-[1.25fr_1fr]">
        <Card title={L("Hồ sơ theo tháng", "Applications by month")} desc={L("Tiếp nhận và đã giải quyết", "Received and resolved")} unit={hs}>
          <VBars data={d.theo_thang} xKey="ky" xFmt={T} unit={hs} keys={[{ key: "tiep_nhan", name: L("Tiếp nhận", "Received"), color: C.blue }, { key: "giai_quyet", name: L("Đã giải quyết", "Resolved"), color: C.aqua }]} />
        </Card>
        <Card title={L("Hình thức nộp hồ sơ", "Submission channel")} unit={`${fmt(t.tiep_nhan)} ${hs}`}>
          <Donut center={`${fmt(t.truc_tuyen_pct, 0)}%`} unit={L("trực tuyến", "online")} data={[
            { ten: L("Nộp trực tuyến", "Online"), so: t.truc_tuyen, color: C.violet }, { ten: L("Nộp trực tiếp", "In person"), so: Math.max(0, t.tiep_nhan - t.truc_tuyen), color: C.yellow },
          ]} />
        </Card>
      </div>
      <Card title={L("Kết quả theo bộ phận giải quyết", "Results by processing unit")} desc={L("Hồ sơ đúng hạn, quá hạn và đang giải quyết", "On time, overdue and in progress")} unit={hs}>
        <HBars stacked data={d.theo_bo_phan.map((b) => ({ ten: dl(b.ten), dung_han: b.dung_han, qua_han: b.qua_han, dang: Math.max(0, b.tiep_nhan - b.giai_quyet) }))}
               keys={[{ key: "dung_han", name: L("Đúng hạn", "On time"), color: C.aqua }, { key: "qua_han", name: L("Quá hạn", "Overdue"), color: C.red }, { key: "dang", name: L("Đang giải quyết", "In progress"), color: C.blue }]} unit={hs} />
      </Card>
    </Section>
  );
}

/* ───────── Phản ánh kiến nghị ───────── */
export function PhanAnh({ d }: { d: NonNullable<ChuyenMuc["phan_anh"]> }) {
  const st = (m: string) => d.theo_trang_thai.find((x) => x.ma === m)?.so ?? 0;
  const color: Record<string, string> = { hoan_thanh: C.aqua, dang_xu_ly: C.blue, tiep_nhan: C.yellow, qua_han: C.red };
  const hl: Record<string, string> = { 5: "#15803d", 4: "#65a30d", 3: "#ca8a04", 2: "#ea580c", 1: "#dc2626", 0: "#64748b" };
  const pa = unit("phản ánh");
  return (
    <Section id="phan-anh" title={L("Phản ánh kiến nghị", "Citizen feedback")} desc={L("Tiếp nhận, xử lý phản ánh của người dân theo lĩnh vực và địa bàn", "Feedback received and handled, by area and neighbourhood")}
             tag={range(d.tu, d.den)}
             csv={() => [[L("Lĩnh vực", "Area"), L("Tổng", "Total"), L("Quá hạn", "Overdue")], ...d.theo_linh_vuc.map((x) => [dl(x.ten), x.tong, x.qua_han])]}>
      <Kpis items={[
        { label: L("Tổng phản ánh", "Total feedback"), num: d.tong, color: C.blue, icon: MessageSquare },
        { label: L("Đã giải quyết", "Resolved"), num: st("hoan_thanh"), sub: L(`${fmt(d.ty_le_da_tra_loi_pct, 1)}% đã trả lời`, `${fmt(d.ty_le_da_tra_loi_pct, 1)}% answered`), color: C.aqua, icon: CheckCircle2 },
        { label: L("Đang xử lý", "In progress"), num: st("dang_xu_ly") + st("tiep_nhan"), color: C.yellow, icon: Clock },
        { label: L("Quá hạn", "Overdue"), num: st("qua_han"), sub: L(`${fmt(d.ty_le_dung_han_pct, 1)}% xử lý đúng hạn`, `${fmt(d.ty_le_dung_han_pct, 1)}% on time`), color: C.red, icon: AlertTriangle },
        { label: L("Mức hài lòng", "Satisfaction"), num: d.hai_long_tb, digits: 1, suffix: "/5", sub: L("Đánh giá của người phản ánh", "Rated by citizens"), color: C.violet, icon: Smile },
      ]} />
      <div className="grid gap-4 lg:grid-cols-[1fr_1.25fr]">
        <Card title={L("Tình trạng xử lý", "Handling status")} unit={`${d.tong} ${pa}`}>
          <Donut center={String(d.tong)} unit={pa} data={d.theo_trang_thai.map((x) => ({ ten: dl(x.ten), so: x.so, color: color[String(x.ma)] ?? C.gray }))} />
        </Card>
        <Card title={L("Phản ánh theo lĩnh vực", "Feedback by area")} desc={L("Số phản ánh, trong đó quá hạn xử lý", "Count, of which overdue")} unit={pa}>
          <HBars stacked data={d.theo_linh_vuc.map((x) => ({ ten: dl(x.ten), dung: x.tong - x.qua_han, qua_han: x.qua_han }))}
                 keys={[{ key: "dung", name: L("Trong hạn / đã xử lý", "On time / handled"), color: C.blue }, { key: "qua_han", name: L("Quá hạn", "Overdue"), color: C.red }]} unit={pa} />
        </Card>
      </div>
      {(d.hai_long?.length || d.theo_tdp?.length) ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {d.hai_long && (
            <Card title={L("Mức độ hài lòng", "Satisfaction levels")} desc={L("Số lượt đánh giá theo từng mức", "Ratings by level")} unit={L("lượt", "ratings")}>
              <HBars data={d.hai_long.map((x) => ({ ten: dl(x.ten), so: x.so }))} keys={[{ key: "so", name: L("Lượt đánh giá", "Ratings"), color: C.orange }]} unit={L("lượt", "ratings")} />
              <div className="mt-2 flex flex-wrap gap-1.5">{d.hai_long.map((x) => <span key={x.ten} className="rounded-full px-2 py-0.5 text-[11.5px] font-semibold text-white" style={{ background: hl[String(x.ma)] }}>{dl(x.ten)}: {x.so}</span>)}</div>
            </Card>
          )}
          {d.theo_tdp && d.theo_tdp.length > 0 && (
            <Card title={L("Phản ánh theo tổ dân phố", "Feedback by residential group")} desc={L("Các địa bàn có nhiều phản ánh nhất", "Neighbourhoods with the most feedback")} unit={pa}>
              <HBars data={d.theo_tdp.slice(0, 10).map((x) => ({ ten: dl(x.ten), so: x.so }))} keys={[{ key: "so", name: L("Phản ánh", "Feedback"), color: C.violet }]} unit={pa} />
            </Card>
          )}
        </div>
      ) : null}
    </Section>
  );
}

/* ───────── Đầu tư công ───────── */
export function DauTuCong({ d, ky }: { d: NonNullable<ChuyenMuc["dau_tu_cong"]>; ky: string }) {
  const rows = d.du_an.filter((x) => x.ke_hoach_von !== null);
  const ty = unit("tỷ");
  return (
    <Section id="dau-tu-cong" title={L("Đầu tư công", "Public investment")} desc={L("Kế hoạch vốn năm và giải ngân các dự án trên địa bàn", "Annual capital plan and disbursement of projects")}
             tag={L(`Lũy kế đến ${period(ky)}`, `YTD to ${period(ky)}`)}
             csv={() => [[L("Dự án", "Project"), L("Chủ đầu tư", "Investor"), L("Kế hoạch vốn (tỷ)", "Capital plan (bn)"), L("Đã giải ngân (tỷ)", "Disbursed (bn)"), L("Tỷ lệ (%)", "Rate (%)"), L("Khối lượng (%)", "Works done (%)"), L("Hoàn thành", "Completion date")],
               ...d.du_an.map((x) => [x.ten, x.chu_dau_tu, x.ke_hoach_von, x.giai_ngan, x.ty_le_pct, x.khoi_luong_pct, x.ngay_ht])]}>
      <Kpis items={[
        { label: L("Dự án theo dõi", "Projects tracked"), num: d.so_du_an, color: C.blue, icon: Building2 },
        { label: L("Kế hoạch vốn năm", "Annual capital plan"), num: d.ke_hoach_von, suffix: ` ${ty}`, color: C.violet, icon: Coins },
        { label: L("Đã giải ngân", "Disbursed"), num: d.giai_ngan, suffix: ` ${ty}`, color: C.aqua, icon: Banknote },
        { label: L("Tỷ lệ giải ngân", "Disbursement rate"), num: d.ty_le_pct, digits: 1, suffix: "%", sub: L("Trên các dự án có số liệu xác nhận", "Projects with confirmed data"), color: C.orange, icon: TrendingUp },
      ]} />
      <div className="grid gap-4 lg:grid-cols-[1.25fr_1fr]">
        <Card title={L("Giải ngân theo dự án", "Disbursement by project")} desc={L("Đã giải ngân và phần vốn còn lại của kế hoạch năm", "Disbursed and remaining annual capital")} unit={unit("tỷ đồng")}>
          <HBars stacked data={rows.map((x) => ({ ten: x.ten, da: x.giai_ngan, con: x.giai_ngan !== null && x.ke_hoach_von !== null ? Math.max(0, Math.round((x.ke_hoach_von - x.giai_ngan) * 100) / 100) : x.ke_hoach_von }))}
                 keys={[{ key: "da", name: L("Đã giải ngân", "Disbursed"), color: C.aqua }, { key: "con", name: L("Vốn còn lại", "Remaining"), color: "#cbd5e1" }]} unit={ty} />
        </Card>
        <Card title={L("Tỷ lệ giải ngân và khối lượng", "Disbursement and works progress")} desc={L("So với kế hoạch vốn năm", "Against the annual capital plan")}>
          <div className="space-y-3.5">
            {rows.map((x, i) => <Meter key={x.ten} label={x.ten} pct={x.ty_le_pct} color={SERIES[i % SERIES.length]}
              sub={`${dl(x.lop_ten)}${x.khoi_luong_pct !== null ? L(` · khối lượng ${fmt(x.khoi_luong_pct, 0)}%`, ` · works ${fmt(x.khoi_luong_pct, 0)}%`) : ""}${x.ngay_ht ? L(` · hoàn thành ${date(x.ngay_ht)}`, ` · due ${date(x.ngay_ht)}`) : ""}`} />)}
          </div>
        </Card>
      </div>
    </Section>
  );
}

/* ───────── Công trình ───────── */
export function CongTrinh({ d }: { d: NonNullable<ChuyenMuc["cong_trinh"]> }) {
  const rows = d.cong_trinh.filter((x) => x.thuc_te_pct !== null);
  return (
    <Section id="cong-trinh" title={L("Công trình xây dựng", "Construction works")} desc={L("Tiến độ thi công đã được xác nhận tại hiện trường", "Site-confirmed construction progress")}
             csv={() => [[L("Công trình", "Work"), L("Loại", "Type"), L("Kế hoạch (%)", "Plan (%)"), L("Thực tế (%)", "Actual (%)"), L("Cập nhật", "Updated"), L("Hoàn thành", "Due")],
               ...d.cong_trinh.map((x) => [x.ten, dl(x.loai), x.ke_hoach_pct, x.thuc_te_pct, x.ngay, x.ngay_ht])]}>
      <Kpis items={[
        { label: L("Công trình", "Works"), num: d.so_cong_trinh, color: C.blue, icon: HardHat },
        { label: L("Đúng / vượt tiến độ", "On / ahead of schedule"), num: d.dung_tien_do, color: STATUS_C.dat, icon: CheckCircle2 },
        { label: L("Chậm tiến độ", "Behind schedule"), num: d.cham, color: STATUS_C.nguy_co, icon: AlertTriangle },
        { label: L("Loại công trình", "Work types"), num: d.theo_loai.length, color: C.violet, icon: Building2 },
      ]} />
      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card title={L("Tiến độ thi công", "Construction progress")} desc={L("Thực tế so với kế hoạch tại lần cập nhật gần nhất", "Actual vs. plan at last update")} unit="%">
          <HBars data={rows} max={100} unit="%" keys={[{ key: "ke_hoach_pct", name: L("Kế hoạch", "Plan"), color: "#94a3b8" }, { key: "thuc_te_pct", name: L("Thực tế", "Actual"), color: C.blue }]} />
        </Card>
        <Card title={L("Theo loại công trình", "By work type")} unit={`${d.so_cong_trinh} ${unit("công trình")}`}>
          <Donut center={String(d.so_cong_trinh)} unit={unit("công trình")} data={d.theo_loai.map((x, i) => ({ ten: dl(x.ten), so: x.so, color: SERIES[i % SERIES.length] }))} />
        </Card>
      </div>
    </Section>
  );
}

/* ───────── Dân cư ───────── */
export function DanCu({ d }: { d: NonNullable<ChuyenMuc["dan_cu"]> }) {
  const pyr = [...d.thap_tuoi].reverse().map((x) => ({ ten: x.nhom_tuoi, nam: x.nam === null ? null : -x.nam, nu: x.nu }));
  const bd = d.bien_dong.slice(-12);
  const ng = unit("người");
  const last = bd.at(-1); const prev = bd.at(-2);
  const diff = last?.dan_so && prev?.dan_so ? last.dan_so - prev.dan_so : null;
  return (
    <Section id="dan-cu" title={L("Dân cư", "Population")} desc={L("Số liệu dân cư tổng hợp (không chứa thông tin cá nhân; ô dưới 5 người được ẩn)", "Aggregate population data (no personal data; cells under 5 are suppressed)")}
             tag={period(d.ky)}
             csv={() => [[L("Nhóm tuổi", "Age group"), L("Nam", "Male"), L("Nữ", "Female")], ...d.thap_tuoi.map((x) => [x.nhom_tuoi, x.nam, x.nu])]}>
      <Kpis items={[
        { label: L("Dân số", "Population"), num: d.tong_dan_so, sub: diff !== null ? `${diff >= 0 ? "▲" : "▼"} ${n(Math.abs(diff), 0)} ${L("người so với tháng trước", "vs. previous month")}` : ng, color: C.blue, icon: Users },
        { label: L("Số hộ", "Households"), num: d.so_ho, sub: L(`${fmt(d.tong_dan_so / d.so_ho, 1)} người/hộ`, `${fmt(d.tong_dan_so / d.so_ho, 1)} people/household`), color: C.aqua, icon: Home },
        { label: L("Nam", "Male"), num: d.nam, sub: `${fmt(pct(d.nam, d.tong_dan_so), 1)}%`, color: C.blue },
        { label: L("Nữ", "Female"), num: d.nu, sub: `${fmt(pct(d.nu, d.tong_dan_so), 1)}%`, color: C.orange },
      ]} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={L("Tháp dân số", "Population pyramid")} desc={L("Nam (trái) – nữ (phải) theo nhóm tuổi", "Male (left) – female (right) by age group")} unit={ng}>
          <div className="h-[420px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={pyr} layout="vertical" stackOffset="sign" margin={{ top: 0, right: 8, left: 0, bottom: 0 }} barCategoryGap="12%">
                <CartesianGrid stroke="var(--vien)" horizontal={false} />
                <XAxis type="number" tick={AX} tickLine={false} axisLine={false} tickFormatter={(v: number) => fmt(Math.abs(v))} />
                <YAxis type="category" dataKey="ten" width={44} tick={AX} tickLine={false} axisLine={false} />
                <Tooltip {...TT} formatter={(v, nm) => [`${fmt(Math.abs(Number(v)))} ${ng}`, String(nm)]} />
                <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 12.5 }} />
                <Bar dataKey="nam" name={L("Nam", "Male")} stackId="p" fill={C.blue} radius={[4, 0, 0, 4]} animationDuration={900} />
                <Bar dataKey="nu" name={L("Nữ", "Female")} stackId="p" fill={C.orange} radius={[0, 4, 4, 0]} animationDuration={900} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <div className="flex min-w-0 flex-col gap-4">
          <Card title={L("Quy mô dân số theo tháng", "Population by month")} unit={ng}>
            <div className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={bd} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <defs><linearGradient id="g-ds" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={C.blue} stopOpacity={0.45} /><stop offset="100%" stopColor={C.blue} stopOpacity={0.02} /></linearGradient></defs>
                  <CartesianGrid stroke="var(--vien)" vertical={false} />
                  <XAxis dataKey="ky" tickFormatter={T} tick={AX} tickLine={false} />
                  <YAxis tick={AX} tickLine={false} axisLine={false} width={56} domain={["dataMin - 200", "dataMax + 200"]} tickFormatter={(v: number) => fmt(v, 0)} />
                  <Tooltip {...TT} formatter={(v) => [`${fmt(Number(v))} ${ng}`, L("Dân số", "Population")]} labelFormatter={(k) => period(String(k))} />
                  <Area dataKey="dan_so" name={L("Dân số", "Population")} stroke={C.blue} strokeWidth={2.5} fill="url(#g-ds)" dot={{ r: 3, fill: C.blue }} animationDuration={900} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title={L("Biến động dân cư", "Population change")} desc={L("Sinh, tử, chuyển đến, chuyển đi theo tháng", "Births, deaths, arrivals, departures")} unit={ng}>
            <VBars data={bd} xKey="ky" xFmt={T} unit={ng} height={200} keys={[
              { key: "sinh", name: L("Sinh", "Births"), color: C.aqua }, { key: "tu", name: L("Tử", "Deaths"), color: C.gray },
              { key: "chuyen_den", name: L("Chuyển đến", "Arrivals"), color: C.blue }, { key: "chuyen_di", name: L("Chuyển đi", "Departures"), color: C.orange },
            ]} />
          </Card>
        </div>
      </div>
    </Section>
  );
}

/* ───────── Bản đồ: dự án, công trình, trường học, y tế, môi trường (bật/tắt lớp) ───────── */
const LAYERS = [
  { key: "du_an", color: "#16324a", vi: "Dự án đầu tư công", en: "Public investment projects" },
  { key: "cong_trinh", color: "#b7791f", vi: "Công trình xây dựng", en: "Construction works" },
  { key: "truong", color: "#1e7358", vi: "Trường học", en: "Schools" },
  { key: "tram_y_te", color: "#b42318", vi: "Y tế", en: "Health stations" },
  { key: "diem_moi_truong", color: "#3b7ea1", vi: "Điểm môi trường", en: "Environment points" },
];
export function BanDo({ cm, diem, center, zoom, tileUrl }: { cm: ChuyenMuc; diem: Diem[]; center: [number, number]; zoom?: number; tileUrl?: string }) {
  const [on, setOn] = useState<Record<string, boolean>>(() => Object.fromEntries(LAYERS.map((l) => [l.key, true])));
  const pts = [
    ...(cm.dau_tu_cong?.du_an ?? []).filter((x) => x.lat && x.lng).map((x) => ({ loai: "du_an", ten: x.ten, lat: x.lat as number, lng: x.lng as number,
      note: x.ty_le_pct !== null ? L(`Giải ngân ${fmt(x.ty_le_pct, 1)}%`, `Disbursed ${fmt(x.ty_le_pct, 1)}%`) : "" })),
    ...(cm.cong_trinh?.cong_trinh ?? []).filter((x) => x.lat && x.lng).map((x) => ({ loai: "cong_trinh", ten: x.ten, lat: x.lat as number, lng: x.lng as number,
      note: x.thuc_te_pct !== null ? L(`Tiến độ ${fmt(x.thuc_te_pct, 0)}%`, `Progress ${fmt(x.thuc_te_pct, 0)}%`) : "" })),
    ...diem.filter((x) => x.lat && x.lng).map((x) => ({ loai: x.loai, ten: x.ten, lat: x.lat as number, lng: x.lng as number, note: "" })),
  ];
  if (!pts.length) return null;
  const present = LAYERS.filter((l) => pts.some((p) => p.loai === l.key));
  return (
    <Section id="ban-do" title={L("Bản đồ địa bàn", "Ward map")} desc={L("Dự án, công trình, trường học, cơ sở y tế và điểm môi trường trên địa bàn", "Projects, works, schools, health and environment points")}>
      <Reveal lazy minH={460} className="khu overflow-hidden p-2 sm:p-3">
        <div className="mb-2 flex flex-wrap gap-2 px-1">
          {present.map((l) => (
            <button key={l.key} type="button" aria-pressed={on[l.key]} onClick={() => setOn({ ...on, [l.key]: !on[l.key] })}
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12.5px] font-semibold transition ${on[l.key] ? "border-transparent text-white" : "border-[var(--vien-dam)] bg-[var(--be-mat)] text-muc-nhat"}`}
                    style={on[l.key] ? { background: l.color } : undefined}>
              <span aria-hidden className="h-2.5 w-2.5 rounded-full border-2 border-white" style={{ background: l.color }} />
              {L(l.vi, l.en)} ({pts.filter((p) => p.loai === l.key).length})
            </button>
          ))}
        </div>
        <div className="h-[380px] overflow-hidden rounded-lg border border-[var(--vien)] sm:h-[460px]">
          <MapContainer center={center} zoom={zoom ?? 14} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
            <MapTiles tileUrl={tileUrl} />
            {pts.filter((p) => on[p.loai]).map((p) => {
              const l = LAYERS.find((x) => x.key === p.loai);
              return (
                <CircleMarker key={`${p.loai}-${p.ten}`} center={[p.lat, p.lng]} radius={p.loai === "du_an" ? 10 : 8}
                              pathOptions={{ color: "#fff", weight: 2, fillColor: l?.color ?? "#16324a", fillOpacity: 0.95 }}>
                  <MapTip><b>{p.ten}</b>{p.note ? <><br />{p.note}</> : null}<br /><span style={{ color: "#64748b" }}>{l ? L(l.vi, l.en) : ""}</span></MapTip>
                </CircleMarker>
              );
            })}
          </MapContainer>
        </div>
        <p className="px-1 pt-2 text-[12px] text-muc-nhat">{L("Bấm vào nút lớp để bật/tắt; rê chuột hoặc chạm vào điểm để xem thông tin.", "Toggle layers with the buttons; hover or tap a point for details.")}</p>
      </Reveal>
    </Section>
  );
}
