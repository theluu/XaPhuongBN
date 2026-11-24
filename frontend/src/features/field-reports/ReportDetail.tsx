import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageButton } from "@/features/tin-nhan/MessagesPage";
import { useState } from "react";
import { Link } from "react-router-dom";
import { MapPin, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatDateTime } from "@/lib/format";
import { AuthImage } from "@/components/AuthImage";
import { LocationPicker } from "@/components/LocationPicker";
import { DeadlineTag, NoLocationTag, UrgentTag } from "@/components/StatusTag";
import { HANH_DONG, type Catalogs, type FieldReport } from "@/features/operations/types";
import { headOf, useOrg } from "@/features/org/types";
import { AssigneePicker, type Assignee } from "@/features/org/AssigneePicker";

/** Liên hệ đơn vị và cán bộ phụ trách (từ Cơ cấu tổ chức). */
function UnitContact({ ma, nguoi }: { ma: string | null; nguoi: string | null }) {
  const org = useOrg();
  const d = org.data;
  if (!d?.don_vi || !ma) return null;
  const unit = d.don_vi.find((u) => u.ma === ma);
  const person = d.can_bo.find((x) => nguoi && x.ho_ten.toLowerCase() === nguoi.toLowerCase()) ?? headOf(d, ma);
  const phone = person?.dien_thoai ?? unit?.dien_thoai;
  if (!phone) return null;
  return (
    <div className="text-[12.5px] text-muc-nhat">
      Liên hệ: {person ? `${person.ho_ten} (${person.chuc_vu})` : unit?.ten} ·{" "}
      <a className="lien-ket" href={`tel:${phone.replace(/\s/g, "")}`}>{phone}</a>
      {" · "}<Link className="lien-ket" to={`/co-cau-to-chuc?don_vi=${ma}`}>Xem đơn vị</Link>
    </div>
  );
}

const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");
const today = () => new Date().toISOString().slice(0, 10);

export function useCatalogs() {
  return useQuery({ queryKey: ["danh-muc"], queryFn: () => api<Catalogs>("/api/dieu-hanh/danh-muc"), staleTime: 300_000 });
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[130px_1fr] gap-2 py-1.5 text-[14px]">
      <dt className="text-muc-nhat">{label}</dt><dd className="min-w-0">{children}</dd>
    </div>
  );
}

function AssignForm({ r, cat, onDone }: { r: FieldReport; cat: Catalogs; onDone: (x: FieldReport) => void }) {
  const unit0 = r.don_vi_phu_trach ?? cat.phong_ban[0]?.ma ?? "";
  const [who, setWho] = useState<Assignee>({ unitMa: unit0, unitTen: cat.phong_ban.find((p) => p.ma === unit0)?.ten ?? "", nguoi: r.nguoi_phu_trach ?? "" });
  const [f, setF] = useState({ han_xu_ly: r.han_xu_ly && r.han_xu_ly >= today() ? r.han_xu_ly : today(), chi_dao: r.chi_dao ?? "" });
  const [err, setErr] = useState<string | null>(null);
  const m = useMutation({ mutationFn: () => api<FieldReport>(`/api/phan-anh/${r.id}/giao`, { method: "POST",
    body: { don_vi_phu_trach: who.unitMa, nguoi_phu_trach: who.nguoi.trim(), ...f } }), onSuccess: onDone, onError: (e) => setErr(errText(e)) });
  return (
    <form className="space-y-2" aria-label="Giao xử lý" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <AssigneePicker value={who} onChange={setWho} units={cat.phong_ban.map((p) => p.ma)} unitLabel="Đơn vị phụ trách" />
      <label className="block text-sm font-medium">Hạn xử lý<input type="date" className="o-nhap mt-1" min={today()} value={f.han_xu_ly} onChange={(e) => setF({ ...f, han_xu_ly: e.target.value })} /></label>
      <label className="block text-sm font-medium">Ý kiến chỉ đạo<textarea className="o-nhap mt-1" rows={2} value={f.chi_dao} onChange={(e) => setF({ ...f, chi_dao: e.target.value })} /></label>
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <button type="submit" className="btn-chinh" disabled={m.isPending || !who.unitMa}>{r.trang_thai === "moi" ? "Giao xử lý" : "Giao lại"}</button>
    </form>
  );
}

