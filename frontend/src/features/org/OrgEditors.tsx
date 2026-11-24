import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { OrgData, OrgUnit, StaffRow } from "./types";

const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");
const CAP = { truong: "Cấp trưởng", pho: "Cấp phó", thanh_vien: "Cán bộ, công chức" };

export function StaffForm({ d, unitMa, staff, onDone }: { d: OrgData; unitMa: string; staff?: StaffRow; onDone: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState({ ma: staff?.ma ?? "", don_vi_ma: staff?.don_vi_ma ?? unitMa, ho_ten: staff?.ho_ten ?? "", chuc_vu: staff?.chuc_vu ?? "", cap: staff?.cap ?? "thanh_vien",
    dien_thoai: staff?.dien_thoai ?? "", email: staff?.email ?? "", nhiem_vu: staff?.nhiem_vu ?? "", dia_ban_ids: staff?.dia_ban_ids ?? [] as number[] });
  const [err, setErr] = useState<string | null>(null);
  const done = () => { qc.invalidateQueries({ queryKey: ["co-cau"] }); onDone(); };
  const save = useMutation({ mutationFn: () => api(staff ? `/api/co-cau/can-bo/${staff.id}` : "/api/co-cau/can-bo", { method: staff ? "PUT" : "POST",
    body: { ...f, linh_vuc: staff?.linh_vuc ?? [], user_id: staff?.user_id ?? null, thu_tu: staff?.thu_tu ?? 99 } }), onSuccess: done, onError: (e) => setErr(errText(e)) });
  const del = useMutation({ mutationFn: () => api(`/api/co-cau/can-bo/${staff!.id}`, { method: "DELETE" }), onSuccess: done, onError: (e) => setErr(errText(e)) });
  const [confirmDel, setConfirmDel] = useState(false);
  return (
    <form aria-label={staff ? `Sửa cán bộ ${staff.ho_ten}` : "Thêm cán bộ"} className="space-y-2 rounded-md border border-vien bg-be-mat-2 p-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-sm font-medium">Mã cán bộ<input className="o-nhap mt-1" value={f.ma} onChange={(e) => setF({ ...f, ma: e.target.value })} /></label>
        <label className="text-sm font-medium">Họ tên<input className="o-nhap mt-1" value={f.ho_ten} onChange={(e) => setF({ ...f, ho_ten: e.target.value })} /></label>
        <label className="text-sm font-medium">Chức vụ<input className="o-nhap mt-1" value={f.chuc_vu} onChange={(e) => setF({ ...f, chuc_vu: e.target.value })} /></label>
        <label className="text-sm font-medium">Cấp<select className="o-nhap mt-1" value={f.cap} onChange={(e) => setF({ ...f, cap: e.target.value as StaffRow["cap"] })}>
          {Object.entries(CAP).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label className="text-sm font-medium">Đơn vị công tác<select className="o-nhap mt-1" value={f.don_vi_ma} onChange={(e) => setF({ ...f, don_vi_ma: e.target.value })}>
          {d.don_vi.map((u) => <option key={u.ma} value={u.ma}>{u.ten}</option>)}</select></label>
        <label className="text-sm font-medium">Điện thoại công vụ<input className="o-nhap mt-1" inputMode="tel" value={f.dien_thoai} onChange={(e) => setF({ ...f, dien_thoai: e.target.value })} /></label>
        <label className="col-span-2 text-sm font-medium">Email công vụ<input className="o-nhap mt-1" type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
      </div>
      <label className="block text-sm font-medium">Nhiệm vụ được phân công<textarea className="o-nhap mt-1" rows={2} value={f.nhiem_vu} onChange={(e) => setF({ ...f, nhiem_vu: e.target.value })} /></label>
      {d.dia_ban.length > 0 && (
        <fieldset className="flex flex-wrap gap-x-3 gap-y-1 text-[13px]"><legend className="mb-1 text-sm font-medium">{d.dia_ban_label} được phân công theo dõi</legend>
          {d.dia_ban.map((g) => <label key={g.id} className="flex items-center gap-1"><input type="checkbox" checked={f.dia_ban_ids.includes(g.id)}
            onChange={(e) => setF({ ...f, dia_ban_ids: e.target.checked ? [...f.dia_ban_ids, g.id] : f.dia_ban_ids.filter((x) => x !== g.id) })} />{g.ten}</label>)}
        </fieldset>
      )}
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <div className="flex flex-wrap items-center gap-2">
        <button type="submit" className="btn-chinh py-1.5" disabled={!f.ma.trim() || !f.ho_ten.trim() || !f.chuc_vu.trim() || save.isPending}>Lưu</button>
        <button type="button" className="btn-phu py-1.5" onClick={onDone}>Hủy</button>
        {staff && (confirmDel
          ? <><span className="text-[13px] text-son">Xóa {staff.ho_ten} khỏi danh bạ?</span><button type="button" className="btn-nguy py-1.5" onClick={() => del.mutate()}>Xóa</button>
              <button type="button" className="btn-phu py-1.5" onClick={() => setConfirmDel(false)}>Không</button></>
          : <button type="button" className="lien-ket ml-auto text-[13px] text-son" onClick={() => setConfirmDel(true)}>Xóa cán bộ</button>)}
      </div>
    </form>
  );
}

export function UnitForm({ d, unit, onDone }: { d: OrgData; unit: OrgUnit; onDone: () => void }) {
  const qc = useQueryClient();
  const leaders = d.can_bo.filter((x) => ["UBND", "DU", "HDND"].includes(x.don_vi_ma) && x.cap !== "thanh_vien");
  const [f, setF] = useState({ ma: unit.ma, ten: unit.ten, khoi: unit.khoi, cap_tren_ma: unit.cap_tren_ma ?? "", lanh_dao_phu_trach_ma: unit.lanh_dao_phu_trach_ma ?? "",
    chuc_nang: unit.chuc_nang, dien_thoai: unit.dien_thoai ?? "", email: unit.email ?? "", dia_chi: unit.dia_chi ?? "", thu_tu: unit.thu_tu });
  const [err, setErr] = useState<string | null>(null);
  const save = useMutation({ mutationFn: () => api(`/api/co-cau/don-vi/${unit.ma}`, { method: "PUT", body: { ...f, cap_tren_ma: f.cap_tren_ma || null, lanh_dao_phu_trach_ma: f.lanh_dao_phu_trach_ma || null } }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["co-cau"] }); onDone(); }, onError: (e) => setErr(errText(e)) });
  return (
    <form aria-label={`Sửa đơn vị ${unit.ten}`} className="space-y-2 rounded-md border border-vien bg-be-mat-2 p-3" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <label className="block text-sm font-medium">Tên đơn vị<input className="o-nhap mt-1" value={f.ten} onChange={(e) => setF({ ...f, ten: e.target.value })} /></label>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-sm font-medium">Đơn vị cấp trên<select className="o-nhap mt-1" value={f.cap_tren_ma} onChange={(e) => setF({ ...f, cap_tren_ma: e.target.value })}>
          <option value="">Không có</option>{d.don_vi.filter((u) => u.ma !== unit.ma).map((u) => <option key={u.ma} value={u.ma}>{u.ten}</option>)}</select></label>
        <label className="text-sm font-medium">Lãnh đạo phụ trách<select className="o-nhap mt-1" value={f.lanh_dao_phu_trach_ma} onChange={(e) => setF({ ...f, lanh_dao_phu_trach_ma: e.target.value })}>
          <option value="">Chưa phân công</option>{leaders.map((x) => <option key={x.ma} value={x.ma}>{x.ho_ten} – {x.chuc_vu}</option>)}</select></label>
        <label className="text-sm font-medium">Điện thoại<input className="o-nhap mt-1" value={f.dien_thoai} onChange={(e) => setF({ ...f, dien_thoai: e.target.value })} /></label>
        <label className="text-sm font-medium">Email<input className="o-nhap mt-1" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
      </div>
      <label className="block text-sm font-medium">Chức năng, nhiệm vụ<textarea className="o-nhap mt-1" rows={2} value={f.chuc_nang} onChange={(e) => setF({ ...f, chuc_nang: e.target.value })} /></label>
      {err && <p role="alert" className="text-sm text-son">{err}</p>}
      <div className="flex gap-2"><button type="submit" className="btn-chinh py-1.5" disabled={!f.ten.trim() || save.isPending}>Lưu</button>
        <button type="button" className="btn-phu py-1.5" onClick={onDone}>Hủy</button></div>
    </form>
  );
}
