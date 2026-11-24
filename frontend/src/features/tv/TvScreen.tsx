import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Maximize, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatDateTime } from "@/lib/format";
import { GovHeader } from "@/components/GovHeader";
import { NewsTicker } from "@/components/NewsTicker";
import { LichHomNay } from "@/features/lich/LichPage";
import { OpsLegend, OpsMap } from "@/components/OpsMap";
import { toPoints } from "@/features/operations/OperationsPage";
import type { OpsOverview } from "@/features/operations/types";

/** Màn hình TV phòng điều hành (§3): bản đồ chiếm phần lớn, 3–5 việc nổi bật, thời điểm cập nhật; không thông tin cá nhân người gửi. */
export function TvScreen() {
  const { tenant } = useAuth();
  const [now, setNow] = useState(new Date());
  const q = useQuery({ queryKey: ["dieu-hanh-tv"], queryFn: () => api<OpsOverview>("/api/dieu-hanh/tong-quan", { params: { che_do: "tv" } }), refetchInterval: 60_000 });
  useEffect(() => { const t = window.setInterval(() => setNow(new Date()), 30_000); return () => window.clearInterval(t); }, []);
  const d = q.data;
  const full = () => document.documentElement.requestFullscreen?.().catch(() => undefined);
  return (
    <div className="flex h-screen flex-col bg-[#0b1d31] text-white">
      {tenant && (
        <GovHeader tenant={tenant} large>
          <div className="text-right">
            <div className="font-so text-4xl font-bold tabular">{String(now.getHours()).padStart(2, "0")}:{String(now.getMinutes()).padStart(2, "0")}</div>
            <div className="text-sm text-white/75">{formatDate(now.toISOString())}</div>
          </div>
          <button type="button" className="btn ml-3 border border-white/30 text-white" onClick={full} aria-label="Toàn màn hình"><Maximize size={20} /></button>
          <Link to="/" className="btn border border-white/30 text-white" aria-label="Thoát màn hình TV"><X size={20} /></Link>
        </GovHeader>
      )}
      <NewsTicker dark large />
      <div className="grid min-h-0 flex-1 gap-4 p-4 lg:grid-cols-[1fr_520px]">
        <div className="min-h-0">
          <OpsMap points={toPoints(d?.viec ?? [])} center={tenant?.ban_do?.tam ?? [21.2725, 106.0975]} zoom={tenant?.ban_do?.zoom ?? 14} tileUrl={tenant?.ban_do?.tile_url} large />
        </div>
        <aside className="flex min-h-0 flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            {([["Việc quá hạn", d?.chi_so.qua_han, "#f87171"], ["Đến hạn hôm nay", d?.chi_so.den_han_hom_nay, "#facc15"], ["Phản ánh mới", d?.chi_so.phan_anh_moi, "#93c5fd"],
              ["Cảnh báo đang mở", d?.chi_so.canh_bao_mo, "#e2e8f0"]] as const).map(([t, v, c]) => (
              <div key={t} className="rounded-md bg-white/5 px-4 py-3"><div className="text-lg text-white/75">{t}</div><div className="font-so text-6xl font-bold tabular" style={{ color: c }}>{v ?? "–"}</div></div>
            ))}
          </div>
          <LichHomNay tv />
          <section aria-label="Việc nổi bật" className="min-h-0 flex-1 overflow-hidden rounded-md bg-white/5 p-4">
            <h2 className="mb-3 text-2xl font-bold">Việc cần ưu tiên</h2>
            <ol className="space-y-4">
              {(d?.viec ?? []).map((x, i) => (
                <li key={`${x.loai}-${x.id}`} className="flex gap-3">
                  <span className="font-so text-3xl text-white/50 tabular">{String(i + 1).padStart(2, "0")}</span>
                  <div className="min-w-0">
                    <div className="text-[22px] font-semibold leading-snug">{x.ten}</div>
                    <div className="text-lg text-white/75">{[x.dia_diem, x.don_vi].filter(Boolean).join(" · ")}</div>
                    <div className="text-lg font-semibold" style={{ color: x.khan_cap || x.qua_han_ngay ? "#f87171" : "#facc15" }}>
                      {x.khan_cap ? "KHẨN CẤP · " : ""}{x.qua_han_ngay ? `Quá hạn ${x.qua_han_ngay} ngày` : x.han ? `Hạn ${formatDate(x.han)}` : "Chưa đặt hạn"}
                    </div>
                  </div>
                </li>
              ))}
              {d && d.viec.length === 0 && <li className="text-xl text-white/75">Không có việc quá hạn hoặc khẩn cấp.</li>}
            </ol>
          </section>
          <div className="flex items-center justify-between text-base text-white/75">
            <span>Cập nhật lúc {d ? formatDateTime(d.cap_nhat_luc) : "…"}</span>
            <span className="[&_*]:!text-white/75"><OpsLegend /></span>
          </div>
        </aside>
      </div>
    </div>
  );
}
