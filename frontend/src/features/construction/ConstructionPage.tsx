import { useQuery } from "@tanstack/react-query";
import { NguonTrachNhiem } from "@/features/org/DauMoi";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatNumber } from "@/lib/format";
import { usePeriod } from "@/lib/period";
import type { IndicatorCard } from "@/lib/types";
import { KpiTile } from "@/components/KpiTile";
import { PageHeader } from "@/components/PageHeader";
import { MapLegend, ProjectMap, type MapFeature } from "@/components/ProjectMap";

export interface Prog { id: number; ngay: string; ke_hoach_pct: number | null; thuc_te_pct: number | null; cham: boolean; gpmb: string; vuong_mac: string;
  can_quyet_dinh: boolean; anh_keys: string[]; minh_chung_keys: string[]; trang_thai_xac_nhan: string }
export interface WorkRow { id: number; ma: string; ten: string; don_vi_thuc_hien: string; ngay_ht: string | null; tre_han_ngay: number | null; chat_luong: string | null;
  camera_url: string | null; moi_nhat: Prog | null; trang_thai: string; lat: number | null; lng: number | null }
interface Summary { so_cong_trinh: number; so_cham: number; so_tre_han: number; so_can_quyet_dinh: number; so_chua_cap_nhat: number; chi_tieu_do_thi: IndicatorCard[] }

export function DualBar({ kh, tt }: { kh: number | null; tt: number | null }) {
  if (kh === null && tt === null) return <div className="is-missing h-4 rounded" />;
  return (
    <div className="space-y-1" role="img" aria-label={`Kế hoạch ${formatNumber(kh)}%, thực tế ${formatNumber(tt)}%`}>
      <div className="h-1.5 rounded-full bg-nen"><div className="h-full rounded-full bg-muc-nhat" style={{ width: `${kh ?? 0}%` }} /></div>
      <div className="h-2.5 rounded-full bg-nen"><div className="h-full rounded-full" style={{ width: `${tt ?? 0}%`, background: tt !== null && kh !== null && tt < kh ? "var(--tam-thoi)" : "var(--xac-nhan)" }} /></div>
    </div>
  );
}

function statusText(w: WorkRow): { text: string; color: string } {
  if (w.tre_han_ngay) return { text: `Quá hạn ${w.tre_han_ngay} ngày`, color: "var(--son)" };
  const m = w.moi_nhat;
  if (!m) return { text: "Chưa có báo cáo tiến độ", color: "var(--thieu)" };
  if (m.cham && m.ke_hoach_pct !== null && m.thuc_te_pct !== null) return { text: `Chậm ${formatNumber(m.ke_hoach_pct - m.thuc_te_pct)}%`, color: "var(--tam-thoi)" };
  return { text: "Đúng tiến độ", color: "var(--xac-nhan)" };
}

export function ConstructionPage() {
  const { ky } = usePeriod();
  const { tenant } = useAuth();
  const s = useQuery({ queryKey: ["works-summary", ky], queryFn: () => api<Summary>("/api/works/summary", { params: { ky } }) });
  const w = useQuery({ queryKey: ["works"], queryFn: () => api<WorkRow[]>("/api/works") });
  const g = useQuery({ queryKey: ["works-geo"], queryFn: () => api<{ features: MapFeature[] }>("/api/works/geojson") });
  const rows = w.data ?? [];
  const onMap = new Set((g.data?.features ?? []).map((f) => String(f.properties.ma)));
  const noLoc = rows.filter((r) => !onMap.has(r.ma)).length;
  const center: [number, number] = tenant?.ban_do?.tam ?? [21.2725, 106.0975];
  return (
    <>
      <PageHeader title="Công trình xây dựng, chỉnh trang và quản lý đô thị" desc="Tiến độ kế hoạch và thực tế theo báo cáo hằng tuần của chủ đầu tư, có ảnh hiện trường làm minh chứng." />
      <div className="mb-4"><NguonTrachNhiem nhom="cong_trinh" /></div>
      {s.data && (
        <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {[["Công trình đang theo dõi", s.data.so_cong_trinh, ""], ["Chậm tiến độ", s.data.so_cham, "var(--tam-thoi)"], ["Quá hạn hoàn thành", s.data.so_tre_han, "var(--son)"],
            ["Vướng mắc cần quyết định", s.data.so_can_quyet_dinh, "var(--son)"], ["Quá 1 tuần chưa cập nhật", s.data.so_chua_cap_nhat, "var(--thieu)"]].map(([t, v, c]) => (
            <div key={t as string} className="khu rounded-md p-3"><div className="text-[13px] text-muc-nhat">{t}</div>
              <div className="font-so text-[36px] font-semibold leading-tight tabular" style={{ color: (c as string) || undefined }}>{v as number}</div></div>
          ))}
        </div>
      )}
      <div className="grid gap-4 xl:grid-cols-[1fr_1.4fr]">
        <section className="khu rounded-md p-4">
          <h2 className="mb-2 font-semibold">Bản đồ công trình</h2>
          <ProjectMap features={g.data?.features ?? []} center={center} height={380} tileUrl={tenant?.ban_do?.tile_url} />
          <MapLegend items={[{ loai: "cong_trinh", ten: "Công trình" }]} />
          {noLoc > 0 && <p className="mt-2 text-[13px] text-muc-nhat">{noLoc} công trình chưa có vị trí hợp lệ nên không hiển thị trên bản đồ.</p>}
        </section>
        <section className="khu overflow-x-auto rounded-md">
          <table aria-label="Tiến độ công trình" className="w-full text-[14px]">
            <thead><tr className="border-b border-vien text-left text-muc-nhat">
              <th className="px-4 py-2 font-medium">Công trình</th><th className="w-48 font-medium">Kế hoạch / thực tế</th><th className="font-medium">Cập nhật</th><th className="px-4 font-medium">Tình trạng</th>
            </tr></thead>
            <tbody>
              {rows.map((r) => {
                const st = statusText(r);
                return (
                  <tr key={r.id} className="border-b border-vien">
                    <td className="px-4 py-2.5"><Link to={`/cong-trinh/${r.ma}`} className="font-medium hover:underline">{r.ten}</Link>
                      <div className="text-[12.5px] text-muc-nhat">{r.don_vi_thuc_hien}{r.moi_nhat?.can_quyet_dinh ? ". Cần lãnh đạo quyết định" : ""}</div></td>
                    <td className="pr-3"><DualBar kh={r.moi_nhat?.ke_hoach_pct ?? null} tt={r.moi_nhat?.thuc_te_pct ?? null} /></td>
                    <td className="text-[13px] text-muc-nhat">{formatDate(r.moi_nhat?.ngay)}</td>
                    <td className="px-4 font-medium" style={{ color: st.color }}>{st.text}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="px-4 py-2 text-[12.5px] text-muc-nhat">Thanh mảnh: kế hoạch. Thanh đậm: thực tế.</p>
        </section>
      </div>
      {(s.data?.chi_tieu_do_thi ?? []).length > 0 && (
        <section className="mt-4">
          <h2 className="mb-2 font-semibold">Chỉ tiêu quy hoạch, hạ tầng đô thị</h2>
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(250px,1fr))]">{s.data!.chi_tieu_do_thi.map((c) => <KpiTile key={c.ma} card={{ ...c, link: `/chi-tieu?ma=${c.ma}` }} />)}</div>
        </section>
      )}
    </>
  );
}
