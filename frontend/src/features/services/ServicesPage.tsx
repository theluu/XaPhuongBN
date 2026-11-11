import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatNumber } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";

interface Agg { tiep_nhan: number; giai_quyet: number; dung_han: number; qua_han: number; truc_tuyen: number; dung_han_pct: number | null; truc_tuyen_pct: number | null; co_so_tam_thoi: boolean }
interface Tthc { tong: Agg; theo_ky: (Agg & { ky: string })[]; theo_bo_phan: (Agg & { bo_phan: string })[]; co_so_tam_thoi: boolean }
interface Pakn { tong: number; theo_trang_thai: Record<string, number>; ty_le_da_tra_loi_pct: number | null; ty_le_dung_han_pct: number | null; hai_long_tb: number | null }
interface Urge { ma: string; loai_viec: string; ngay_nhan: string; han_xu_ly: string; con_lai_ngay_lam_viec: number; muc: string }

const LOAI: Record<string, string> = { moi_truong: "Vệ sinh môi trường", trat_tu_do_thi: "Trật tự đô thị", ha_tang: "Hạ tầng", an_ninh: "An ninh trật tự", dat_dai: "Đất đai, xây dựng" };
const FIELDS = ["Tiếp nhận", "Giải quyết", "Đúng hạn", "Quá hạn", "Trực tuyến"] as const;
const KEY: Record<string, string> = { "Tiếp nhận": "tiep_nhan", "Giải quyết": "giai_quyet", "Đúng hạn": "dung_han", "Quá hạn": "qua_han", "Trực tuyến": "truc_tuyen" };

function validate(v: Record<string, number>): string | null {
  if (v.giai_quyet > v.tiep_nhan) return "Số đã giải quyết không được lớn hơn số tiếp nhận";
  if (v.dung_han + v.qua_han > v.giai_quyet) return "Số đúng hạn cộng quá hạn không được lớn hơn số đã giải quyết";
  if (v.truc_tuyen > v.tiep_nhan) return "Số hồ sơ trực tuyến không được lớn hơn số tiếp nhận";
  return null;
}

function ManualTthcForm({ onDone }: { onDone: () => void }) {
  const [ngay, setNgay] = useState(new Date().toISOString().slice(0, 10));
  const [boPhan, setBoPhan] = useState("");
  const [vals, setVals] = useState<Record<string, number>>({ tiep_nhan: 0, giai_quyet: 0, dung_han: 0, qua_han: 0, truc_tuyen: 0 });
  const [serverErr, setServerErr] = useState<string | null>(null);
  const err = validate(vals);
  const m = useMutation({
    mutationFn: () => api("/api/tthc/bieu-mau", { method: "POST", body: { ngay, bo_phan: boPhan.trim(), ...vals } }),
    onSuccess: onDone,
    onError: (e) => setServerErr(e instanceof ApiError ? String(e.detail) : "Không lưu được"),
  });
  return (
    <form onSubmit={(e) => { e.preventDefault(); m.mutate(); }} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <label className="text-sm font-medium">Ngày<input type="date" className="o-nhap mt-1" value={ngay} onChange={(e) => setNgay(e.target.value)} required /></label>
        <label className="text-sm font-medium">Bộ phận<input className="o-nhap mt-1" value={boPhan} onChange={(e) => setBoPhan(e.target.value)} required /></label>
        {FIELDS.map((f) => (
          <label key={f} className="text-sm font-medium">{f}
            <input type="number" min={0} inputMode="numeric" className="o-nhap mt-1 tabular" value={vals[KEY[f]]}
              onChange={(e) => setVals({ ...vals, [KEY[f]]: Math.max(0, Number(e.target.value) || 0) })} />
          </label>
        ))}
      </div>
      {(err || serverErr) && <p role="alert" className="text-sm text-son">{err ?? serverErr}</p>}
      <p className="text-[13px] text-muc-nhat">Số liệu được lưu ở trạng thái Tạm thời, chờ cán bộ có thẩm quyền xác nhận.</p>
      <button type="submit" className="btn-chinh" disabled={!!err || !boPhan.trim() || m.isPending}>Lưu số liệu</button>
    </form>
  );
}

