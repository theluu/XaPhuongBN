import * as Tabs from "@radix-ui/react-tabs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError, getToken } from "@/lib/api";
import { formatDate, formatNumber, formatPeriod } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";

interface Val { id: number; ma: string; ten: string; nhom: string; don_vi: string; ky_bao_cao: string; gia_tri: number | null; nguon: string; don_vi_cung_cap: string;
  thoi_diem_chot: string; trang_thai: string; version: number; ly_do: string }
interface Col { ten: string; kieu: string; bat_buoc: boolean; lua_chon: string[]; goi_y: string }
interface Spec { loai: string; ten: string; huong_dan: string[]; cot: Col[] }
interface Preview { preview_id: number; hop_le: number; loi: { dong: number; cot: string; thong_bao: string }[] }

const LOAI: [string, string][] = [["chi_tieu", "Chỉ tiêu KT-XH"], ["ngan_sach", "Thu, chi ngân sách"], ["tthc", "Hồ sơ TTHC"], ["giai_ngan", "Giải ngân dự án"]];
const err = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");

function InboxItem({ v }: { v: Val }) {
  const qc = useQueryClient();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const act = useMutation({
    mutationFn: (kind: "confirm" | "reject") => api(`/api/values/${v.id}/${kind}`, { method: "POST", body: kind === "reject" ? { ly_do: reason } : undefined }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inbox"] }), onError: (e) => setMsg(err(e)),
  });
  return (
    <article className="khu rounded-md p-4">
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold">{v.ten}</h3>
          <p className="text-[13px] text-muc-nhat">{v.ma}, {formatPeriod(v.ky_bao_cao)}{v.version > 1 ? `, phiên bản ${v.version}: ${v.ly_do}` : ""}</p>
          <p className="text-[13px] text-muc-nhat">Nguồn: {v.nguon}. {v.don_vi_cung_cap}. Chốt {formatDate(v.thoi_diem_chot)}.</p>
        </div>
        <div className="text-right"><span className="font-so text-3xl font-semibold tabular">{formatNumber(v.gia_tri)}</span> <span className="text-muc-nhat">{v.don_vi}</span></div>
      </div>
      {msg && <p role="alert" className="mt-2 text-sm text-son">{msg}</p>}
      <div className="mt-3 flex flex-wrap items-end gap-2">
        <button type="button" className="btn-chinh" onClick={() => act.mutate("confirm")} disabled={act.isPending}>Xác nhận</button>
        {!rejecting ? <button type="button" className="btn-phu" onClick={() => setRejecting(true)}>Từ chối</button> : (
          <>
            <label className="min-w-[260px] flex-1 text-sm font-medium">Lý do từ chối<input className="o-nhap mt-1" value={reason} onChange={(e) => setReason(e.target.value)} /></label>
            <button type="button" className="btn-phu" disabled={!reason.trim()} onClick={() => act.mutate("reject")}>Gửi từ chối</button>
          </>
        )}
      </div>
    </article>
  );
}

async function download(loai: string) {
  const r = await fetch(`/api/import/templates/${loai}`, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
  if (!r.ok) return;
  const url = URL.createObjectURL(await r.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: `bieu_mau_${loai}.xlsx` });
  a.click();
  URL.revokeObjectURL(url);
}

function ImportWizard() {
  const qc = useQueryClient();
  const [loai, setLoai] = useState("chi_tieu");
  const [pv, setPv] = useState<Preview | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const up = useMutation({
    mutationFn: (f: File) => { const fd = new FormData(); fd.append("file", f); return api<Preview>(`/api/import/${loai}/preview`, { method: "POST", form: fd }); },
    onSuccess: (r) => { setPv(r); setMsg(null); }, onError: (e) => { setPv(null); setMsg(err(e)); },
  });
  const commit = useMutation({
    mutationFn: () => api<{ da_nhap: number }>(`/api/import/${loai}/commit`, { method: "POST", body: { preview_id: pv!.preview_id } }),
    onSuccess: (r) => { setMsg(`Đã nhập ${r.da_nhap} dòng ở trạng thái tạm thời, chờ xác nhận.`); setPv(null); qc.invalidateQueries(); }, onError: (e) => setMsg(err(e)),
  });
  return (
    <ol className="space-y-4">
      <li className="khu rounded-md p-4">
        <h3 className="font-semibold">Bước 1. Chọn loại số liệu và tải biểu mẫu</h3>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <select className="o-nhap w-auto" value={loai} onChange={(e) => { setLoai(e.target.value); setPv(null); }} aria-label="Loại số liệu">
            {LOAI.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
          </select>
          <button type="button" className="btn-phu" onClick={() => download(loai)}>Tải biểu mẫu Excel</button>
        </div>
      </li>
      <li className="khu rounded-md p-4">
        <h3 className="font-semibold">Bước 2. Tải tệp lên và xem lỗi</h3>
        <label className="mt-2 block text-sm">Chọn tệp Excel hoặc CSV
          <input type="file" accept=".xlsx,.csv" className="mt-1 block text-sm" onChange={(e) => e.target.files?.[0] && up.mutate(e.target.files[0])} />
        </label>
        {pv && (
          <div className="mt-3 text-[14px]">
            <p>{pv.hop_le} dòng hợp lệ, {pv.loi.length} lỗi.</p>
            {pv.loi.length > 0 && (
              <table aria-label="Lỗi trong tệp" className="mt-2 w-full">
                <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="py-1 font-medium">Vị trí</th><th className="font-medium">Lỗi</th></tr></thead>
                <tbody>{pv.loi.map((l) => <tr key={`${l.dong}-${l.cot}`} className="border-b border-vien"><td className="py-1 pr-3">Dòng {l.dong}, cột {l.cot}</td><td className="text-son">{l.thong_bao}</td></tr>)}</tbody>
              </table>
            )}
          </div>
        )}
      </li>
      <li className="khu rounded-md p-4">
        <h3 className="font-semibold">Bước 3. Nhập vào hệ thống</h3>
        <p className="text-[13px] text-muc-nhat">Chỉ nhập khi toàn bộ tệp không còn lỗi. Không dòng nào được nhập nếu tệp còn lỗi.</p>
        {msg && <p role="status" className="mt-2 text-[14px]">{msg}</p>}
        <button type="button" className="btn-chinh mt-2" disabled={!pv || pv.loi.length > 0 || pv.hop_le === 0 || commit.isPending} onClick={() => commit.mutate()}>Nhập vào hệ thống</button>
      </li>
    </ol>
  );
}

function DynamicForm({ loai, defaults }: { loai: string; defaults: Record<string, string> }) {
  const q = useQuery({ queryKey: ["spec", loai], queryFn: () => api<Spec>(`/api/import/templates/${loai}/spec`) });
  const [vals, setVals] = useState<Record<string, string>>(defaults);
  const [msg, setMsg] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: () => api<{ da_nhap: number }>(`/api/import/${loai}/rows`, { method: "POST", body: { rows: [vals] } }),
    onSuccess: () => { setMsg("Đã lưu ở trạng thái tạm thời, chờ xác nhận."); setVals(defaults); },
    onError: (e) => setMsg(e instanceof ApiError && typeof e.detail === "object" && e.detail && "loi" in e.detail
      ? (e.detail as { loi: { cot: string; thong_bao: string }[] }).loi.map((l) => `${l.cot}: ${l.thong_bao}`).join("; ") : err(e)),
  });
  if (!q.data) return <p className="text-muc-nhat">Đang tải biểu mẫu…</p>;
  const missing = q.data.cot.some((c) => c.bat_buoc && !vals[c.ten]?.trim());
  return (
    <form className="khu max-w-3xl rounded-md p-4" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <h3 className="mb-1 font-semibold">{q.data.ten}</h3>
      <ul className="mb-3 list-disc pl-5 text-[13px] text-muc-nhat">{q.data.huong_dan.map((h) => <li key={h}>{h}</li>)}</ul>
      <div className="grid gap-3 sm:grid-cols-2">
        {q.data.cot.map((c) => {
          const label = `${c.ten}${c.bat_buoc ? " *" : ""}`;
          const common = { className: "o-nhap mt-1", value: vals[c.ten] ?? "", onChange: (e: { target: { value: string } }) => setVals({ ...vals, [c.ten]: e.target.value }) };
          return (
            <label key={c.ten} className="text-sm font-medium">{label}
              {c.kieu === "lua_chon" ? (
                <select {...common}><option value="">— Chọn —</option>{c.lua_chon.map((o) => <option key={o} value={o}>{o}</option>)}</select>
              ) : c.kieu === "ngay" ? <input type="date" {...common} />
                : <input inputMode={c.kieu === "so" ? "decimal" : undefined} placeholder={c.goi_y} {...common} />}
            </label>
          );
        })}
      </div>
      {msg && <p role="status" className="mt-3 text-[14px]">{msg}</p>}
      <button type="submit" className="btn-chinh mt-3" disabled={missing || save.isPending}>Lưu số liệu</button>
    </form>
  );
}

