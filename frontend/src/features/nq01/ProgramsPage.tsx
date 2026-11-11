import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { usePeriod } from "@/lib/period";
import type { IndicatorCard } from "@/lib/types";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { formatNumber } from "@/lib/format";

interface ProgramRow {
  id: number; ma: string; ten: string; mo_ta: string; don_vi_chu_tri: string; trang_thai: string;
  tien_do: { tong: number; dat: number; nguy_co: number; chua_du_du_lieu: number; ty_le_dat_pct: number | null };
  chi_tieu: IndicatorCard[];
}

export function ProgramsPage() {
  const { ky } = usePeriod();
  const q = useQuery({ queryKey: ["programs", ky], queryFn: () => api<ProgramRow[]>("/api/programs", { params: { ky } }) });
  return (
    <>
      <PageHeader title="Nhiệm vụ, chương trình trọng tâm"
        desc="08 nhiệm vụ, chương trình trọng tâm của Nghị quyết 01-NQ/ĐU. Tiến độ tính từ trạng thái các chỉ tiêu gắn với từng nhiệm vụ." />
      <ol className="space-y-3">
        {(q.data ?? []).map((p, i) => (
          <li key={p.id} className="khu grid gap-3 rounded-md p-4 md:grid-cols-[3rem_1fr_220px]">
            <div className="font-so text-3xl font-semibold text-muc-nhat tabular">{String(i + 1).padStart(2, "0")}</div>
            <div className="min-w-0">
              <h2 className="text-[16px] font-semibold">{p.ten}</h2>
              {p.don_vi_chu_tri && <p className="text-[13px] text-muc-nhat">Chủ trì: {p.don_vi_chu_tri}</p>}
              {p.chi_tieu.length > 0 && (
                <ul className="mt-2 grid gap-1 text-[14px]">
                  {p.chi_tieu.map((c) => (
                    <li key={c.ma} className="flex items-center justify-between gap-3 border-b border-vien py-1">
                      <span className="min-w-0 truncate">{c.ten}</span>
                      <span className="flex shrink-0 items-center gap-3"><span className="tabular">{formatNumber(c.thuc_hien)} {c.don_vi}</span><StatusBadge status={c.status} /></span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="self-center">
              {p.tien_do.tong === 0 ? (
                <p className="is-missing rounded px-3 py-2 text-[14px] text-muc-nhat">Chưa gắn chỉ tiêu theo dõi</p>
              ) : (
                <>
                  <div className="mb-1 text-[14px] font-medium">{p.tien_do.dat}/{p.tien_do.tong} chỉ tiêu đạt</div>
                  <div className="flex h-2.5 overflow-hidden rounded-full bg-nen" role="img"
                    aria-label={`${p.tien_do.dat} đạt, ${p.tien_do.nguy_co} có nguy cơ, ${p.tien_do.chua_du_du_lieu} chưa đủ dữ liệu`}>
                    <div style={{ flex: p.tien_do.dat, background: "var(--xac-nhan)" }} />
                    <div style={{ flex: p.tien_do.nguy_co, background: "var(--tam-thoi)" }} />
                    <div className="is-missing" style={{ flex: p.tien_do.chua_du_du_lieu }} />
                  </div>
                </>
              )}
            </div>
          </li>
        ))}
      </ol>
    </>
  );
}
