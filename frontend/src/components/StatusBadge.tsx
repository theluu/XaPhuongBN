import { STATUS_COLOR, STATUS_LABEL } from "@/lib/labels";
import type { Status } from "@/lib/types";

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[13px] font-medium" style={{ color: STATUS_COLOR[status] }}>
      <span aria-hidden className="h-2 w-2 rounded-full" style={{ background: STATUS_COLOR[status] }} />
      {STATUS_LABEL[status]}
    </span>
  );
}
