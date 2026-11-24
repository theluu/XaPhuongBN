import type { ReactNode } from "react";
import type { TenantInfo } from "@/lib/types";

/** Đầu trang: dải màu navy, vạch nhận diện đỏ – vàng phía trên, tên cơ quan / tên hệ thống. `lead` = nút mở menu (điện thoại). */
export function GovHeader({ tenant, children, large = false, lead }: { tenant: TenantInfo; children?: ReactNode; large?: boolean; lead?: ReactNode }) {
  const logo = tenant.logo_url ?? "/brand/quoc-huy.svg";
  const alt = tenant.logo_url ? `Biểu trưng ${tenant.ten}` : "Quốc huy nước Cộng hòa xã hội chủ nghĩa Việt Nam";
  const [line1, line2] = tenant.ten_co_quan;
  return (
    <header className="relative z-30 bg-[linear-gradient(115deg,#0f2a4d_0%,#0c2242_55%,#1f1d3d_100%)] text-white shadow-[0_2px_12px_rgba(8,20,40,.25)]">
      <div aria-hidden className="flex h-[3px]"><div className="w-[62%] bg-nhan-dien" /><div className="flex-1 bg-[var(--vang)]" /></div>
      <div className="flex items-center gap-2.5 px-3 py-2 sm:gap-3 md:px-5">
        {lead}
        <img src={logo} alt={alt} className={large ? "h-16 w-auto" : "h-9 w-auto sm:h-11"} />
        <div className="min-w-0 flex-1">
          <div className={`truncate font-extrabold uppercase leading-tight tracking-wide ${large ? "text-2xl" : "text-[12.5px] sm:text-[14px] md:text-[15px]"}`}>{line1}</div>
          {line2 && <div className={`truncate font-bold uppercase leading-tight tracking-[0.06em] text-[var(--vang)] ${large ? "text-lg" : "text-[10.5px] sm:text-[12px] md:text-[12.5px]"}`}>{line2}</div>}
        </div>
        {children}
      </div>
    </header>
  );
}
