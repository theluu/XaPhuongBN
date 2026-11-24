import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { AlertOctagon, BellRing, CalendarClock, Inbox, Maximize2, Minimize2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import { OpsLegend, OpsMap, pointColor, type OpsPoint } from "@/components/OpsMap";
import { DeadlineTag, NoLocationTag, UrgentTag } from "@/components/StatusTag";
import { ReportDetail } from "@/features/field-reports/ReportDetail";
import { KeyIndicators } from "./KeyIndicators";
import { MyResponsibility } from "@/features/org/DauMoi";
import { LichHomNay } from "@/features/lich/LichPage";
import type { OpsOverview, WorkItem } from "./types";

const KPI = [
  { loc: "moi", ten: "Phản ánh mới", key: "phan_anh_moi", icon: Inbox, mau: "var(--chinh)" },
  { loc: "den_han", ten: "Đến hạn hôm nay", key: "den_han_hom_nay", icon: CalendarClock, mau: "var(--tam-thoi)" },
  { loc: "qua_han", ten: "Việc quá hạn", key: "qua_han", icon: AlertOctagon, mau: "var(--son)" },
  { loc: "canh_bao", ten: "Cảnh báo đang mở", key: "canh_bao_mo", icon: BellRing, mau: "var(--dieu-huong)" },
] as const;
const LOAI = { phan_anh: "Phản ánh", nhiem_vu: "Nhiệm vụ chỉ đạo", canh_bao: "Cảnh báo" };

export const itemKey = (x: Pick<WorkItem, "loai" | "id">) => `${x.loai}-${x.id}`;

export function toPoints(items: WorkItem[]): OpsPoint[] {
  return items.filter((x) => x.lat !== null && x.lng !== null).map((x) => ({ key: itemKey(x), lat: x.lat!, lng: x.lng!, ten: x.ten, mau: pointColor(x) }));
}

function WorkRow({ x, active, onSelect }: { x: WorkItem; active: boolean; onSelect: () => void }) {
  return (
    <tr aria-selected={active} onClick={onSelect} className={`cursor-pointer border-b border-vien align-top ${active ? "bg-[color-mix(in_srgb,var(--chinh)_8%,transparent)]" : "hover:bg-be-mat-2"}`}>
      <td className={`py-2 pl-3 pr-2 ${active ? "shadow-[inset_3px_0_0_var(--chinh)]" : ""}`}>
        <button type="button" className="text-left text-[14px] font-medium leading-snug hover:underline" onClick={(e) => { e.stopPropagation(); onSelect(); }}>{x.ten}</button>
        <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[12px] text-muc-nhat">
          <span>{LOAI[x.loai]} · {x.ma}</span>{x.khan_cap && <UrgentTag />}{x.loai === "phan_anh" && x.lat === null && <NoLocationTag />}
        </div>
      </td>
      <td className="px-2 py-2 text-[13.5px]">{x.dia_diem || <span className="text-muc-nhat">—</span>}</td>
      <td className="px-2 py-2 text-[13.5px]">{x.don_vi ?? <span className="text-muc-nhat">Chưa giao</span>}</td>
      <td className="px-2 py-2 text-[13px]">{x.trang_thai_ten}</td>
      <td className="py-2 pl-2 pr-3"><DeadlineTag han={x.han} quaHan={x.qua_han_ngay} /></td>
    </tr>
  );
}

/** Màn hình Tổng quan điều hành (§2). */
export function OperationsPage() {
  const { tenant, me } = useAuth();
  const [params, setParams] = useSearchParams();
  // Mục 3: lãnh đạo, quản trị mặc định xem toàn đơn vị; cán bộ chuyên môn mặc định "Việc của tôi"
  const leader = !me || me.roles.some((r) => r === "lanh_dao" || r === "quan_tri_don_vi");
  const phamVi = params.get("pham_vi") ?? (leader ? "tat_ca" : "cua_toi");
  const loc = params.get("loc") ?? "";
  const tdp = params.get("tdp") ?? "";
  const sel = params.get("chon");
  const wide = params.get("mo_rong") === "1";
  const set = (k: string, v: string | null) => { const p = new URLSearchParams(params); if (v) p.set(k, v); else p.delete(k); setParams(p, { replace: true }); };
  const q = useQuery({ queryKey: ["dieu-hanh", loc, tdp, phamVi], queryFn: () => api<OpsOverview>("/api/dieu-hanh/tong-quan", { params: { loc: loc || undefined, tdp: tdp || undefined, pham_vi: phamVi } }),
    refetchInterval: 60_000 });
  const d = q.data;
  const selected = d?.viec.find((x) => itemKey(x) === sel);
  const center: [number, number] = tenant?.ban_do?.tam ?? [21.2725, 106.0975];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-full sm:w-auto sm:flex-1">
          <h1 className="text-[22px] font-extrabold leading-tight sm:text-[26px] md:text-[28px]">Tổng quan điều hành</h1>
          <p className="text-[13.5px] text-muc-nhat">
            {phamVi === "cua_toi" && d?.toi && <><b>Việc của {d.toi.ten || "tôi"}</b>{d.toi.don_vi_ten ? ` và ${d.toi.don_vi_ten}` : " (giao đích danh)"} · </>}
            {d ? <>Cập nhật lúc {formatDateTime(d.cap_nhat_luc)}{d.du_lieu_moi_nhat && <> · dữ liệu mới nhất nhận lúc {formatDateTime(d.du_lieu_moi_nhat)}</>}</> : "Đang tải…"}
          </p>
        </div>
        <div role="radiogroup" aria-label="Phạm vi" className="flex overflow-hidden rounded-md border border-vien text-sm">
          {([["tat_ca", "Toàn đơn vị"], ["cua_toi", "Việc của tôi"]] as const).map(([k, t]) => (
            <button key={k} type="button" role="radio" aria-checked={phamVi === k} onClick={() => set("pham_vi", k)}
              className={`px-3 py-1.5 ${phamVi === k ? "bg-chinh font-semibold text-white" : "bg-be-mat hover:bg-be-mat-2"}`}>{t}</button>
          ))}
        </div>
        {d && d.bo_loc.tdp.length > 0 && (
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muc-nhat">{d.bo_loc.dia_ban_label}</span>
            <select className="o-nhap w-auto py-1.5" value={tdp} onChange={(e) => set("tdp", e.target.value || null)}>
              <option value="">Toàn địa bàn</option>
              {d.bo_loc.tdp.map((t) => <option key={t.id} value={t.id}>{t.ten}</option>)}
            </select>
          </label>
        )}
      </div>

      <MyResponsibility />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" role="group" aria-label="Chỉ số điều hành">
        {KPI.map((k) => {
          const active = loc === k.loc;
          return (
            <button key={k.loc} type="button" aria-pressed={active} onClick={() => set("loc", active ? null : k.loc)}
              className={`khu flex items-start gap-3 overflow-hidden px-4 pb-3.5 pt-3 text-left transition hover:-translate-y-0.5 hover:shadow-lg sm:px-5 ${active ? "ring-2 ring-[var(--chinh)]" : ""}`}
              style={{ borderTop: `4px solid ${k.mau}` }}>
              <span className="min-w-0 flex-1">
                <span className="chu-nho-hoa block">{k.ten}</span>
                <span className="mt-1.5 block font-so text-[30px] font-extrabold leading-none tabular sm:text-[36px]" style={{ color: k.key === "qua_han" && d?.chi_so.qua_han ? "var(--son)" : "var(--muc)" }}>{d ? d.chi_so[k.key] : "–"}</span>
              </span>
              <span aria-hidden className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-xl sm:flex" style={{ background: `color-mix(in srgb, ${k.mau} 12%, transparent)`, color: k.mau }}><k.icon size={21} /></span>
            </button>
          );
        })}
      </div>

      <div className={`grid gap-4 ${selected?.loai === "phan_anh" ? "xl:grid-cols-[minmax(0,1fr)_420px]" : ""}`}>
        <div className={`grid gap-4 ${wide ? "" : "lg:grid-cols-[3fr_2fr]"}`}>
          <section aria-labelledby="viec-can-xu-ly" className="khu min-w-0 rounded-md">
            <div className="flex items-center gap-2 border-b border-vien px-3 py-2.5">
              <h2 id="viec-can-xu-ly" className="flex-1 the-tieu-de">
                Việc cần xử lý{loc && ` · ${KPI.find((k) => k.loc === loc)?.ten}`} <span className="font-normal text-muc-nhat">({d?.tong ?? 0})</span>
              </h2>
              {loc && <button type="button" className="lien-ket text-[13px]" onClick={() => set("loc", null)}>Bỏ lọc</button>}
              <button type="button" className="btn-phu px-2 py-1" onClick={() => set("mo_rong", wide ? null : "1")} aria-label={wide ? "Thu gọn danh sách" : "Mở rộng danh sách"}>
                {wide ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
              </button>
            </div>
            <div className="max-h-[620px] overflow-auto">
              <table className="w-full" aria-label="Việc cần xử lý">
                <thead className="sticky top-0 bg-be-mat">
                  <tr className="border-b border-vien text-left text-[12.5px] text-muc-nhat">
                    <th className="py-2 pl-3 font-medium">Tên việc</th><th className="px-2 font-medium">Địa điểm</th><th className="px-2 font-medium">Đơn vị phụ trách</th>
                    <th className="px-2 font-medium">Trạng thái</th><th className="pl-2 pr-3 font-medium">Hạn xử lý</th>
                  </tr>
                </thead>
                <tbody>
                  {(d?.viec ?? []).map((x) => <WorkRow key={itemKey(x)} x={x} active={itemKey(x) === sel} onSelect={() => set("chon", itemKey(x))} />)}
                  {d && d.viec.length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-[14px] text-muc-nhat">Không có việc nào theo bộ lọc đang chọn.</td></tr>}
                </tbody>
              </table>
            </div>
          </section>

          {!wide && (
            <section aria-labelledby="ban-do-dia-ban" className="khu flex flex-col rounded-md p-3">
              <div className="mb-2 flex items-center justify-between gap-2">
                <h2 id="ban-do-dia-ban" className="the-tieu-de">Bản đồ địa bàn</h2>
                <Link to="/ban-do" className="lien-ket text-[13px]">Mở bản đồ lớn</Link>
              </div>
              <div className="h-[480px]">
                <OpsMap points={toPoints(d?.viec ?? [])} center={center} zoom={tenant?.ban_do?.zoom ?? 14} selected={sel} onSelect={(k) => set("chon", k)} tileUrl={tenant?.ban_do?.tile_url} />
              </div>
              <div className="mt-2"><OpsLegend /></div>
            </section>
          )}
        </div>

        {selected?.loai === "phan_anh" && (
          <div className="xl:sticky xl:top-4 xl:h-[calc(100vh-120px)]"><ReportDetail id={selected.id} onClose={() => set("chon", null)} /></div>
        )}
      </div>
      <LichHomNay />
      <KeyIndicators />
      {selected && selected.loai !== "phan_anh" && (
        <div role="status" className="khu flex flex-wrap items-center gap-3 rounded-md px-4 py-3 text-[14px]">
          <span className="flex-1"><b>{LOAI[selected.loai]}:</b> {selected.ten}{selected.nguoi_phu_trach && ` · Phụ trách: ${selected.nguoi_phu_trach}`}</span>
          <Link to={selected.link} className="btn-chinh">Mở hồ sơ</Link>
        </div>
      )}
    </div>
  );
}
