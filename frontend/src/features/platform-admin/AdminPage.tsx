import * as Tabs from "@radix-ui/react-tabs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError, getToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatNumber } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { OnboardWizard } from "./OnboardWizard";
import { UsersAdmin } from "./UsersAdmin";
import { RoleMatrix } from "./RoleMatrix";
import { CatalogAdmin } from "./CatalogAdmin";
import { TenantPanel, TT_DV, type TenantRow } from "./TenantManager";

const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");
const TAB = "-mb-px border-b-2 border-transparent px-3 py-2 text-[14.5px] text-muc-nhat data-[state=active]:border-muc data-[state=active]:font-semibold data-[state=active]:text-muc";

function PlatformAdmin() {
  const [wizard, setWizard] = useState(false);
  const [sel, setSel] = useState<number | null>(null);
  const qc = useQueryClient();
  const t = useQuery({ queryKey: ["platform-tenants"], queryFn: () => api<TenantRow[]>("/api/platform/tenants") });
  const units = (t.data ?? []).filter((x) => x.cap === "xa" || x.cap === "phuong");
  const parents = (t.data ?? []).filter((x) => x.cap === "tinh");
  const ten = (id: number | null) => parents.find((p) => p.id === id)?.ten ?? "—";
  return (
    <>
      <PageHeader title="Quản trị nền tảng" desc="Các xã/phường dùng chung một nền tảng; dữ liệu mỗi đơn vị được cách ly. Từ đây: khởi tạo, sửa, tạm dừng, xóa xã/phường; quản lý tài khoản từng đơn vị; nạp/xóa dữ liệu minh họa; “Vào quản trị nội dung” để chỉnh sửa toàn bộ dữ liệu của đơn vị. Mọi thao tác ghi nhật ký.">
        {!wizard && <button type="button" className="btn-chinh" onClick={() => setWizard(true)}>Khởi tạo đơn vị mới</button>}
      </PageHeader>
      {wizard && <div className="mb-4"><OnboardWizard onDone={() => { setWizard(false); qc.invalidateQueries({ queryKey: ["platform-tenants"] }); }} /></div>}
      <div className="khu mb-4 overflow-x-auto rounded-md">
        <table className="w-full text-[14.5px]" aria-label="Đơn vị trên nền tảng">
          <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="px-4 py-2 font-medium">Đơn vị</th><th className="font-medium">Mã</th><th className="font-medium">Thuộc</th>
            <th className="font-medium">Trạng thái</th><th className="text-right font-medium">Tài khoản</th><th className="text-right font-medium">Chỉ tiêu</th><th className="px-4" /></tr></thead>
          <tbody>{units.map((x) => {
            const [tt, cls] = TT_DV[x.trang_thai] ?? [x.trang_thai, ""];
            return (
              <tr key={x.id} className={`border-b border-vien ${sel === x.id ? "bg-be-mat-2" : ""}`}>
                <td className="px-4 py-2">{x.ten}</td><td className="tabular">{x.ma_dvhc}</td><td>{ten(x.parent_id)}</td>
                <td><span className={`nhan-tt ${cls}`}>{tt}</span></td>
                <td className="text-right tabular">{x.so_nguoi_dung}</td><td className="text-right tabular">{x.so_chi_tieu}</td>
                <td className="px-4 text-right"><button type="button" className="btn-phu py-1" aria-label={`Quản trị ${x.ten}`} onClick={() => setSel(sel === x.id ? null : x.id)}>{sel === x.id ? "Thu gọn" : "Quản trị"}</button></td>
              </tr>
            );
          })}
          {t.data && units.length === 0 && <tr><td colSpan={7} className="px-4 py-4 text-center text-muc-nhat">Chưa có xã/phường nào. Bấm “Khởi tạo đơn vị mới”.</td></tr>}</tbody>
        </table>
      </div>
      {sel !== null && <TenantPanel key={sel} tid={sel} parents={parents} onClose={() => { setSel(null); qc.invalidateQueries({ queryKey: ["platform-tenants"] }); }} />}
    </>
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
  const [tile, setTile] = useState(tenant?.ban_do?.tile_url ?? "");
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
        <h3 className="mb-1 mt-5 font-semibold">Nền bản đồ</h3>
        <p className="text-[13.5px] text-muc-nhat">Địa chỉ ảnh nền dạng {"{z}/{x}/{y}"}. Mặc định dùng OpenStreetMap France, dự phòng Esri (không cần khóa API). Triển khai mạng nội bộ thì nhập máy chủ bản đồ của tỉnh; để trống để dùng mặc định. Khi lỗi, hệ thống tự chuyển nguồn dự phòng.</p>
        <label className="mt-2 block text-sm font-medium">Địa chỉ nền bản đồ<input className="o-nhap mt-1 font-mono text-[13px]" value={tile} placeholder="https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png" onChange={(e) => setTile(e.target.value)} /></label>
        <button type="button" className="btn-phu mt-2" onClick={() => save.mutate({ tile_url: tile.trim() })}>Lưu nền bản đồ</button>
      </section>
      <QuickLinks onMsg={setMsg} />
      <FeedSources onMsg={setMsg} />
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

function QuickLinks({ onMsg }: { onMsg: (m: string) => void }) {
  const qc = useQueryClient();
  const bt = useQuery({ queryKey: ["bang-tin"], queryFn: () => api<{ lien_ket: { ten: string; url: string }[] }>("/api/bang-tin") });
  const [rows, setRows] = useState<{ ten: string; url: string }[] | null>(null);
  const cur = rows ?? bt.data?.lien_ket ?? [];
  const save = useMutation({ mutationFn: () => api("/api/admin/tenant", { method: "PATCH", body: { lien_ket: cur.filter((r) => r.ten.trim() || r.url.trim()) } }),
    onSuccess: () => { onMsg("Đã lưu liên kết nhanh."); setRows(null); qc.invalidateQueries({ queryKey: ["bang-tin"] }); }, onError: (e) => onMsg(errText(e)) });
  const set = (i: number, k: "ten" | "url", v: string) => setRows(cur.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  return (
    <section className="khu rounded-md p-4 lg:col-span-2" aria-labelledby="lien-ket-nhanh">
      <h3 id="lien-ket-nhanh" className="mb-1 font-semibold">Liên kết nhanh trên dải bản tin</h3>
      <p className="text-[13.5px] text-muc-nhat">Cổng TTĐT của phường, thành phố, Dịch vụ công, tra cứu hồ sơ… Địa chỉ phải bắt đầu bằng https:// (hoặc / cho trang trong hệ thống). Tối đa 12 liên kết.</p>
      <div className="mt-2 space-y-2">{cur.map((r, i) => (
        <div key={i} className="flex flex-wrap gap-2">
          <input aria-label={`Tên liên kết ${i + 1}`} className="o-nhap w-56" value={r.ten} onChange={(e) => set(i, "ten", e.target.value)} />
          <input aria-label={`Địa chỉ liên kết ${i + 1}`} className="o-nhap min-w-[260px] flex-1 font-mono text-[13px]" value={r.url} onChange={(e) => set(i, "url", e.target.value)} />
          <button type="button" className="lien-ket text-[13px] text-son" onClick={() => setRows(cur.filter((_, j) => j !== i))}>Bỏ</button>
        </div>
      ))}</div>
      <div className="mt-2 flex gap-2">
        {cur.length < 12 && <button type="button" className="btn-phu py-1.5" onClick={() => setRows([...cur, { ten: "", url: "https://" }])}>Thêm liên kết</button>}
        <button type="button" className="btn-chinh py-1.5" disabled={save.isPending || rows === null} onClick={() => save.mutate()}>Lưu liên kết</button>
      </div>
    </section>
  );
}

interface FeedStatus { ok: boolean; luc: string; so_tin: number; loi: string }
function FeedSources({ onMsg }: { onMsg: (m: string) => void }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["nguon-tin"], queryFn: () => api<{ nguon_tin: { ten: string; url: string }[]; trang_thai: Record<string, FeedStatus> }>("/api/admin/nguon-tin") });
  const [rows, setRows] = useState<{ ten: string; url: string }[] | null>(null);
  const cur = rows ?? q.data?.nguon_tin ?? [];
  const st = q.data?.trang_thai ?? {};
  const save = useMutation({ mutationFn: () => api("/api/admin/tenant", { method: "PATCH", body: { nguon_tin: cur.filter((r) => r.ten.trim() || r.url.trim()) } }),
    onSuccess: () => { onMsg("Đã lưu nguồn tin. Bấm “Lấy tin ngay” để kiểm tra."); setRows(null); qc.invalidateQueries({ queryKey: ["nguon-tin"] }); }, onError: (e) => onMsg(errText(e)) });
  const pull = useMutation({ mutationFn: () => api<{ trang_thai: Record<string, FeedStatus> }>("/api/admin/nguon-tin/lam-moi", { method: "POST" }),
    onSuccess: (r) => { const v = Object.values(r.trang_thai); onMsg(`Đã lấy tin: ${v.filter((x) => x.ok).length}/${v.length} nguồn thành công.`);
      qc.invalidateQueries({ queryKey: ["nguon-tin"] }); qc.invalidateQueries({ queryKey: ["bang-tin"] }); }, onError: (e) => onMsg(errText(e)) });
  const set = (i: number, k: "ten" | "url", v: string) => setRows(cur.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  return (
    <section className="khu rounded-md p-4 lg:col-span-2" aria-labelledby="nguon-tin">
      <h3 id="nguon-tin" className="mb-1 font-semibold">Nguồn tin RSS/Atom cho dải bản tin</h3>
      <p className="text-[13.5px] text-muc-nhat">Địa chỉ nguồn tin (RSS/Atom) của Cổng TTĐT phường, thành phố… do đơn vị quản lý cổng cung cấp. Hệ thống tự lấy tin mỗi 30 phút và hiện tin 7 ngày gần nhất.
        Hệ thống không đọc trang web thường; nguồn không phải RSS/Atom hoặc chặn truy cập sẽ báo lỗi bên dưới. Tối đa 5 nguồn, chỉ https.</p>
      <div className="mt-2 space-y-2">{cur.map((r, i) => {
        const s = st[r.url];
        return (
          <div key={i}>
            <div className="flex flex-wrap gap-2">
              <input aria-label={`Tên nguồn tin ${i + 1}`} className="o-nhap w-56" value={r.ten} onChange={(e) => set(i, "ten", e.target.value)} />
              <input aria-label={`Địa chỉ nguồn tin ${i + 1}`} className="o-nhap min-w-[260px] flex-1 font-mono text-[13px]" value={r.url} onChange={(e) => set(i, "url", e.target.value)} />
              <button type="button" className="lien-ket text-[13px] text-son" onClick={() => setRows(cur.filter((_, j) => j !== i))}>Bỏ</button>
            </div>
            {s && <p className={`mt-0.5 text-[12.5px] ${s.ok ? "text-[var(--xac-nhan)]" : "text-son"}`}>{s.ok ? `Lấy được ${s.so_tin} tin` : s.loi} · {new Date(s.luc).toLocaleString("vi-VN")}</p>}
          </div>
        );
      })}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {cur.length < 5 && <button type="button" className="btn-phu py-1.5" onClick={() => setRows([...cur, { ten: "", url: "https://" }])}>Thêm nguồn tin</button>}
        <button type="button" className="btn-chinh py-1.5" disabled={save.isPending || rows === null} onClick={() => save.mutate()}>Lưu nguồn tin</button>
        <button type="button" className="btn-phu py-1.5" disabled={pull.isPending || rows !== null || !cur.length} onClick={() => pull.mutate()}>{pull.isPending ? "Đang lấy tin…" : "Lấy tin ngay"}</button>
      </div>
    </section>
  );
}

function UnitAdmin() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "nguoi-dung";
  return (
    <>
      <PageHeader title="Quản trị đơn vị" desc="Tài khoản và phân quyền, danh mục địa bàn – phòng ban – lĩnh vực, quy tắc cảnh báo, nhật ký truy cập và cấu hình đơn vị. Mọi thay đổi đều được ghi nhật ký." />
      <Tabs.Root value={tab} onValueChange={(t) => setParams({ tab: t })}>
        <Tabs.List aria-label="Quản trị" className="mb-4 flex flex-wrap gap-1 border-b border-vien">
          {[["nguoi-dung", "Người dùng"], ["phan-quyen", "Phân quyền"], ["danh-muc", "Danh mục"], ["quy-tac", "Quy tắc cảnh báo"], ["nhat-ky", "Nhật ký truy cập"], ["cau-hinh", "Cấu hình đơn vị"]].map(([k, t]) => <Tabs.Trigger key={k} value={k} className={TAB}>{t}</Tabs.Trigger>)}
        </Tabs.List>
        <Tabs.Content value="nguoi-dung"><UsersAdmin /></Tabs.Content>
        <Tabs.Content value="phan-quyen"><RoleMatrix /></Tabs.Content>
        <Tabs.Content value="danh-muc"><CatalogAdmin /></Tabs.Content>
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
