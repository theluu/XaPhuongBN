import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import { NHOM, ROLE } from "@/features/platform-admin/labels";

export interface TrachNhiem { nhom: string; vai_tro: string; vai_tro_ten?: string; noi_dung: string }
export interface Account { id: number; username: string; ho_ten: string; chuc_danh: string; trang_thai: string; roles: string[]; nhom: string[] }
export interface ViecTre { ma: string; ten: string; ky: string; han: string; con_lai_ngay: number; muc: string }
export interface DauMoiRow {
  id: number; ma: string; ten: string; cap: string; cap_ten: string; noi_dung: string; trach_nhiem: TrachNhiem[]; phieu_nguon: { ma: string; ten: string; toi_thieu?: string }[];
  chi_tieu: string[]; nguon: string[]; nguoi_lien_he: string; chuc_vu: string; dien_thoai: string | null; email: string | null; tai_khoan: Account[];
  thu_tu: number; viec_tre: ViecTre[]; so_qua_han: number;
}
export interface DauMoiData { toi_thieu_chung?: string; dau_moi: DauMoiRow[]; vai_tro: Record<string, string>; cap: Record<string, string>; phieu: Record<string, string>; nhom: string[]; cua_toi: string[] }

export const NHOM_TN: Record<string, string> = { chung: "Chung, kỹ thuật", ...NHOM };
const VT_MAU: Record<string, string> = { chu_tri: "bg-[var(--chinh)] text-white", phoi_hop: "bg-be-mat-2 text-muc border border-vien",
  cung_cap: "bg-[color-mix(in_srgb,var(--xac-nhan)_14%,transparent)] text-[var(--xac-nhan)]", xac_nhan: "bg-[color-mix(in_srgb,var(--tam-thoi)_16%,transparent)] text-[var(--tam-thoi)]" };
const VT_TAT: Record<string, string> = { chu_tri: "CT", phoi_hop: "PH", cung_cap: "CC", xac_nhan: "XN" };
const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");

export function useDauMoi() {
  return useQuery({ queryKey: ["dau-moi"], queryFn: () => api<DauMoiData>("/api/dau-moi") });
}

function RoleChip({ vt, ten }: { vt: string; ten?: string }) {
  return <span title={ten} className={`inline-block rounded px-1.5 py-0.5 text-[11.5px] font-semibold ${VT_MAU[vt] ?? ""}`}>{VT_TAT[vt] ?? vt}</span>;
}

function Contact({ d }: { d: DauMoiRow }) {
  return (
    <div className="text-[13px] leading-snug">
      {d.nguoi_lien_he && <div className="font-medium">{d.nguoi_lien_he}</div>}
      {d.chuc_vu && <div className="text-muc-nhat">{d.chuc_vu}</div>}
      {d.dien_thoai && <a className="lien-ket" href={`tel:${d.dien_thoai.replace(/\s/g, "")}`}>{d.dien_thoai}</a>}
      {d.email && <div><a className="lien-ket break-all" href={`mailto:${d.email}`}>{d.email}</a></div>}
      {!d.nguoi_lien_he && !d.dien_thoai && <span className="text-muc-nhat">Chưa có người liên hệ</span>}
    </div>
  );
}

/** Ma trận trách nhiệm: nhóm dữ liệu × đầu mối (CT chủ trì, PH phối hợp, CC cung cấp, XN xác nhận). */
function Matrix({ d }: { d: DauMoiData }) {
  const cols = d.nhom;
  return (
    <div className="khu overflow-x-auto rounded-md">
      <table className="w-full text-[13.5px]" aria-label="Ma trận trách nhiệm">
        <thead><tr className="border-b border-vien text-left text-[12px] text-muc-nhat">
          <th className="px-3 py-2 font-medium">Đầu mối</th>{cols.map((n) => <th key={n} className="px-1.5 py-2 text-center font-medium">{NHOM_TN[n] ?? n}</th>)}</tr></thead>
        <tbody>{d.dau_moi.map((x) => (
          <tr key={x.ma} className="border-b border-vien">
            <td className="px-3 py-1.5"><a href={`#dm-${x.ma}`} className="lien-ket">{x.ten}</a> <span className="text-[11.5px] text-muc-nhat">{x.cap_ten}</span></td>
            {cols.map((n) => {
              const ts = x.trach_nhiem.filter((t) => t.nhom === n);
              return <td key={n} className="px-1.5 py-1.5 text-center"><span className="inline-flex flex-wrap justify-center gap-0.5">{ts.map((t, i) => <RoleChip key={i} vt={t.vai_tro} ten={`${t.vai_tro_ten}: ${t.noi_dung}`} />)}</span></td>;
            })}
          </tr>
        ))}</tbody>
      </table>
      <p className="flex flex-wrap gap-3 px-3 py-2 text-[12px] text-muc-nhat">{Object.entries(d.vai_tro).map(([k, v]) => <span key={k} className="flex items-center gap-1"><RoleChip vt={k} />{v}</span>)}</p>
    </div>
  );
}

