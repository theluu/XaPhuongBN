import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";
import { AuthImage } from "@/components/AuthImage";
import { PageHeader } from "@/components/PageHeader";
import { DualBar, type Prog, type WorkRow } from "./ConstructionPage";

export function WorkDetail() {
  const { ma = "" } = useParams();
  const q = useQuery({ queryKey: ["work", ma], queryFn: () => api<WorkRow & { tien_do: Prog[]; ngay_kc: string | null; dia_diem: string }>(`/api/works/${encodeURIComponent(ma)}`) });
  const d = q.data;
  if (q.isError) return <p className="text-son">Không tìm thấy công trình {ma}.</p>;
  if (!d) return <p className="text-muc-nhat">Đang tải…</p>;
  const last = d.tien_do[d.tien_do.length - 1];
  return (
    <>
      <Link to="/cong-trinh" className="text-[14px] text-muc-nhat hover:underline">Công trình – đô thị</Link>
      <PageHeader title={d.ten} desc={`${d.ma}. Đơn vị thực hiện: ${d.don_vi_thuc_hien}. Khởi công ${formatDate(d.ngay_kc)}, hoàn thành theo kế hoạch ${formatDate(d.ngay_ht)}.`}>
        {d.camera_url && <a className="btn-phu" href={d.camera_url} target="_blank" rel="noreferrer noopener">Xem camera hiện trường</a>}
      </PageHeader>
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <section className="khu rounded-md p-4">
          <h2 className="mb-2 font-semibold">Tiến độ theo tuần</h2>
          <ol className="space-y-3">
            {[...d.tien_do].reverse().map((p) => (
              <li key={p.id} className="text-[14px]">
                <div className="mb-1 flex justify-between"><span className="font-medium">{formatDate(p.ngay)}</span>
                  <span className="text-muc-nhat">KH {formatNumber(p.ke_hoach_pct)}%, TT {formatNumber(p.thuc_te_pct)}%{p.trang_thai_xac_nhan === "tam_thoi" ? " (tạm thời)" : ""}</span></div>
                <DualBar kh={p.ke_hoach_pct} tt={p.thuc_te_pct} />
                {p.gpmb && <p className="mt-1 text-[13px]">GPMB: {p.gpmb}</p>}
                {p.vuong_mac && <p className={`text-[13px] ${p.can_quyet_dinh ? "font-medium text-son" : ""}`}>Vướng mắc: {p.vuong_mac}</p>}
              </li>
            ))}
          </ol>
        </section>
        <section className="khu rounded-md p-4">
          <h2 className="mb-2 font-semibold">Ảnh hiện trường gần nhất</h2>
          {last && last.anh_keys.length ? (
            <div className="grid grid-cols-2 gap-2">{last.anh_keys.map((k) => <AuthImage key={k} fileKey={k} alt={`Ảnh hiện trường ${formatDate(last.ngay)}`} className="aspect-video w-full rounded object-cover" />)}</div>
          ) : <p className="is-missing rounded p-4 text-[14px] text-muc-nhat">Báo cáo gần nhất chưa có ảnh hiện trường.</p>}
          <dl className="mt-3 grid grid-cols-[9rem_1fr] gap-y-1 text-[14px]">
            <dt className="nhan">Chất lượng</dt><dd>{d.chat_luong === "dat" ? "Đạt" : d.chat_luong === "can_khac_phuc" ? "Cần khắc phục" : "Chưa đánh giá"}</dd>
            <dt className="nhan">Địa điểm</dt><dd>{d.dia_diem}</dd>
          </dl>
        </section>
      </div>
    </>
  );
}
