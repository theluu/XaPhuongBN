import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, FileText, Pencil, Search } from "lucide-react";
import { api, getToken } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";

export interface NhiemVu { id: number; tieu_de: string; co_quan_xu_ly: string; han: string; trang_thai: string; qua_han: boolean; alert_id: number }
export interface VanBanRow { id: number; so_ky_hieu: string; ngay_ban_hanh: string; loai: string; loai_ten: string; co_quan_ban_hanh: string; nguoi_ky: string;
  trich_yeu: string; file_key: string | null; lien_ket: string | null; han_thuc_hien: string | null; trang_thai: string; nhiem_vu: NhiemVu[];
  tien_do: { tong: number; hoan_thanh: number; qua_han: number }; is_sample: boolean }
interface Data { van_ban: VanBanRow[]; loai: Record<string, string>; co_quyen_sua: boolean }

export async function openFile(key: string) {
  const r = await fetch(`/api/files/${key}`, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
  if (!r.ok) return;
  const url = URL.createObjectURL(await r.blob());
  window.open(url, "_blank", "noopener");
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function DocLinks({ v }: { v: VanBanRow }) {
  return (
    <span className="inline-flex flex-wrap gap-3 text-[13px]">
      {v.file_key && <button type="button" className="lien-ket inline-flex items-center gap-1" onClick={() => openFile(v.file_key!)}><FileText size={13} aria-hidden />Tệp văn bản</button>}
      {v.lien_ket && (v.lien_ket.startsWith("/") ? <Link className="lien-ket" to={v.lien_ket}>Liên kết</Link>
        : <a className="lien-ket inline-flex items-center gap-1" href={v.lien_ket} target="_blank" rel="noopener noreferrer">Bản đăng tải<ExternalLink size={12} aria-hidden /></a>)}
    </span>
  );
}

/** Văn bản chỉ đạo điều hành gắn nhiệm vụ: tra cứu, tiến độ thực hiện theo văn bản. */
export function VanBanPage() {
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  const [loai, setLoai] = useState("");
  const [hl, setHl] = useState(true);
  const r = useQuery({ queryKey: ["van-ban", term, loai, hl], queryFn: () => api<Data>("/api/van-ban", { params: { q: term || undefined, loai: loai || undefined, con_hieu_luc: hl ? "true" : undefined } }) });
  const d = r.data;
  return (
    <>
      <PageHeader title="Văn bản chỉ đạo điều hành" desc="Nghị quyết, quyết định, chỉ thị, kế hoạch, thông báo kết luận… và tiến độ các nhiệm vụ chỉ đạo được giao theo từng văn bản.">
        {d?.co_quyen_sua && <Link className="btn-chinh" to="/quan-ly-du-lieu?bo=van_ban"><Pencil size={15} aria-hidden />Cập nhật văn bản</Link>}
      </PageHeader>
      <form className="mb-3 flex flex-wrap items-center gap-2" onSubmit={(e) => { e.preventDefault(); setTerm(q); }}>
        <label className="relative"><span className="sr-only">Tìm văn bản</span><Search size={15} aria-hidden className="absolute left-2.5 top-2.5 text-muc-nhat" />
          <input className="o-nhap w-72 py-1.5 pl-8" placeholder="Số ký hiệu, trích yếu, cơ quan ban hành" value={q} onChange={(e) => setQ(e.target.value)} /></label>
        <select aria-label="Loại văn bản" className="o-nhap w-auto py-1.5" value={loai} onChange={(e) => setLoai(e.target.value)}>
          <option value="">Tất cả loại</option>{Object.entries(d?.loai ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <label className="flex items-center gap-1.5 text-sm"><input type="checkbox" checked={hl} onChange={(e) => setHl(e.target.checked)} />Chỉ văn bản còn hiệu lực</label>
        <button type="submit" className="btn-phu py-1.5">Tìm</button>
      </form>
      {!d?.van_ban ? <p className="text-muc-nhat">{r.isError ? "Không tải được văn bản." : "Đang tải…"}</p> : (
        <ul className="space-y-2">{d.van_ban.map((v) => (
          <li key={v.id}><article aria-label={v.so_ky_hieu} className="khu rounded-md px-4 py-3">
            <div className="flex flex-wrap items-start gap-x-3 gap-y-1">
              <div className="min-w-0 flex-1">
                <p className="text-[13px] text-muc-nhat"><b className="text-muc">{v.so_ky_hieu}</b> · {v.loai_ten} · {formatDate(v.ngay_ban_hanh)} · {v.co_quan_ban_hanh}{v.nguoi_ky && ` · ${v.nguoi_ky}`}</p>
                <h2 className="text-[15px] font-semibold leading-snug">{v.trich_yeu}</h2>
              </div>
              <span className="flex flex-wrap gap-1">
                {v.trang_thai === "het_hieu_luc" && <span className="nhan-tt tt-cu">Hết hiệu lực</span>}
                {v.han_thuc_hien && <span className={`nhan-tt ${v.tien_do.qua_han ? "tt-qua-han" : "tt-thuong"}`}>Hạn {formatDate(v.han_thuc_hien)}</span>}
                {v.is_sample && <span className="nhan-tt tt-cu">Minh họa</span>}
              </span>
            </div>
            <div className="mt-1"><DocLinks v={v} /></div>
            {v.tien_do.tong > 0 && (
              <details className="mt-2 text-[13.5px]"><summary className="cursor-pointer">
                <b>{v.tien_do.hoan_thanh}/{v.tien_do.tong}</b> nhiệm vụ hoàn thành{v.tien_do.qua_han ? <b className="text-son"> · {v.tien_do.qua_han} quá hạn</b> : ""}</summary>
                <ul className="mt-1 space-y-0.5">{v.nhiem_vu.map((n) => (
                  <li key={n.id}><Link className="lien-ket" to={`/canh-bao?id=${n.alert_id}`}>{n.tieu_de}</Link> · {n.co_quan_xu_ly} · hạn {formatDate(n.han)}
                    {n.trang_thai === "hoan_thanh" ? <span className="text-[var(--xac-nhan)]"> · hoàn thành</span> : n.qua_han ? <b className="text-son"> · quá hạn</b> : ""}</li>
                ))}</ul>
              </details>
            )}
          </article></li>
        ))}
        {d.van_ban.length === 0 && <li className="text-muc-nhat">Không có văn bản.</li>}</ul>
      )}
    </>
  );
}

/** Văn bản liên quan của một nhiệm vụ chỉ đạo (trong hồ sơ theo dõi). */
export function RelatedDocs({ caseId }: { caseId: number }) {
  const r = useQuery({ queryKey: ["van-ban-nv", caseId], queryFn: () => api<Data>("/api/van-ban", { params: { nhiem_vu: caseId } }) });
  const rows = r.data?.van_ban ?? [];
  if (!rows.length) return null;
  return (
    <section aria-label="Văn bản chỉ đạo liên quan" className="rounded border border-vien bg-nen px-3 py-2 text-[13.5px]">
      <h4 className="mb-1 font-semibold">Văn bản chỉ đạo</h4>
      <ul className="space-y-1">{rows.map((v) => <li key={v.id}><b>{v.so_ky_hieu}</b> ({formatDate(v.ngay_ban_hanh)}): {v.trich_yeu} <DocLinks v={v} /></li>)}</ul>
    </section>
  );
}
