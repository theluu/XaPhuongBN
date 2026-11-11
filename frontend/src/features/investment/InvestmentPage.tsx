import * as Tabs from "@radix-ui/react-tabs";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { formatMoney, formatNumber, formatPeriod } from "@/lib/format";
import { usePeriod } from "@/lib/period";
import { PageHeader } from "@/components/PageHeader";
import { Progress } from "@/components/Progress";

export interface ProjectRow { id: number; ma_du_an: string; ten: string; lop: number; chu_dau_tu: string; nguon_von: string; tong_muc_dt: number | null;
  ke_hoach_von_nam: number | null; lich_von_ky: number | null; giai_ngan_luy_ke: number | null; ty_le_giai_ngan_pct: number | null;
  khoi_luong_pct: number | null; cham_giai_ngan: boolean }
interface Layer { ten: string; so_du_an: number; ke_hoach_von: number | null; giai_ngan: number | null; so_cham: number; thieu_so_lieu: number; tinh_vao_ty_le: boolean }
interface Summary { ky: string; ty_le_giai_ngan_ns_phuong: number | null; theo_lop: Record<string, Layer> }

const NOTE: Record<number, string> = {
  1: "Phường làm chủ đầu tư. Chỉ lớp này được tính vào tỷ lệ giải ngân ngân sách phường.",
  2: "Cơ quan cấp thành phố làm chủ đầu tư, thi công trên địa bàn. Phường theo dõi, phối hợp; không tính vào tỷ lệ giải ngân ngân sách phường.",
  3: "Chỉ theo dõi thông tin, không tính vào tỷ lệ giải ngân ngân sách phường.",
};

function statusOf(r: ProjectRow): { text: string; color: string } {
  if (r.giai_ngan_luy_ke === null) return { text: "Chưa có số", color: "var(--thieu)" };
  if (r.cham_giai_ngan) return { text: "Chậm so lịch vốn", color: "var(--tam-thoi)" };
  if (r.lich_von_ky === null) return { text: "Chưa có lịch vốn kỳ", color: "var(--muc-nhat)" };
  return { text: "Đúng lịch vốn", color: "var(--xac-nhan)" };
}

export function InvestmentPage() {
  const { ky } = usePeriod();
  const [lop, setLop] = useState("1");
  const sum = useQuery({ queryKey: ["projects-summary", ky], queryFn: () => api<Summary>("/api/projects/summary", { params: { ky } }) });
  const list = useQuery({ queryKey: ["projects", ky], queryFn: () => api<ProjectRow[]>("/api/projects", { params: { ky } }) });
  const rows = (list.data ?? []).filter((r) => String(r.lop) === lop).sort((a, b) => Number(b.cham_giai_ngan) - Number(a.cham_giai_ngan) || (a.ty_le_giai_ngan_pct ?? 999) - (b.ty_le_giai_ngan_pct ?? 999));
  const s = sum.data;
  return (
    <>
      <PageHeader title="Giải ngân vốn đầu tư công" desc={`Lũy kế đến hết ${formatPeriod(ky)}. So sánh với lịch vốn đã phê duyệt của từng dự án, không chia đều theo tháng.`} />
      {s && (
        <div className="mb-4 grid gap-4 md:grid-cols-[280px_1fr]">
          <section className="khu rounded-md p-4">
            <h2 className="text-[15px] font-semibold">Tỷ lệ giải ngân ngân sách phường</h2>
            <div className="font-so text-[52px] font-semibold leading-tight tabular">{s.ty_le_giai_ngan_ns_phuong === null ? "—" : `${formatNumber(s.ty_le_giai_ngan_ns_phuong, 1)}%`}</div>
            <p className="text-[13px] text-muc-nhat">{formatMoney(s.theo_lop["1"].giai_ngan)} / kế hoạch vốn {formatMoney(s.theo_lop["1"].ke_hoach_von)}</p>
          </section>
          <section className="khu grid gap-3 rounded-md p-4 sm:grid-cols-3">
            {(["1", "2", "3"] as const).map((k) => (
              <div key={k}>
                <div className="text-[13px] text-muc-nhat">Lớp {k}</div>
                <div className="text-[15px] font-medium leading-snug">{s.theo_lop[k].ten}</div>
                <div className="mt-1 text-[14px]">{s.theo_lop[k].so_du_an} dự án{s.theo_lop[k].so_cham ? `, ${s.theo_lop[k].so_cham} chậm` : ""}</div>
              </div>
            ))}
          </section>
        </div>
      )}
      <Tabs.Root value={lop} onValueChange={setLop}>
        <Tabs.List aria-label="Lớp dự án" className="mb-3 flex gap-1 border-b border-vien">
          {(["1", "2", "3"] as const).map((k) => (
            <Tabs.Trigger key={k} value={k} className="-mb-px border-b-2 border-transparent px-3 py-2 text-[14.5px] text-muc-nhat data-[state=active]:border-muc data-[state=active]:font-semibold data-[state=active]:text-muc">
              Lớp {k} ({s?.theo_lop[k].so_du_an ?? 0})
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        <p className="mb-3 text-[14px] text-muc-nhat">{NOTE[Number(lop)]}</p>
        <div className="khu overflow-x-auto rounded-md">
          <table aria-label="Danh sách dự án" className="w-full text-[14px]">
            <thead><tr className="border-b border-vien text-left text-muc-nhat">
              <th className="px-4 py-2 font-medium">Dự án</th><th className="font-medium">Chủ đầu tư</th><th className="text-right font-medium">Kế hoạch vốn năm</th>
              <th className="text-right font-medium">Lịch vốn kỳ</th><th className="text-right font-medium">Đã giải ngân</th><th className="w-44 px-4 font-medium">Tỷ lệ</th><th className="pr-4 font-medium">Tình trạng</th>
            </tr></thead>
            <tbody>
              {rows.map((r) => {
                const st = statusOf(r);
                return (
                  <tr key={r.id} className="border-b border-vien">
                    <td className="px-4 py-2.5"><Link to={`/dau-tu-cong/${r.ma_du_an}`} className="font-medium hover:underline">{r.ten}</Link><div className="text-[12.5px] text-muc-nhat">{r.ma_du_an}</div></td>
                    <td>{r.chu_dau_tu}</td>
                    <td className="text-right tabular">{formatMoney(r.ke_hoach_von_nam)}</td><td className="text-right tabular">{formatMoney(r.lich_von_ky)}</td>
                    <td className="text-right tabular">{formatMoney(r.giai_ngan_luy_ke)}</td>
                    <td className="px-4"><div className="mb-1 text-right tabular text-[13px]">{r.ty_le_giai_ngan_pct === null ? "—" : `${formatNumber(r.ty_le_giai_ngan_pct, 1)}%`}</div>
                      <Progress value={r.giai_ngan_luy_ke} mark={r.lich_von_ky} max={r.ke_hoach_von_nam} label={`${r.ten}: giải ngân so với kế hoạch vốn năm`} /></td>
                    <td className="pr-4 font-medium" style={{ color: st.color }}>{st.text}</td>
                  </tr>
                );
              })}
              {rows.length === 0 && <tr><td colSpan={7} className="px-4 py-3 text-muc-nhat">Không có dự án ở lớp này.</td></tr>}
            </tbody>
          </table>
        </div>
      </Tabs.Root>
    </>
  );
}
