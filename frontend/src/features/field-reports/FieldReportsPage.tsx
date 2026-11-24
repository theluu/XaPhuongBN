import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { LocationPicker } from "@/components/LocationPicker";
import { DeadlineTag, NoLocationTag, UrgentTag } from "@/components/StatusTag";
import type { Catalogs, FieldReport } from "@/features/operations/types";
import { ReportDetail, useCatalogs } from "./ReportDetail";

const TRANG_THAI = [["dang_mo", "Đang mở"], ["moi", "Mới tiếp nhận"], ["da_giao", "Đã giao"], ["dang_xu_ly", "Đang xử lý"], ["cho_xac_nhan", "Chờ xác nhận"],
  ["hoan_thanh", "Đã xử lý"], ["tu_choi", "Không thuộc thẩm quyền"], ["", "Tất cả"]];
const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");

function IntakeForm({ cat, onDone, onCancel }: { cat: Catalogs; onDone: (r: FieldReport) => void; onCancel: () => void }) {
  const { tenant } = useAuth();
  const [f, setF] = useState({ tieu_de: "", mo_ta: "", linh_vuc: cat.linh_vuc[0]?.ma ?? "", nguon: cat.nguon[0]?.ma ?? "truc_tiep", khan_cap: false,
    tdp_id: "", dia_chi: "", nguoi_gui_ten: "", nguoi_gui_sdt: "" });
  const [pos, setPos] = useState<{ lat: number; lng: number } | null>(null);
  const [anh, setAnh] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: () => api<FieldReport>("/api/phan-anh", { method: "POST", body: { ...f, tdp_id: f.tdp_id ? Number(f.tdp_id) : null, lat: pos?.lat ?? null, lng: pos?.lng ?? null, anh_keys: anh } }),
    onSuccess: onDone, onError: (e) => setErr(errText(e)),
  });
  async function upload(files: FileList) {
    for (const file of Array.from(files).slice(0, 5)) {
      const fd = new FormData();
      fd.append("file", file);
      try { const r = await api<{ key: string }>("/api/files", { method: "POST", form: fd }); setAnh((a) => [...a, r.key]); } catch (e) { setErr(errText(e)); }
    }
  }
  const lv = cat.linh_vuc.find((x) => x.ma === f.linh_vuc);
  const chuTri = cat.phong_ban.find((p) => p.ma === lv?.chu_tri)?.ten;
  return (
    <form aria-label="Tiếp nhận phản ánh" className="khu space-y-3 rounded-md p-4" onSubmit={(e) => { e.preventDefault(); m.mutate(); }}>
      <h2 className="the-tieu-de">Tiếp nhận phản ánh</h2>
      <div className="grid gap-3 lg:grid-cols-2">
        <div className="space-y-3">
          <label className="block text-sm font-medium">Nội dung phản ánh (tiêu đề)<input className="o-nhap mt-1" required minLength={3} value={f.tieu_de} onChange={(e) => setF({ ...f, tieu_de: e.target.value })} /></label>
          <label className="block text-sm font-medium">Mô tả chi tiết<textarea className="o-nhap mt-1" rows={3} value={f.mo_ta} onChange={(e) => setF({ ...f, mo_ta: e.target.value })} /></label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm font-medium">Lĩnh vực<select className="o-nhap mt-1" value={f.linh_vuc} onChange={(e) => setF({ ...f, linh_vuc: e.target.value })}>
              {cat.linh_vuc.map((x) => <option key={x.ma} value={x.ma}>{x.ten}</option>)}</select></label>
            <label className="block text-sm font-medium">Nguồn tiếp nhận<select className="o-nhap mt-1" value={f.nguon} onChange={(e) => setF({ ...f, nguon: e.target.value })}>
              {cat.nguon.map((x) => <option key={x.ma} value={x.ma}>{x.ten}</option>)}</select></label>
          </div>
          {chuTri && <p className="text-[13px] text-muc-nhat">Đơn vị chủ trì đề xuất: <b>{chuTri}</b>, hạn {f.khan_cap ? 1 : lv?.han_ngay} ngày. Lãnh đạo có thể điều chỉnh khi giao.</p>}
          <label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" checked={f.khan_cap} onChange={(e) => setF({ ...f, khan_cap: e.target.checked })} />Khẩn cấp (nguy hiểm tính mạng, tài sản, cần xử lý trong ngày)</label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm font-medium">{cat.dia_ban_label}<select className="o-nhap mt-1" value={f.tdp_id} onChange={(e) => setF({ ...f, tdp_id: e.target.value })}>
              <option value="">Chưa xác định</option>{cat.dia_ban.map((g) => <option key={g.id} value={g.id}>{g.ten}</option>)}</select></label>
            <label className="block text-sm font-medium">Địa chỉ cụ thể<input className="o-nhap mt-1" value={f.dia_chi} onChange={(e) => setF({ ...f, dia_chi: e.target.value })} /></label>
          </div>
          <fieldset className="rounded-md border border-vien p-3">
            <legend className="px-1 text-sm font-medium">Người phản ánh (không bắt buộc; không hiển thị trên màn hình TV)</legend>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm">Họ tên<input className="o-nhap mt-1" value={f.nguoi_gui_ten} onChange={(e) => setF({ ...f, nguoi_gui_ten: e.target.value })} /></label>
              <label className="block text-sm">Số điện thoại<input className="o-nhap mt-1" inputMode="tel" value={f.nguoi_gui_sdt} onChange={(e) => setF({ ...f, nguoi_gui_sdt: e.target.value })} /></label>
            </div>
          </fieldset>
        </div>
        <div className="space-y-3">
          <div><div className="mb-1 text-sm font-medium">Vị trí hiện trường</div>
            <LocationPicker value={pos} center={tenant?.ban_do?.tam ?? [21.2725, 106.0975]} onChange={setPos} tileUrl={tenant?.ban_do?.tile_url} /></div>
          <label className="block text-sm font-medium">Ảnh hiện trường (tối đa 5 ảnh)
            <input type="file" accept="image/png,image/jpeg,image/webp" multiple className="mt-1 block text-sm" onChange={(e) => e.target.files && upload(e.target.files)} /></label>
          {anh.length > 0 && <p className="text-[13px] text-muc-nhat">Đã tải {anh.length} ảnh.</p>}
        </div>
      </div>
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <div className="flex gap-2">
        <button type="submit" className="btn-chinh" disabled={m.isPending || f.tieu_de.trim().length < 3}>Tiếp nhận</button>
        <button type="button" className="btn-phu" onClick={onCancel}>Hủy</button>
      </div>
    </form>
  );
}