interface Report { tong: number; dung_han: number; cham: number; thieu: number; chua_den_han: number; dung_han_pct: number | null; cham_pct: number | null; thieu_pct: number | null;
  theo_don_vi: { don_vi: string; dung_han: number; cham: number; thieu: number; dung_han_pct: number | null }[];
  theo_dau_moi?: { ma: string; ten: string; dung_han: number; cham: number; thieu: number; dung_han_pct: number | null }[];
  chi_tiet: { ma: string; ten: string; ky: string; han: string; ngay_nop: string | null; ket_qua: string; don_vi: string; dau_moi?: { ma: string; ten: string }[] }[] }
type DM = { ma: string; ten: string };

function Compliance() {
  const r = useQuery({ queryKey: ["compliance"], queryFn: () => api<Report>("/api/compliance") });
  const rem = useQuery({ queryKey: ["reminders"], queryFn: () => api<{ ma: string; ten: string; ky: string; han: string; con_lai_ngay: number; muc: string; dau_moi?: DM[]; cua_dau_moi_toi?: boolean }[]>("/api/reminders") });
  const d = r.data;
  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_1.3fr]">
      <section className="khu rounded-md p-4">
        <h3 className="mb-2 font-semibold">Việc nộp số của tôi</h3>
        <ul className="divide-y divide-[var(--vien)] text-[14px]">
          {(rem.data ?? []).map((x) => (
            <li key={x.ma + x.ky} className="flex justify-between gap-3 py-2"><span>{x.ten} ({formatPeriod(x.ky)})
              {!!x.dau_moi?.length && <span className="block text-[12.5px] text-muc-nhat">Đầu mối: {x.dau_moi.map((m) => m.ten).join(", ")}{x.cua_dau_moi_toi && <b className="text-chinh"> · của bạn</b>}</span>}</span>
              <span className={x.muc === "qua_han" ? "font-medium text-son" : ""}>{x.muc === "qua_han" ? `Quá hạn ${-x.con_lai_ngay} ngày` : `Hạn ${formatDate(x.han)}`}</span></li>
          ))}
          {rem.data?.length === 0 && <li className="py-2 text-muc-nhat">Không có số liệu sắp đến hạn.</li>}
        </ul>
      </section>
      <section className="khu rounded-md p-4">
        <h3 className="mb-2 font-semibold">Tình hình nộp số liệu (120 ngày)</h3>
        {d && (
          <>
            <p className="text-[14px]">{d.tong} kỳ đã đến hạn: đúng hạn {d.dung_han_pct === null ? "—" : `${formatNumber(d.dung_han_pct)}%`}, chậm {formatNumber(d.cham_pct)}%, thiếu {formatNumber(d.thieu_pct)}%.</p>
            <table aria-label="Nộp số theo đơn vị" className="mt-2 w-full text-[14px]">
              <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="py-1 font-medium">Đơn vị</th><th className="text-right font-medium">Đúng hạn</th><th className="text-right font-medium">Chậm</th><th className="text-right font-medium">Thiếu</th></tr></thead>
              <tbody>{d.theo_don_vi.map((x) => <tr key={x.don_vi} className="border-b border-vien"><td className="py-1">{x.don_vi}</td><td className="text-right tabular">{x.dung_han}</td><td className="text-right tabular">{x.cham}</td><td className="text-right tabular text-son">{x.thieu}</td></tr>)}</tbody>
            </table>
            {!!d.theo_dau_moi?.length && (
              <table aria-label="Nộp số theo đầu mối" className="mt-4 w-full text-[14px]">
                <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="py-1 font-medium">Đầu mối cung cấp (mục V.1)</th><th className="text-right font-medium">Đúng hạn</th><th className="text-right font-medium">Chậm</th><th className="text-right font-medium">Thiếu</th></tr></thead>
                <tbody>{d.theo_dau_moi.map((x) => <tr key={x.ma} className="border-b border-vien"><td className="py-1"><Link className="lien-ket" to={`/co-cau-to-chuc?tab=dau-moi#dm-${x.ma}`}>{x.ten}</Link></td><td className="text-right tabular">{x.dung_han}</td><td className="text-right tabular">{x.cham}</td><td className="text-right tabular text-son">{x.thieu}</td></tr>)}</tbody>
              </table>
            )}
          </>
        )}
      </section>
    </div>
  );
}

