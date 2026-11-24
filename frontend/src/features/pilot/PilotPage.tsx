import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { ROLE } from "@/features/platform-admin/labels";

interface Viec { ma: string; ten: string; xong: boolean; goi_y?: string | null }
interface GiaiDoan { ma: string; tu_ngay: number; den_ngay: number; ten: string; tu: string | null; den: string | null; hien_tai: boolean; qua_han: boolean; viec: Viec[] }
interface TieuChi { ma: string; ten: string; ket_qua: "dat" | "chua_dat" | "chua_du_du_lieu"; chi_tiet: string[]; can_lam: string[]; link: string }
interface HoSo { ma: string; ten: string; trang_thai: string; ghi_chu: string; goi_y?: string | null }
interface Pilot {
  bat_dau: string | null; ngay_thu: number | null; nguong_dung_han: number; lo_trinh: GiaiDoan[]; tieu_chi: TieuChi[]; dat: number; ho_so: HoSo[];
  su_dung: { so_ngay: number; so_dang_nhap: number; so_nguoi_dung_hoat_dong: number; so_thao_tac_du_lieu: number; theo_vai_tro: { role: string; so_nguoi: number }[] };
  co_quyen_sua: boolean; con_du_lieu_minh_hoa: boolean;
}
const KQ: Record<string, [string, string]> = { dat: ["Đạt", "tt-xong"], chua_dat: ["Chưa đạt", "tt-qua-han"], chua_du_du_lieu: ["Chưa đủ dữ liệu", "tt-cu"] };
const HS: Record<string, string> = { chua_co: "Chưa có", dang_chuan_bi: "Đang chuẩn bị", da_co: "Đã có" };
const errText = (e: unknown) => (e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Có lỗi, thử lại");

/** Thí điểm và nghiệm thu: lộ trình 90 ngày (DT V.2), tiêu chí nghiệm thu tự đánh giá (V.3), hồ sơ chuẩn bị (VI). */
export function PilotPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["thi-diem"], queryFn: () => api<Pilot>("/api/thi-diem") });
  const [msg, setMsg] = useState<string | null>(null);
  const put = useMutation({ mutationFn: (body: Record<string, unknown>) => api("/api/thi-diem", { method: "PUT", body }),
    onSuccess: () => { setMsg(null); qc.invalidateQueries({ queryKey: ["thi-diem"] }); }, onError: (e) => setMsg(errText(e)) });
  const d = q.data;
  const [start, setStart] = useState<string | null>(null);
  const [nguong, setNguong] = useState<string | null>(null);
  if (!d?.lo_trinh) return <><PageHeader title="Thí điểm và nghiệm thu" /><p className="text-muc-nhat">{q.isError ? "Bạn không có quyền xem hoặc không tải được." : "Đang tải…"}</p></>;
  const edit = d.co_quyen_sua;
  return (
    <>
      <PageHeader title="Thí điểm và nghiệm thu" desc="Lộ trình 90 ngày, tiêu chí nghiệm thu thử nghiệm và hồ sơ phường cần chuẩn bị theo mục V, VI của kịch bản điều hành. Tiêu chí được hệ thống tự đánh giá trên dữ liệu thật; dữ liệu minh họa không bao giờ được tính là kết quả." />
      {d.con_du_lieu_minh_hoa && <p role="status" className="mb-4 rounded border border-[var(--tam-thoi)] bg-be-mat px-3 py-2 text-[14px]">Đơn vị còn dữ liệu minh họa: các tiêu chí chỉ tính số liệu thật, nên kết quả dưới đây phản ánh đúng phần dữ liệu thật đã có.</p>}
      {msg && <p role="alert" className="mb-3 text-sm text-son">{msg}</p>}

      <section aria-labelledby="tieu-chi" className="mb-5">
        <h2 id="tieu-chi" className="mb-2 text-[19px] font-extrabold">Tiêu chí nghiệm thu thử nghiệm <span className="text-[14px] font-normal text-muc-nhat">· đạt {d.dat}/{d.tieu_chi.length}</span></h2>
        <ol className="space-y-2">{d.tieu_chi.map((c, i) => {
          const [t, cls] = KQ[c.ket_qua];
          return (
            <li key={c.ma} className="khu rounded-md px-4 py-3">
              <div className="flex flex-wrap items-start gap-3">
                <span className="font-so text-[18px] font-bold text-muc-nhat">{i + 1}</span>
                <p className="min-w-0 flex-1 text-[14.5px] font-medium">{c.ten}</p>
                <span className={`nhan-tt ${cls}`}>{t}</span>
              </div>
              <ul className="ml-7 mt-1 list-disc pl-4 text-[13.5px] text-muc-nhat">{c.chi_tiet.map((x) => <li key={x}>{x}</li>)}</ul>
              {c.can_lam.length > 0 && <p className="ml-7 mt-1 text-[13.5px]"><b>Cần làm:</b> {c.can_lam.join("; ")}. <Link className="lien-ket" to={c.link}>Mở</Link></p>}
            </li>
          );
        })}</ol>
      </section>

      <section aria-labelledby="lo-trinh" className="mb-5">
        <div className="mb-2 flex flex-wrap items-end gap-3">
          <h2 id="lo-trinh" className="flex-1 text-[19px] font-extrabold">Lộ trình triển khai thí điểm
            <span className="text-[14px] font-normal text-muc-nhat"> · {d.bat_dau ? `bắt đầu ${formatDate(d.bat_dau)}, ngày thứ ${d.ngay_thu}` : "chưa đặt ngày bắt đầu"}</span></h2>
          {edit && <>
            <label className="text-sm">Ngày bắt đầu<input type="date" className="o-nhap ml-2 w-auto py-1" value={start ?? d.bat_dau ?? ""} onChange={(e) => setStart(e.target.value)} /></label>
            <label className="text-sm">Ngưỡng đúng hạn (%)<input type="number" min={0} max={100} className="o-nhap ml-2 w-20 py-1" value={nguong ?? String(d.nguong_dung_han)} onChange={(e) => setNguong(e.target.value)} /></label>
            <button type="button" className="btn-phu py-1" disabled={put.isPending} onClick={() => put.mutate({ bat_dau: (start ?? d.bat_dau) || null, nguong_dung_han: Number(nguong ?? d.nguong_dung_han) })}>Lưu</button>
          </>}
        </div>
        <div className="grid gap-3 lg:grid-cols-4">{d.lo_trinh.map((g) => {
          const xong = g.viec.filter((v) => v.xong).length;
          return (
            <article key={g.ma} aria-label={g.ten} className={`khu rounded-md p-3 ${g.hien_tai ? "ring-2 ring-[var(--chinh)]" : ""}`}>
              <p className="text-[12.5px] text-muc-nhat">Ngày {g.tu_ngay}–{g.den_ngay}{g.tu && ` · ${formatDate(g.tu)}–${formatDate(g.den)}`}</p>
              <h3 className="font-semibold">{g.ten} {g.hien_tai && <span className="nhan-tt tt-thuong">Đang thực hiện</span>}
                {g.qua_han && xong < g.viec.length && <span className="nhan-tt tt-qua-han">Quá hạn</span>}</h3>
              <p className="text-[12.5px] text-muc-nhat">{xong}/{g.viec.length} việc hoàn thành</p>
              <ul className="mt-2 space-y-1.5 text-[13.5px]">{g.viec.map((v) => (
                <li key={v.ma}><label className="flex items-start gap-2">
                  <input type="checkbox" className="mt-0.5" checked={v.xong} disabled={!edit || put.isPending} onChange={(e) => put.mutate({ viec: { [v.ma]: e.target.checked } })} />
                  <span>{v.ten}{v.goi_y && <span className="block text-[12px] text-muc-nhat">Hệ thống ghi nhận: {v.goi_y}</span>}</span></label></li>
              ))}</ul>
            </article>
          );
        })}</div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <section aria-labelledby="ho-so">
          <h2 id="ho-so" className="mb-2 text-[19px] font-extrabold">Hồ sơ UBND phường chuẩn bị trước khi triển khai</h2>
          <div className="khu overflow-x-auto rounded-md">
            <table className="w-full text-[14px]" aria-label="Hồ sơ chuẩn bị">
              <thead><tr className="border-b border-vien text-left text-[12.5px] text-muc-nhat"><th className="px-3 py-2 font-medium">Nội dung</th><th className="font-medium">Trạng thái</th><th className="px-3 font-medium">Ghi chú</th></tr></thead>
              <tbody>{d.ho_so.map((h) => <HoSoRow key={h.ma} h={h} edit={edit} onSave={(v) => put.mutate({ ho_so: { [h.ma]: v } })} />)}</tbody>
            </table>
          </div>
          <p className="mt-1 text-[12.5px] text-muc-nhat">Danh mục theo mục VI. Đầu mối, trách nhiệm cung cấp và phiếu xác định nguồn: <Link className="lien-ket" to="/co-cau-to-chuc?tab=dau-moi">Cơ cấu tổ chức → Đầu mối và trách nhiệm</Link>.</p>
        </section>
        <section aria-labelledby="su-dung">
          <h2 id="su-dung" className="mb-2 text-[19px] font-extrabold">Mức độ sử dụng ({d.su_dung.so_ngay} ngày)</h2>
          <div className="khu rounded-md p-4">
            <dl className="grid grid-cols-3 gap-3">
              {([["Lượt đăng nhập", d.su_dung.so_dang_nhap], ["Người dùng hoạt động", d.su_dung.so_nguoi_dung_hoat_dong], ["Thao tác dữ liệu", d.su_dung.so_thao_tac_du_lieu]] as const).map(([k, v]) => (
                <div key={k}><dt className="text-[12.5px] text-muc-nhat">{k}</dt><dd className="font-so text-[22px] font-bold tabular">{formatNumber(v)}</dd></div>
              ))}
            </dl>
            {d.su_dung.theo_vai_tro.length > 0 && <ul className="mt-3 text-[13.5px]">{d.su_dung.theo_vai_tro.map((r) => <li key={r.role} className="flex justify-between border-b border-vien py-1"><span>{ROLE[r.role] ?? r.role}</span><span className="tabular">{r.so_nguoi} người</span></li>)}</ul>}
          </div>
        </section>
      </div>
    </>
  );
}

