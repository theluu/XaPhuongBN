import { useEffect } from "react";
import { headOf, useOrg, type OrgData, type OrgUnit } from "./types";

export interface Assignee { unitMa: string; unitTen: string; nguoi: string }
const KHAC = "__khac__";

/** Gợi ý đơn vị theo nhóm dữ liệu của cảnh báo. */
const NHOM_DON_VI: Record<string, string[]> = {
  ktxh: ["VP"], ngan_sach: ["KTHTDT", "KT"], dau_tu_cong: ["KTHTDT", "KT"], cong_trinh: ["KTHTDT", "KT"],
  dan_cu: ["VHXH", "CA"], gd_yt_mt: ["VHXH"], tthc_pakn: ["HCC"],
};

export function suggestUnit(d: OrgData, nhom?: string): OrgUnit | undefined {
  for (const ma of NHOM_DON_VI[nhom ?? ""] ?? []) {
    const u = d.don_vi.find((x) => x.ma === ma);
    if (u) return u;
  }
  return undefined;
}

/** Chọn đơn vị → chọn cán bộ của đơn vị (mặc định người đứng đầu) từ Cơ cấu tổ chức; vẫn cho nhập tay khi cần.
 *  `units` giới hạn danh sách đơn vị (VD chỉ phòng ban trong danh mục giao việc phản ánh). */
export function AssigneePicker({ value, onChange, nhom, units, unitLabel = "Đơn vị xử lý" }: {
  value: Assignee; onChange: (v: Assignee) => void; nhom?: string; units?: string[]; unitLabel?: string;
}) {
  const org = useOrg();
  const d = org.data?.don_vi ? org.data : undefined;
  const list = d ? d.don_vi.filter((u) => !units || units.includes(u.ma)) : [];
  const staff = d ? d.can_bo.filter((x) => x.don_vi_ma === value.unitMa) : [];
  const custom = !!value.nguoi && !staff.some((x) => x.ho_ten === value.nguoi);

  const pickUnit = (ma: string) => {
    const u = d?.don_vi.find((x) => x.ma === ma);
    const head = d && u ? headOf(d, u.ma) : undefined;
    onChange({ unitMa: ma, unitTen: u?.ten ?? "", nguoi: head?.ho_ten ?? "" });
  };
  // Lần đầu: điền sẵn đơn vị gợi ý theo nhóm dữ liệu và người đứng đầu
  useEffect(() => {
    if (!d || value.unitMa) return;
    const s = suggestUnit(d, nhom);
    if (s && (!units || units.includes(s.ma))) pickUnit(s.ma);
  }, [d, nhom]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!d) {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm font-medium">{unitLabel}<input className="o-nhap mt-1" value={value.unitTen} onChange={(e) => onChange({ ...value, unitMa: "", unitTen: e.target.value })} /></label>
        <label className="block text-sm font-medium">Người phụ trách<input className="o-nhap mt-1" value={value.nguoi} onChange={(e) => onChange({ ...value, nguoi: e.target.value })} /></label>
      </div>
    );
  }
  const groups = Object.entries(d.khoi).map(([k, ten]) => [ten, list.filter((u) => u.khoi === k)] as const).filter(([, us]) => us.length);
  const person = staff.find((x) => x.ho_ten === value.nguoi);
  const suggested = suggestUnit(d, nhom);
  return (
    <div className="space-y-2">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm font-medium">{unitLabel}
          <select className="o-nhap mt-1" value={value.unitMa} onChange={(e) => pickUnit(e.target.value)}>
            <option value="">Chọn đơn vị…</option>
            {groups.map(([ten, us]) => <optgroup key={ten} label={ten}>{us.map((u) => <option key={u.ma} value={u.ma}>{u.ten}</option>)}</optgroup>)}
          </select></label>
        <label className="block text-sm font-medium">Người phụ trách
          <select className="o-nhap mt-1" value={custom ? KHAC : value.nguoi} disabled={!value.unitMa}
            onChange={(e) => onChange({ ...value, nguoi: e.target.value === KHAC ? " " : e.target.value })}>
            <option value="">Chọn cán bộ…</option>
            {staff.map((x) => <option key={x.id} value={x.ho_ten}>{x.ho_ten} – {x.chuc_vu}</option>)}
            <option value={KHAC}>Người khác (nhập tên)…</option>
          </select></label>
      </div>
      {custom && <label className="block text-sm font-medium">Họ tên người phụ trách<input className="o-nhap mt-1" value={value.nguoi.trimStart()} onChange={(e) => onChange({ ...value, nguoi: e.target.value || " " })} /></label>}
      <p className="text-[12.5px] text-muc-nhat">
        {suggested && value.unitMa === suggested.ma && <>Gợi ý theo lĩnh vực của cảnh báo. </>}
        {person ? <>{person.chuc_vu}{person.dien_thoai && <> · <a className="lien-ket" href={`tel:${person.dien_thoai.replace(/\s/g, "")}`}>{person.dien_thoai}</a></>}
          {person.khoi_luong && <> · đang xử lý {person.khoi_luong.dang_xu_ly} việc{person.khoi_luong.qua_han ? `, ${person.khoi_luong.qua_han} quá hạn` : ""}</>}</> :
          value.unitMa && !staff.length ? "Đơn vị chưa có cán bộ trong danh bạ — chọn “Người khác” hoặc cập nhật tại Cơ cấu tổ chức." : null}
      </p>
    </div>
  );
}