function ProgressForm({ r, onDone }: { r: FieldReport; onDone: (x: FieldReport) => void }) {
  const [pct, setPct] = useState(r.tien_do_pct);
  const [note, setNote] = useState("");
  const [kq, setKq] = useState(r.ket_qua ?? "");
  const [err, setErr] = useState<string | null>(null);
  const m = useMutation({ mutationFn: (done: boolean) => api<FieldReport>(`/api/phan-anh/${r.id}/tien-do`, { method: "POST",
    body: done ? { bao_cao_hoan_thanh: true, ket_qua: kq, ghi_chu: note } : { tien_do_pct: pct, ghi_chu: note, ket_qua: kq || undefined } }),
    onSuccess: (x) => { setNote(""); setErr(null); onDone(x); }, onError: (e) => setErr(errText(e)) });
  return (
    <div className="space-y-2" role="group" aria-label="Cập nhật tiến độ">
      <label className="block text-sm font-medium">Tiến độ: {pct}%
        <input type="range" min={0} max={100} step={10} value={pct} onChange={(e) => setPct(Number(e.target.value))} className="mt-1 w-full" /></label>
      <label className="block text-sm font-medium">Nội dung cập nhật<textarea className="o-nhap mt-1" rows={2} value={note} onChange={(e) => setNote(e.target.value)} /></label>
      <label className="block text-sm font-medium">Kết quả xử lý (bắt buộc khi báo cáo hoàn thành)<textarea className="o-nhap mt-1" rows={2} value={kq} onChange={(e) => setKq(e.target.value)} /></label>
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-chinh" disabled={m.isPending} onClick={() => m.mutate(false)}>Cập nhật tiến độ</button>
        <button type="button" className="btn-phu" disabled={m.isPending || !kq.trim()} onClick={() => m.mutate(true)}>Báo cáo hoàn thành</button>
      </div>
    </div>
  );
}

function ConfirmForm({ r, onDone }: { r: FieldReport; onDone: (x: FieldReport) => void }) {
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const m = useMutation({ mutationFn: (dong_y: boolean) => api<FieldReport>(`/api/phan-anh/${r.id}/xac-nhan`, { method: "POST", body: { dong_y, ghi_chu: note } }),
    onSuccess: onDone, onError: (e) => setErr(errText(e)) });
  return (
    <div className="space-y-2" role="group" aria-label="Xác nhận kết quả">
      <p className="text-[14px]">Kết quả báo cáo: <b>{r.ket_qua}</b></p>
      <label className="block text-sm font-medium">Ghi chú (bắt buộc khi trả lại)<textarea className="o-nhap mt-1" rows={2} value={note} onChange={(e) => setNote(e.target.value)} /></label>
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <div className="flex gap-2">
        <button type="button" className="btn-chinh bg-[var(--xac-nhan)]" disabled={m.isPending} onClick={() => m.mutate(true)}>Xác nhận đã xử lý</button>
        <button type="button" className="btn-phu" disabled={m.isPending || !note.trim()} onClick={() => m.mutate(false)}>Trả lại xử lý tiếp</button>
      </div>
    </div>
  );
}

function LocateForm({ r, onDone }: { r: FieldReport; onDone: (x: FieldReport) => void }) {
  const { tenant } = useAuth();
  const [open, setOpen] = useState(false);
  const [v, setV] = useState<{ lat: number; lng: number } | null>(null);
  const m = useMutation({ mutationFn: () => api<FieldReport>(`/api/phan-anh/${r.id}/vi-tri`, { method: "PATCH", body: { lat: v?.lat ?? null, lng: v?.lng ?? null } }), onSuccess: onDone });
  if (!open) return <button type="button" className="btn-phu py-1" onClick={() => setOpen(true)}><MapPin size={14} aria-hidden />Xác định vị trí</button>;
  return (
    <div className="space-y-2">
      <LocationPicker value={v} center={tenant?.ban_do?.tam ?? [21.2725, 106.0975]} onChange={setV} tileUrl={tenant?.ban_do?.tile_url} />
      <button type="button" className="btn-chinh" disabled={!v || m.isPending} onClick={() => m.mutate()}>Lưu vị trí</button>
    </div>
  );
}

