import * as Tooltip from "@radix-ui/react-tooltip";
import { Check, Clock, GitCompareArrows } from "lucide-react";
import { formatDate, formatNumber, formatPeriod } from "@/lib/format";
import type { IndicatorCard } from "@/lib/types";

type Kind = "da_xac_nhan" | "tam_thoi" | "chua_co" | "lech_nguon";

function kindOf(c: IndicatorCard): Kind {
  if (c.thuc_hien === null || c.data_state === "chua_co_qua_han") return "chua_co";
  if (c.lech_nguon) return "lech_nguon";
  return c.data_state === "tam_thoi" ? "tam_thoi" : "da_xac_nhan";
}

const LABEL: Record<Kind, (c: IndicatorCard) => string> = {
  da_xac_nhan: (c) => `Đã xác nhận${c.nguoi_xac_nhan ? ` bởi ${c.nguoi_xac_nhan}` : ""}`,
  tam_thoi: () => "Tạm thời – chờ xác nhận",
  chua_co: () => "Chưa có số liệu hoặc quá hạn cập nhật",
  lech_nguon: () => "Số liệu giữa các nguồn chưa thống nhất",
};

/** "Con dấu xác nhận": cho biết số liệu đáng tin đến đâu và lấy từ đâu. */
export function ProvenanceStamp({ card, size = 30 }: { card: IndicatorCard; size?: number }) {
  const kind = kindOf(card);
  const label = LABEL[kind](card);
  const ring: Record<Kind, string> = {
    da_xac_nhan: "bg-[var(--xac-nhan)] text-white border-2 border-[var(--xac-nhan)]",
    tam_thoi: "border-2 border-dashed border-[var(--tam-thoi)] text-[var(--tam-thoi)]",
    lech_nguon: "border-[3px] border-double border-[var(--tam-thoi)] text-[var(--tam-thoi)]",
    chua_co: "border border-dotted border-[var(--thieu)] text-[var(--thieu)]",
  };
  const Icon = kind === "da_xac_nhan" ? Check : kind === "lech_nguon" ? GitCompareArrows : kind === "tam_thoi" ? Clock : null;
  return (
    <Tooltip.Provider delayDuration={150}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <button
            type="button"
            data-testid="stamp"
            data-kind={kind}
            aria-label={label}
            className={`dong-dau inline-flex shrink-0 items-center justify-center rounded-full ${ring[kind]}`}
            style={{ width: size, height: size }}
          >
            {Icon && <Icon aria-hidden size={size * 0.5} strokeWidth={2.5} />}
          </button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content side="bottom" align="end" sideOffset={6}
            className="z-50 max-w-xs rounded-md border border-vien bg-be-mat p-3 text-[13px] leading-relaxed text-muc shadow-lg">
            <div className="mb-1 font-semibold">{label}</div>
            <dl className="grid grid-cols-[auto_1fr] gap-x-3">
              <dt className="text-muc-nhat">Kỳ số liệu</dt><dd>{formatPeriod(card.ky)}</dd>
              <dt className="text-muc-nhat">Nguồn</dt><dd>{card.nguon}</dd>
              <dt className="text-muc-nhat">Đơn vị cung cấp</dt><dd>{card.don_vi_cung_cap}</dd>
              <dt className="text-muc-nhat">Thời điểm chốt</dt><dd>{formatDate(card.thoi_diem_chot)}</dd>
              <dt className="text-muc-nhat">Đồng bộ lúc</dt><dd>{formatDate(card.thoi_diem_dong_bo)}</dd>
              {card.lech_nguon && (<>
                <dt className="text-muc-nhat">Số phường</dt><dd>{formatNumber(card.lech_nguon.phuong)}</dd>
                <dt className="text-muc-nhat">Số chuyên ngành</dt><dd>{formatNumber(card.lech_nguon.chuyen_nganh)}</dd>
              </>)}
            </dl>
            {kind === "chua_co" && <p className="mt-2 text-muc-nhat">Đây là cảnh báo chất lượng dữ liệu, chưa kết luận chỉ tiêu không đạt.</p>}
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
