import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Catalogs } from "@/features/operations/types";

interface Group { id: number; ma: string; ten: string; loai: string | null; nguoi_dung_dau: string | null; dien_thoai: string | null; lat: number | null; lng: number | null; ngung_hoat_dong: boolean }
const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");
const blank = { ma_tdp: "", ten: "", nguoi_dung_dau: "", dien_thoai: "", lat: "", lng: "", ngung_hoat_dong: false };

function GroupsAdmin({ label }: { label: string }) {
  const { tenant } = useAuth();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-dia-ban"], queryFn: () => api<Group[]>("/api/admin/dia-ban") });
  const [edit, setEdit] = useState<number | "new" | null>(null);
  const [f, setF] = useState(blank);
  const [err, setErr] = useState<string | null>(null);
  const loai = tenant?.cap === "xa" ? "thon" : "tdp";
  const save = useMutation({
    mutationFn: () => {
      const body = { ...f, loai, lat: f.lat === "" ? null : Number(f.lat), lng: f.lng === "" ? null : Number(f.lng) };
      return edit === "new" ? api("/api/admin/dia-ban", { method: "POST", body }) : api(`/api/admin/dia-ban/${edit}`, { method: "PUT", body });
    },
    onSuccess: () => { setEdit(null); setErr(null); qc.invalidateQueries({ queryKey: ["admin-dia-ban"] }); qc.invalidateQueries({ queryKey: ["danh-muc"] }); },
    onError: (e) => setErr(errText(e)),
  });
  const start = (g?: Group) => { setErr(null); setEdit(g ? g.id : "new"); setF(g ? { ma_tdp: g.ma, ten: g.ten, nguoi_dung_dau: g.nguoi_dung_dau ?? "", dien_thoai: g.dien_thoai ?? "",
    lat: g.lat === null ? "" : String(g.lat), lng: g.lng === null ? "" : String(g.lng), ngung_hoat_dong: g.ngung_hoat_dong } : blank); };
  const form = (
    <tr><td colSpan={5} className="bg-be-mat-2 px-3 py-3">
      <form aria-label={`Thông tin ${label.toLowerCase()}`} className="grid gap-2 sm:grid-cols-6" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
        <label className="text-sm font-medium">Mã<input className="o-nhap mt-1" value={f.ma_tdp} onChange={(e) => setF({ ...f, ma_tdp: e.target.value })} /></label>
        <label className="text-sm font-medium sm:col-span-2">Tên {label.toLowerCase()}<input className="o-nhap mt-1" value={f.ten} onChange={(e) => setF({ ...f, ten: e.target.value })} /></label>
        <label className="text-sm font-medium">{loai === "thon" ? "Trưởng thôn" : "Tổ trưởng"}<input className="o-nhap mt-1" value={f.nguoi_dung_dau} onChange={(e) => setF({ ...f, nguoi_dung_dau: e.target.value })} /></label>
        <label className="text-sm font-medium">Điện thoại<input className="o-nhap mt-1" value={f.dien_thoai} onChange={(e) => setF({ ...f, dien_thoai: e.target.value })} /></label>
        <div className="grid grid-cols-2 gap-1">
          <label className="text-sm font-medium">Vĩ độ<input className="o-nhap mt-1" inputMode="decimal" value={f.lat} onChange={(e) => setF({ ...f, lat: e.target.value })} /></label>
          <label className="text-sm font-medium">Kinh độ<input className="o-nhap mt-1" inputMode="decimal" value={f.lng} onChange={(e) => setF({ ...f, lng: e.target.value })} /></label>
        </div>
        <label className="flex items-center gap-2 text-sm sm:col-span-3"><input type="checkbox" checked={f.ngung_hoat_dong} onChange={(e) => setF({ ...f, ngung_hoat_dong: e.target.checked })} />
          Ngừng hoạt động (đã sáp nhập, giải thể) — giữ lịch sử, không còn trong biểu mẫu</label>
        {err && <p role="alert" className="text-sm text-son sm:col-span-6">{err}</p>}
        <div className="flex gap-2 sm:col-span-6"><button type="submit" className="btn-chinh py-1.5" disabled={!f.ma_tdp.trim() || !f.ten.trim() || save.isPending}>Lưu</button>
          <button type="button" className="btn-phu py-1.5" onClick={() => setEdit(null)}>Hủy</button></div>
      </form>
    </td></tr>
  );
  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2"><h3 className="flex-1 font-semibold">{label} ({q.data?.length ?? 0})</h3>
        {edit === null && <button type="button" className="btn-phu py-1" onClick={() => start()}>Thêm {label.toLowerCase()}</button>}</div>
      <div className="khu overflow-x-auto rounded-md">
        <table className="w-full text-[14px]" aria-label={`Danh mục ${label.toLowerCase()}`}>
          <thead><tr className="border-b border-vien text-left text-[12.5px] text-muc-nhat"><th className="px-3 py-2 font-medium">Mã</th><th className="font-medium">Tên</th>
            <th className="font-medium">Người đứng đầu</th><th className="font-medium">Vị trí</th><th className="px-3" /></tr></thead>
          <tbody>
            {edit === "new" && form}
            {(q.data ?? []).map((g) => [
              <tr key={g.id} className={`border-b border-vien ${g.ngung_hoat_dong ? "text-muc-nhat" : ""}`}>
                <td className="px-3 py-1.5 tabular">{g.ma}</td><td>{g.ten}{g.ngung_hoat_dong && <span className="nhan-tt tt-cu ml-2">Ngừng hoạt động</span>}</td>
                <td>{g.nguoi_dung_dau ?? "—"}{g.dien_thoai && ` · ${g.dien_thoai}`}</td><td className="text-[13px]">{g.lat !== null ? "Đã có tọa độ" : "—"}</td>
                <td className="px-3 text-right"><button type="button" className="lien-ket text-[13px]" onClick={() => start(g)}>Sửa</button></td>
              </tr>,
              edit === g.id && <Fragment key={`${g.id}-f`}>{form}</Fragment>,
            ])}
          </tbody>
        </table>
      </div>
    </section>
  );
}

