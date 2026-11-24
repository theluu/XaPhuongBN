import { useQuery } from "@tanstack/react-query";
import { NguonTrachNhiem } from "@/features/org/DauMoi";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePeriod } from "@/lib/period";
import type { IndicatorCard } from "@/lib/types";
import { KpiTile } from "@/components/KpiTile";
import { PageHeader } from "@/components/PageHeader";
import { MapLegend, ProjectMap, type MapFeature } from "@/components/ProjectMap";

const GROUPS: [string, string][] = [["giao_duc", "Giáo dục"], ["y_te", "Y tế"], ["moi_truong", "Môi trường, nước sạch"]];
const LAYERS: [string, string][] = [["truong", "Điểm trường"], ["tram_y_te", "Trạm y tế"], ["diem_moi_truong", "Điểm môi trường"]];

export function QualityOfLifePage() {
  const { ky } = usePeriod();
  const { tenant } = useAuth();
  const [layers, setLayers] = useState<string[]>(["truong", "diem_moi_truong", "tram_y_te"]);
  const q = useQuery({ queryKey: ["qol", ky], queryFn: () => api<Record<string, IndicatorCard[]>>("/api/qol/summary", { params: { ky } }) });
  const geo = useQuery({ queryKey: ["qol-layers", layers], queryFn: async () => (await Promise.all(layers.map((l) => api<{ features: MapFeature[] }>(`/api/qol/layers/${l}`)))).flatMap((x) => x.features) });
  const env = useQuery({ queryKey: ["env-feedback"], queryFn: () => api<{ khu_vuc: string; so_phan_anh: number }[]>("/api/qol/env-feedback") });
  return (
    <>
      <PageHeader title="Giáo dục, y tế, môi trường và chất lượng sống" desc="Mục tiêu hằng năm và đến 2030. Chỉ chia sẻ số liệu y tế tổng hợp; lớp bản đồ chỉ hiển thị điểm được phép và đạt chất lượng dữ liệu." />
      <div className="mb-4"><NguonTrachNhiem nhom="gd_yt_mt" /></div>
      <div className="space-y-5">
        {GROUPS.map(([k, t]) => (q.data?.[k] ?? []).length > 0 && (
          <section key={k}>
            <h2 className="mb-2 font-semibold">{t}</h2>
            <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(250px,1fr))]">{q.data![k].map((c) => <KpiTile key={c.ma} card={{ ...c, link: `/chi-tieu?ma=${c.ma}` }} />)}</div>
          </section>
        ))}
        <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
          <section className="khu rounded-md p-4">
            <div className="mb-2 flex flex-wrap items-center gap-4">
              <h2 className="font-semibold">Bản đồ</h2>
              {LAYERS.map(([k, t]) => (
                <label key={k} className="flex items-center gap-1.5 text-[14px]">
                  <input type="checkbox" checked={layers.includes(k)} onChange={(e) => setLayers(e.target.checked ? [...layers, k] : layers.filter((x) => x !== k))} />{t}
                </label>
              ))}
            </div>
            <ProjectMap features={geo.data ?? []} center={tenant?.ban_do?.tam ?? [21.2725, 106.0975]} height={360} tileUrl={tenant?.ban_do?.tile_url} />
            <MapLegend items={LAYERS.map(([loai, ten]) => ({ loai, ten }))} />
          </section>
          <section className="khu rounded-md p-4">
            <h2 className="mb-2 font-semibold">Phản ánh môi trường theo địa bàn (90 ngày)</h2>
            <ul className="divide-y divide-[var(--vien)] text-[14px]">
              {(env.data ?? []).map((r) => (
                <li key={r.khu_vuc} className="flex justify-between py-1.5"><span>{r.khu_vuc}</span><span className="tabular font-medium">{r.so_phan_anh}</span></li>
              ))}
              {env.data?.length === 0 && <li className="py-2 text-muc-nhat">Chưa có phản ánh môi trường.</li>}
            </ul>
          </section>
        </div>
      </div>
    </>
  );
}
