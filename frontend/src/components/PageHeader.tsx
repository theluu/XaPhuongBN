import type { ReactNode } from "react";

export function PageHeader({ title, desc, children }: { title: string; desc?: string; children?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end gap-3">
      <div className="min-w-0 flex-1">
        <h1 className="text-[26px] font-bold leading-tight">{title}</h1>
        {desc && <p className="mt-1 max-w-[75ch] text-[15px] text-muc-nhat">{desc}</p>}
      </div>
      {children}
    </div>
  );
}