/** Khung chi tiết (§2): ảnh hiện trường, địa chỉ, đơn vị phụ trách, hạn, lịch sử; nút thao tác theo quyền. */
export function ReportDetail({ id, onClose }: { id: number; onClose: () => void }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["phan-anh", id], queryFn: () => api<FieldReport>(`/api/phan-anh/${id}`) });
  const cat = useCatalogs();
  const [tab, setTab] = useState<"giao" | "tien_do" | null>(null);
  const r = q.data;
  const done = (x: FieldReport) => {
    qc.setQueryData(["phan-anh", id], x);
    qc.invalidateQueries({ queryKey: ["dieu-hanh"] });
    qc.invalidateQueries({ queryKey: ["phan-anh-list"] });
    setTab(null);
  };
  return (
    <aside aria-label="Chi tiết phản ánh" className="khu flex h-full flex-col rounded-md">
      <div className="flex items-start gap-2 border-b border-vien px-4 py-3">
        <div className="min-w-0 flex-1">
          <div className="text-[12.5px] text-muc-nhat">{r?.ma ?? "…"} · {r?.linh_vuc_ten}</div>
          <h2 className="text-[16px] font-semibold leading-snug">{r?.tieu_de ?? "Đang tải…"}</h2>
          {r && <div className="mt-1 flex flex-wrap gap-1.5">{r.khan_cap && <UrgentTag />}<DeadlineTag han={r.han_xu_ly} quaHan={r.qua_han_ngay} trangThai={r.trang_thai} />
            <span className="nhan-tt tt-cu">{r.trang_thai_ten}</span>{!r.co_vi_tri && <NoLocationTag />}</div>}
        </div>
        <button type="button" className="btn-phu px-2 py-1" onClick={onClose} aria-label="Đóng chi tiết"><X size={16} /></button>
      </div>
      {r && (
        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-3">
          {(r.anh_keys?.length ?? 0) > 0 && (
            <div className="grid grid-cols-3 gap-2">{r.anh_keys!.map((k) => <AuthImage key={k} fileKey={k} alt="Ảnh hiện trường" className="h-24 w-full rounded object-cover" />)}</div>
          )}
          <dl className="divide-y divide-[var(--vien)]">
            <Row label="Địa chỉ">{r.dia_chi || "—"}{r.tdp_ten && <span className="text-muc-nhat"> ({r.tdp_ten})</span>}</Row>
            <Row label="Nội dung">{r.mo_ta || "—"}</Row>
            <Row label="Nguồn tiếp nhận">{r.nguon_ten} · {formatDateTime(r.tiep_nhan_luc)}</Row>
            {"nguoi_gui_ten" in r && <Row label="Người phản ánh">{r.nguoi_gui_ten || "Không ghi"}{r.nguoi_gui_sdt && ` · ${r.nguoi_gui_sdt}`}</Row>}
            <Row label="Đơn vị phụ trách">{r.don_vi_phu_trach_ten ?? "Chưa giao"}{r.nguoi_phu_trach && ` · ${r.nguoi_phu_trach}`}
              <UnitContact ma={r.don_vi_phu_trach} nguoi={r.nguoi_phu_trach} /></Row>
            <Row label="Hạn xử lý">{formatDate(r.han_xu_ly)}</Row>
            <Row label="Trao đổi"><MessageButton loai="phan_anh" id={r.id} ten={`${r.ma} – ${r.tieu_de}`} goiY={r.nguoi_phu_trach} /></Row>
            {r.chi_dao && <Row label="Chỉ đạo">{r.chi_dao}</Row>}
            <Row label="Tiến độ"><div className="flex items-center gap-2"><div className="h-2 flex-1 rounded bg-be-mat-2"><div className="h-2 rounded bg-chinh" style={{ width: `${r.tien_do_pct}%` }} /></div><span className="tabular text-[13px]">{r.tien_do_pct}%</span></div></Row>
            {r.ket_qua && <Row label="Kết quả">{r.ket_qua}</Row>}
          </dl>

          {!r.co_vi_tri && r.quyen?.cap_nhat && <LocateForm r={r} onDone={done} />}
          {(r.quyen?.giao || r.quyen?.cap_nhat) && cat.data && (
            <div className="rounded-md border border-vien p-3">
              <div className="mb-2 flex gap-2">
                {r.quyen?.giao && <button type="button" className={tab === "giao" ? "btn-chinh py-1" : "btn-phu py-1"} onClick={() => setTab(tab === "giao" ? null : "giao")}>{r.trang_thai === "moi" ? "Giao xử lý" : "Giao lại / đổi hạn"}</button>}
                {r.quyen?.cap_nhat && <button type="button" className={tab === "tien_do" ? "btn-chinh py-1" : "btn-phu py-1"} onClick={() => setTab(tab === "tien_do" ? null : "tien_do")}>Cập nhật tiến độ</button>}
              </div>
              {tab === "giao" && <AssignForm r={r} cat={cat.data} onDone={done} />}
              {tab === "tien_do" && <ProgressForm r={r} onDone={done} />}
            </div>
          )}
          {r.quyen?.xac_nhan && <div className="rounded-md border border-vien p-3"><ConfirmForm r={r} onDone={done} /></div>}

          <section aria-label="Lịch sử xử lý">
            <h3 className="mb-1 the-tieu-de">Lịch sử xử lý</h3>
            <ol className="border-l-2 border-vien pl-3">
              {[...(r.lich_su ?? [])].reverse().map((h, i) => (
                <li key={i} className="relative pb-2.5 text-[13.5px]">
                  <span aria-hidden className="absolute -left-[17px] top-1.5 h-2 w-2 rounded-full bg-chinh" />
                  <div className="font-medium">{HANH_DONG[h.hanh_dong] ?? h.hanh_dong}{h.tien_do !== undefined && ` · ${h.tien_do}%`}</div>
                  <div className="text-[12.5px] text-muc-nhat">{formatDateTime(h.luc)} · {h.nguoi}{h.don_vi && ` · ${h.don_vi}`}{h.han && ` · hạn ${formatDate(h.han)}`}</div>
                  {h.ghi_chu && <div className="text-[13px]">{h.ghi_chu}</div>}
                </li>
              ))}
            </ol>
          </section>
        </div>
      )}
    </aside>
  );
}
