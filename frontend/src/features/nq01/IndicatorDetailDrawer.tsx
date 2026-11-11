import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate, formatNumber, formatPeriod } from "@/lib/format";
import { DATA_STATE_LABEL } from "@/lib/labels";
import type { IndicatorCard } from "@/lib/types";
import { ProvenanceStamp } from "@/components/ProvenanceStamp";
import { StatusBadge } from "@/components/StatusBadge";
import { SeriesChart, type SeriesPoint } from "@/components/SeriesChart";

interface Detail extends IndicatorCard {
  metadata: { dinh_nghia: string; cong_thuc: string; pham_vi_dia_ban: string; don_vi_chu_quan: string; ky_cap_nhat: string; nguon_mac_dinh: string; ghi_chu: string; can_minh_chung: boolean };
  lich_su: { id: number; version: number; nguon_loai: string; gia_tri: number | null; trang_thai: string; nguoi_xac_nhan: string | null; ly_do: string }[];
}

const NGUON: Record<string, string> = { phuong: "Phường", chuyen_nganh: "Chuyên ngành", api: "API" };
const TT: Record<string, string> = { da_xac_nhan: "Đã xác nhận", tam_thoi: "Tạm thời", tu_choi: "Bị từ chối" };

function back(ky: string, n: number): string {
  const m = ky.match(/^(\d{4})-(\d{2})$/);
  if (m) { const d = new Date(Number(m[1]), Number(m[2]) - 1 - n, 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`; }
  const q = ky.match(/^(\d{4})-Q(\d)$/);
  if (q) { const idx = Number(q[1]) * 4 + Number(q[2]) - 1 - n; return `${Math.floor(idx / 4)}-Q${(idx % 4) + 1}`; }
  return /^\d{4}$/.test(ky) ? String(Number(ky) - n) : ky;
}

export function IndicatorDetailDrawer({ ma, ky, onClose }: { ma: string | null; ky: string; onClose: () => void }) {
  const { can } = useAuth();
  const q = useQuery({ queryKey: ["indicator", ma, ky], queryFn: () => api<Detail>(`/api/indicators/${ma}`, { params: { ky } }), enabled: !!ma });
  const d = q.data;
  const series = useQuery({
    queryKey: ["series", ma, d?.ky], enabled: !!d,
    queryFn: () => api<SeriesPoint[]>(`/api/indicators/${ma}/series`, { params: { tu: back(d!.ky, d!.ky.length === 4 ? 4 : d!.ky.includes("Q") ? 6 : 12), den: d!.ky } }),
  });
  return (
    <Dialog.Root open={!!ma} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[rgba(15,36,54,0.35)]" />
        <Dialog.Content aria-describedby={undefined}
          className="fixed inset-y-0 right-0 z-50 w-full max-w-[640px] overflow-y-auto bg-be-mat p-6 shadow-2xl focus:outline-none">
          <div className="flex items-start gap-3">
            <Dialog.Title className="flex-1 text-xl font-bold leading-snug">{d?.ten ?? "Đang tải…"}</Dialog.Title>
            <Dialog.Close className="btn-phu" aria-label="Đóng"><X size={16} /></Dialog.Close>
          </div>
          {d && (
            <div className="mt-4 space-y-6">
              <div className={`flex items-center gap-4 rounded-md p-3 ${d.thuc_hien === null ? "is-missing" : "bg-nen"}`}>
                <ProvenanceStamp card={d} size={44} />
                <div className="flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="font-so text-5xl font-semibold tabular">{formatNumber(d.thuc_hien)}</span>
                    <span className="text-muc-nhat">{d.don_vi}</span>
                  </div>
                  <div className="text-[13px] text-muc-nhat">{formatPeriod(d.ky)}. {DATA_STATE_LABEL[d.data_state]}</div>
                </div>
                <StatusBadge status={d.status} />
              </div>

              <section>
                <h3 className="mb-2 font-semibold">So sánh</h3>
                <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-[14px] sm:grid-cols-4">
                  <div><dt className="nhan">{d.ke_hoach !== null ? "Kế hoạch kỳ" : "Mục tiêu"}</dt><dd className="tabular font-medium">{formatNumber(d.muc_so_sanh)}</dd></div>
                  <div><dt className="nhan">Mức hoàn thành</dt><dd className="tabular font-medium">{d.hoan_thanh_pct === null ? "—" : `${formatNumber(d.hoan_thanh_pct)}%`}</dd></div>
                  <div><dt className="nhan">Kỳ trước ({formatPeriod(d.ky_truoc.ky)})</dt><dd className="tabular font-medium">{formatNumber(d.ky_truoc.gia_tri)}</dd></div>
                  <div><dt className="nhan">Cùng kỳ ({formatPeriod(d.cung_ky.ky)})</dt><dd className="tabular font-medium">{formatNumber(d.cung_ky.gia_tri)}</dd></div>
                  {d.muc_tieu_2030 !== null && <div><dt className="nhan">Mục tiêu 2030</dt><dd className="tabular font-medium">{formatNumber(d.muc_tieu_2030)}</dd></div>}
                  {d.du_bao !== null && <div><dt className="nhan">Dự báo/ước</dt><dd className="tabular font-medium">{formatNumber(d.du_bao)}</dd></div>}
                </dl>
              </section>

              {d.lech_nguon && (
                <section className="rounded-md border border-[var(--tam-thoi)] p-3">
                  <h3 className="font-semibold text-[var(--tam-thoi)]">Số liệu giữa các nguồn chưa thống nhất</h3>
                  <p className="text-[14px]">Số phường báo cáo {formatNumber(d.lech_nguon.phuong)}, nguồn chuyên ngành {formatNumber(d.lech_nguon.chuyen_nganh)} (chênh {formatNumber(d.lech_nguon.chenh)}). Hệ thống đang dùng số theo thứ tự ưu tiên nguồn của chỉ tiêu.</p>
                  <p className="mt-1 text-[13px] text-muc-nhat">Đây là cảnh báo chất lượng dữ liệu, chưa kết luận chỉ tiêu không đạt.</p>
                </section>
              )}

              <section>
                <h3 className="mb-2 font-semibold">Lý lịch số liệu</h3>
                <dl className="grid grid-cols-[10rem_1fr] gap-y-1 text-[14px]">
                  <dt className="nhan">Nguồn</dt><dd>{d.nguon}</dd>
                  <dt className="nhan">Đơn vị cung cấp</dt><dd>{d.don_vi_cung_cap}</dd>
                  <dt className="nhan">Người xác nhận</dt><dd>{d.nguoi_xac_nhan ?? "Chưa xác nhận"}</dd>
                  <dt className="nhan">Thời điểm chốt</dt><dd>{formatDate(d.thoi_diem_chot)}</dd>
                  <dt className="nhan">Đồng bộ lúc</dt><dd>{formatDate(d.thoi_diem_dong_bo)}</dd>
                </dl>
              </section>

              <section>
                <h3 className="mb-2 font-semibold">Diễn biến</h3>
                {series.data ? <SeriesChart data={series.data} unit={d.don_vi} /> : <div className="h-[220px]" />}
              </section>

              <section>
                <h3 className="mb-2 font-semibold">Định nghĩa và công thức</h3>
                <dl className="grid grid-cols-[10rem_1fr] gap-y-1 text-[14px]">
                  <dt className="nhan">Định nghĩa</dt><dd>{d.metadata.dinh_nghia}</dd>
                  <dt className="nhan">Công thức</dt><dd>{d.metadata.cong_thuc}</dd>
                  <dt className="nhan">Phạm vi</dt><dd>{d.metadata.pham_vi_dia_ban}</dd>
                  <dt className="nhan">Đơn vị chủ quản</dt><dd>{d.metadata.don_vi_chu_quan}</dd>
                  {d.metadata.ghi_chu && (<><dt className="nhan">Ghi chú</dt><dd>{d.metadata.ghi_chu}</dd></>)}
                </dl>
              </section>

              <section>
                <table aria-label="Lịch sử số liệu" className="w-full text-[14px]">
                  <caption className="mb-2 text-left font-semibold">Lịch sử số liệu kỳ {formatPeriod(d.ky)}</caption>
                  <thead><tr className="border-b border-vien text-left text-muc-nhat"><th className="py-1 font-medium">Phiên bản</th><th className="font-medium">Nguồn</th><th className="text-right font-medium">Giá trị</th><th className="pl-3 font-medium">Trạng thái</th></tr></thead>
                  <tbody>
                    {d.lich_su.length === 0 && <tr><td colSpan={4} className="py-2 text-muc-nhat">Chưa có số liệu nào được nhập cho kỳ này.</td></tr>}
                    {d.lich_su.map((h) => (
                      <tr key={h.id} className="border-b border-vien">
                        <td className="py-1.5">{h.version}</td><td>{NGUON[h.nguon_loai] ?? h.nguon_loai}</td>
                        <td className="text-right tabular">{formatNumber(h.gia_tri)}</td>
                        <td className="pl-3">{TT[h.trang_thai] ?? h.trang_thai}{h.ly_do ? `: ${h.ly_do}` : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              {can("nhap", d.nhom) && (
                <Link to={`/nhap-lieu?ma=${encodeURIComponent(d.ma)}&ky=${d.ky}`} className="btn-chinh">Nhập số liệu kỳ này</Link>
              )}
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
