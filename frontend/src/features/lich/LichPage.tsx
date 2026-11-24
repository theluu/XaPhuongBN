import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { CalendarDays, ChevronLeft, ChevronRight, Pencil, Printer } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";

export interface LichItem { id: number; ngay: string; gio_bat_dau: string; gio_ket_thuc: string | null; noi_dung: string; chu_tri: string; dia_diem: string;
  thanh_phan: string; don_vi_chuan_bi: string; loai: string; loai_ten: string; trang_thai: string; trang_thai_ten: string; ghi_chu: string; is_sample: boolean }
interface Week { tu: string; den: string; tuan_so: number; hom_nay: string; co_quyen_sua: boolean; ngay: { ngay: string; thu: string; muc: LichItem[] }[] }

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const shift = (s: string, days: number) => { const d = new Date(`${s}T00:00:00`); d.setDate(d.getDate() + days); return iso(d); };
const gio = (x: LichItem) => (x.gio_ket_thuc ? `${x.gio_bat_dau}–${x.gio_ket_thuc}` : x.gio_bat_dau);

/** Lịch công tác tuần của lãnh đạo (tham khảo mục Lịch công tác trên Cổng TTĐT). */
export function LichPage() {
  const [params, setParams] = useSearchParams();
  const tuan = params.get("tuan") ?? undefined;
  const q = useQuery({ queryKey: ["lich", tuan], queryFn: () => api<Week>("/api/lich-cong-tac", { params: { tuan } }) });
  const d = q.data;
  return (
    <>
      <PageHeader title="Lịch công tác" desc="Lịch công tác tuần của Thường trực Đảng ủy, lãnh đạo UBND: thời gian, nội dung, chủ trì, địa điểm, thành phần và đơn vị chuẩn bị.">
        <div className="flex flex-wrap gap-2 print:hidden">
          {d?.co_quyen_sua && <Link className="btn-chinh" to="/quan-ly-du-lieu?bo=lich_cong_tac"><Pencil size={15} aria-hidden />Cập nhật lịch</Link>}
          <button type="button" className="btn-phu" onClick={() => window.print()}><Printer size={15} aria-hidden />In lịch</button>
        </div>
      </PageHeader>
      {!d?.ngay ? <p className="text-muc-nhat">{q.isError ? "Không tải được lịch." : "Đang tải…"}</p> : (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2 print:hidden">
            <button type="button" className="btn-phu py-1.5" onClick={() => setParams({ tuan: shift(d.tu, -7) })}><ChevronLeft size={15} aria-hidden />Tuần trước</button>
            <button type="button" className="btn-phu py-1.5" onClick={() => setParams({})}>Tuần này</button>
            <button type="button" className="btn-phu py-1.5" onClick={() => setParams({ tuan: shift(d.tu, 7) })}>Tuần sau<ChevronRight size={15} aria-hidden /></button>
            <h2 className="ml-2 text-[16px] font-semibold">Tuần {d.tuan_so}: {formatDate(d.tu)} – {formatDate(d.den)}</h2>
          </div>
          <div className="khu overflow-x-auto rounded-md">
            <table className="w-full text-[14px]" aria-label="Lịch công tác tuần">
              <thead><tr className="border-b border-vien text-left text-[12.5px] text-muc-nhat">
                <th className="w-36 px-3 py-2 font-medium">Ngày</th><th className="w-24 font-medium">Thời gian</th><th className="font-medium">Nội dung</th>
                <th className="font-medium">Chủ trì</th><th className="font-medium">Địa điểm</th><th className="px-3 font-medium">Thành phần, chuẩn bị</th></tr></thead>
              <tbody>{d.ngay.map((n) => {
                const today = n.ngay === d.hom_nay;
                const rows = n.muc.length ? n.muc : [null];
                return rows.map((x, i) => (
                  <tr key={`${n.ngay}-${x?.id ?? "x"}`} className={`border-b border-vien align-top ${today ? "bg-[color-mix(in_srgb,var(--chinh)_6%,transparent)]" : ""} ${x?.trang_thai === "hoan" ? "text-muc-nhat" : ""}`}>
                    {i === 0 && <td rowSpan={rows.length} className={`px-3 py-2 ${today ? "shadow-[inset_3px_0_0_var(--chinh)]" : ""}`}>
                      <div className="font-semibold">{n.thu}</div><div className="text-[13px] text-muc-nhat">{formatDate(n.ngay)}{today && " · Hôm nay"}</div></td>}
                    {x ? <>
                      <td className="py-2 font-medium tabular">{gio(x)}</td>
                      <td className="py-2 pr-2"><span className={x.trang_thai === "hoan" ? "line-through" : ""}>{x.noi_dung}</span>
                        <span className="ml-1.5 inline-flex flex-wrap gap-1 align-middle">
                          <span className="nhan-tt tt-thuong">{x.loai_ten}</span>
                          {x.trang_thai !== "chinh_thuc" && <span className={`nhan-tt ${x.trang_thai === "hoan" ? "tt-qua-han" : "tt-sap-han"}`}>{x.trang_thai_ten}</span>}
                          {x.is_sample && <span className="nhan-tt tt-cu">Minh họa</span>}</span>
                        {x.ghi_chu && <div className="text-[12.5px] text-muc-nhat">{x.ghi_chu}</div>}</td>
                      <td className="py-2 pr-2">{x.chu_tri || "—"}</td>
                      <td className="py-2 pr-2">{x.dia_diem || "—"}</td>
                      <td className="px-3 py-2 text-[13px]">{x.thanh_phan}{x.don_vi_chuan_bi && <div className="text-muc-nhat">Chuẩn bị: {x.don_vi_chuan_bi}</div>}</td>
                    </> : <td colSpan={5} className="py-2 text-muc-nhat">Không có lịch</td>}
                  </tr>
                ));
              })}</tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}

/** Lịch hôm nay: thẻ trên trang chủ / khối trên màn hình TV. */
export function LichHomNay({ tv = false }: { tv?: boolean }) {
  const q = useQuery({ queryKey: ["lich-hom-nay"], queryFn: () => api<LichItem[]>("/api/lich-cong-tac/hom-nay"), refetchInterval: 300_000 });
  const rows = Array.isArray(q.data) ? q.data : [];
  if (tv) {
    if (!rows.length) return null;
    return (
      <section aria-label="Lịch công tác hôm nay" className="rounded-md bg-white/5 p-4">
        <h2 className="mb-2 text-2xl font-bold">Lịch công tác hôm nay</h2>
        <ul className="space-y-2">{rows.slice(0, 4).map((x) => <li key={x.id} className="text-xl"><b className="tabular text-[#f3d27a]">{x.gio_bat_dau}</b> {x.noi_dung}
          <span className="text-white/70">{x.chu_tri && ` · ${x.chu_tri}`}{x.dia_diem && ` · ${x.dia_diem}`}</span></li>)}</ul>
      </section>
    );
  }
  return (
    <section aria-labelledby="lich-hom-nay" className="khu rounded-md px-4 py-3">
      <div className="mb-1 flex items-center gap-2"><CalendarDays size={17} aria-hidden className="text-[var(--chinh)]" />
        <h2 id="lich-hom-nay" className="flex-1 the-tieu-de">Lịch công tác hôm nay</h2>
        <Link to="/lich-cong-tac" className="lien-ket text-[13px]">Cả tuần</Link></div>
      {rows.length === 0 ? <p className="text-[13.5px] text-muc-nhat">Không có lịch công tác hôm nay.</p> : (
        <ul className="divide-y divide-[var(--vien)] text-[13.5px]">{rows.map((x) => (
          <li key={x.id} className="flex gap-3 py-1.5"><span className="w-20 shrink-0 font-semibold tabular">{gio(x)}</span>
            <span className="min-w-0">{x.noi_dung}<span className="block text-[12.5px] text-muc-nhat">{[x.chu_tri && `Chủ trì: ${x.chu_tri}`, x.dia_diem].filter(Boolean).join(" · ")}</span></span></li>
        ))}</ul>
      )}
    </section>
  );
}
