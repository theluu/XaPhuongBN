import * as Tabs from "@radix-ui/react-tabs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { PHAN_HE } from "@/lib/labels";
import { CAN_NHOM, ROLE } from "./labels";
import { NhomPicker, SecretBox, type Secret, type UserRow } from "./UsersAdmin";

export interface TenantRow { id: number; ma_dvhc: string; ten: string; cap: string; parent_id: number | null; trang_thai: string; so_nguoi_dung: number; so_chi_tieu: number }
interface TenantDetail extends TenantRow { ten_co_quan: string[]; ban_do: { tam?: [number, number]; zoom?: number }; modules: Record<string, string>; slug?: string | null; ten_mien?: string[]; tong_ban_ghi: number; ban_ghi_minh_hoa: number }

const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");
const TAB = "-mb-px border-b-2 border-transparent px-3 py-2 text-[14px] text-muc-nhat data-[state=active]:border-muc data-[state=active]:font-semibold data-[state=active]:text-muc";
const TT_DV: Record<string, [string, string]> = { hoat_dong: ["Hoạt động", "tt-xong"], tam_dung: ["Tạm dừng", "tt-qua-han"] };
const TT_TK: Record<string, string> = { hoat_dong: "Hoạt động", cho_duyet: "Chờ phê duyệt", thu_hoi: "Đã thu hồi" };

function useInvalidate(tid: number) {
  const qc = useQueryClient();
  return () => { qc.invalidateQueries({ queryKey: ["platform-tenants"] }); qc.invalidateQueries({ queryKey: ["platform-tenant", tid] }); qc.invalidateQueries({ queryKey: ["platform-users", tid] }); };
}

