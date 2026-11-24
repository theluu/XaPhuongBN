import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Download, Info, Lock, Pencil, Plus, Search, Trash2, Upload, X } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { openFile } from "@/features/van-ban/VanBanPage";

interface Field { name: string; label: string; kind: string; required: boolean; options: Record<string, string> | null; cat: string | null; ref: string | null;
  readonly: boolean; create_only: boolean; list: boolean; help: string }
interface Schema { quyen_mo_ta?: string; them_link?: string | null; key: string; ten: string; nhom_phan_he: string; mo_ta: string; link: string | null; co_minh_hoa: boolean; them: boolean; sua: boolean; xoa: boolean;
  xac_nhan: { truong: string; khoa: string[]; ve: string } | null; truong: Field[] }
interface DsInfo extends Schema { so_ban_ghi: number; so_minh_hoa: number }
type Row = Record<string, unknown> & { id: number; is_sample?: boolean };
interface Page { schema: Schema; rows: Row[]; tong: number; trang: number; co_trang: number;
  lua_chon: { cat: Record<string, { value: string; label: string }[]>; ref: Record<string, { value: number; label: string }[]> } }

const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");

function show(f: Field, r: Row): string {
  const v = r[f.name];
  if (v === null || v === undefined || v === "") return "—";
  if (f.kind === "ref") return String(r[`${f.name}__nhan`] ?? v);
  if (f.kind === "enum") return f.options?.[String(v)] ?? String(v);
  if (f.kind === "multi") return Array.isArray(v) && v.length ? v.map((x) => f.options?.[String(x)] ?? String(x)).join(", ") : "Mọi người";
  if (f.kind === "bool") return v ? "Có" : "Không";
  if (f.kind === "refmulti") return Array.isArray(v) ? `${v.length} mục` : "—";
  if (f.kind === "file") return "Có tệp";
  if (f.kind === "dec" || f.kind === "int") return formatNumber(Number(v));
  if (f.kind === "date") return new Date(String(v)).toLocaleDateString("vi-VN");
  if (f.kind === "datetime") return new Date(String(v)).toLocaleString("vi-VN");
  return String(v);
}