/** Phản ánh hiện trường: tiếp nhận → xác định địa điểm → giao → theo dõi hạn → xác nhận đã xử lý. */
export function FieldReportsPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const cat = useCatalogs();
  const [params, setParams] = useSearchParams();
  const set = (k: string, v: string | null) => { const p = new URLSearchParams(params); if (v) p.set(k, v); else p.delete(k); setParams(p, { replace: true }); };
  const tt = params.get("trang_thai") ?? "dang_mo";
  const lv = params.get("linh_vuc") ?? "";
  const tdp = params.get("tdp") ?? "";
  const [text, setText] = useState(params.get("q") ?? "");
  const sel = params.get("id");
  const [intake, setIntake] = useState(params.get("tiep_nhan") === "1");
  const list = useQuery({ queryKey: ["phan-anh-list", tt, lv, tdp, params.get("q")], queryFn: () => api<FieldReport[]>("/api/phan-anh", { params: { trang_thai: tt || undefined, linh_vuc: lv || undefined, tdp: tdp || undefined, q: params.get("q") || undefined } }) });
  const canIntake = can("nhap", "tthc_pakn") || can("duyet", "canh_bao");
  return (
    <>
      <PageHeader title="Phản ánh hiện trường" desc="Tiếp nhận phản ánh của người dân, xác định địa điểm, giao đơn vị phụ trách, theo dõi hạn và xác nhận kết quả xử lý.">
        {canIntake && !intake && <button type="button" className="btn-chinh" onClick={() => setIntake(true)}><Plus size={16} aria-hidden />Tiếp nhận phản ánh</button>}
      </PageHeader>
      {intake && cat.data && (
        <div className="mb-4"><IntakeForm cat={cat.data} onCancel={() => setIntake(false)} onDone={(r) => { setIntake(false); qc.invalidateQueries({ queryKey: ["phan-anh-list"] }); qc.invalidateQueries({ queryKey: ["dieu-hanh"] }); set("id", String(r.id)); }} /></div>
      )}
      <div className="mb-3 flex flex-wrap items-end gap-2">
        <label className="text-sm"><span className="block text-muc-nhat">Trạng thái</span><select className="o-nhap w-auto py-1.5" value={tt} onChange={(e) => set("trang_thai", e.target.value || "")}>
          {TRANG_THAI.map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label className="text-sm"><span className="block text-muc-nhat">Lĩnh vực</span><select className="o-nhap w-auto py-1.5" value={lv} onChange={(e) => set("linh_vuc", e.target.value || null)}>
          <option value="">Tất cả</option>{cat.data?.linh_vuc.map((x) => <option key={x.ma} value={x.ma}>{x.ten}</option>)}</select></label>
        <label className="text-sm"><span className="block text-muc-nhat">{cat.data?.dia_ban_label ?? "Địa bàn"}</span><select className="o-nhap w-auto py-1.5" value={tdp} onChange={(e) => set("tdp", e.target.value || null)}>
          <option value="">Toàn địa bàn</option>{cat.data?.dia_ban.map((g) => <option key={g.id} value={g.id}>{g.ten}</option>)}</select></label>
        <form className="flex items-end gap-2" onSubmit={(e) => { e.preventDefault(); set("q", text.trim() || null); }}>
          <label className="text-sm"><span className="block text-muc-nhat">Tìm theo mã, nội dung, địa chỉ</span><input className="o-nhap w-60 py-1.5" value={text} onChange={(e) => setText(e.target.value)} /></label>
          <button type="submit" className="btn-phu py-1.5">Tìm</button>
        </form>
      </div>
      <div className={`grid gap-4 ${sel ? "xl:grid-cols-[minmax(0,1fr)_420px]" : ""}`}>
        <div className="khu overflow-x-auto rounded-md">
          <table className="w-full text-[14px]" aria-label="Danh sách phản ánh">
            <thead><tr className="border-b border-vien text-left text-[12.5px] text-muc-nhat">
              <th className="px-3 py-2 font-medium">Phản ánh</th><th className="font-medium">Địa điểm</th><th className="font-medium">Đơn vị phụ trách</th>
              <th className="font-medium">Trạng thái</th><th className="px-3 font-medium">Hạn</th></tr></thead>
            <tbody>
              {(list.data ?? []).map((r) => (
                <tr key={r.id} onClick={() => set("id", String(r.id))} aria-selected={sel === String(r.id)}
                  className={`cursor-pointer border-b border-vien align-top ${sel === String(r.id) ? "bg-[color-mix(in_srgb,var(--chinh)_8%,transparent)]" : "hover:bg-be-mat-2"}`}>
                  <td className="px-3 py-2"><div className="font-medium">{r.tieu_de}</div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[12px] text-muc-nhat"><span>{r.ma} · {r.linh_vuc_ten} · {formatDateTime(r.tiep_nhan_luc)}</span>{r.khan_cap && <UrgentTag />}{!r.co_vi_tri && <NoLocationTag />}</div></td>
                  <td className="py-2 pr-2 text-[13.5px]">{r.dia_chi || r.tdp_ten || "—"}</td>
                  <td className="py-2 pr-2 text-[13.5px]">{r.don_vi_phu_trach_ten ?? "—"}</td>
                  <td className="py-2 pr-2 text-[13px]">{r.trang_thai_ten}</td>
                  <td className="px-3 py-2"><DeadlineTag han={r.han_xu_ly} quaHan={r.qua_han_ngay} trangThai={r.trang_thai} /></td>
                </tr>
              ))}
              {list.data?.length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-muc-nhat">Không có phản ánh theo bộ lọc.</td></tr>}
              {list.isError && <tr><td colSpan={5} className="px-3 py-6 text-center text-muc-nhat">Bạn chưa được cấp quyền xem phản ánh, hoặc không tải được dữ liệu.</td></tr>}
            </tbody>
          </table>
        </div>
        {sel && <div className="xl:sticky xl:top-4 xl:h-[calc(100vh-120px)]"><ReportDetail id={Number(sel)} onClose={() => set("id", null)} /></div>}
      </div>
    </>
  );
}
