import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, FileDown, Pause, Play, X } from "lucide-react";
import { api, getToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatNumber, formatPeriod } from "@/lib/format";
import { usePeriod } from "@/lib/period";
import type { IndicatorCard } from "@/lib/types";
import { GovHeader } from "@/components/GovHeader";
import { KpiTile } from "@/components/KpiTile";
import type { Overview } from "@/features/overview/OverviewPage";

const MUC: Record<string, string> = { cao: "Mức cao", trung_binh: "Mức trung bình", thap: "Mức thấp" };
const AUTO_MS = 30_000;

async function exportMinutes(ky: string) {
  const r = await fetch("/api/reports/bien-ban-giao-ban", { method: "POST", headers: { Authorization: `Bearer ${getToken() ?? ""}`, "Content-Type": "application/json" },
    body: JSON.stringify({ ky }) });
  if (!r.ok) return;
  const url = URL.createObjectURL(await r.blob());
  Object.assign(document.createElement("a"), { href: url, download: `bien-ban-giao-ban-${ky}.pdf` }).click();
  URL.revokeObjectURL(url);
}

/** Màn hình giao ban: chữ lớn, nền tối, chỉ số liệu tổng hợp (DT IV.2: họp mở rộng chỉ trình chiếu số tổng hợp). */
export function PresentationMode() {
  const { tenant, can } = useAuth();
  const { ky } = usePeriod();
  const [i, setI] = useState(0);
  const [auto, setAuto] = useState(false);
  const ov = useQuery({ queryKey: ["overview-present", ky], queryFn: () => api<Overview>("/api/overview", { params: { ky, che_do: "trinh_chieu" } }) });
  const risky = useQuery({ queryKey: ["indicators", "NQ01", ky], queryFn: () => api<IndicatorCard[]>("/api/indicators", { params: { bo: "NQ01", ky } }) });
  const d = ov.data;
  const slides = [
    { ten: `Tổng quan kỳ ${formatPeriod(ky)}`, body: d && (
      <>
        <p className="mb-6 text-2xl">Nghị quyết 01-NQ/ĐU: <b>{d.nq01.dat}</b> đạt, <b style={{ color: "var(--tam-thoi)" }}>{d.nq01.nguy_co}</b> có nguy cơ, <b className="text-thieu">{d.nq01.chua_du_du_lieu}</b> chưa đủ dữ liệu trên tổng {d.nq01.tong} chỉ tiêu.</p>
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(320px,1fr))]">{d.the_chi_so.map((c) => <KpiTile key={c.ma} card={c} size="xl" />)}</div>
      </>) },
    { ten: "Chỉ tiêu có nguy cơ", body: (
      <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(320px,1fr))]">
        {(risky.data ?? []).filter((c) => c.status === "nguy_co").map((c) => <KpiTile key={c.ma} card={c} size="xl" />)}
      </div>) },
    { ten: "Việc cần chỉ đạo", body: d && (
      <ol className="space-y-4 text-[26px] leading-snug">
        {d.can_chi_dao.map((a, n) => (
          <li key={a.id} className="flex gap-4"><span className="font-so text-muc-nhat tabular">{String(n + 1).padStart(2, "0")}</span>
            <span className="flex-1">{a.tieu_de}<span className="ml-3 text-lg" style={{ color: a.muc_do === "cao" ? "var(--son)" : "var(--muc-nhat)" }}>{MUC[a.muc_do]}</span></span></li>
        ))}
      </ol>) },
    { ten: "Độ đầy đủ dữ liệu", body: d && (
      <div className="text-3xl leading-relaxed">
        <p><span className="font-so text-8xl font-semibold tabular">{formatNumber(d.do_day_du.ty_le_pct)}%</span> chỉ tiêu có số liệu ({d.do_day_du.co_so}/{d.do_day_du.du_kien}).</p>
        <p className="mt-4 text-xl text-muc-nhat">Số liệu tạm thời và số chưa có được ghi rõ trên từng ô; đây là cảnh báo chất lượng dữ liệu, chưa kết luận chỉ tiêu không đạt.</p>
      </div>) },
  ];
  const n = slides.length;

  useEffect(() => {
    const prev = document.documentElement.dataset.theme;
    document.documentElement.dataset.theme = "dark";
    return () => { if (prev) document.documentElement.dataset.theme = prev; else delete document.documentElement.dataset.theme; };
  }, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "PageDown" || e.key === " ") setI((x) => (x + 1) % n);
      if (e.key === "ArrowLeft" || e.key === "PageUp") setI((x) => (x - 1 + n) % n);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [n]);
  useEffect(() => {
    if (!auto) return;
    const t = window.setInterval(() => setI((x) => (x + 1) % n), AUTO_MS);
    return () => window.clearInterval(t);
  }, [auto, n]);

  return (
    <div className="flex min-h-screen flex-col bg-nen text-muc">
      {tenant && (
        <GovHeader tenant={tenant} large>
          <div className="flex items-center gap-2">
            <button type="button" className="btn-phu" onClick={() => setI((i - 1 + n) % n)} aria-label="Trang trước"><ChevronLeft size={18} /></button>
            <span className="tabular text-sm">{i + 1}/{n}</span>
            <button type="button" className="btn-phu" onClick={() => setI((i + 1) % n)} aria-label="Trang sau"><ChevronRight size={18} /></button>
            <button type="button" className="btn-phu" onClick={() => setAuto(!auto)} aria-label={auto ? "Dừng tự chuyển" : "Tự chuyển 30 giây"}>{auto ? <Pause size={18} /> : <Play size={18} />}</button>
            {can("duyet", "canh_bao") && <button type="button" className="btn-phu" onClick={() => exportMinutes(ky)}><FileDown size={18} aria-hidden />Xuất biên bản</button>}
            <Link to="/" className="btn-phu" aria-label="Thoát trình chiếu"><X size={18} /></Link>
          </div>
        </GovHeader>
      )}
      <main className="flex-1 px-10 py-8">
        <h2 className="mb-6 text-4xl font-bold">{slides[i].ten}</h2>
        {slides[i].body ?? <p className="text-2xl text-muc-nhat">Đang tải…</p>}
      </main>
    </div>
  );
}
