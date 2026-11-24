import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Search } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { CAN_NHOM, NHOM, NHOM_GIAO, ROLE } from "./labels";

export interface UserRow { id: number; username: string; ho_ten: string; chuc_danh: string; don_vi: string; email: string | null; trang_thai: string; roles: string[];
  nhom: string[]; co_2fa: boolean; bi_khoa: boolean; phai_doi_mat_khau: boolean; ly_do_thu_hoi: string | null }
export interface Secret { username?: string; mat_khau_tam?: string | null; totp_secret?: string | null; trang_thai?: string; secret?: string }

const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");
const TT: Record<string, [string, string]> = { hoat_dong: ["Hoạt động", "tt-xong"], cho_duyet: ["Chờ phê duyệt", "tt-sap-han"], thu_hoi: ["Đã thu hồi", "tt-cu"] };

export function NhomPicker({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <fieldset className="flex flex-wrap gap-x-4 gap-y-1.5 text-[13.5px]"><legend className="mb-1 text-sm font-medium">Nhóm dữ liệu được giao</legend>
      {NHOM_GIAO.map((n) => <label key={n} className="flex items-center gap-1.5"><input type="checkbox" checked={value.includes(n)} onChange={(e) => onChange(e.target.checked ? [...value, n] : value.filter((x) => x !== n))} />{NHOM[n]}</label>)}
    </fieldset>
  );
}

export function SecretBox({ s, onClose }: { s: Secret; onClose: () => void }) {
  return (
    <div role="status" className="rounded-md border border-[var(--tam-thoi)] bg-be-mat px-4 py-3 text-[14px]">
      {s.trang_thai === "cho_duyet" && !s.mat_khau_tam && <p className="font-medium">Đã tạo tài khoản {s.username}: chờ lãnh đạo phê duyệt. Mật khẩu tạm sẽ cấp khi phê duyệt.</p>}
      {s.mat_khau_tam && <p>Tài khoản <b>{s.username}</b> — mật khẩu tạm: <code className="rounded bg-nen px-2 py-0.5 font-mono text-[15px]">{s.mat_khau_tam}</code></p>}
      {(s.totp_secret || s.secret) && <p className="mt-1">Mã khóa xác thực 2 lớp: <code className="rounded bg-nen px-2 py-0.5 font-mono text-[15px]">{s.totp_secret ?? s.secret}</code> (nhập vào ứng dụng xác thực)</p>}
      <p className="mt-1 text-[12.5px] text-muc-nhat">Chỉ hiển thị một lần. Chuyển cho người dùng qua kênh an toàn; người dùng phải đổi mật khẩu khi đăng nhập.</p>
      <button type="button" className="lien-ket mt-1 text-[13px]" onClick={onClose}>Đã ghi lại, ẩn thông tin</button>
    </div>
  );
}