export function DataEntryPage() {
  const [params, setParams] = useSearchParams();
  const ma = params.get("ma");
  const tab = params.get("tab") ?? (ma ? "bieu-mau" : "xac-nhan");
  const loai = params.get("loai") ?? "chi_tieu";
  const inbox = useQuery({ queryKey: ["inbox"], queryFn: () => api<Val[]>("/api/values/inbox"), enabled: tab === "xac-nhan" });
  const defaults: Record<string, string> = ma ? { "Mã chỉ tiêu": ma, "Kỳ báo cáo": params.get("ky") ?? "" } : {};
  return (
    <>
      <PageHeader title="Nhập liệu và xác nhận" desc="Số liệu nhập vào ở trạng thái Tạm thời. Cán bộ có thẩm quyền xác nhận thì mới trở thành số chính thức; người nhập không tự xác nhận số của mình." />
      <Tabs.Root value={tab} onValueChange={(t) => setParams({ tab: t })}>
        <Tabs.List aria-label="Nhập liệu" className="mb-4 flex flex-wrap gap-1 border-b border-vien">
          {[["xac-nhan", "Chờ tôi xác nhận"], ["excel", "Nhập từ Excel/CSV"], ["bieu-mau", "Biểu mẫu trực tuyến"], ["tuan-thu", "Hạn nộp và tuân thủ"]].map(([k, t]) => (
            <Tabs.Trigger key={k} value={k} className="-mb-px border-b-2 border-transparent px-3 py-2 text-[14.5px] text-muc-nhat data-[state=active]:border-muc data-[state=active]:font-semibold data-[state=active]:text-muc">{t}</Tabs.Trigger>
          ))}
        </Tabs.List>
        <Tabs.Content value="xac-nhan" className="space-y-3">
          {(inbox.data ?? []).map((v) => <InboxItem key={v.id} v={v} />)}
          {inbox.data?.length === 0 && <p className="text-muc-nhat">Không có số liệu nào đang chờ bạn xác nhận.</p>}
        </Tabs.Content>
        <Tabs.Content value="excel"><ImportWizard /></Tabs.Content>
        <Tabs.Content value="bieu-mau">
          <label className="mb-3 flex items-center gap-2 text-sm"><span className="text-muc-nhat">Loại số liệu</span>
            <select className="o-nhap w-auto" value={loai} onChange={(e) => setParams({ tab: "bieu-mau", loai: e.target.value })}>{LOAI.map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select>
          </label>
          <DynamicForm key={loai + (ma ?? "")} loai={loai} defaults={loai === "chi_tieu" ? defaults : {}} />
        </Tabs.Content>
        <Tabs.Content value="tuan-thu"><Compliance /></Tabs.Content>
      </Tabs.Root>
    </>
  );
}
