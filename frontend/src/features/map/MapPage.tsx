import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePeriod } from "@/lib/period";
import { OpsLegend, OpsMap, type OpsPoint } from "@/components/OpsMap";
import { DeadlineTag } from "@/components/StatusTag";
import type { Overview } from "@/features/overview/OverviewPage";
import { itemKey, toPoints } from "@/features/operations/OperationsPage";
import type { OpsOverview } from "@/features/operations/types";

/** Bản đồ địa bàn: phản ánh đang mở + dự án, công trình; bật/tắt từng lớp. */
export function MapPage() {
  const { tenant } = useAuth();
  const { ky } = usePeriod();
  const nav = useNavigate();
  const [lop, setLop] = useState({ viec: true, du_an: true, cong_trinh: true });
  const [sel, setSel] = useState<string | null>(null);
  const ops = useQuery({ queryKey: ["dieu-hanh", "", ""], queryFn: () => api<OpsOverview>("/api/dieu-hanh/tong-quan"), refetchInterval: 60_000 });
  const ov = useQuery({ queryKey: ["overview", ky, ""], queryFn: () => api<Overview>("/api/overview", { params: { ky } }) });
  const items = ops.data?.viec ?? [];
  const other: OpsPoint[] = (ov.data?.ban_do.features ?? []).filter((f) => lop[f.properties.loai as "du_an" | "cong_trinh"])
    .map((f) => ({ key: `${String(f.properties.loai)}-${String(f.properties.ma)}`, lat: f.geometry.coordinates[1], lng: f.geometry.coordinates[0], ten: String(f.properties.ten),
      mau: f.properties.loai === "du_an" ? "du_an" : "cong_trinh", nhan: f.properties.loai === "du_an" ? "Dự án" : "Công trình" }));
  const points = [...(lop.viec ? toPoints(items) : []), ...other];
  const links = new Map<string, string>([...items.map((x) => [itemKey(x), x.link] as [string, string]),
    ...(ov.data?.ban_do.features ?? []).map((f) => [`${String(f.properties.loai)}-${String(f.properties.ma)}`, String(f.properties.link)] as [string, string])]);
  const chosen = items.find((x) => itemKey(x) === sel);
  const noPos = items.filter((x) => x.loai === "phan_anh" && x.lat === null);
  return (
    <div className="flex h-[calc(100dvh-170px)] min-h-[520px] flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h1 className="w-full text-[22px] font-extrabold sm:w-auto sm:flex-1 sm:text-[26px]">Bản đồ địa bàn</h1>
        {([["viec", "Phản ánh đang mở"], ["du_an", "Dự án đầu tư công"], ["cong_trinh", "Công trình"]] as const).map(([k, t]) => (
          <label key={k} className="flex items-center gap-1.5 text-sm"><input type="checkbox" checked={lop[k]} onChange={(e) => setLop({ ...lop, [k]: e.target.checked })} />{t}</label>
        ))}
      </div>
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[1fr_300px]">
        <OpsMap points={points} center={tenant?.ban_do?.tam ?? [21.2725, 106.0975]} zoom={tenant?.ban_do?.zoom ?? 14} selected={sel} tileUrl={tenant?.ban_do?.tile_url}
          onSelect={(k) => { if (k.startsWith("phan_anh-")) setSel(k); else if (links.get(k)) nav(links.get(k)!); }} />
        <aside className="khu flex min-h-0 flex-col rounded-md p-3 text-[14px]">
          <OpsLegend items={["khan", "qua_han", "thuong", "du_an", "cong_trinh"]} />
          {chosen ? (
            <div className="mt-3 space-y-1 border-t border-vien pt-3">
              <div className="font-semibold">{chosen.ten}</div>
              <div className="text-muc-nhat">{chosen.dia_diem}</div>
              <div>{chosen.don_vi ?? "Chưa giao"} · {chosen.trang_thai_ten}</div>
              <DeadlineTag han={chosen.han} quaHan={chosen.qua_han_ngay} />
              <div><Link className="lien-ket" to={`/?chon=${itemKey(chosen)}`}>Mở chi tiết</Link></div>
            </div>
          ) : <p className="mt-3 text-muc-nhat">Bấm một điểm để xem thông tin.</p>}
          {noPos.length > 0 && (
            <div className="mt-3 min-h-0 flex-1 overflow-y-auto border-t border-vien pt-3">
              <div className="mb-1 font-semibold">Chưa có vị trí trên bản đồ ({noPos.length})</div>
              <ul className="space-y-1">{noPos.map((x) => <li key={x.id}><Link className="lien-ket" to={`/phan-anh?id=${x.id}`}>{x.ten}</Link></li>)}</ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
