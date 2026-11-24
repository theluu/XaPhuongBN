import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { formatPeriod } from "@/lib/format";
import { usePeriod } from "@/lib/period";
import { KpiTile } from "@/components/KpiTile";
import type { Overview } from "@/features/overview/OverviewPage";

/** Dải "Chỉ tiêu trọng tâm" gọn trên trang chủ (Dự thảo IV.1 khu ①); đầy đủ ở trang Báo cáo. */
export function KeyIndicators() {
  const { ky } = usePeriod();
  const q = useQuery({ queryKey: ["overview", ky, "", ""], queryFn: () => api<Overview>("/api/overview", { params: { ky } }) });
  const d = q.data;
  if (!d?.the_chi_so) return null;
  const tiles = d.the_chi_so.slice(0, 6);
  return (
    <section aria-labelledby="chi-tieu-trong-tam" className="khu rounded-md p-3">
      <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1">
        <h2 id="chi-tieu-trong-tam" className="the-tieu-de">Chỉ tiêu trọng tâm · kỳ {formatPeriod(d.ky)}</h2>
        <Link to="/chi-tieu" className="flex flex-wrap gap-x-3 text-[13.5px] hover:underline">
          <span className="font-medium">Nghị quyết 01: {d.nq01.tong} chỉ tiêu</span>
          <span style={{ color: "var(--xac-nhan)" }}>{d.nq01.dat} đạt</span>
          <span style={{ color: "var(--tam-thoi)" }}>{d.nq01.nguy_co} có nguy cơ</span>
          <span className="text-thieu">{d.nq01.chua_du_du_lieu} chưa đủ dữ liệu</span>
        </Link>
        <Link to="/bao-cao" className="lien-ket ml-auto text-[13.5px]">Xem báo cáo đầy đủ</Link>
      </div>
      {tiles.length > 0
        ? <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(220px,1fr))]">{tiles.map((c) => <KpiTile key={c.ma} card={c} />)}</div>
        : <p className="text-[14px] text-muc-nhat">Bạn chưa được cấp quyền xem chỉ tiêu, hoặc chưa có số liệu kỳ này.</p>}
    </section>
  );
}