function Input({ f, value, onChange, disabled, p }: { f: Field; value: unknown; onChange: (v: unknown) => void; disabled: boolean; p: Page }) {
  const common = { id: `f-${f.name}`, disabled, className: "o-nhap mt-1" };
  const sv = value === null || value === undefined ? "" : String(value);
  if (f.kind === "textarea") return <textarea {...common} rows={3} value={sv} onChange={(e) => onChange(e.target.value)} />;
  if (f.kind === "multi") {
    const arr = Array.isArray(value) ? (value as string[]) : [];
    return <span id={common.id} className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[13px] font-normal">{Object.entries(f.options ?? {}).map(([k, t]) => (
      <label key={k} className="flex items-center gap-1"><input type="checkbox" disabled={disabled} checked={arr.includes(k)}
        onChange={(e) => onChange(e.target.checked ? [...arr, k] : arr.filter((x) => x !== k))} />{t}</label>))}</span>;
  }
  if (f.kind === "refmulti") {
    const arr = Array.isArray(value) ? (value as number[]) : [];
    const opts = p.lua_chon.ref[f.ref ?? ""] ?? [];
    return <span id={common.id} className="mt-1 block max-h-40 overflow-auto rounded border border-vien px-2 py-1 text-[13px] font-normal">
      {opts.length === 0 && <span className="text-muc-nhat">Chưa có mục nào để chọn.</span>}
      {opts.map((o) => <label key={o.value} className="flex items-start gap-1.5 py-0.5"><input type="checkbox" className="mt-0.5" disabled={disabled} checked={arr.includes(o.value)}
        onChange={(e) => onChange(e.target.checked ? [...arr, o.value] : arr.filter((x) => x !== o.value))} />{o.label}</label>)}</span>;
  }
  if (f.kind === "file") return <FileInput id={common.id} value={value as string | null} onChange={onChange} disabled={disabled} />;
  if (f.kind === "time") return <input {...common} type="time" value={sv} onChange={(e) => onChange(e.target.value)} />;
  if (f.kind === "bool") return <input id={common.id} disabled={disabled} type="checkbox" className="mt-2 block" checked={!!value} onChange={(e) => onChange(e.target.checked)} />;
  if (f.kind === "enum") return <select {...common} value={sv} onChange={(e) => onChange(e.target.value)}>
    {!f.required && !Object.keys(f.options ?? {}).includes("") && <option value="">—</option>}
    {f.required && sv === "" && <option value="">Chọn…</option>}
    {Object.entries(f.options ?? {}).map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select>;
  if (f.kind === "cat") return <select {...common} value={sv} onChange={(e) => onChange(e.target.value)}>
    <option value="">{f.required ? "Chọn…" : "—"}</option>{(p.lua_chon.cat[f.cat ?? ""] ?? []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>;
  if (f.kind === "ref") return <select {...common} value={sv} onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}>
    <option value="">{f.required ? "Chọn…" : "—"}</option>{(p.lua_chon.ref[f.ref ?? ""] ?? []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>;
  const type = f.kind === "int" || f.kind === "dec" ? "text" : f.kind === "date" ? "date" : f.kind === "datetime" ? "datetime-local" : "text";
  const val = f.kind === "datetime" ? sv.slice(0, 16) : sv;
  return <input {...common} type={type} inputMode={f.kind === "int" || f.kind === "dec" ? "decimal" : undefined} placeholder={f.kind === "ky" ? "2026-10" : undefined}
    value={val} onChange={(e) => onChange(e.target.value)} />;
}

function FileInput({ id, value, onChange, disabled }: { id: string; value: string | null; onChange: (v: unknown) => void; disabled: boolean }) {
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function up(file: File) {
    setBusy(true); setErr(null);
    const fd = new FormData();
    fd.append("file", file);
    try { const r = await api<{ key: string }>("/api/files", { method: "POST", form: fd }); onChange(r.key); } catch (e) { setErr(errText(e)); } finally { setBusy(false); }
  }
  return (
    <span className="mt-1 block text-[13px] font-normal">
      {value ? <span className="flex items-center gap-2"><button type="button" className="lien-ket" onClick={() => openFile(value)}>Xem tệp đã tải</button>
        {!disabled && <button type="button" className="lien-ket text-son" onClick={() => onChange(null)}>Bỏ tệp</button>}</span> : <span className="text-muc-nhat">Chưa có tệp</span>}
      {!disabled && <input id={id} type="file" accept=".pdf,.doc,.docx,application/pdf" className="mt-1 block" disabled={busy} onChange={(e) => e.target.files?.[0] && up(e.target.files[0])} />}
      {busy && <span className="text-muc-nhat">Đang tải lên…</span>}{err && <span role="alert" className="block text-son">{err}</span>}
    </span>
  );
}

function Editor({ p, row, onDone, onCancel }: { p: Page; row: Row | null; onDone: (msg: string) => void; onCancel: () => void }) {
  const sc = p.schema;
  const creating = row === null;
  const [f, setF] = useState<Record<string, unknown>>(() => Object.fromEntries(sc.truong.map((x) => [x.name, row ? row[x.name] : x.kind === "bool" ? x.name === "hien_tren_tv" : x.kind === "multi" || x.kind === "refmulti" ? [] : null])));
  const [lyDo, setLyDo] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const locked = !creating && sc.xac_nhan && sc.xac_nhan.khoa.includes(String(row?.[sc.xac_nhan.truong]));
  const editable = (x: Field) => !x.readonly && !(x.create_only && !creating);
  const m = useMutation({
    mutationFn: () => {
      const data = Object.fromEntries(sc.truong.filter(editable).map((x) => [x.name, f[x.name]]));
      return creating ? api<Row>(`/api/du-lieu/${sc.key}`, { method: "POST", body: { data } })
        : api<Row & { can_xac_nhan_lai?: boolean }>(`/api/du-lieu/${sc.key}/${row!.id}`, { method: "PUT", body: { data, ly_do: lyDo } });
    },
    onSuccess: (r) => onDone(creating ? "Đã thêm bản ghi." : (r as { can_xac_nhan_lai?: boolean }).can_xac_nhan_lai ? "Đã lưu. Bản ghi chuyển về trạng thái chờ, cần xác nhận/đối soát lại." : "Đã lưu thay đổi."),
    onError: (e) => setErr(errText(e)),
  });
  return (
    <form aria-label={creating ? `Thêm ${sc.ten}` : `Sửa bản ghi ${row!.id}`} className="khu space-y-3 rounded-md p-4" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <div className="flex items-center"><h3 className="flex-1 font-semibold">{creating ? `Thêm: ${sc.ten}` : `Sửa bản ghi #${row!.id}`}</h3>
        <button type="button" aria-label="Đóng" className="btn-phu px-2 py-1" onClick={onCancel}><X size={15} /></button></div>
      {row?.is_sample && <p className="text-[13px] text-[var(--tam-thoi)]">Bản ghi minh họa: chỉnh sửa vẫn giữ cờ minh họa.</p>}
      <div className="grid gap-3 sm:grid-cols-2">
        {sc.truong.map((x) => (
          <label key={x.name} htmlFor={`f-${x.name}`} className={`text-sm font-medium ${x.kind === "textarea" ? "sm:col-span-2" : ""}`}>
            {x.label}{x.required && editable(x) && <span className="text-son"> *</span>}
            <Input f={x} value={f[x.name]} onChange={(v) => setF({ ...f, [x.name]: v })} disabled={!editable(x) || m.isPending} p={p} />
            {x.help && <span className="mt-0.5 block text-[12px] font-normal text-muc-nhat">{x.help}</span>}
          </label>
        ))}
      </div>
      {locked && (
        <div className="rounded border border-[var(--tam-thoi)] px-3 py-2 text-[13.5px]">
          <p>Bản ghi đã xác nhận/đối soát. Lưu thay đổi sẽ chuyển về trạng thái chờ và phải được xác nhận lại.</p>
          <label className="mt-1 block text-sm font-medium">Lý do sửa<span className="text-son"> *</span><input className="o-nhap mt-1" value={lyDo} onChange={(e) => setLyDo(e.target.value)} /></label>
        </div>
      )}
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <div className="flex gap-2"><button type="submit" className="btn-chinh py-1.5" disabled={m.isPending || (!!locked && !lyDo.trim())}>{creating ? "Thêm" : "Lưu"}</button>
        <button type="button" className="btn-phu py-1.5" onClick={onCancel}>Hủy</button></div>
    </form>
  );
}

function Table({ ds }: { ds: string }) {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  const [page, setPage] = useState(1);
  const [mh, setMh] = useState("");
  const [sel, setSel] = useState<number[]>([]);
  const [edit, setEdit] = useState<Row | null | "new">(null);
  const [del, setDel] = useState(false);
  const [lyDo, setLyDo] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const key = ["du-lieu", ds, term, page, mh];
  const pq = useQuery({ queryKey: key, queryFn: () => api<Page>(`/api/du-lieu/${ds}`, { params: { q: term || undefined, page, size: 50, minh_hoa: mh || undefined } }) });
  const refresh = () => { qc.invalidateQueries({ queryKey: ["du-lieu"] }); qc.invalidateQueries({ queryKey: ["du-lieu-cat"] }); };
  const rm = useMutation({ mutationFn: () => api<{ da_xoa: number }>(`/api/du-lieu/${ds}/xoa`, { method: "POST", body: { ids: sel, ly_do: lyDo } }),
    onSuccess: (r) => { setMsg(`Đã xóa ${r.da_xoa} bản ghi. Nội dung bản ghi đã xóa được lưu trong nhật ký.`); setSel([]); setDel(false); setLyDo(""); refresh(); },
    onError: (e) => setMsg(errText(e)) });
  const p = pq.data;
  if (!p?.schema) return <p className="text-muc-nhat">{pq.isError ? "Không tải được dữ liệu." : "Đang tải…"}</p>;
  const sc = p.schema;
  const cols = sc.truong.filter((f) => f.list);
  const pages = Math.max(1, Math.ceil(p.tong / p.co_trang));
  async function exportCsv() {
    const r = await fetch(`/api/du-lieu/${ds}/csv`, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
    if (!r.ok) return setMsg("Không xuất được tệp");
    const url = URL.createObjectURL(await r.blob());
    Object.assign(document.createElement("a"), { href: url, download: `${ds}.csv` }).click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="min-w-0 space-y-3">
      <div className="flex flex-wrap items-start gap-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-[17px] font-semibold">{sc.ten} <span className="text-[14px] font-normal text-muc-nhat">({formatNumber(p.tong)} bản ghi)</span></h2>
          {sc.mo_ta && <p className="text-[13.5px] text-muc-nhat">{sc.mo_ta}</p>}
          {(!sc.sua || !sc.xoa) && sc.quyen_mo_ta && (
            <p role="note" className={`mt-2 flex items-start gap-2 rounded-md border border-l-4 px-3 py-2 text-[13.5px] leading-snug ${sc.sua
              ? "border-[color-mix(in_srgb,var(--chinh)_35%,transparent)] border-l-[var(--chinh)] bg-[color-mix(in_srgb,var(--chinh)_8%,var(--be-mat))]"
              : "border-[color-mix(in_srgb,var(--tam-thoi)_40%,transparent)] border-l-[var(--tam-thoi)] bg-[color-mix(in_srgb,var(--tam-thoi)_12%,var(--be-mat))]"}`}>
              {sc.sua ? <Info size={17} aria-hidden className="mt-px shrink-0 text-[var(--chinh)]" /> : <Lock size={17} aria-hidden className="mt-px shrink-0 text-[var(--tam-thoi)]" />}
              <span><b className={sc.sua ? "text-[var(--chinh)]" : "text-[var(--tam-thoi)]"}>{sc.sua ? "Bạn được thêm, sửa nhưng không xóa." : "Bạn chỉ có quyền xem bộ dữ liệu này."}</b> {sc.quyen_mo_ta}</span></p>)}
        </div>
        {sc.link && <Link className="btn-phu py-1.5" to={sc.link}>Mở màn hình nghiệp vụ</Link>}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <form className="relative" onSubmit={(e) => { e.preventDefault(); setTerm(q); setPage(1); }}>
          <label className="sr-only" htmlFor="tim-du-lieu">Tìm</label><Search size={15} aria-hidden className="absolute left-2.5 top-2.5 text-muc-nhat" />
          <input id="tim-du-lieu" className="o-nhap w-64 py-1.5 pl-8" placeholder="Tìm theo mã, tên, kỳ…" value={q} onChange={(e) => setQ(e.target.value)} />
        </form>
        {sc.co_minh_hoa && <select aria-label="Lọc dữ liệu minh họa" className="o-nhap w-auto py-1.5" value={mh} onChange={(e) => { setMh(e.target.value); setPage(1); }}>
          <option value="">Tất cả</option><option value="khong">Chỉ dữ liệu thật</option><option value="co">Chỉ dữ liệu minh họa</option></select>}
        <span className="flex-1" />
        {sc.them && <button type="button" className="btn-chinh py-1.5" onClick={() => setEdit("new")}><Plus size={15} aria-hidden />Thêm</button>}
        {!sc.them && sc.them_link && <Link className="btn-chinh py-1.5" to={sc.them_link}><Plus size={15} aria-hidden />Thêm tại màn hình nghiệp vụ</Link>}
        {sc.them && <Link className="btn-phu py-1.5" to="/nhap-lieu?tab=excel"><Upload size={15} aria-hidden />Nhập Excel</Link>}
        <button type="button" className="btn-phu py-1.5" onClick={exportCsv}><Download size={15} aria-hidden />Xuất CSV</button>
        {sc.xoa && <button type="button" className="btn-phu py-1.5 text-son" disabled={!sel.length} onClick={() => setDel(true)}><Trash2 size={15} aria-hidden />Xóa ({sel.length})</button>}
      </div>
      {msg && <p role="status" className="rounded border border-vien bg-be-mat px-3 py-2 text-[14px]">{msg} <button type="button" className="lien-ket ml-2 text-[13px]" onClick={() => setMsg(null)}>Ẩn</button></p>}
      {del && (
        <form aria-label="Xác nhận xóa" className="flex flex-wrap items-end gap-2 rounded-md border border-son px-3 py-2" onSubmit={(e) => { e.preventDefault(); rm.mutate(); }}>
          <p className="w-full text-[14px]">Xóa vĩnh viễn {sel.length} bản ghi đã chọn. Không hoàn tác được; nội dung bản ghi được lưu trong nhật ký.</p>
          <label className="flex-1 text-sm font-medium">Lý do xóa<input className="o-nhap mt-1" value={lyDo} onChange={(e) => setLyDo(e.target.value)} placeholder="VD: nhập trùng, sai kỳ" /></label>
          <button type="submit" className="btn-chinh bg-son py-1.5" disabled={!lyDo.trim() || rm.isPending}>Xóa</button>
          <button type="button" className="btn-phu py-1.5" onClick={() => setDel(false)}>Hủy</button>
        </form>
      )}
      {edit !== null && <Editor key={edit === "new" ? "new" : edit.id} p={p} row={edit === "new" ? null : edit} onCancel={() => setEdit(null)}
        onDone={(m) => { setMsg(m); setEdit(null); refresh(); }} />}
      <div className="khu overflow-x-auto rounded-md">
        <table className="w-full text-[13.5px]" aria-label={sc.ten}>
          <thead><tr className="border-b border-vien text-left text-[12.5px] text-muc-nhat">
            {sc.xoa && <th className="w-8 px-3 py-2"><input type="checkbox" aria-label="Chọn tất cả" checked={p.rows.length > 0 && p.rows.every((r) => sel.includes(r.id))}
              onChange={(e) => setSel(e.target.checked ? [...new Set([...sel, ...p.rows.map((r) => r.id)])] : sel.filter((i) => !p.rows.some((r) => r.id === i)))} /></th>}
            {cols.map((f) => <th key={f.name} className={`px-2 py-2 font-medium ${f.kind === "dec" || f.kind === "int" ? "text-right" : ""}`}>{f.label}</th>)}
            <th className="px-3" />
          </tr></thead>
          <tbody>{p.rows.map((r) => (
            <tr key={r.id} className={`border-b border-vien ${sel.includes(r.id) ? "bg-be-mat-2" : ""}`}>
              {sc.xoa && <td className="px-3 py-1.5"><input type="checkbox" aria-label={`Chọn bản ghi ${r.id}`} checked={sel.includes(r.id)} onChange={(e) => setSel(e.target.checked ? [...sel, r.id] : sel.filter((i) => i !== r.id))} /></td>}
              {cols.map((f, i) => <td key={f.name} className={`px-2 py-1.5 ${f.kind === "dec" || f.kind === "int" ? "text-right tabular" : ""}`}>
                {show(f, r)}{i === 0 && r.is_sample && <span className="nhan-tt tt-cu ml-1.5">Minh họa</span>}</td>)}
              <td className="px-3 py-1.5 text-right">{sc.sua && <button type="button" className="lien-ket inline-flex items-center gap-1 text-[13px]" aria-label={`Sửa bản ghi ${r.id}`} onClick={() => setEdit(r)}><Pencil size={13} aria-hidden />Sửa</button>}</td>
            </tr>
          ))}
          {p.rows.length === 0 && <tr><td colSpan={cols.length + 2} className="px-3 py-6 text-center text-muc-nhat">Không có bản ghi.</td></tr>}</tbody>
        </table>
      </div>
      {pages > 1 && <div className="flex items-center justify-end gap-2 text-[13.5px]">
        <button type="button" className="btn-phu py-1" disabled={page <= 1} onClick={() => setPage(page - 1)}>Trước</button>
        <span>Trang {page}/{pages}</span>
        <button type="button" className="btn-phu py-1" disabled={page >= pages} onClick={() => setPage(page + 1)}>Sau</button></div>}
    </div>
  );
}

/** Quản lý dữ liệu tập trung: mọi bộ dữ liệu của đơn vị, thêm/sửa/xóa theo quyền nhóm dữ liệu, có nhật ký. */
export function DataAdminPage() {
  const [params, setParams] = useSearchParams();
  const cat = useQuery({ queryKey: ["du-lieu-cat"], queryFn: () => api<{ bo_du_lieu: DsInfo[] }>("/api/du-lieu") });
  const list = cat.data?.bo_du_lieu ?? [];
  const cur = params.get("bo") ?? list[0]?.key;
  const groups = [...new Set(list.map((d) => d.nhom_phan_he))];
  return (
    <>
      <PageHeader title="Quản lý dữ liệu" desc="Tất cả dữ liệu của đơn vị ở một nơi: tìm, thêm, sửa, xóa theo quyền từng nhóm dữ liệu. Sửa số đã xác nhận/đối soát sẽ phải xác nhận lại; xóa phải ghi lý do. Mọi thay đổi được ghi nhật ký." />
      {cat.data && !list.length ? <p className="text-muc-nhat">Tài khoản chưa được giao nhóm dữ liệu nào.</p> : (
        <div className="grid gap-4 lg:grid-cols-[250px_minmax(0,1fr)]">
          <label className="block lg:hidden"><span className="chu-nho-hoa">Bộ dữ liệu</span>
            <select className="o-nhap mt-1" value={cur ?? ""} onChange={(e) => setParams({ bo: e.target.value })}>
              {groups.map((g) => <optgroup key={g} label={g}>{list.filter((d) => d.nhom_phan_he === g).map((d) => <option key={d.key} value={d.key}>{d.ten} ({d.so_ban_ghi})</option>)}</optgroup>)}
            </select></label>
          <nav aria-label="Bộ dữ liệu" className="khu hidden h-fit rounded-md py-2 text-[13.5px] lg:block">
            {groups.map((g) => (
              <div key={g} className="mb-1">
                <p className="px-3 pb-0.5 pt-2 text-[11.5px] font-semibold uppercase tracking-wide text-muc-nhat">{g}</p>
                {list.filter((d) => d.nhom_phan_he === g).map((d) => (
                  <button key={d.key} type="button" aria-current={cur === d.key ? "page" : undefined} onClick={() => setParams({ bo: d.key })}
                    className={`flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-be-mat-2 ${cur === d.key ? "bg-be-mat-2 font-semibold shadow-[inset_3px_0_0_var(--chinh)]" : ""}`}>
                    <span className="flex-1">{d.ten}</span><span className="tabular text-[12px] text-muc-nhat">{formatNumber(d.so_ban_ghi)}</span>
                  </button>
                ))}
              </div>
            ))}
          </nav>
          {cur && <Table key={cur} ds={cur} />}
        </div>
      )}
    </>
  );
}
