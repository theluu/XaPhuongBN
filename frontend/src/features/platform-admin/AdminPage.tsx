import * as Tabs from "@radix-ui/react-tabs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError, getToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatNumber } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { OnboardWizard } from "./OnboardWizard";

const ROLE: Record<string, string> = { quan_tri_don_vi: "Quản trị đơn vị", lanh_dao: "Lãnh đạo", xac_nhan: "Cán bộ xác nhận", nhap_lieu: "Cán bộ nhập liệu",
  chuyen_nganh: "Cơ quan chuyên ngành", nguoi_xem: "Người xem" };
const NHOM = ["ktxh", "dan_cu", "ngan_sach", "dau_tu_cong", "cong_trinh", "tthc_pakn", "gd_yt_mt"];
const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");
const TAB = "-mb-px border-b-2 border-transparent px-3 py-2 text-[14.5px] text-muc-nhat data-[state=active]:border-muc data-[state=active]:font-semibold data-[state=active]:text-muc";

function PlatformAdmin() {
  const [wizard, setWizard] = useState(false);
  const qc = useQueryClient();
  const t = useQuery({ queryKey: ["platform-tenants"], queryFn: () => api<{ id: number; ma_dvhc: string; ten: string; cap: string; trang_thai: string; so_nguoi_dung: number; so_chi_tieu: number }[]>("/api/platform/tenants") });
  return (
    <>
      <PageHeader title="Quản trị nền tảng" desc="Các xã/phường dùng chung một nền tảng; dữ liệu mỗi đơn vị được cách ly. Tài khoản quản trị nền tảng không đọc được dữ liệu nghiệp vụ nhạy cảm.">
        {!wizard && <button type="button" className="btn-chinh" onClick={() => setWizard(true)}>Khởi tạo đơn vị mới</button>}
      </PageHeader>
      {wizard && <div className="mb-4"><OnboardWizard onDone={() => { setWizard(false); qc.invalidateQueries({ queryKey: ["platform-tenants"] }); }} /></div>}
      <div className="khu overflow-x-auto rounded-md">
        <table className="w-full text-[14.5px]" aria-label="Đơn vị trên nền tảng">
          <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="px-4 py-2 font-medium">Đơn vị</th><th className="font-medium">Mã</th><th className="font-medium">Cấp</th>
            <th className="text-right font-medium">Người dùng</th><th className="px-4 text-right font-medium">Chỉ tiêu</th></tr></thead>
          <tbody>{(t.data ?? []).map((x) => (
            <tr key={x.id} className="border-b border-vien"><td className="px-4 py-2">{x.ten}</td><td className="tabular">{x.ma_dvhc}</td><td>{x.cap}</td>
              <td className="text-right tabular">{x.so_nguoi_dung}</td><td className="px-4 text-right tabular">{x.so_chi_tieu}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </>
  );
}

interface UserRow { id: number; username: string; ho_ten: string; chuc_danh: string; don_vi: string; trang_thai: string; roles: string[]; nhom: string[]; co_2fa: boolean }

function Users() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-users"], queryFn: () => api<UserRow[]>("/api/admin/users") });
  const [f, setF] = useState({ username: "", ho_ten: "", chuc_danh: "", don_vi: "", role: "nhap_lieu", nhom: [] as string[] });
  const [shown, setShown] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["admin-users"] });
  const create = useMutation({ mutationFn: () => api<{ mat_khau_tam: string; username: string }>("/api/admin/users", { method: "POST", body: { ...f, nhom: f.nhom.length ? f.nhom : null } }),
    onSuccess: (r) => { setShown(`Tài khoản ${r.username}: mật khẩu tạm ${r.mat_khau_tam} (chỉ hiển thị một lần)`); setErr(null); refresh(); }, onError: (e) => setErr(errText(e)) });
  const totp = useMutation({ mutationFn: (id: number) => api<{ secret: string }>(`/api/admin/users/${id}/totp`, { method: "POST" }),
    onSuccess: (r) => { setShown(`Mã khóa xác thực 2 lớp: ${r.secret}. Nhập mã này vào ứng dụng xác thực (chỉ hiển thị một lần).`); refresh(); } });
  const revoke = useMutation({ mutationFn: ({ id, ly_do }: { id: number; ly_do: string }) => api(`/api/users/${id}/revoke`, { method: "POST", body: { ly_do } }), onSuccess: refresh });
  const needNhom = ["xac_nhan", "nhap_lieu", "chuyen_nganh"].includes(f.role);
  return (
    <div className="space-y-4">
      {shown && <p role="status" className="rounded border border-[var(--tam-thoi)] bg-be-mat px-3 py-2 font-medium">{shown}</p>}
      <div className="khu overflow-x-auto rounded-md">
        <table aria-label="Người dùng" className="w-full text-[14px]">
          <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="px-4 py-2 font-medium">Người dùng</th><th className="font-medium">Vai trò</th><th className="font-medium">Nhóm dữ liệu</th>
            <th className="font-medium">2 lớp</th><th className="font-medium">Trạng thái</th><th className="px-4 font-medium" /></tr></thead>
          <tbody>{(q.data ?? []).map((u) => (
            <tr key={u.id} className="border-b border-vien">
              <td className="px-4 py-2"><div className="font-medium">{u.ho_ten}</div><div className="text-[12.5px] text-muc-nhat">{u.username}, {u.chuc_danh}</div></td>
              <td>{u.roles.map((r) => ROLE[r] ?? r).join(", ")}</td><td className="text-[13px]">{u.nhom.includes("*") ? "Tất cả" : u.nhom.join(", ")}</td>
              <td>{u.co_2fa ? "Đã bật" : "Chưa"}</td><td>{u.trang_thai === "hoat_dong" ? "Hoạt động" : u.trang_thai === "thu_hoi" ? "Đã thu hồi" : "Chờ duyệt"}</td>
              <td className="space-x-2 whitespace-nowrap px-4 text-right">
                <button type="button" className="btn-phu py-1" onClick={() => totp.mutate(u.id)}>Cấp mã 2 lớp</button>
                {u.trang_thai === "hoat_dong" && <button type="button" className="btn-phu py-1 text-son" onClick={() => { const ly_do = window.prompt("Lý do thu hồi quyền"); if (ly_do?.trim()) revoke.mutate({ id: u.id, ly_do }); }}>Thu hồi quyền</button>}
              </td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <form className="khu rounded-md p-4" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <h3 className="mb-2 font-semibold">Tạo tài khoản</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          {(["username", "ho_ten", "chuc_danh", "don_vi"] as const).map((k) => (
            <label key={k} className="text-sm font-medium">{{ username: "Tên đăng nhập", ho_ten: "Họ tên", chuc_danh: "Chức danh", don_vi: "Đơn vị công tác" }[k]}
              <input className="o-nhap mt-1" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>
          ))}
          <label className="text-sm font-medium">Vai trò<select className="o-nhap mt-1" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
            {Object.entries(ROLE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        </div>
        {needNhom && (
          <fieldset className="mt-3 flex flex-wrap gap-3 text-[14px]"><legend className="mb-1 text-sm font-medium">Nhóm dữ liệu được giao</legend>
            {NHOM.map((n) => <label key={n} className="flex items-center gap-1.5"><input type="checkbox" checked={f.nhom.includes(n)} onChange={(e) => setF({ ...f, nhom: e.target.checked ? [...f.nhom, n] : f.nhom.filter((x) => x !== n) })} />{n}</label>)}
          </fieldset>
        )}
        {err && <p role="alert" className="mt-2 text-sm text-son">{err}</p>}
        <button type="submit" className="btn-chinh mt-3" disabled={!f.username || !f.ho_ten || (needNhom && !f.nhom.length) || create.isPending}>Tạo tài khoản</button>
      </form>
    </div>
  );
}

function Rules() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-rules"], queryFn: () => api<{ ma: string; ten: string; loai: string; can_cu: string; bat: boolean }[]>("/api/admin/alert-rules") });
  const put = useMutation({ mutationFn: ({ ma, bat }: { ma: string; bat: boolean }) => api(`/api/admin/alert-rules/${ma}`, { method: "PUT", body: { bat } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-rules"] }) });
  return (
    <ul className="khu divide-y divide-[var(--vien)] rounded-md">
      {(q.data ?? []).map((r) => (
        <li key={r.ma} className="flex items-center gap-3 px-4 py-2.5 text-[14.5px]">
          <input type="checkbox" checked={r.bat} onChange={(e) => put.mutate({ ma: r.ma, bat: e.target.checked })} aria-label={`Bật quy tắc ${r.ten}`} />
          <span className="flex-1">{r.ten}</span><span className="text-[13px] text-muc-nhat">Dự thảo mục {r.can_cu}</span>
        </li>
      ))}
    </ul>
  );
}

function Audit() {
  const q = useQuery({ queryKey: ["admin-audit"], queryFn: () => api<{ id: number; ts: string; user_id: number | null; ip: string; method: string; path: string; status: number; doi_tuong: string | null }[]>("/api/admin/audit") });
  return (
    <div className="khu overflow-x-auto rounded-md">
      <table aria-label="Nhật ký truy cập" className="w-full text-[13.5px]">
        <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="px-4 py-2 font-medium">Thời điểm</th><th className="font-medium">Người dùng</th><th className="font-medium">Thao tác</th><th className="font-medium">Kết quả</th><th className="px-4 font-medium">IP</th></tr></thead>
        <tbody>{(q.data ?? []).map((r) => (
          <tr key={r.id} className="border-b border-vien"><td className="whitespace-nowrap px-4 py-1.5 tabular">{new Date(r.ts).toLocaleString("vi-VN")}</td><td className="tabular">{r.user_id ?? "—"}</td>
            <td>{r.doi_tuong ?? `${r.method} ${r.path}`}</td><td className="tabular">{r.status}</td><td className="px-4 tabular">{r.ip}</td></tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function Settings() {
  const { tenant } = useAuth();
  const qc = useQueryClient();
  const [phrase, setPhrase] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [l1, setL1] = useState(tenant?.ten_co_quan[0] ?? "");
  const [l2, setL2] = useState(tenant?.ten_co_quan[1] ?? "");
  const purge = useMutation({ mutationFn: () => api<{ da_xoa: number }>("/api/admin/purge-sample", { method: "POST", body: { xac_nhan: phrase } }),
    onSuccess: (r) => { setMsg(`Đã xóa ${formatNumber(r.da_xoa)} bản ghi minh họa.`); qc.invalidateQueries(); }, onError: (e) => setMsg(errText(e)) });
  const save = useMutation({ mutationFn: (body: Record<string, unknown>) => api("/api/admin/tenant", { method: "PATCH", body }), onSuccess: () => { setMsg("Đã lưu cấu hình."); qc.invalidateQueries({ queryKey: ["tenant"] }); }, onError: (e) => setMsg(errText(e)) });
  async function uploadLogo(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    try { const r = await api<{ key: string }>("/api/files", { method: "POST", form: fd }); save.mutate({ logo_key: r.key }); } catch (e) { setMsg(errText(e)); }
  }
  async function exportData() {
    const r = await fetch("/api/admin/export", { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
    if (!r.ok) return setMsg("Không xuất được dữ liệu");
    const url = URL.createObjectURL(await r.blob());
    Object.assign(document.createElement("a"), { href: url, download: `du-lieu-don-vi-${formatDate(new Date().toISOString())}.json` }).click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {msg && <p role="status" className="lg:col-span-2 rounded border border-vien bg-be-mat px-3 py-2">{msg}</p>}
      <section className="khu rounded-md p-4">
        <h3 className="mb-2 font-semibold">Nhận diện đơn vị</h3>
        <label className="block text-sm font-medium">Dòng 1 (tên cơ quan)<input className="o-nhap mt-1" value={l1} onChange={(e) => setL1(e.target.value)} /></label>
        <label className="mt-2 block text-sm font-medium">Dòng 2<input className="o-nhap mt-1" value={l2} onChange={(e) => setL2(e.target.value)} /></label>
        <button type="button" className="btn-phu mt-2" onClick={() => save.mutate({ ten_co_quan: [l1, l2] })}>Lưu tên cơ quan</button>
        <label className="mt-4 block text-sm font-medium">Biểu trưng của đơn vị (ảnh PNG/JPG). Không có biểu trưng thì hệ thống dùng Quốc huy.
          <input type="file" accept="image/png,image/jpeg,image/webp" className="mt-1 block text-sm" onChange={(e) => e.target.files?.[0] && uploadLogo(e.target.files[0])} /></label>
      </section>
      <section className="khu rounded-md p-4">
        <h3 className="mb-2 font-semibold">Dữ liệu của đơn vị</h3>
        <p className="text-[14px] text-muc-nhat">Tải toàn bộ dữ liệu của đơn vị (không gồm mật khẩu, khóa 2 lớp). Đơn vị không bị khóa vào nền tảng.</p>
        <button type="button" className="btn-phu mt-2" onClick={exportData}>Xuất toàn bộ dữ liệu</button>
        <h3 className="mb-1 mt-5 font-semibold text-son">Xóa dữ liệu minh họa</h3>
        <p className="text-[14px] text-muc-nhat">Làm một lần trước khi đưa vào sử dụng thật. Không ảnh hưởng số liệu do phường nhập.</p>
        <label className="mt-2 block text-sm font-medium">Gõ XÓA DỮ LIỆU MINH HỌA để xác nhận<input className="o-nhap mt-1" value={phrase} onChange={(e) => setPhrase(e.target.value)} /></label>
        <button type="button" className="btn-chinh mt-2 bg-son" disabled={phrase !== "XÓA DỮ LIỆU MINH HỌA" || purge.isPending} onClick={() => purge.mutate()}>Xóa dữ liệu minh họa</button>
      </section>
    </div>
  );
}

function UnitAdmin() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "nguoi-dung";
  return (
    <>
      <PageHeader title="Quản trị đơn vị" desc="Tài khoản, quy tắc cảnh báo, nhật ký truy cập và cấu hình đơn vị. Mọi thay đổi đều được ghi nhật ký." />
      <Tabs.Root value={tab} onValueChange={(t) => setParams({ tab: t })}>
        <Tabs.List aria-label="Quản trị" className="mb-4 flex flex-wrap gap-1 border-b border-vien">
          {[["nguoi-dung", "Người dùng"], ["quy-tac", "Quy tắc cảnh báo"], ["nhat-ky", "Nhật ký truy cập"], ["cau-hinh", "Cấu hình đơn vị"]].map(([k, t]) => <Tabs.Trigger key={k} value={k} className={TAB}>{t}</Tabs.Trigger>)}
        </Tabs.List>
        <Tabs.Content value="nguoi-dung"><Users /></Tabs.Content>
        <Tabs.Content value="quy-tac"><Rules /></Tabs.Content>
        <Tabs.Content value="nhat-ky"><Audit /></Tabs.Content>
        <Tabs.Content value="cau-hinh"><Settings /></Tabs.Content>
      </Tabs.Root>
    </>
  );
}

export function AdminPage() {
  const { me } = useAuth();
  return me?.roles.includes("quan_tri_nen_tang") ? <PlatformAdmin /> : <UnitAdmin />;
}
