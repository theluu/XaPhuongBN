import type { ReactNode } from "react";
import type { TenantInfo } from "@/lib/types";

/** Đầu trang theo mẫu cổng thông tin cơ quan nhà nước. */
export function GovHeader({ tenant, children, large = false }: { tenant: TenantInfo; children?: ReactNode; large?: boolean }) {
  const logo = tenant.logo_url ?? "/brand/quoc-huy.svg";
  const alt = tenant.logo_url ? `Biểu trưng ${tenant.ten}` : "Quốc huy nước Cộng hòa xã hội chủ nghĩa Việt Nam";
  const [line1, line2] = tenant.ten_co_quan;
  return (
    <header className="bg-be-mat">
      <div className="flex items-center gap-3 px-4 py-2.5 md:px-6">
        <img src={logo} alt={alt} className={large ? "h-[72px] w-auto" : "h-12 w-auto"} />
        <div className="min-w-0 flex-1">
          <div className={`font-bold leading-tight text-son ${large ? "text-2xl" : "text-[15px] md:text-base"}`}>{line1}</div>
          {line2 && <div className={`leading-tight text-muc ${large ? "text-lg" : "text-[13px] md:text-sm"}`}>{line2}</div>}
        </div>
        {children}
      </div>
      <div aria-hidden className="flex h-1">
        <div className="flex-1 bg-[var(--co-do)]" />
        <div className="w-24 bg-[var(--co-vang)]" />
      </div>
    </header>
  );
}