function InfoTab({ t, parents }: { t: TenantDetail; parents: TenantRow[] }) {
  const done = useInvalidate(t.id);
  const [f, setF] = useState({ ten: t.ten, parent_id: t.parent_id ?? "", l1: t.ten_co_quan[0] ?? "", l2: t.ten_co_quan[1] ?? "",
    lat: t.ban_do.tam?.[0]?.toString() ?? "", lng: t.ban_do.tam?.[1]?.toString() ?? "", zoom: t.ban_do.zoom ?? 14, modules: { ...t.modules },
    slug: t.slug ?? "", ten_mien: (t.ten_mien ?? []).join("\n") });
  const [msg, setMsg] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: () => api(`/api/platform/tenants/${t.id}`, { method: "PATCH", body: {
      ten: f.ten.trim(), parent_id: f.parent_id === "" ? null : Number(f.parent_id), ten_co_quan: [f.l1, f.l2], zoom: f.zoom, modules: f.modules,
      tam: f.lat && f.lng ? [Number(f.lat), Number(f.lng)] : null,
      slug: f.slug.trim(), ten_mien: f.ten_mien.split(/[\s,]+/).filter(Boolean) } }),
    onSuccess: () => { setMsg("Đã lưu thông tin đơn vị."); done(); }, onError: (e) => setMsg(errText(e)) });
  return (
    <form aria-label="Thông tin đơn vị" className="space-y-4" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm font-medium">Tên đơn vị<input className="o-nhap mt-1" value={f.ten} onChange={(e) => setF({ ...f, ten: e.target.value })} /></label>
        <label className="text-sm font-medium">Thuộc tỉnh/thành phố<select className="o-nhap mt-1" value={f.parent_id} onChange={(e) => setF({ ...f, parent_id: e.target.value })}>
          <option value="">—</option>{parents.map((p) => <option key={p.id} value={p.id}>{p.ten}</option>)}</select></label>
        <label className="text-sm font-medium">Tên cơ quan (dòng 1)<input className="o-nhap mt-1" value={f.l1} placeholder={`ỦY BAN NHÂN DÂN ${t.ten.toUpperCase()}`} onChange={(e) => setF({ ...f, l1: e.target.value })} /></label>
        <label className="text-sm font-medium">Dòng 2<input className="o-nhap mt-1" value={f.l2} placeholder="TRUNG TÂM ĐIỀU HÀNH THÔNG MINH" onChange={(e) => setF({ ...f, l2: e.target.value })} /></label>
      </div>
      <fieldset className="grid gap-3 sm:grid-cols-3"><legend className="mb-1 text-sm font-semibold">Tâm bản đồ địa bàn</legend>
        <label className="text-sm font-medium">Vĩ độ<input className="o-nhap mt-1 tabular" inputMode="decimal" value={f.lat} placeholder="21.2725" onChange={(e) => setF({ ...f, lat: e.target.value })} /></label>
        <label className="text-sm font-medium">Kinh độ<input className="o-nhap mt-1 tabular" inputMode="decimal" value={f.lng} placeholder="106.0975" onChange={(e) => setF({ ...f, lng: e.target.value })} /></label>
        <label className="text-sm font-medium">Mức thu phóng<input type="number" min={8} max={19} className="o-nhap mt-1" value={f.zoom} onChange={(e) => setF({ ...f, zoom: Number(e.target.value) || 14 })} /></label>
      </fieldset>
      <fieldset className="grid gap-3 sm:grid-cols-2"><legend className="mb-1 text-sm font-semibold">Địa chỉ trang công khai</legend>
        <label className="text-sm font-medium">Mã đường dẫn<input className="o-nhap mt-1" value={f.slug} placeholder="viet-yen" onChange={(e) => setF({ ...f, slug: e.target.value })} />
          <span className="mt-1 block text-[12px] font-normal text-muc-nhat">Dùng cho đường dẫn dự phòng /p/{f.slug || "ma-don-vi"}</span></label>
        <label className="text-sm font-medium">Tên miền riêng (mỗi dòng một tên miền)<textarea className="o-nhap mt-1" rows={2} value={f.ten_mien} placeholder="vietyen.bacninh.gov.vn" onChange={(e) => setF({ ...f, ten_mien: e.target.value })} />
          <span className="mt-1 block text-[12px] font-normal text-muc-nhat">Truy cập tên miền này sẽ mở trang công khai của đơn vị; chỉ cán bộ đơn vị đăng nhập được.</span></label>
      </fieldset>
      <fieldset><legend className="mb-1 text-sm font-semibold">Phân hệ sử dụng</legend>
        <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-[14px]">
          {PHAN_HE.map((p) => <label key={p.key} className="flex items-center gap-1.5"><input type="checkbox" checked={f.modules[p.key] !== "tat"}
            onChange={(e) => setF({ ...f, modules: { ...f.modules, [p.key]: e.target.checked ? "bat" : "tat" } })} />{p.ten}</label>)}
        </div></fieldset>
      {msg && <p role="status" className="text-[14px]">{msg}</p>}
      <button type="submit" className="btn-chinh" disabled={m.isPending || !f.ten.trim()}>Lưu thông tin</button>
    </form>
  );
}

