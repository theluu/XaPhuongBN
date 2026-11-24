import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, BellRing, FileText, Image as ImageIcon, MessageSquarePlus, Paperclip, Search, Send, Stamp, UserPlus, X } from "lucide-react";
import { api, ApiError, getToken } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";

export interface Person { id: number; ho_ten: string; chuc_danh: string; don_vi: string; username: string }
interface Conv { id: number; tieu_de: string; loai: string; lien_ket_loai: string | null; lien_ket_ten: string | null; lien_ket_url: string | null; so_thanh_vien: number;
  chua_doc: number; cuoi: { nguoi: string; noi_dung: string; luc: string; he_thong: boolean } | null; cap_nhat_luc: string; is_sample: boolean }
interface Tep { key: string; ten: string; content_type: string; kich_thuoc: number }
interface CongVan { id: number; so_ky_hieu: string; trich_yeu: string; loai: string; ngay_ban_hanh: string; han_thuc_hien: string | null; co_quan_ban_hanh: string; nguoi_ky: string }
interface Msg { id: number; nguoi_gui: Person; cua_toi: boolean; noi_dung: string; gui_luc: string; he_thong: boolean; tep: Tep[]; cong_van: CongVan | null }
interface Thread { id: number; tieu_de: string; loai: string; lien_ket_loai: string | null; lien_ket_ten: string | null; lien_ket_url: string | null; thanh_vien: Person[];
  phat_hanh_cong_van: boolean; tin: Msg[] }

const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");
const LK: Record<string, string> = { canh_bao: "Cảnh báo", phan_anh: "Phản ánh" };
const LOAI_CV: Record<string, string> = { cong_van: "Công văn", thong_bao: "Thông báo kết luận", chi_thi: "Chỉ thị", quyet_dinh: "Quyết định", ke_hoach: "Kế hoạch" };
const size = (n: number) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
const time = (s: string) => { const d = new Date(s); const today = new Date().toDateString() === d.toDateString();
  return today ? d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }) : d.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); };

export function useUnread() {
  return useQuery({ queryKey: ["tin-nhan-chua-doc"], queryFn: () => api<{ tong: number }>("/api/tin-nhan/chua-doc"), refetchInterval: 20_000 });
}

