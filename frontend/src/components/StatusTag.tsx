import { AlertTriangle, CheckCircle2, Clock, Siren } from "lucide-react";
import { formatDate } from "@/lib/format";

/** Nhãn trạng thái/hạn: luôn có chữ đi cùng màu (§1). */
export function DeadlineTag({ han, quaHan, trangThai }: { han: string | null; quaHan: number | null; trangThai?: string }) {
  if (trangThai === "hoan_thanh") return <span className="nhan-tt tt-xong"><CheckCircle2 size={12} aria-hidden />Đã xử lý</span>;
  if (quaHan) return <span className="nhan-tt tt-qua-han"><AlertTriangle size={12} aria-hidden />Quá hạn {quaHan} ngày</span>;
  if (!han) return <span className="nhan-tt tt-cu">Chưa đặt hạn</span>;
  const days = Math.round((new Date(han).getTime() - new Date(new Date().toISOString().slice(0, 10)).getTime()) / 86_400_000);
  if (days <= 0) return <span className="nhan-tt tt-sap-han"><Clock size={12} aria-hidden />Đến hạn hôm nay</span>;
  if (days <= 2) return <span className="nhan-tt tt-sap-han"><Clock size={12} aria-hidden />Còn {days} ngày · {formatDate(han)}</span>;
  return <span className="nhan-tt tt-thuong">Hạn {formatDate(han)}</span>;
}

export function UrgentTag() {
  return <span className="nhan-tt tt-khan"><Siren size={12} aria-hidden />Khẩn cấp</span>;
}

export function NoLocationTag() {
  return <span className="nhan-tt tt-cu">Chưa có vị trí trên bản đồ</span>;
}
