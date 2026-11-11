import * as Tabs from "@radix-ui/react-tabs";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "@/lib/api";
import { formatNumber, formatPeriod } from "@/lib/format";
import { usePeriod } from "@/lib/period";
import type { IndicatorCard, Status } from "@/lib/types";
import { KpiTile } from "@/components/KpiTile";
import { PageHeader } from "@/components/PageHeader";
import { IndicatorDetailDrawer } from "./IndicatorDetailDrawer";

const NHOM_HIEN_THI: { key: string; ten: string }[] = [
  { key: "ktxh", ten: "Kinh tế, ngân sách và công tác xây dựng Đảng" },
  { key: "cong_trinh", ten: "Quy hoạch, hạ tầng đô thị" },
  { key: "dan_cu", ten: "An sinh xã hội" },
  { key: "gd_yt_mt", ten: "Giáo dục, y tế, môi trường" },
  { key: "tthc_pakn", ten: "Giải quyết đơn thư, khiếu nại, tố cáo" },
];
const TABS: { key: "all" | Status; ten: string }[] = [
  { key: "all", ten: "Tất cả" }, { key: "nguy_co", ten: "Có nguy cơ" }, { key: "chua_du_du_lieu", ten: "Chưa đủ dữ liệu" }, { key: "dat", ten: "Đạt" },
];

function reasons(c: IndicatorCard): string[] {
  const out: string[] = [];
  if (c.status === "nguy_co") out.push(`Thực hiện ${formatNumber(c.thuc_hien)} so với ${c.ke_hoach !== null ? "kế hoạch" : "mục tiêu"} ${formatNumber(c.muc_so_sanh)} ${c.don_vi}`);
  if (c.thuc_hien === null) out.push(`Chưa có số liệu kỳ ${formatPeriod(c.ky)}`);
  else if (c.status === "chua_du_du_lieu") out.push("Chưa có kế hoạch năm để đánh giá");
  if (c.data_state === "tam_thoi") out.push("Số tạm thời chờ xác nhận");
  if (c.lech_nguon) out.push("Số giữa các nguồn chưa thống nhất");
  return out;
}

export function Nq01Page() {
  const { ky } = usePeriod();
  const [tab, setTab] = useState<"all" | Status>("all");
  const [params, setParams] = useSearchParams();
  const open = params.get("ma");
  const setOpen = (ma: string | null) => setParams(ma ? { ma } : {});
  const q = useQuery({ queryKey: ["indicators", "NQ01", ky], queryFn: () => api<IndicatorCard[]>("/api/indicators", { params: { bo: "NQ01", ky } }) });
  const cards = useMemo(() => q.data ?? [], [q.data]);
  const count = (k: "all" | Status) => (k === "all" ? cards.length : cards.filter((c) => c.status === k).length);
  const shown = tab === "all" ? cards : cards.filter((c) => c.status === tab);
  const urge = cards.filter((c) => c.status !== "dat" || c.data_state === "tam_thoi" || c.lech_nguon).filter((c) => reasons(c).length > 0);

  return (
    <>
      <PageHeader title="Chỉ tiêu kinh tế – xã hội và Nghị quyết Đại hội"
        desc="16 chỉ tiêu chủ yếu đến năm 2030 của Nghị quyết 01-NQ/ĐU. Mỗi ô hiển thị số của kỳ báo cáo gần nhất đã kết thúc; dấu tròn cho biết số đã được xác nhận hay chưa." />
      <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
        <Tabs.Root value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
          <Tabs.List aria-label="Lọc theo trạng thái" className="mb-4 flex flex-wrap gap-1 border-b border-vien">
            {TABS.map((t) => (
              <Tabs.Trigger key={t.key} value={t.key}
                className="-mb-px border-b-2 border-transparent px-3 py-2 text-[14.5px] text-muc-nhat data-[state=active]:border-muc data-[state=active]:font-semibold data-[state=active]:text-muc">
                {t.ten} <span className="tabular">({count(t.key)})</span>
              </Tabs.Trigger>
            ))}
          </Tabs.List>
          <div data-testid="indicator-grid" className="space-y-6">
            {q.isLoading && <p className="text-muc-nhat">Đang tải chỉ tiêu…</p>}
            {NHOM_HIEN_THI.map((g) => {
              const items = shown.filter((c) => c.phan_he === g.key);
              if (!items.length) return null;
              return (
                <section key={g.key} aria-labelledby={`g-${g.key}`}>
                  <h2 id={`g-${g.key}`} className="mb-2 text-[15px] font-semibold text-muc-nhat">{g.ten}</h2>
                  <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(260px,1fr))]">
                    {items.map((c) => <KpiTile key={c.ma} card={c} onOpen={() => setOpen(c.ma)} />)}
                  </div>
                </section>
              );
            })}
            {!q.isLoading && shown.length === 0 && <p className="text-muc-nhat">Không có chỉ tiêu nào ở trạng thái này.</p>}
          </div>
        </Tabs.Root>
        <aside className="khu h-fit rounded-md border-t-[3px] border-t-son p-4">
          <h2 className="text-[16px] font-semibold">Cần đôn đốc</h2>
          <p className="mb-3 text-[13px] text-muc-nhat">Chỉ tiêu có nguy cơ, thiếu số liệu hoặc số chưa được xác nhận.</p>
          <ul aria-label="Chỉ tiêu cần đôn đốc" className="divide-y divide-[var(--vien)]">
            {urge.map((c) => (
              <li key={c.ma} className="py-2.5">
                <button type="button" onClick={() => setOpen(c.ma)} className="text-left text-[14.5px] font-medium hover:underline">{c.ten}</button>
                {reasons(c).map((r) => <p key={r} className="mt-0.5 text-[13px] text-muc-nhat">{r}</p>)}
              </li>
            ))}
            {urge.length === 0 && <li className="py-2 text-[14px] text-muc-nhat">Không có chỉ tiêu cần đôn đốc trong kỳ này.</li>}
          </ul>
        </aside>
      </div>
      <IndicatorDetailDrawer ma={open} ky={ky} onClose={() => setOpen(null)} />
    </>
  );
}