async function openTep(t: Tep) {
  const r = await fetch(`/api/tin-nhan/tep/${t.key}`, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
  if (!r.ok) return;
  const url = URL.createObjectURL(await r.blob());
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

function TepChip({ t }: { t: Tep }) {
  const img = t.content_type.startsWith("image/");
  return (
    <button type="button" onClick={() => openTep(t)} className="flex max-w-full items-center gap-2 rounded-md border border-vien bg-be-mat px-2.5 py-1.5 text-left text-[13px] hover:bg-be-mat-2">
      {img ? <ImageIcon size={16} aria-hidden className="shrink-0 text-[var(--chinh)]" /> : <FileText size={16} aria-hidden className="shrink-0 text-son" />}
      <span className="min-w-0 truncate">{t.ten}</span><span className="shrink-0 text-muc-nhat">{size(t.kich_thuoc)}</span>
    </button>
  );
}

function PeoplePicker({ ppl, value, onChange }: { ppl: Person[]; value: number[]; onChange: (v: number[]) => void }) {
  const [q, setQ] = useState("");
  const rows = ppl.filter((p) => !q || `${p.ho_ten} ${p.chuc_danh} ${p.don_vi}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <label className="relative block"><span className="sr-only">Tìm người nhận</span><Search size={15} aria-hidden className="absolute left-2.5 top-2.5 text-muc-nhat" />
        <input className="o-nhap py-1.5 pl-8" placeholder="Tìm theo tên, chức danh, đơn vị" value={q} onChange={(e) => setQ(e.target.value)} /></label>
      <ul className="mt-1.5 max-h-56 overflow-auto rounded border border-vien" aria-label="Danh sách người nhận">{rows.map((p) => (
        <li key={p.id}><label className="flex cursor-pointer items-start gap-2 px-2.5 py-1.5 text-[13.5px] hover:bg-be-mat-2">
          <input type="checkbox" className="mt-1" checked={value.includes(p.id)} onChange={(e) => onChange(e.target.checked ? [...value, p.id] : value.filter((i) => i !== p.id))} />
          <span><b className="font-medium">{p.ho_ten}</b><span className="block text-[12.5px] text-muc-nhat">{[p.chuc_danh, p.don_vi].filter(Boolean).join(" · ")}</span></span></label></li>
      ))}</ul>
    </div>
  );
}

function NewConv({ ppl, ctx, onDone, onCancel }: { ppl: Person[]; ctx: { loai: string; id: number; ten?: string; goi_y?: string } | null; onDone: (id: number) => void; onCancel: () => void }) {
  const pre = ctx?.goi_y ? ppl.filter((p) => p.ho_ten === ctx.goi_y).map((p) => p.id) : [];
  const [ids, setIds] = useState<number[]>(pre);
  const [title, setTitle] = useState(ctx?.ten ?? "");
  const [err, setErr] = useState<string | null>(null);
  const m = useMutation({ mutationFn: () => api<{ id: number }>("/api/tin-nhan/hoi-thoai", { method: "POST", body: {
    thanh_vien_ids: ids, tieu_de: ctx ? title : (ids.length > 1 ? title : ""), lien_ket_loai: ctx?.loai ?? null, lien_ket_id: ctx?.id ?? null } }),
    onSuccess: (r) => onDone(r.id), onError: (e) => setErr(errText(e)) });
  return (
    <form aria-label="Trao đổi mới" className="khu space-y-3 rounded-md p-4" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <div className="flex items-center"><h2 className="flex-1 text-[16px] font-semibold">Trao đổi mới</h2>
        <button type="button" className="btn-phu px-2 py-1" aria-label="Đóng" onClick={onCancel}><X size={15} /></button></div>
      {ctx && <p className="flex items-start gap-2 rounded border border-l-4 border-[color-mix(in_srgb,var(--son)_30%,transparent)] border-l-[var(--son)] bg-[color-mix(in_srgb,var(--son)_7%,var(--be-mat))] px-3 py-2 text-[13.5px]">
        <BellRing size={16} aria-hidden className="mt-0.5 shrink-0 text-son" /><span>Gắn với {LK[ctx.loai]?.toLowerCase()}: <b>{ctx.ten}</b></span></p>}
      {(ctx || ids.length > 1) && <label className="block text-sm font-medium">Tiêu đề<input className="o-nhap mt-1" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="VD: Xử lý thu ngân sách chậm" /></label>}
      <div><span className="text-sm font-medium">Người nhận ({ids.length})</span>{ctx?.goi_y && pre.length > 0 && <span className="ml-2 text-[12.5px] text-muc-nhat">Đã chọn sẵn người phụ trách: {ctx.goi_y}</span>}
        <PeoplePicker ppl={ppl} value={ids} onChange={setIds} /></div>
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <button type="submit" className="btn-chinh" disabled={!ids.length || m.isPending}>Bắt đầu trao đổi</button>
    </form>
  );
}

function Composer({ th, onSent }: { th: Thread; onSent: () => void }) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState<Tep[]>([]);
  const [busy, setBusy] = useState(false);
  const [cv, setCv] = useState<null | { so_ky_hieu: string; trich_yeu: string; loai: string; han_thuc_hien: string }>(null);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  async function upload(list: FileList) {
    setBusy(true); setErr(null);
    try {
      for (const f of Array.from(list)) {
        const fd = new FormData(); fd.append("file", f);
        const r = await api<Tep>("/api/tin-nhan/tep", { method: "POST", form: fd });
        setFiles((x) => [...x, { ...r, ten: r.ten || f.name }]);
      }
    } catch (e) { setErr(errText(e)); } finally { setBusy(false); if (fileRef.current) fileRef.current.value = ""; }
  }
  const hasDoc = files.some((f) => f.content_type === "application/pdf" || f.content_type.includes("wordprocessingml"));
  const m = useMutation({
    mutationFn: () => api(`/api/tin-nhan/hoi-thoai/${th.id}/tin`, { method: "POST", body: { noi_dung: text, tep_keys: files.map((f) => f.key),
      cong_van: cv ? { ...cv, han_thuc_hien: cv.han_thuc_hien || null } : null } }),
    onSuccess: () => { setText(""); setFiles([]); setCv(null); setErr(null); onSent(); }, onError: (e) => setErr(errText(e)) });
  const ready = !m.isPending && !busy && (text.trim() || files.length || cv) && (!cv || (cv.so_ky_hieu.trim() && cv.trich_yeu.trim() && hasDoc));
  return (
    <form aria-label="Soạn tin" className="space-y-2 border-t border-vien p-3" onSubmit={(e) => { e.preventDefault(); if (ready) m.mutate(); }}>
      {cv && (
        <fieldset className="space-y-2 rounded-md border border-l-4 border-[color-mix(in_srgb,var(--son)_30%,transparent)] border-l-[var(--son)] bg-[color-mix(in_srgb,var(--son)_6%,var(--be-mat))] p-3">
          <legend className="px-1 text-[13.5px] font-semibold text-son">Công văn xử lý — vào sổ Văn bản chỉ đạo khi gửi</legend>
          <div className="grid gap-2 sm:grid-cols-[1fr_1fr_10rem]">
            <label className="text-[13px] font-medium">Số, ký hiệu<input className="o-nhap mt-0.5 py-1" placeholder="215/UBND-KT" value={cv.so_ky_hieu} onChange={(e) => setCv({ ...cv, so_ky_hieu: e.target.value })} /></label>
            <label className="text-[13px] font-medium">Loại<select className="o-nhap mt-0.5 py-1" value={cv.loai} onChange={(e) => setCv({ ...cv, loai: e.target.value })}>
              {Object.entries(LOAI_CV).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label className="text-[13px] font-medium">Hạn xử lý<input type="date" className="o-nhap mt-0.5 py-1" value={cv.han_thuc_hien} onChange={(e) => setCv({ ...cv, han_thuc_hien: e.target.value })} /></label>
          </div>
          <label className="block text-[13px] font-medium">Trích yếu<input className="o-nhap mt-0.5 py-1" placeholder="V/v đôn đốc thu tiền sử dụng đất" value={cv.trich_yeu} onChange={(e) => setCv({ ...cv, trich_yeu: e.target.value })} /></label>
          {!hasDoc && <p className="text-[12.5px] text-son">Đính kèm tệp công văn (PDF hoặc Word) bằng nút kẹp giấy.</p>}
        </fieldset>
      )}
      {files.length > 0 && <div className="flex flex-wrap gap-2">{files.map((f) => (
        <span key={f.key} className="flex items-center gap-1 rounded-md border border-vien bg-be-mat-2 px-2 py-1 text-[12.5px]">
          <Paperclip size={13} aria-hidden />{f.ten}<button type="button" aria-label={`Bỏ tệp ${f.ten}`} className="ml-1 text-muc-nhat hover:text-son" onClick={() => setFiles(files.filter((x) => x.key !== f.key))}><X size={13} /></button></span>
      ))}</div>}
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <div className="flex items-end gap-2">
        <input ref={fileRef} type="file" multiple hidden accept=".pdf,.doc,.docx,.xlsx,image/png,image/jpeg,image/webp" onChange={(e) => e.target.files?.length && upload(e.target.files)} aria-label="Chọn tệp" />
        <button type="button" className="btn-phu px-2.5" title="Đính kèm tệp" aria-label="Đính kèm tệp" disabled={busy} onClick={() => fileRef.current?.click()}><Paperclip size={17} /></button>
        {th.phat_hanh_cong_van && <button type="button" className={`btn-phu px-2.5 ${cv ? "text-son" : ""}`} aria-pressed={!!cv} title="Gửi kèm công văn xử lý" aria-label="Gửi kèm công văn xử lý"
          onClick={() => setCv(cv ? null : { so_ky_hieu: "", trich_yeu: th.lien_ket_ten ? `V/v xử lý: ${th.lien_ket_ten}` : "", loai: "cong_van", han_thuc_hien: "" })}><Stamp size={17} /></button>}
        <label className="min-w-0 flex-1"><span className="sr-only">Nội dung tin nhắn</span>
          <textarea className="o-nhap max-h-40 min-h-[42px] resize-y py-2" rows={1} placeholder={busy ? "Đang tải tệp…" : "Nhập tin nhắn — Enter để gửi, Shift+Enter xuống dòng"} value={text}
            onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (ready) m.mutate(); } }} /></label>
        <button type="submit" className="btn-chinh px-3" disabled={!ready} aria-label="Gửi"><Send size={17} /></button>
      </div>
    </form>
  );
}

function ThreadView({ id, ppl, onBack }: { id: number; ppl: Person[]; onBack?: () => void }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["tin-nhan-hoi-thoai", id], queryFn: () => api<Thread>(`/api/tin-nhan/hoi-thoai/${id}`), refetchInterval: 5000 });
  const [adding, setAdding] = useState(false);
  const [add, setAdd] = useState<number[]>([]);
  const end = useRef<HTMLDivElement>(null);
  const th = q.data;
  const n = th?.tin.length ?? 0;
  useEffect(() => { end.current?.scrollIntoView?.({ block: "end" }); qc.invalidateQueries({ queryKey: ["tin-nhan-list"] }); qc.invalidateQueries({ queryKey: ["tin-nhan-chua-doc"] }); }, [n, qc]);
  const addM = useMutation({ mutationFn: () => api(`/api/tin-nhan/hoi-thoai/${id}/thanh-vien`, { method: "POST", body: { user_ids: add } }),
    onSuccess: () => { setAdding(false); setAdd([]); qc.invalidateQueries({ queryKey: ["tin-nhan-hoi-thoai", id] }); } });
  if (!th?.tin) return <div className="p-6 text-muc-nhat">{q.isError ? "Không mở được cuộc trao đổi." : "Đang tải…"}</div>;
  const others = ppl.filter((p) => !th.thanh_vien.some((t) => t.id === p.id));
  return (
    <section aria-label={`Trao đổi: ${th.tieu_de}`} className="flex h-full min-h-0 flex-col">
      <header className="border-b border-vien px-4 py-2.5">
        <div className="flex items-start gap-2">
          {onBack && <button type="button" className="btn-phu -ml-1 px-2 py-1 lg:hidden" aria-label="Quay lại danh sách" onClick={onBack}><ArrowLeft size={16} /></button>}
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-[16px] font-semibold">{th.tieu_de}</h2>
            <p className="truncate text-[12.5px] text-muc-nhat">{th.thanh_vien.map((p) => p.ho_ten).join(", ")}</p>
          </div>
          {th.loai !== "truc_tiep" && <button type="button" className="btn-phu px-2 py-1 text-[13px]" onClick={() => setAdding(!adding)} aria-label="Thêm người"><UserPlus size={15} aria-hidden /><span className="hidden sm:inline">Thêm người</span></button>}
        </div>
        {th.lien_ket_url && <Link to={th.lien_ket_url} className="mt-1.5 inline-flex items-center gap-1.5 rounded border border-[color-mix(in_srgb,var(--son)_30%,transparent)] bg-[color-mix(in_srgb,var(--son)_7%,var(--be-mat))] px-2 py-0.5 text-[12.5px] text-son hover:underline">
          <BellRing size={13} aria-hidden />{LK[th.lien_ket_loai ?? ""] ?? "Liên quan"}: {th.lien_ket_ten}</Link>}
        {adding && <div className="mt-2 space-y-2"><PeoplePicker ppl={others} value={add} onChange={setAdd} />
          <button type="button" className="btn-chinh py-1.5" disabled={!add.length || addM.isPending} onClick={() => addM.mutate()}>Thêm {add.length || ""} người</button></div>}
      </header>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-nen px-4 py-3" aria-live="polite">
        {th.tin.length === 0 && <p className="py-8 text-center text-[14px] text-muc-nhat">Chưa có tin nhắn. Gửi tin đầu tiên bên dưới.</p>}
        {th.tin.map((m) => m.he_thong
          ? <p key={m.id} className="text-center text-[12.5px] text-muc-nhat">{m.noi_dung} · {time(m.gui_luc)}</p>
          : (
            <div key={m.id} className={`flex ${m.cua_toi ? "justify-end" : "justify-start"}`}>
              <article aria-label={`Tin của ${m.nguoi_gui.ho_ten}`} className={`max-w-[88%] space-y-1.5 sm:max-w-[78%] rounded-lg px-3 py-2 shadow-sm ${m.cua_toi ? "bg-[color-mix(in_srgb,var(--chinh)_12%,var(--be-mat))]" : "bg-be-mat"}`}>
                {!m.cua_toi && <p className="text-[12.5px] font-semibold text-[var(--chinh)]">{m.nguoi_gui.ho_ten}<span className="font-normal text-muc-nhat"> · {m.nguoi_gui.chuc_danh}</span></p>}
                {m.cong_van && (
                  <div className="rounded-md border border-l-4 border-[color-mix(in_srgb,var(--son)_30%,transparent)] border-l-[var(--son)] bg-be-mat px-3 py-2 text-[13.5px]">
                    <p className="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide text-son"><Stamp size={13} aria-hidden />{LOAI_CV[m.cong_van.loai] ?? "Công văn"} xử lý</p>
                    <p className="font-semibold">Số {m.cong_van.so_ky_hieu} · {formatDate(m.cong_van.ngay_ban_hanh)}</p>
                    <p>{m.cong_van.trich_yeu}</p>
                    <p className="text-[12.5px] text-muc-nhat">{m.cong_van.co_quan_ban_hanh} · {m.cong_van.nguoi_ky}{m.cong_van.han_thuc_hien && <b className="text-son"> · Hạn {formatDate(m.cong_van.han_thuc_hien)}</b>}</p>
                    <Link to="/van-ban" className="lien-ket text-[12.5px]">Xem trong sổ Văn bản chỉ đạo</Link>
                  </div>
                )}
                {m.noi_dung && <p className="whitespace-pre-wrap break-words text-[14px]">{m.noi_dung}</p>}
                {m.tep.length > 0 && <div className="flex flex-col gap-1.5">{m.tep.map((t) => <TepChip key={t.key} t={t} />)}</div>}
                <p className="text-right text-[11.5px] text-muc-nhat">{time(m.gui_luc)}</p>
              </article>
            </div>
          ))}
        <div ref={end} />
      </div>
      <Composer th={th} onSent={() => { qc.invalidateQueries({ queryKey: ["tin-nhan-hoi-thoai", id] }); qc.invalidateQueries({ queryKey: ["tin-nhan-list"] }); }} />
    </section>
  );
}

/** Tin nhắn nội bộ: trao đổi theo việc (cảnh báo, phản ánh), gửi tệp và công văn xử lý. */
export function MessagesPage() {
  const [params, setParams] = useSearchParams();
  const list = useQuery({ queryKey: ["tin-nhan-list"], queryFn: () => api<Conv[]>("/api/tin-nhan/hoi-thoai"), refetchInterval: 15_000 });
  const dir = useQuery({ queryKey: ["tin-nhan-nguoi"], queryFn: () => api<{ nguoi: Person[]; phat_hanh_cong_van: boolean }>("/api/tin-nhan/nguoi-nhan") });
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);
  const sel = Number(params.get("id")) || null;
  const lkLoai = params.get("lien_ket");
  const lkId = Number(params.get("lien_ket_id")) || null;
  const ctx = useMemo(() => (lkLoai && lkId ? { loai: lkLoai, id: lkId, ten: params.get("ten") ?? "", goi_y: params.get("goi_y") ?? undefined } : null), [lkLoai, lkId, params]);
  // Mở từ một cảnh báo/phản ánh: có sẵn cuộc trao đổi gắn việc đó thì mở, chưa có thì tạo mới
  useEffect(() => {
    if (!ctx || !list.data) return;
    const url = ctx.loai === "canh_bao" ? `/canh-bao?id=${ctx.id}` : `/phan-anh?id=${ctx.id}`;
    const found = list.data.find((c) => c.lien_ket_url === url);
    if (found) setParams({ id: String(found.id) }, { replace: true }); else setCreating(true);
  }, [ctx, list.data]); // eslint-disable-line react-hooks/exhaustive-deps
  const convs = (list.data ?? []).filter((c) => !q || `${c.tieu_de} ${c.lien_ket_ten ?? ""}`.toLowerCase().includes(q.toLowerCase()));
  const ppl = dir.data?.nguoi ?? [];
  return (
    <>
      <PageHeader title="Tin nhắn" desc="Trao đổi nội bộ giữa cán bộ trong đơn vị: gửi tin, tệp; lãnh đạo gửi kèm công văn xử lý ngay từ cảnh báo, phản ánh. Chỉ người trong cuộc trao đổi đọc được tin và tệp.">
        <button type="button" className="btn-chinh" onClick={() => { setCreating(true); setParams({}); }}><MessageSquarePlus size={16} aria-hidden />Trao đổi mới</button>
      </PageHeader>
      <div className="grid h-[calc(100dvh-230px)] min-h-[460px] grid-cols-1 gap-4 lg:h-[calc(100vh-300px)] lg:grid-cols-[330px_minmax(0,1fr)]">
        <aside className={`khu min-h-0 flex-col rounded-md ${sel || creating ? "hidden lg:flex" : "flex"}`}>
          <label className="relative m-2"><span className="sr-only">Tìm cuộc trao đổi</span><Search size={15} aria-hidden className="absolute left-2.5 top-2.5 text-muc-nhat" />
            <input className="o-nhap py-1.5 pl-8" placeholder="Tìm cuộc trao đổi" value={q} onChange={(e) => setQ(e.target.value)} /></label>
          <ul className="min-h-0 flex-1 overflow-y-auto" aria-label="Cuộc trao đổi">
            {convs.map((c) => (
              <li key={c.id}><button type="button" onClick={() => { setCreating(false); setParams({ id: String(c.id) }); }} aria-current={sel === c.id ? "true" : undefined}
                className={`w-full border-b border-vien px-3 py-2.5 text-left hover:bg-be-mat-2 ${sel === c.id ? "bg-be-mat-2 shadow-[inset_3px_0_0_var(--chinh)]" : ""}`}>
                <div className="flex items-start gap-2">
                  <span className={`min-w-0 flex-1 truncate text-[14px] ${c.chua_doc ? "font-bold" : "font-medium"}`}>{c.tieu_de}</span>
                  {c.cuoi && <span className="shrink-0 text-[11.5px] text-muc-nhat">{time(c.cuoi.luc)}</span>}
                </div>
                {c.lien_ket_loai && <span className="mt-0.5 inline-flex items-center gap-1 text-[11.5px] font-semibold text-son"><BellRing size={11} aria-hidden />{LK[c.lien_ket_loai]}</span>}
                <div className="flex items-center gap-2"><span className={`min-w-0 flex-1 truncate text-[12.5px] ${c.chua_doc ? "text-muc" : "text-muc-nhat"}`}>
                  {c.cuoi ? `${c.cuoi.he_thong ? "" : `${c.cuoi.nguoi}: `}${c.cuoi.noi_dung}` : "Chưa có tin nhắn"}</span>
                  {c.chua_doc > 0 && <span className="shrink-0 rounded-full bg-son px-1.5 text-[11px] font-bold text-white">{c.chua_doc}</span>}</div>
              </button></li>
            ))}
            {list.data && convs.length === 0 && <li className="px-3 py-6 text-center text-[13.5px] text-muc-nhat">Chưa có cuộc trao đổi nào.</li>}
          </ul>
        </aside>
        <div className={`khu min-h-0 overflow-hidden rounded-md ${sel || creating ? "" : "hidden lg:block"}`}>
          {creating && dir.data ? <div className="h-full overflow-y-auto p-3"><NewConv ppl={ppl} ctx={ctx} onCancel={() => { setCreating(false); setParams({}); }}
            onDone={(id) => { setCreating(false); setParams({ id: String(id) }); list.refetch(); }} /></div>
            : sel ? <ThreadView key={sel} id={sel} ppl={ppl} onBack={() => setParams({})} />
            : <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-muc-nhat"><MessageSquarePlus size={36} aria-hidden />
              <p className="text-[14px]">Chọn một cuộc trao đổi bên trái, hoặc bấm <b>Trao đổi mới</b>.</p>
              <p className="text-[13px]">Từ một cảnh báo, bấm <b>Nhắn tin, gửi công văn</b> để trao đổi ngay với người phụ trách.</p></div>}
        </div>
      </div>
    </>
  );
}

/** Nút mở trao đổi gắn với một cảnh báo/phản ánh, chọn sẵn người phụ trách. */
export function MessageButton({ loai, id, ten, goiY }: { loai: "canh_bao" | "phan_anh"; id: number; ten: string; goiY?: string | null }) {
  const p = new URLSearchParams({ lien_ket: loai, lien_ket_id: String(id), ten });
  if (goiY) p.set("goi_y", goiY);
  return <Link to={`/tin-nhan?${p.toString()}`} className="btn-phu"><Send size={15} aria-hidden />Nhắn tin, gửi công văn</Link>;
}