function Editor({ x, onDone, onCancel }: { x?: DauMoiRow; onDone: () => void; onCancel: () => void }) {
  const users = useQuery({ queryKey: ["admin-users"], queryFn: () => api<Account[]>("/api/admin/users") });
  const [f, setF] = useState({
    ma: x?.ma ?? "", ten: x?.ten ?? "", cap: x?.cap ?? "chuyen_nganh", noi_dung: x?.noi_dung ?? "",
    trach_nhiem: x?.trach_nhiem.map(({ nhom, vai_tro, noi_dung }) => ({ nhom, vai_tro, noi_dung })) ?? [{ nhom: "ktxh", vai_tro: "cung_cap", noi_dung: "" }],
    phieu_nguon: x?.phieu_nguon.map((p) => p.ma) ?? [], chi_tieu: (x?.chi_tieu ?? []).join(", "), nguon: (x?.nguon ?? []).join(", "),
    nguoi_lien_he: x?.nguoi_lien_he ?? "", chuc_vu: x?.chuc_vu ?? "", dien_thoai: x?.dien_thoai ?? "", email: x?.email ?? "",
    user_ids: x?.tai_khoan.map((a) => a.id) ?? [],
  });
  const [err, setErr] = useState<string | null>(null);
  const list = (s: string) => s.split(/[,\s]+/).map((v) => v.trim()).filter(Boolean);
  const m = useMutation({
    mutationFn: () => api(x ? `/api/dau-moi/${x.ma}` : "/api/dau-moi", { method: x ? "PUT" : "POST",
      body: { ...f, chi_tieu: list(f.chi_tieu), nguon: list(f.nguon), dien_thoai: f.dien_thoai || null, email: f.email || null } }),
    onSuccess: onDone, onError: (e) => setErr(errText(e)) });
  const setTn = (i: number, k: keyof TrachNhiem, v: string) => setF({ ...f, trach_nhiem: f.trach_nhiem.map((t, j) => (j === i ? { ...t, [k]: v } : t)) });
  // tài khoản nền tảng đã gắn (không nằm trong danh sách đơn vị) vẫn giữ nguyên
  const extra = (x?.tai_khoan ?? []).filter((a) => !(users.data ?? []).some((u) => u.id === a.id));
  return (
    <form aria-label={x ? `Sửa đầu mối ${x.ten}` : "Thêm đầu mối"} className="space-y-3 rounded-md border border-vien bg-be-mat-2 p-4" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <div className="grid gap-3 sm:grid-cols-4">
        <label className="text-sm font-medium">Mã<input className="o-nhap mt-1 uppercase" value={f.ma} onChange={(e) => setF({ ...f, ma: e.target.value })} /></label>
        <label className="text-sm font-medium sm:col-span-2">Tên cơ quan, đơn vị<input className="o-nhap mt-1" value={f.ten} onChange={(e) => setF({ ...f, ten: e.target.value })} /></label>
        <label className="text-sm font-medium">Cấp<select className="o-nhap mt-1" value={f.cap} onChange={(e) => setF({ ...f, cap: e.target.value })}>
          {[["phuong", "Phường"], ["thanh_pho", "Thành phố"], ["chuyen_nganh", "Cơ quan chuyên ngành"], ["chu_dau_tu", "Chủ đầu tư"]].map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      </div>
      <label className="block text-sm font-medium">Trách nhiệm chung<textarea className="o-nhap mt-1" rows={2} value={f.noi_dung} onChange={(e) => setF({ ...f, noi_dung: e.target.value })} /></label>
      <fieldset className="space-y-2"><legend className="text-sm font-semibold">Trách nhiệm theo nhóm dữ liệu</legend>
        {f.trach_nhiem.map((t, i) => (
          <div key={i} className="flex flex-wrap items-end gap-2">
            <label className="text-[13px]">Nhóm<select aria-label={`Nhóm ${i + 1}`} className="o-nhap mt-0.5 w-auto py-1" value={t.nhom} onChange={(e) => setTn(i, "nhom", e.target.value)}>
              {Object.entries(NHOM_TN).filter(([k]) => k !== "canh_bao" && k !== "quan_tri").map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label className="text-[13px]">Vai trò<select aria-label={`Vai trò ${i + 1}`} className="o-nhap mt-0.5 w-auto py-1" value={t.vai_tro} onChange={(e) => setTn(i, "vai_tro", e.target.value)}>
              {Object.entries({ chu_tri: "Chủ trì", phoi_hop: "Phối hợp", cung_cap: "Cung cấp số liệu", xac_nhan: "Xác nhận" }).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label className="min-w-[220px] flex-1 text-[13px]">Nội dung<input aria-label={`Nội dung ${i + 1}`} className="o-nhap mt-0.5 py-1" value={t.noi_dung} onChange={(e) => setTn(i, "noi_dung", e.target.value)} /></label>
            <button type="button" className="lien-ket text-[13px] text-son" onClick={() => setF({ ...f, trach_nhiem: f.trach_nhiem.filter((_, j) => j !== i) })}>Bỏ</button>
          </div>
        ))}
        <button type="button" className="lien-ket text-[13px]" onClick={() => setF({ ...f, trach_nhiem: [...f.trach_nhiem, { nhom: "ktxh", vai_tro: "phoi_hop", noi_dung: "" }] })}>+ Thêm trách nhiệm</button>
      </fieldset>
      <fieldset className="flex flex-wrap gap-x-4 gap-y-1 text-[13.5px]"><legend className="mb-1 text-sm font-semibold">Phiếu xác định nguồn (Phụ lục 02)</legend>
        {Object.entries({ A: "Chỉ tiêu KT-XH", B: "Thu, chi ngân sách", C: "Đầu tư công", D: "Tiến độ công trình", E: "Đô thị, môi trường", F: "An sinh, GD, YT", G: "Hành chính, PAKN", H: "Tài khoản người dùng" }).map(([k, v]) => (
          <label key={k} className="flex items-center gap-1"><input type="checkbox" checked={f.phieu_nguon.includes(k)} onChange={(e) => setF({ ...f, phieu_nguon: e.target.checked ? [...f.phieu_nguon, k] : f.phieu_nguon.filter((p) => p !== k) })} />{k}. {v}</label>
        ))}
      </fieldset>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm font-medium">Mã chỉ tiêu cung cấp/xác nhận<input className="o-nhap mt-1 font-mono text-[13px]" placeholder="NQ01-12, NQ01-14" value={f.chi_tieu} onChange={(e) => setF({ ...f, chi_tieu: e.target.value })} /></label>
        <label className="text-sm font-medium">Mã nguồn dữ liệu<input className="o-nhap mt-1 font-mono text-[13px]" placeholder="KHO_DL_DAN_CU" value={f.nguon} onChange={(e) => setF({ ...f, nguon: e.target.value })} /></label>
        <label className="text-sm font-medium">Người liên hệ<input className="o-nhap mt-1" value={f.nguoi_lien_he} onChange={(e) => setF({ ...f, nguoi_lien_he: e.target.value })} /></label>
        <label className="text-sm font-medium">Chức vụ<input className="o-nhap mt-1" value={f.chuc_vu} onChange={(e) => setF({ ...f, chuc_vu: e.target.value })} /></label>
        <label className="text-sm font-medium">Điện thoại<input className="o-nhap mt-1" value={f.dien_thoai} onChange={(e) => setF({ ...f, dien_thoai: e.target.value })} /></label>
        <label className="text-sm font-medium">Email<input className="o-nhap mt-1" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
      </div>
      <fieldset><legend className="mb-1 text-sm font-semibold">Tài khoản gắn với đầu mối</legend>
        <div className="grid max-h-48 gap-1 overflow-auto text-[13.5px] sm:grid-cols-2">
          {extra.map((a) => <label key={a.id} className="flex items-center gap-1.5 text-muc-nhat"><input type="checkbox" checked={f.user_ids.includes(a.id)}
            onChange={(e) => setF({ ...f, user_ids: e.target.checked ? [...f.user_ids, a.id] : f.user_ids.filter((i) => i !== a.id) })} />{a.ho_ten} ({a.username})</label>)}
          {(users.data ?? []).filter((u) => u.trang_thai === "hoat_dong").map((u) => (
            <label key={u.id} className="flex items-center gap-1.5"><input type="checkbox" checked={f.user_ids.includes(u.id)}
              onChange={(e) => setF({ ...f, user_ids: e.target.checked ? [...f.user_ids, u.id] : f.user_ids.filter((i) => i !== u.id) })} />{u.ho_ten} <span className="text-muc-nhat">({u.username})</span></label>
          ))}
        </div>
        <p className="mt-1 text-[12.5px] text-muc-nhat">Cơ quan ngoài phường cần tài khoản riêng: tạo ở Quản trị → Người dùng với vai trò “Cơ quan chuyên ngành” và nhóm dữ liệu được giao, rồi gắn vào đây.</p>
      </fieldset>
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <div className="flex gap-2"><button type="submit" className="btn-chinh py-1.5" disabled={m.isPending || !f.ma.trim() || !f.ten.trim()}>Lưu</button>
        <button type="button" className="btn-phu py-1.5" onClick={onCancel}>Hủy</button></div>
    </form>
  );
}

function Card({ x, edit, mine, onEdit, onDelete }: { x: DauMoiRow; edit: boolean; mine: boolean; onEdit: () => void; onDelete: () => void }) {
  return (
    <article id={`dm-${x.ma}`} aria-label={x.ten} className={`khu rounded-md p-4 ${mine ? "ring-2 ring-[var(--chinh)]" : ""}`}>
      <div className="flex flex-wrap items-start gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-[15.5px] font-semibold leading-snug">{x.ten} {mine && <span className="ml-1 rounded bg-chinh px-1.5 py-0.5 text-[11.5px] font-semibold text-white">Đầu mối của bạn</span>}</h3>
          <p className="text-[12.5px] text-muc-nhat">{x.cap_ten} · mã {x.ma}</p>
        </div>
        {x.so_qua_han > 0 && <span className="nhan-tt tt-qua-han">{x.so_qua_han} kỳ quá hạn nộp</span>}
        {edit && <><button type="button" className="lien-ket text-[13px]" onClick={onEdit}>Sửa</button><button type="button" className="lien-ket text-[13px] text-son" onClick={onDelete}>Xóa</button></>}
      </div>
      {x.noi_dung && <p className="mt-2 text-[13.5px]">{x.noi_dung}</p>}
      <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div>
          <ul className="space-y-1 text-[13.5px]">{x.trach_nhiem.map((t, i) => (
            <li key={i} className="flex gap-2"><RoleChip vt={t.vai_tro} ten={t.vai_tro_ten} /><span><b>{t.vai_tro_ten}</b> · {NHOM_TN[t.nhom] ?? t.nhom}{t.noi_dung && <>: {t.noi_dung}</>}</span></li>
          ))}</ul>
          {(x.chi_tieu.length > 0 || x.nguon.length > 0 || x.phieu_nguon.length > 0) && (
            <p className="mt-2 text-[12.5px] text-muc-nhat">
              {x.phieu_nguon.length > 0 && <>Phiếu nguồn: {x.phieu_nguon.map((p) => `${p.ma}. ${p.ten}`).join("; ")}. </>}
              {x.chi_tieu.length > 0 && <>Chỉ tiêu: {x.chi_tieu.map((m, i) => <span key={m}>{i > 0 && ", "}<Link className="lien-ket" to={`/chi-tieu?ma=${m}`}>{m}</Link></span>)}. </>}
              {x.nguon.length > 0 && <>Nguồn: <Link className="lien-ket" to="/nguon-du-lieu">{x.nguon.join(", ")}</Link>.</>}
            </p>
          )}
        </div>
        <div className="space-y-2">
          <Contact d={x} />
          <div className="text-[13px]"><div className="text-[12px] font-medium text-muc-nhat">Tài khoản trên hệ thống</div>
            {x.tai_khoan.length ? <ul>{x.tai_khoan.map((a) => <li key={a.id}><b>{a.username}</b> – {a.ho_ten} <span className="text-muc-nhat">({a.roles.map((r) => ROLE[r] ?? (r === "quan_tri_nen_tang" ? "Quản trị nền tảng" : r)).join(", ")}{a.nhom.length && !a.nhom.includes("*") ? `: ${a.nhom.map((n) => NHOM[n] ?? n).join(", ")}` : ""})</span></li>)}</ul>
              : <span className="text-muc-nhat">Chưa gắn tài khoản (dữ liệu nhận qua API/tệp hoặc cán bộ phường nhập thay)</span>}
          </div>
        </div>
      </div>
      {x.phieu_nguon.some((p) => p.toi_thieu) && (
        <details className="mt-3 text-[13px]"><summary className="cursor-pointer font-medium">Thông tin tối thiểu phải gửi (Phụ lục 02)</summary>
          <ul className="mt-1 space-y-0.5">{x.phieu_nguon.map((p) => <li key={p.ma}><b>{p.ma}. {p.ten}:</b> {p.toi_thieu}</li>)}</ul>
        </details>
      )}
      {x.viec_tre.length > 0 && (
        <details className="mt-3 text-[13px]"><summary className="cursor-pointer font-medium">Kỳ số liệu sắp đến hạn/quá hạn ({x.viec_tre.length})</summary>
          <ul className="mt-1 space-y-0.5">{x.viec_tre.map((v) => <li key={`${v.ma}-${v.ky}`}>{v.ma} {v.ten} · kỳ {v.ky} · hạn {formatDate(v.han)} {v.muc === "qua_han" ? <b className="text-son">quá {-v.con_lai_ngay} ngày</b> : `còn ${v.con_lai_ngay} ngày`}</li>)}</ul>
        </details>
      )}
    </article>
  );
}

/** Tab "Đầu mối & trách nhiệm" (DT V.1): ma trận chủ trì/phối hợp và thẻ từng đầu mối. */
export function DauMoiTab() {
  const q = useDauMoi();
  const { can } = useAuth();
  const qc = useQueryClient();
  const edit = can("duyet", "quan_tri");
  const [editing, setEditing] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [cap, setCap] = useState("");
  const done = () => { setEditing(null); qc.invalidateQueries({ queryKey: ["dau-moi"] }); };
  const del = useMutation({ mutationFn: (ma: string) => api(`/api/dau-moi/${ma}`, { method: "DELETE" }), onSuccess: done, onError: (e) => setErr(errText(e)) });
  const d = q.data;
  const { hash } = useLocation();
  useEffect(() => { if (d?.dau_moi && hash) document.getElementById(decodeURIComponent(hash.slice(1)))?.scrollIntoView?.({ block: "start" }); }, [d, hash]);
  if (!d?.dau_moi) return <p className="text-muc-nhat">{q.isError ? "Không tải được danh mục đầu mối." : "Đang tải…"}</p>;
  const rows = d.dau_moi.filter((x) => !cap || x.cap === cap);
  return (
    <div className="space-y-4">
      <p className="text-[13.5px] text-muc-nhat">Phân công chủ trì, phối hợp theo mục V.1 và Phiếu xác định nguồn dữ liệu (Phụ lục 02) của kịch bản điều hành. Nhắc hạn nộp số liệu gửi đúng đầu mối chịu trách nhiệm.</p>
      <Matrix d={d} />
      {d.toi_thieu_chung && <p className="rounded border border-vien bg-be-mat px-3 py-2 text-[13px]"><b>Mỗi đầu mối gửi tối thiểu (mục III.1):</b> {d.toi_thieu_chung}</p>}
      <div className="flex flex-wrap items-center gap-2">
        <select aria-label="Lọc theo cấp" className="o-nhap w-auto py-1.5" value={cap} onChange={(e) => setCap(e.target.value)}>
          <option value="">Tất cả đầu mối ({d.dau_moi.length})</option>{Object.entries(d.cap).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        {edit && editing !== "__new__" && <button type="button" className="btn-chinh py-1.5" onClick={() => setEditing("__new__")}>Thêm đầu mối</button>}
      </div>
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      {editing === "__new__" && <Editor onDone={done} onCancel={() => setEditing(null)} />}
      <div className="space-y-3">{rows.map((x) => editing === x.ma
        ? <Editor key={x.ma} x={x} onDone={done} onCancel={() => setEditing(null)} />
        : <Card key={x.ma} x={x} edit={edit} mine={d.cua_toi.includes(x.ma)} onEdit={() => setEditing(x.ma)} onDelete={() => del.mutate(x.ma)} />)}</div>
    </div>
  );
}

/** Thẻ trên trang chủ: tài khoản đang đăng nhập là đầu mối nào, chịu trách nhiệm gì, kỳ số liệu nào cần nộp. */
export function MyResponsibility() {
  const q = useDauMoi();
  const mine = (q.data?.dau_moi ?? []).filter((x) => q.data?.cua_toi?.includes(x.ma));
  if (!mine.length) return null;
  return (
    <section aria-label="Trách nhiệm đầu mối của bạn" className="khu rounded-md border-l-4 border-l-[var(--chinh)] px-4 py-3">
      {mine.map((x) => (
        <div key={x.ma} className="flex flex-col gap-x-4 gap-y-1.5 sm:flex-row sm:items-start">
          <div className="min-w-0 flex-1">
            <h2 className="text-[15px] font-semibold">Bạn là đầu mối của {x.ten}</h2>
            <p className="text-[13.5px]">{x.trach_nhiem.map((t) => `${t.vai_tro_ten} ${(NHOM_TN[t.nhom] ?? t.nhom).toLowerCase()}`).join(" · ")}</p>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13.5px] sm:shrink-0">
            {x.viec_tre.length > 0
              ? <Link to="/nhap-lieu" className={x.so_qua_han ? "font-semibold text-son" : "lien-ket"}>{x.viec_tre.length} kỳ số liệu cần nộp{x.so_qua_han ? `, ${x.so_qua_han} quá hạn` : ""}</Link>
              : <span className="text-muc-nhat">Không có kỳ số liệu đến hạn</span>}
            <Link to={`/co-cau-to-chuc?tab=dau-moi#dm-${x.ma}`} className="lien-ket">Xem trách nhiệm</Link>
          </div>
        </div>
      ))}
    </section>
  );
}

/** "Nguồn và trách nhiệm" của một phân hệ (DT II.1–II.7): đầu mối chủ trì/phối hợp/cung cấp/xác nhận nhóm dữ liệu. */
export function NguonTrachNhiem({ nhom }: { nhom: string }) {
  const q = useDauMoi();
  const rows = (q.data?.dau_moi ?? []).map((x) => ({ x, ts: x.trach_nhiem.filter((t) => t.nhom === nhom) })).filter((r) => r.ts.length);
  if (!rows.length) return null;
  const order = ["chu_tri", "xac_nhan", "cung_cap", "phoi_hop"];
  rows.sort((a, b) => Math.min(...a.ts.map((t) => order.indexOf(t.vai_tro))) - Math.min(...b.ts.map((t) => order.indexOf(t.vai_tro))));
  return (
    <details className="khu rounded-md px-4 py-2.5 text-[13.5px]" aria-label="Nguồn và trách nhiệm">
      <summary className="cursor-pointer"><b>Nguồn và trách nhiệm:</b> {rows.slice(0, 4).map((r) => `${r.x.ten} (${r.ts.map((t) => (t.vai_tro_ten ?? t.vai_tro).toLowerCase()).join(", ")})`).join("; ")}{rows.length > 4 ? "…" : ""}</summary>
      <ul className="mt-2 space-y-1">{rows.map(({ x, ts }) => (
        <li key={x.ma} className="flex flex-wrap gap-x-2">
          <span className="flex gap-1">{ts.map((t, i) => <RoleChip key={i} vt={t.vai_tro} ten={t.vai_tro_ten} />)}</span>
          <Link className="lien-ket font-medium" to={`/co-cau-to-chuc?tab=dau-moi#dm-${x.ma}`}>{x.ten}</Link>
          <span className="text-muc-nhat">{ts.map((t) => t.noi_dung).filter(Boolean).join("; ")}</span>
          {x.nguoi_lien_he && <span className="text-muc-nhat">· {x.nguoi_lien_he}{x.dien_thoai ? `, ${x.dien_thoai}` : ""}</span>}
          {x.so_qua_han > 0 && <span className="font-medium text-son">· {x.so_qua_han} kỳ quá hạn</span>}
        </li>
      ))}</ul>
    </details>
  );
}