type Row = Record<string, string | number>;

function ListEditor({ title, desc, loai, rows, cols, onSaved }: { title: string; desc: string; loai: string; rows: Row[]; cols: { k: string; t: string; options?: { v: string; t: string }[]; w?: string }[]; onSaved: () => void }) {
  const [items, setItems] = useState<Row[]>(rows);
  const [msg, setMsg] = useState<string | null>(null);
  const save = useMutation({ mutationFn: () => api(`/api/admin/danh-muc/${loai}`, { method: "PUT", body: { items } }), onSuccess: () => { setMsg("Đã lưu."); onSaved(); }, onError: (e) => setMsg(errText(e)) });
  return (
    <section className="space-y-2">
      <h3 className="font-semibold">{title}</h3>
      <p className="text-[13.5px] text-muc-nhat">{desc}</p>
      <div className="khu overflow-x-auto rounded-md p-2">
        <table className="w-full text-[14px]" aria-label={title}>
          <thead><tr className="text-left text-[12.5px] text-muc-nhat">{cols.map((c) => <th key={c.k} className="px-1 py-1 font-medium">{c.t}</th>)}<th /></tr></thead>
          <tbody>{items.map((it, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c.k} className={`px-1 py-1 ${c.w ?? ""}`}>
                  {c.options ? <select aria-label={`${c.t} dòng ${i + 1}`} className="o-nhap py-1" value={String(it[c.k] ?? "")} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, [c.k]: e.target.value } : x)))}>
                    {c.options.map((o) => <option key={o.v} value={o.v}>{o.t}</option>)}</select>
                    : <input aria-label={`${c.t} dòng ${i + 1}`} className="o-nhap py-1" value={String(it[c.k] ?? "")} onChange={(e) => setItems(items.map((x, j) => (j === i ? { ...x, [c.k]: e.target.value } : x)))} />}
                </td>
              ))}
              <td className="px-1"><button type="button" className="lien-ket text-[13px] text-son" onClick={() => setItems(items.filter((_, j) => j !== i))}>Xóa</button></td>
            </tr>
          ))}</tbody>
        </table>
        <div className="mt-2 flex items-center gap-2 px-1">
          <button type="button" className="btn-phu py-1" onClick={() => setItems([...items, Object.fromEntries(cols.map((c) => [c.k, c.options?.[0]?.v ?? ""]))])}>Thêm dòng</button>
          <button type="button" className="btn-chinh py-1" disabled={save.isPending} onClick={() => save.mutate()}>Lưu {title.toLowerCase()}</button>
          {msg && <span role="status" className="text-[13px]">{msg}</span>}
        </div>
      </div>
    </section>
  );
}

/** Danh mục của đơn vị: thôn/tổ dân phố, phòng ban, lĩnh vực phản ánh. */
export function CatalogAdmin() {
  const qc = useQueryClient();
  const c = useQuery({ queryKey: ["danh-muc"], queryFn: () => api<Catalogs>("/api/dieu-hanh/danh-muc") });
  if (!c.data) return <p className="text-muc-nhat">Đang tải…</p>;
  const d = c.data;
  const saved = () => qc.invalidateQueries({ queryKey: ["danh-muc"] });
  return (
    <div className="space-y-6">
      <GroupsAdmin label={d.dia_ban_label} />
      <ListEditor key={`pb-${d.phong_ban.length}`} title="Phòng ban, đơn vị phụ trách" loai="phong-ban" onSaved={saved}
        desc={`Theo mô hình chính quyền 2 cấp: Văn phòng HĐND và UBND, ${d.cap === "phuong" ? "Phòng Kinh tế, Hạ tầng và Đô thị" : "Phòng Kinh tế"}, Phòng Văn hóa – Xã hội, Trung tâm Phục vụ hành chính công; cùng các lực lượng phối hợp (Công an, Quân sự, MTTQ, Trạm Y tế).`}
        rows={d.phong_ban as unknown as Row[]} cols={[{ k: "ma", t: "Mã", w: "w-28" }, { k: "ten", t: "Tên" },
          { k: "loai", t: "Loại", w: "w-44", options: [{ v: "chuyen_mon", t: "Cơ quan chuyên môn" }, { v: "phoi_hop", t: "Lực lượng phối hợp" }] }]} />
      <ListEditor key={`lv-${d.linh_vuc.length}`} title="Lĩnh vực phản ánh" loai="linh-vuc" onSaved={saved}
        desc="Mỗi lĩnh vực có đơn vị chủ trì và thời hạn xử lý mặc định (ngày). Phản ánh khẩn cấp luôn có hạn 1 ngày."
        rows={d.linh_vuc as unknown as Row[]} cols={[{ k: "ma", t: "Mã", w: "w-36" }, { k: "ten", t: "Tên" },
          { k: "chu_tri", t: "Đơn vị chủ trì", w: "w-64", options: d.phong_ban.map((p) => ({ v: p.ma, t: p.ten })) }, { k: "han_ngay", t: "Hạn (ngày)", w: "w-24" }]} />
    </div>
  );
}