function HoSoRow({ h, edit, onSave }: { h: HoSo; edit: boolean; onSave: (v: { trang_thai: string; ghi_chu: string }) => void }) {
  const [note, setNote] = useState(h.ghi_chu);
  return (
    <tr className="border-b border-vien align-top">
      <td className="px-3 py-2"><b>({h.ma})</b> {h.ten}{h.goi_y && <span className="block text-[12px] text-muc-nhat">Hệ thống ghi nhận: {h.goi_y}</span>}</td>
      <td className="py-2">{edit
        ? <select aria-label={`Trạng thái hồ sơ ${h.ma}`} className="o-nhap w-auto py-1" value={h.trang_thai} onChange={(e) => onSave({ trang_thai: e.target.value, ghi_chu: note })}>
          {Object.entries(HS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        : <span className={`nhan-tt ${h.trang_thai === "da_co" ? "tt-xong" : h.trang_thai === "dang_chuan_bi" ? "tt-sap-han" : "tt-cu"}`}>{HS[h.trang_thai]}</span>}</td>
      <td className="px-3 py-2">{edit
        ? <input aria-label={`Ghi chú hồ sơ ${h.ma}`} className="o-nhap py-1" value={note} placeholder="Số văn bản, nơi lưu…" onChange={(e) => setNote(e.target.value)} onBlur={() => note !== h.ghi_chu && onSave({ trang_thai: h.trang_thai, ghi_chu: note })} />
        : <span className="text-[13.5px]">{h.ghi_chu || "—"}</span>}</td>
    </tr>
  );
}