function AddUser({ tid, onDone }: { tid: number; onDone: (s: Secret) => void }) {
  const [f, setF] = useState({ username: "", ho_ten: "", chuc_danh: "", role: "quan_tri_don_vi", nhom: [] as string[] });
  const [err, setErr] = useState<string | null>(null);
  const m = useMutation({ mutationFn: () => api<Secret>(`/api/platform/tenants/${tid}/users`, { method: "POST", body: { ...f, nhom: CAN_NHOM.includes(f.role) ? f.nhom : null } }),
    onSuccess: (r) => { setF({ username: "", ho_ten: "", chuc_danh: "", role: "quan_tri_don_vi", nhom: [] }); setErr(null); onDone(r); }, onError: (e) => setErr(errText(e)) });
  return (
    <form aria-label="Thêm tài khoản" className="khu space-y-3 rounded-md p-4" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <h4 className="font-semibold">Thêm tài khoản</h4>
      <div className="grid gap-3 sm:grid-cols-4">
        <label className="text-sm font-medium">Tên đăng nhập<input className="o-nhap mt-1" value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} /></label>
        <label className="text-sm font-medium">Họ tên<input className="o-nhap mt-1" value={f.ho_ten} onChange={(e) => setF({ ...f, ho_ten: e.target.value })} /></label>
        <label className="text-sm font-medium">Chức danh<input className="o-nhap mt-1" value={f.chuc_danh} onChange={(e) => setF({ ...f, chuc_danh: e.target.value })} /></label>
        <label className="text-sm font-medium">Vai trò<select className="o-nhap mt-1" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
          {Object.entries(ROLE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      </div>
      {CAN_NHOM.includes(f.role) && <NhomPicker value={f.nhom} onChange={(nhom) => setF({ ...f, nhom })} />}
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <button type="submit" className="btn-chinh py-1.5" disabled={m.isPending || !/^[a-zA-Z0-9_.-]{3,}$/.test(f.username) || !f.ho_ten.trim() || (CAN_NHOM.includes(f.role) && !f.nhom.length)}>Tạo tài khoản</button>
    </form>
  );
}

function UserLine({ tid, u, onSecret }: { tid: number; u: UserRow; onSecret: (s: Secret) => void }) {
  const done = useInvalidate(tid);
  const [mode, setMode] = useState<"" | "sua" | "thu_hoi">("");
  const [f, setF] = useState({ ho_ten: u.ho_ten, chuc_danh: u.chuc_danh, role: u.roles[0] ?? "nguoi_xem", nhom: u.nhom.filter((n) => n !== "*"), ly_do: "" });
  const [err, setErr] = useState<string | null>(null);
  const call = useMutation({ mutationFn: ({ path, method, body }: { path: string; method: string; body?: unknown }) => api<Secret>(`/api/platform/tenants/${tid}/users/${u.id}${path}`, { method, body }),
    onSuccess: (r) => { setMode(""); setErr(null); if (r?.mat_khau_tam) onSecret(r); done(); }, onError: (e) => setErr(errText(e)) });
  const roleChanged = f.role !== (u.roles[0] ?? "") || (CAN_NHOM.includes(f.role) && f.nhom.slice().sort().join() !== u.nhom.filter((n) => n !== "*").sort().join());
  return (
    <>
      <tr className="border-b border-vien align-top">
        <td className="px-4 py-2"><div className="font-medium">{u.ho_ten}</div><div className="text-[12.5px] text-muc-nhat">{u.username} · {u.chuc_danh}</div></td>
        <td className="py-2 text-[13.5px]">{u.roles.map((r) => ROLE[r] ?? r).join(", ")}</td>
        <td className="py-2 text-[13.5px]">{TT_TK[u.trang_thai] ?? u.trang_thai}{u.bi_khoa && " · đang khóa"}</td>
        <td className="px-4 py-2 text-right">
          <div className="flex flex-wrap justify-end gap-2 text-[13px]">
            <button type="button" className="lien-ket" onClick={() => setMode(mode === "sua" ? "" : "sua")}>Sửa</button>
            <button type="button" className="lien-ket" onClick={() => call.mutate({ path: "/reset-password", method: "POST" })}>Đặt lại mật khẩu</button>
            {u.trang_thai === "thu_hoi" ? <>
              <button type="button" className="lien-ket" onClick={() => call.mutate({ path: "", method: "PATCH", body: { trang_thai: "hoat_dong" } })}>Khôi phục</button>
              <button type="button" className="lien-ket text-son" onClick={() => call.mutate({ path: "", method: "DELETE" })}>Xóa hẳn</button>
            </> : <button type="button" className="lien-ket text-son" onClick={() => setMode(mode === "thu_hoi" ? "" : "thu_hoi")}>Thu hồi</button>}
          </div>
          {err && <p role="alert" className="mt-1 text-[13px] text-son">{err}</p>}
        </td>
      </tr>
      {mode === "sua" && (
        <tr className="border-b border-vien bg-be-mat-2"><td colSpan={4} className="px-4 py-3">
          <form aria-label={`Sửa ${u.username}`} className="space-y-3" onSubmit={(e) => { e.preventDefault();
            call.mutate({ path: "", method: "PATCH", body: { ho_ten: f.ho_ten, chuc_danh: f.chuc_danh, ...(roleChanged ? { role: f.role, nhom: CAN_NHOM.includes(f.role) ? f.nhom : null } : {}) } }); }}>
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="text-sm font-medium">Họ tên<input className="o-nhap mt-1" value={f.ho_ten} onChange={(e) => setF({ ...f, ho_ten: e.target.value })} /></label>
              <label className="text-sm font-medium">Chức danh<input className="o-nhap mt-1" value={f.chuc_danh} onChange={(e) => setF({ ...f, chuc_danh: e.target.value })} /></label>
              <label className="text-sm font-medium">Vai trò<select className="o-nhap mt-1" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
                {Object.entries(ROLE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
            </div>
            {CAN_NHOM.includes(f.role) && <NhomPicker value={f.nhom} onChange={(nhom) => setF({ ...f, nhom })} />}
            <div className="flex gap-2"><button type="submit" className="btn-chinh py-1.5" disabled={call.isPending}>Lưu</button><button type="button" className="btn-phu py-1.5" onClick={() => setMode("")}>Hủy</button></div>
          </form>
        </td></tr>
      )}
      {mode === "thu_hoi" && (
        <tr className="border-b border-vien bg-be-mat-2"><td colSpan={4} className="px-4 py-3">
          <form aria-label={`Thu hồi ${u.username}`} className="flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); call.mutate({ path: "", method: "PATCH", body: { trang_thai: "thu_hoi", ly_do: f.ly_do } }); }}>
            <label className="flex-1 text-sm font-medium">Lý do thu hồi<input className="o-nhap mt-1" value={f.ly_do} placeholder="VD: chuyển công tác" onChange={(e) => setF({ ...f, ly_do: e.target.value })} /></label>
            <button type="submit" className="btn-chinh bg-son py-1.5" disabled={!f.ly_do.trim() || call.isPending}>Thu hồi</button>
          </form>
        </td></tr>
      )}
    </>
  );
}

function UsersTab({ tid }: { tid: number }) {
  const done = useInvalidate(tid);
  const [secret, setSecret] = useState<Secret | null>(null);
  const q = useQuery({ queryKey: ["platform-users", tid], queryFn: () => api<UserRow[]>(`/api/platform/tenants/${tid}/users`) });
  return (
    <div className="space-y-4">
      {secret && <SecretBox s={secret} onClose={() => setSecret(null)} />}
      <div className="khu overflow-x-auto rounded-md">
        <table className="w-full text-[14px]" aria-label="Tài khoản của đơn vị">
          <thead><tr className="border-b border-vien text-left text-[13px] text-muc-nhat"><th className="px-4 py-2 font-medium">Người dùng</th><th className="font-medium">Vai trò</th><th className="font-medium">Trạng thái</th><th className="px-4 text-right font-medium">Thao tác</th></tr></thead>
          <tbody>{(q.data ?? []).map((u) => <UserLine key={u.id} tid={tid} u={u} onSecret={setSecret} />)}
            {q.data?.length === 0 && <tr><td colSpan={4} className="px-4 py-4 text-center text-muc-nhat">Đơn vị chưa có tài khoản.</td></tr>}</tbody>
        </table>
      </div>
      <AddUser tid={tid} onDone={(s) => { setSecret(s); done(); }} />
    </div>
  );
}

function DataTab({ t }: { t: TenantDetail }) {
  const done = useInvalidate(t.id);
  const qc = useQueryClient();
  const [msg, setMsg] = useState<string | null>(null);
  const seed = useMutation({ mutationFn: () => api<{ so_ban_ghi: number; tai_khoan: Record<string, string> }>(`/api/platform/tenants/${t.id}/du-lieu-minh-hoa`, { method: "POST" }),
    onSuccess: (r) => { setMsg(`Đã nạp ${formatNumber(r.so_ban_ghi)} bản ghi minh họa. Tài khoản đóng vai: ${Object.entries(r.tai_khoan).map(([k, v]) => `${k} → ${v}`).join(", ")}.`); done(); qc.invalidateQueries(); },
    onError: (e) => setMsg(errText(e)) });
  const purge = useMutation({ mutationFn: () => api<{ da_xoa: number }>(`/api/platform/tenants/${t.id}/du-lieu-minh-hoa`, { method: "DELETE" }),
    onSuccess: (r) => { setMsg(`Đã xóa ${formatNumber(r.da_xoa)} bản ghi minh họa.`); done(); qc.invalidateQueries(); }, onError: (e) => setMsg(errText(e)) });
  const that = t.tong_ban_ghi - t.ban_ghi_minh_hoa;
  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-3 gap-3">
        {([["Tổng bản ghi", t.tong_ban_ghi], ["Dữ liệu minh họa", t.ban_ghi_minh_hoa], ["Dữ liệu phường nhập/đồng bộ", that]] as const).map(([k, v]) => (
          <div key={k} className="khu rounded-md px-4 py-3"><dt className="text-[13px] text-muc-nhat">{k}</dt><dd className="font-so text-[24px] font-bold tabular">{formatNumber(v)}</dd></div>
        ))}
      </dl>
      <p className="text-[13.5px] text-muc-nhat">Để xem, thêm, sửa, xóa nội dung (số liệu, phản ánh, cơ cấu tổ chức, danh mục, dự án…) bấm “Vào quản trị nội dung” ở đầu khung này.</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-chinh" disabled={seed.isPending || t.trang_thai !== "hoat_dong"} onClick={() => seed.mutate()}>
          {seed.isPending ? "Đang nạp…" : t.ban_ghi_minh_hoa ? "Nạp lại dữ liệu minh họa" : "Nạp dữ liệu minh họa"}</button>
        <button type="button" className="btn-phu text-son" disabled={purge.isPending || !t.ban_ghi_minh_hoa} onClick={() => purge.mutate()}>Xóa dữ liệu minh họa</button>
      </div>
      <p className="text-[12.5px] text-muc-nhat">Dữ liệu minh họa dùng tên, vị trí riêng của đơn vị và gắn cờ “minh họa”; xóa không ảnh hưởng dữ liệu thật.</p>
      {msg && <p role="status" className="rounded border border-vien bg-be-mat px-3 py-2 text-[14px]">{msg}</p>}
    </div>
  );
}

function StatusTab({ t, onDeleted }: { t: TenantDetail; onDeleted: () => void }) {
  const done = useInvalidate(t.id);
  const [lyDo, setLyDo] = useState("");
  const [ma, setMa] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const st = useMutation({ mutationFn: (trang_thai: string) => api(`/api/platform/tenants/${t.id}/trang-thai`, { method: "POST", body: { trang_thai, ly_do: lyDo } }),
    onSuccess: () => { setMsg(null); setLyDo(""); done(); }, onError: (e) => setMsg(errText(e)) });
  const del = useMutation({ mutationFn: () => api(`/api/platform/tenants/${t.id}`, { method: "DELETE", body: { xac_nhan: ma } }),
    onSuccess: onDeleted, onError: (e) => setMsg(errText(e)) });
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="khu rounded-md p-4">
        <h4 className="font-semibold">{t.trang_thai === "hoat_dong" ? "Tạm dừng đơn vị" : "Kích hoạt lại"}</h4>
        {t.trang_thai === "hoat_dong" ? <>
          <p className="mt-1 text-[14px] text-muc-nhat">Mọi tài khoản của đơn vị bị đăng xuất và không đăng nhập được. Dữ liệu được giữ nguyên.</p>
          <label className="mt-2 block text-sm font-medium">Lý do<input className="o-nhap mt-1" value={lyDo} placeholder="VD: sắp xếp đơn vị hành chính" onChange={(e) => setLyDo(e.target.value)} /></label>
          <button type="button" className="btn-chinh mt-2 bg-[var(--tam-thoi)]" disabled={!lyDo.trim() || st.isPending} onClick={() => st.mutate("tam_dung")}>Tạm dừng</button>
        </> : <>
          <p className="mt-1 text-[14px] text-muc-nhat">Đơn vị đang tạm dừng. Kích hoạt để tài khoản đăng nhập lại được.</p>
          <button type="button" className="btn-chinh mt-2" disabled={st.isPending} onClick={() => st.mutate("hoat_dong")}>Kích hoạt</button>
        </>}
      </section>
      <section className="khu rounded-md p-4">
        <h4 className="font-semibold text-son">Xóa vĩnh viễn đơn vị</h4>
        <p className="mt-1 text-[14px] text-muc-nhat">Xóa toàn bộ dữ liệu và tài khoản của {t.ten}; không khôi phục được (trừ từ bản sao lưu toàn hệ thống). Nên xuất dữ liệu trước. Chỉ thực hiện khi đơn vị đã tạm dừng. Nhật ký truy cập được giữ lại.</p>
        <label className="mt-2 block text-sm font-medium">Gõ mã đơn vị <code>{t.ma_dvhc}</code> để xác nhận<input className="o-nhap mt-1" value={ma} onChange={(e) => setMa(e.target.value)} /></label>
        <button type="button" className="btn-chinh mt-2 bg-son" disabled={t.trang_thai !== "tam_dung" || ma !== t.ma_dvhc || del.isPending} onClick={() => del.mutate()}>Xóa đơn vị</button>
      </section>
      {msg && <p role="alert" className="text-[14px] text-son lg:col-span-2">{msg}</p>}
    </div>
  );
}

export function TenantPanel({ tid, parents, onClose }: { tid: number; parents: TenantRow[]; onClose: () => void }) {
  const [tab, setTab] = useState("thong-tin");
  const { enterTenant } = useAuth();
  const navigate = useNavigate();
  const [err, setErr] = useState<string | null>(null);
  const enter = useMutation({ mutationFn: () => enterTenant(tid), onSuccess: () => navigate("/"), onError: (e) => setErr(errText(e)) });
  const q = useQuery({ queryKey: ["platform-tenant", tid], queryFn: () => api<TenantDetail>(`/api/platform/tenants/${tid}`) });
  const t = q.data;
  if (!t) return <section className="khu rounded-md p-4 text-muc-nhat">Đang tải…</section>;
  const [ttTen, ttCls] = TT_DV[t.trang_thai] ?? [t.trang_thai, ""];
  return (
    <section aria-label={`Quản trị ${t.ten}`} className="khu rounded-md p-4">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h3 className="flex-1 text-[17px] font-semibold">{t.ten} <span className="text-[13px] font-normal text-muc-nhat">· {t.ma_dvhc} · {t.so_nguoi_dung} tài khoản</span></h3>
        <span className={`nhan-tt ${ttCls}`}>{ttTen}</span>
        <button type="button" className="btn-chinh py-1" disabled={t.trang_thai !== "hoat_dong" || enter.isPending} onClick={() => enter.mutate()}
          title="Mở hệ thống như quản trị của đơn vị: xem và chỉnh sửa toàn bộ nội dung">Vào quản trị nội dung</button>
        <button type="button" className="btn-phu py-1" onClick={onClose}>Đóng</button>
      </div>
      {err && <p role="alert" className="mb-2 text-[14px] text-son">{err}</p>}
      <Tabs.Root value={tab} onValueChange={setTab}>
        <Tabs.List aria-label="Quản trị đơn vị" className="mb-4 flex flex-wrap gap-1 border-b border-vien">
          {[["thong-tin", "Thông tin"], ["tai-khoan", "Tài khoản"], ["du-lieu", "Dữ liệu"], ["trang-thai", "Trạng thái"]].map(([k, v]) => <Tabs.Trigger key={k} value={k} className={TAB}>{v}</Tabs.Trigger>)}
        </Tabs.List>
        <Tabs.Content value="thong-tin"><InfoTab key={t.id} t={t} parents={parents} /></Tabs.Content>
        <Tabs.Content value="tai-khoan"><UsersTab tid={t.id} /></Tabs.Content>
        <Tabs.Content value="du-lieu"><DataTab t={t} /></Tabs.Content>
        <Tabs.Content value="trang-thai"><StatusTab t={t} onDeleted={onClose} /></Tabs.Content>
      </Tabs.Root>
    </section>
  );
}

export { TT_DV };