export function ServicesPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const [group, setGroup] = useState("tuan");
  const [open, setOpen] = useState(false);
  const t = useQuery({ queryKey: ["tthc", group], queryFn: () => api<Tthc>("/api/tthc/summary", { params: { group } }) });
  const p = useQuery({ queryKey: ["pakn"], queryFn: () => api<Pakn>("/api/pakn/summary") });
  const u = useQuery({ queryKey: ["pakn-urge"], queryFn: () => api<Urge[]>("/api/pakn/can-don-doc") });
  return (
    <>
      <PageHeader title="Hành chính công, phản ánh kiến nghị" desc="Hồ sơ TTHC theo ngày/tuần/tháng và bộ phận; phản ánh kiến nghị theo trạng thái và thời hạn xử lý quy định cho từng loại việc.">
        {can("nhap", "tthc_pakn") && <button type="button" className="btn-chinh" onClick={() => setOpen(true)}>Nhập số liệu TTHC</button>}
      </PageHeader>
      <p className="mb-4 rounded border border-vien bg-be-mat px-3 py-2 text-[14px]">
        Luồng dữ liệu TTHC từ Cổng Dịch vụ công quốc gia gián đoạn từ 01/6/2026; số liệu tạm thời được nhập qua biểu mẫu động.
        {t.data?.co_so_tam_thoi && <strong className="ml-1 font-medium" style={{ color: "var(--tam-thoi)" }}>Kỳ đang xem có số liệu tạm thời chờ xác nhận.</strong>}
      </p>
      {t.data && (
        <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
          <section className="khu rounded-md p-4">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-semibold">Hồ sơ thủ tục hành chính</h2>
              <select className="o-nhap w-auto py-1" value={group} onChange={(e) => setGroup(e.target.value)} aria-label="Nhóm theo">
                <option value="ngay">Theo ngày</option><option value="tuan">Theo tuần</option><option value="thang">Theo tháng</option>
              </select>
            </div>
            <dl className="mb-3 grid grid-cols-2 gap-3 text-[14px] sm:grid-cols-4">
              <div><dt className="nhan">Tiếp nhận</dt><dd className="font-so text-3xl font-semibold tabular">{formatNumber(t.data.tong.tiep_nhan)}</dd></div>
              <div><dt className="nhan">Đúng hạn</dt><dd className="font-so text-3xl font-semibold tabular">{t.data.tong.dung_han_pct === null ? "—" : `${formatNumber(t.data.tong.dung_han_pct)}%`}</dd></div>
              <div><dt className="nhan">Quá hạn</dt><dd className="font-so text-3xl font-semibold tabular text-son">{formatNumber(t.data.tong.qua_han)}</dd></div>
              <div><dt className="nhan">Trực tuyến</dt><dd className="font-so text-3xl font-semibold tabular">{t.data.tong.truc_tuyen_pct === null ? "—" : `${formatNumber(t.data.tong.truc_tuyen_pct)}%`}</dd></div>
            </dl>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={t.data.theo_ky} margin={{ left: -12, right: 8 }}>
                <CartesianGrid stroke="var(--vien)" vertical={false} />
                <XAxis dataKey="ky" tick={{ fontSize: 11, fill: "var(--muc-nhat)" }} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: "var(--muc-nhat)" }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: "var(--be-mat)", border: "1px solid var(--vien)", borderRadius: 6, fontSize: 13 }} />
                <Bar name="Đúng hạn" dataKey="dung_han" stackId="a" fill="var(--xac-nhan)" isAnimationActive={false} />
                <Bar name="Quá hạn" dataKey="qua_han" stackId="a" fill="var(--son)" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
            <table aria-label="Theo bộ phận" className="mt-3 w-full text-[14px]">
              <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="py-1.5 font-medium">Bộ phận</th><th className="text-right font-medium">Tiếp nhận</th><th className="text-right font-medium">Đúng hạn</th><th className="text-right font-medium">Quá hạn</th></tr></thead>
              <tbody>{t.data.theo_bo_phan.map((b) => (
                <tr key={b.bo_phan} className="border-b border-vien"><td className="py-1.5">{b.bo_phan}</td><td className="text-right tabular">{formatNumber(b.tiep_nhan)}</td>
                  <td className="text-right tabular">{b.dung_han_pct === null ? "—" : `${formatNumber(b.dung_han_pct)}%`}</td><td className="text-right tabular">{formatNumber(b.qua_han)}</td></tr>
              ))}</tbody>
            </table>
          </section>
          <section className="khu rounded-md p-4">
            <h2 className="mb-2 font-semibold">Phản ánh kiến nghị</h2>
            {p.data && (
              <dl className="mb-3 grid grid-cols-2 gap-2 text-[14px]">
                <div><dt className="nhan">Đang xử lý</dt><dd className="text-2xl font-semibold tabular">{p.data.theo_trang_thai.dang_xu_ly}</dd></div>
                <div><dt className="nhan">Quá hạn</dt><dd className="text-2xl font-semibold tabular text-son">{p.data.theo_trang_thai.qua_han}</dd></div>
                <div><dt className="nhan">Đã trả lời</dt><dd className="text-2xl font-semibold tabular">{p.data.ty_le_da_tra_loi_pct === null ? "—" : `${formatNumber(p.data.ty_le_da_tra_loi_pct)}%`}</dd></div>
                <div><dt className="nhan">Hài lòng (1–5)</dt><dd className="text-2xl font-semibold tabular">{formatNumber(p.data.hai_long_tb)}</dd></div>
              </dl>
            )}
            <h3 className="mb-1 text-[15px] font-semibold">Cần đôn đốc</h3>
            <ul className="divide-y divide-[var(--vien)] text-[14px]">
              {(u.data ?? []).map((x) => (
                <li key={x.ma} className="flex items-start justify-between gap-3 py-2">
                  <div><div className="font-medium tabular">{x.ma}</div><div className="text-[12.5px] text-muc-nhat">{LOAI[x.loai_viec] ?? x.loai_viec}, nhận {formatDate(x.ngay_nhan)}, hạn {formatDate(x.han_xu_ly)}</div></div>
                  <span className={`shrink-0 text-[13px] font-medium ${x.muc === "qua_han" ? "text-son" : ""}`} style={x.muc === "qua_han" ? undefined : { color: "var(--tam-thoi)" }}>
                    {x.muc === "qua_han" ? `Quá hạn ${Math.abs(x.con_lai_ngay_lam_viec)} ngày làm việc` : `Còn ${x.con_lai_ngay_lam_viec} ngày làm việc`}
                  </span>
                </li>
              ))}
              {u.data?.length === 0 && <li className="py-2 text-muc-nhat">Không có phản ánh cần đôn đốc.</li>}
            </ul>
          </section>
        </div>
      )}
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-[rgba(15,36,54,0.35)]" />
          <Dialog.Content aria-describedby={undefined} className="fixed left-1/2 top-1/2 z-50 w-[min(560px,92vw)] -translate-x-1/2 -translate-y-1/2 rounded-md bg-be-mat p-6 shadow-2xl">
            <div className="mb-3 flex items-center justify-between"><Dialog.Title className="text-lg font-bold">Nhập số liệu hồ sơ TTHC</Dialog.Title>
              <Dialog.Close className="btn-phu" aria-label="Đóng"><X size={16} /></Dialog.Close></div>
            <ManualTthcForm onDone={() => { setOpen(false); qc.invalidateQueries({ queryKey: ["tthc"] }); }} />
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
