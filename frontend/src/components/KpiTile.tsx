import { Link } from "react-router-dom";
import { formatNumber, formatPeriod } from "@/lib/format";
import { STATUS_COLOR } from "@/lib/labels";
import type { IndicatorCard } from "@/lib/types";
import { ProvenanceStamp } from "./ProvenanceStamp";
import { StatusBadge } from "./StatusBadge";

function targetText(c: IndicatorCard): string | null {
  if (c.chieu === "theo_doi") return null;
  if (c.ke_hoach === null && c.muc_tieu_khoang) return `Mục tiêu ${formatNumber(c.muc_tieu_khoang[0])}–${formatNumber(c.muc_tieu_khoang[1])}`;
  if (c.muc_so_sanh !== null) {
    const op = c.chieu === "giam_tot" ? "≤" : c.nguong_toan_tu === ">" ? ">" : "≥";
    return `${c.ke_hoach !== null ? "Kế hoạch" : "Mục tiêu"} ${op} ${formatNumber(c.muc_so_sanh)}`;
  }
  if (c.muc_tieu_2030 !== null) return `Mục tiêu 2030: ${formatNumber(c.muc_tieu_2030)} (chưa có kế hoạch năm)`;
  return null;
}

export function KpiTile({ card, size = "md", onOpen }: { card: IndicatorCard; size?: "md" | "xl"; onOpen?: () => void }) {
  const missing = card.thuc_hien === null;
  const target = targetText(card);
  const xl = size === "xl";
  return (
    <article
      className="khu relative flex min-h-[148px] flex-col rounded-md border-l-[3px] p-3.5"
      style={{ borderLeftColor: STATUS_COLOR[card.status] }}
    >
      <div className="flex items-start gap-2">
        <h3 className={`flex-1 font-semibold leading-snug ${xl ? "text-lg" : "text-[15px]"}`}>
          {onOpen ? (
            <button type="button" onClick={onOpen} className="text-left hover:underline">{card.ten}</button>
          ) : card.link ? (
            <Link to={card.link} className="hover:underline">{card.ten}</Link>
          ) : card.ten}
        </h3>
        <ProvenanceStamp card={card} size={xl ? 40 : 30} />
      </div>
      <div className={`mt-2 flex items-baseline gap-1.5 rounded ${missing ? "is-missing px-2 py-1" : ""}`}>
        <span data-testid="kpi-value" className={`font-so font-semibold tabular leading-none ${xl ? "text-6xl" : "text-[40px]"} ${missing ? "text-thieu" : ""}`}>
          {formatNumber(card.thuc_hien)}
        </span>
        <span className="text-sm text-muc-nhat">{card.don_vi}</span>
      </div>
      {target && <div className="mt-1 text-[13px] text-muc-nhat">{target}</div>}
      {card.ghi_chu && <div className="mt-0.5 text-[13px] text-muc-nhat">{card.ghi_chu}</div>}
      <div className="mt-auto flex items-center justify-between gap-2 pt-2">
        <span className="text-[13px] text-muc-nhat">{formatPeriod(card.ky)}</span>
        <StatusBadge status={card.status} />
      </div>
      {card.co_so_moi_cho_xac_nhan && (
        <div className="mt-1 text-[12px] text-[var(--tam-thoi)]">Có số mới chờ xác nhận</div>
      )}
    </article>
  );
}
