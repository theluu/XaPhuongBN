import type { ReactNode } from "react";

/** Tiêu đề trang: chữ đậm lớn, mô tả nhạt; nút thao tác xuống dòng gọn trên điện thoại. */
export function PageHeader({ title, desc, eyebrow, children }: { title: string; desc?: string; eyebrow?: string; children?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end md:mb-6">
      <div className="min-w-0 flex-1">
        {eyebrow && <p className="chu-nho-hoa mb-1">{eyebrow}</p>}
        <h1 className="text-[22px] font-extrabold leading-tight text-muc sm:text-[26px] md:text-[28px]">{title}</h1>
        {desc && <p className="mt-1.5 max-w-[80ch] text-[14px] leading-relaxed text-muc-nhat sm:text-[15px]">{desc}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}