function EditUser({ u, onDone, onCancel }: { u: UserRow; onDone: () => void; onCancel: () => void }) {
  const role0 = u.roles[0] ?? "nguoi_xem";
  const [f, setF] = useState({ ho_ten: u.ho_ten, chuc_danh: u.chuc_danh, don_vi: u.don_vi, email: u.email ?? "", role: role0, nhom: u.nhom.filter((n) => NHOM_GIAO.includes(n)) });
  const [err, setErr] = useState<string | null>(null);
  const roleChanged = f.role !== role0 || (CAN_NHOM.includes(f.role) && f.nhom.slice().sort().join() !== u.nhom.filter((n) => NHOM_GIAO.includes(n)).sort().join());
  const m = useMutation({ mutationFn: () => api(`/api/admin/users/${u.id}`, { method: "PATCH", body: { ho_ten: f.ho_ten, chuc_danh: f.chuc_danh, don_vi: f.don_vi, email: f.email,
    ...(roleChanged ? { role: f.role, nhom: CAN_NHOM.includes(f.role) ? f.nhom : null } : {}) } }), onSuccess: onDone, onError: (e) => setErr(errText(e)) });
  return (
    <form aria-label={`Sửa tài khoản ${u.username}`} className="space-y-3 bg-be-mat-2 px-4 py-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <div className="grid gap-3 sm:grid-cols-4">
        <label className="text-sm font-medium">Họ tên<input className="o-nhap mt-1" value={f.ho_ten} onChange={(e) => setF({ ...f, ho_ten: e.target.value })} /></label>
        <label className="text-sm font-medium">Chức danh<input className="o-nhap mt-1" value={f.chuc_danh} onChange={(e) => setF({ ...f, chuc_danh: e.target.value })} /></label>
        <label className="text-sm font-medium">Phòng/đơn vị công tác<input className="o-nhap mt-1" value={f.don_vi} onChange={(e) => setF({ ...f, don_vi: e.target.value })} /></label>
        <label className="text-sm font-medium">Email công vụ<input className="o-nhap mt-1" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
        <label className="text-sm font-medium">Vai trò<select className="o-nhap mt-1" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
          {Object.entries(ROLE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      </div>
      {CAN_NHOM.includes(f.role) && <NhomPicker value={f.nhom} onChange={(nhom) => setF({ ...f, nhom })} />}
      {roleChanged && <p className="text-[13px] text-[var(--tam-thoi)]">Đổi quyền sẽ đăng xuất người dùng khỏi mọi phiên đang mở.</p>}
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <div className="flex gap-2"><button type="submit" className="btn-chinh py-1.5" disabled={m.isPending || (CAN_NHOM.includes(f.role) && !f.nhom.length)}>Lưu</button>
        <button type="button" className="btn-phu py-1.5" onClick={onCancel}>Hủy</button></div>
    </form>
  );
}

function RevokeForm({ u, onDone, onCancel }: { u: UserRow; onDone: () => void; onCancel: () => void }) {
  const [ly, setLy] = useState("");
  const m = useMutation({ mutationFn: () => api(`/api/users/${u.id}/revoke`, { method: "POST", body: { ly_do: ly } }), onSuccess: onDone });
  return (
    <form className="flex flex-wrap items-end gap-2 bg-be-mat-2 px-4 py-3" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <label className="flex-1 text-sm font-medium">Lý do thu hồi quyền của {u.ho_ten} (VD: chuyển công tác, nghỉ hưu)<input className="o-nhap mt-1" value={ly} onChange={(e) => setLy(e.target.value)} /></label>
      <button type="submit" className="btn-nguy py-2" disabled={!ly.trim() || m.isPending}>Thu hồi</button>
      <button type="button" className="btn-phu py-2" onClick={onCancel}>Hủy</button>
    </form>
  );
}

export function UsersAdmin() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-users"], queryFn: () => api<UserRow[]>("/api/admin/users") });
  const [f, setF] = useState({ username: "", ho_ten: "", chuc_danh: "", don_vi: "", role: "nhap_lieu", nhom: [] as string[] });
  const [shown, setShown] = useState<Secret | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<{ id: number; kind: "sua" | "thu_hoi" } | null>(null);
  const [text, setText] = useState("");
  const [loc, setLoc] = useState("");
  const [creating, setCreating] = useState(false);
  const refresh = () => { setOpen(null); qc.invalidateQueries({ queryKey: ["admin-users"] }); };
  const onErr = (e: unknown) => setErr(errText(e));
  const create = useMutation({ mutationFn: () => api<Secret>("/api/admin/users", { method: "POST", body: { ...f, nhom: CAN_NHOM.includes(f.role) ? f.nhom : null } }),
    onSuccess: (r) => { setShown({ ...r, username: r.username ?? f.username }); setErr(null); setCreating(false); setF({ ...f, username: "", ho_ten: "", chuc_danh: "" }); refresh(); }, onError: onErr });
  const act = useMutation({
    mutationFn: ({ id, path }: { id: number; path: string }) => api<Secret>(path.startsWith("/api/users") ? path : `/api/admin/users/${id}/${path}`, { method: "POST" }),
    onSuccess: (r) => { if (r && (r.mat_khau_tam || r.totp_secret || r.secret)) setShown(r); setErr(null); refresh(); }, onError: onErr,
  });
  const rows = (q.data ?? []).filter((u) => (!loc || (loc === "bi_khoa" ? u.bi_khoa : u.trang_thai === loc)) &&
    (!text || `${u.ho_ten} ${u.username} ${u.chuc_danh} ${u.don_vi}`.toLowerCase().includes(text.toLowerCase())));
  const pending = (q.data ?? []).filter((u) => u.trang_thai === "cho_duyet").length;
  return (
    <div className="space-y-4">
      {shown && <SecretBox s={shown} onClose={() => setShown(null)} />}
      {err && <p role="alert" className="rounded border border-son px-3 py-2 text-sm text-son">{err}</p>}
      <div className="flex flex-wrap items-end gap-2">
        <label className="relative text-sm"><span className="sr-only">Tìm người dùng</span><Search size={15} aria-hidden className="absolute left-2.5 top-2.5 text-muc-nhat" />
          <input className="o-nhap w-64 py-1.5 pl-8" placeholder="Tìm theo tên, chức danh, phòng" value={text} onChange={(e) => setText(e.target.value)} /></label>
        <select aria-label="Lọc trạng thái" className="o-nhap w-auto py-1.5" value={loc} onChange={(e) => setLoc(e.target.value)}>
          <option value="">Tất cả trạng thái</option><option value="hoat_dong">Hoạt động</option><option value="cho_duyet">Chờ phê duyệt{pending ? ` (${pending})` : ""}</option>
          <option value="thu_hoi">Đã thu hồi</option><option value="bi_khoa">Đang bị khóa</option></select>
        <span className="flex-1 text-[13px] text-muc-nhat">{rows.length}/{q.data?.length ?? 0} tài khoản</span>
        {!creating && <button type="button" className="btn-chinh" onClick={() => setCreating(true)}>Tạo tài khoản</button>}
      </div>
      {creating && (
        <form aria-label="Tạo tài khoản" className="khu rounded-md p-4" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
          <div className="grid gap-3 sm:grid-cols-5">
            {(["username", "ho_ten", "chuc_danh", "don_vi"] as const).map((k) => (
              <label key={k} className="text-sm font-medium">{{ username: "Tên đăng nhập", ho_ten: "Họ tên", chuc_danh: "Chức danh", don_vi: "Phòng/đơn vị công tác" }[k]}
                <input className="o-nhap mt-1" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>
            ))}
            <label className="text-sm font-medium">Vai trò<select className="o-nhap mt-1" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
              {Object.entries(ROLE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
          </div>
          {CAN_NHOM.includes(f.role) && <div className="mt-3"><NhomPicker value={f.nhom} onChange={(nhom) => setF({ ...f, nhom })} /></div>}
          {(f.role === "lanh_dao" || f.role === "quan_tri_don_vi") && <p className="mt-2 text-[13px] text-muc-nhat">Tài khoản lãnh đạo, quản trị đơn vị cần lãnh đạo đơn vị phê duyệt trước khi sử dụng.</p>}
          <div className="mt-3 flex gap-2">
            <button type="submit" className="btn-chinh" disabled={!f.username || !f.ho_ten || (CAN_NHOM.includes(f.role) && !f.nhom.length) || create.isPending}>Tạo tài khoản</button>
            <button type="button" className="btn-phu" onClick={() => setCreating(false)}>Hủy</button>
          </div>
        </form>
      )}
      <div className="khu overflow-x-auto rounded-md">
        <table aria-label="Người dùng" className="w-full text-[14px]">
          <thead><tr className="border-b border-vien text-left text-[12.5px] text-muc-nhat"><th className="px-4 py-2 font-medium">Người dùng</th><th className="font-medium">Vai trò</th>
            <th className="font-medium">Nhóm dữ liệu</th><th className="font-medium">2 lớp</th><th className="font-medium">Trạng thái</th><th className="px-4 font-medium" /></tr></thead>
          <tbody>{rows.map((u) => {
            const [tt, cls] = TT[u.trang_thai] ?? [u.trang_thai, "tt-cu"];
            return [
              <tr key={u.id} className="border-b border-vien align-top">
                <td className="px-4 py-2"><div className="font-medium">{u.ho_ten}</div><div className="text-[12.5px] text-muc-nhat">{u.username} · {u.chuc_danh}{u.don_vi && ` · ${u.don_vi}`}</div></td>
                <td className="py-2">{u.roles.map((r) => ROLE[r] ?? r).join(", ")}</td>
                <td className="py-2 text-[13px]">{u.nhom.includes("*") ? "Tất cả" : u.nhom.map((n) => NHOM[n] ?? n).join(", ")}</td>
                <td className="py-2">{u.co_2fa ? "Đã bật" : "Chưa"}</td>
                <td className="py-2"><span className={`nhan-tt ${cls}`}>{tt}</span>{u.bi_khoa && <span className="nhan-tt tt-qua-han ml-1">Đang khóa</span>}
                  {u.ly_do_thu_hoi && <div className="text-[12px] text-muc-nhat">{u.ly_do_thu_hoi}</div>}</td>
                <td className="whitespace-nowrap px-4 py-2 text-right">
                  <div className="flex flex-wrap justify-end gap-1.5">
                    {u.trang_thai === "cho_duyet" && <button type="button" className="btn-chinh py-1" onClick={() => act.mutate({ id: u.id, path: `/api/users/${u.id}/approve` })}>Phê duyệt</button>}
                    {u.trang_thai !== "thu_hoi" && <button type="button" className="btn-phu py-1" onClick={() => setOpen(open?.id === u.id && open.kind === "sua" ? null : { id: u.id, kind: "sua" })}>Sửa quyền</button>}
                    {u.bi_khoa && <button type="button" className="btn-phu py-1" onClick={() => act.mutate({ id: u.id, path: "unlock" })}>Mở khóa</button>}
                    {u.trang_thai === "hoat_dong" && <>
                      <button type="button" className="btn-phu py-1" onClick={() => act.mutate({ id: u.id, path: "reset-password" })}>Đặt lại mật khẩu</button>
                      <button type="button" className="btn-phu py-1" onClick={() => act.mutate({ id: u.id, path: "totp" })}>Cấp mã 2 lớp</button>
                      <button type="button" className="btn-phu py-1 text-son" onClick={() => setOpen({ id: u.id, kind: "thu_hoi" })}>Thu hồi quyền</button></>}
                    {u.trang_thai === "thu_hoi" && <button type="button" className="btn-phu py-1" onClick={() => act.mutate({ id: u.id, path: "restore" })}>Khôi phục</button>}
                  </div>
                </td>
              </tr>,
              open?.id === u.id && <tr key={`${u.id}-f`} className="border-b border-vien"><td colSpan={6} className="p-0">
                {open.kind === "sua" ? <EditUser u={u} onDone={refresh} onCancel={() => setOpen(null)} /> : <RevokeForm u={u} onDone={refresh} onCancel={() => setOpen(null)} />}</td></tr>,
            ];
          })}</tbody>
        </table>
      </div>
    </div>
  );
}
