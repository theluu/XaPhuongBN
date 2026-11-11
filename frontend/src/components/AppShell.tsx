import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BellRing, Building2, ClipboardCheck, Database, Gauge, GraduationCap, HardHat, Landmark, LogOut, MonitorPlay, Settings, Target, Users, Wallet } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { GovHeader } from "./GovHeader";
import { Footer } from "./Footer";
import { PeriodFilter } from "./PeriodFilter";
import { SampleBanner } from "./SampleBanner";

const NAV = [
  { to: "/", ten: "Tổng quan", icon: Gauge, nhom: null },
  { to: "/chi-tieu", ten: "Chỉ tiêu KT-XH & Nghị quyết", icon: Target, nhom: "ktxh", module: "ktxh" },
  { to: "/dan-cu", ten: "Dân cư – an sinh", icon: Users, nhom: "dan_cu", module: "dan_cu" },
  { to: "/ngan-sach", ten: "Thu – chi ngân sách", icon: Wallet, nhom: "ngan_sach", module: "ngan_sach" },
  { to: "/dau-tu-cong", ten: "Đầu tư công", icon: Landmark, nhom: "dau_tu_cong", module: "dau_tu_cong" },
  { to: "/cong-trinh", ten: "Công trình – đô thị", icon: HardHat, nhom: "cong_trinh", module: "cong_trinh" },
  { to: "/hanh-chinh", ten: "Hành chính công – PAKN", icon: Building2, nhom: "tthc_pakn", module: "tthc_pakn" },
  { to: "/chat-luong-song", ten: "Giáo dục – Y tế – Môi trường", icon: GraduationCap, nhom: "gd_yt_mt", module: "gd_yt_mt" },
  { to: "/canh-bao", ten: "Cảnh báo & hồ sơ theo dõi", icon: BellRing, nhom: "canh_bao" },
  { to: "/nhap-lieu", ten: "Nhập liệu & xác nhận", icon: ClipboardCheck, nhom: null, needs: "nhap" as const },
  { to: "/nguon-du-lieu", ten: "Nguồn dữ liệu", icon: Database, nhom: null },
  { to: "/quan-tri", ten: "Quản trị", icon: Settings, nhom: "quan_tri" },
];

export function AppShell() {
  const { me, tenant, can, logout } = useAuth();
  const sample = useQuery({ queryKey: ["sample-flag"], queryFn: () => api<{ co_du_lieu_minh_hoa: boolean }>("/api/sample-flag") });
  if (!tenant || !me) return null;
  const canNhap = Object.values(me.quyen).some((q) => q.includes("nhap") || q.includes("duyet"));
  const items = NAV.filter((n) => (n.needs ? canNhap : !n.nhom || can("doc", n.nhom)));
  return (
    <div className="flex min-h-screen flex-col">
      <SampleBanner show={!!sample.data?.co_du_lieu_minh_hoa} />
      <GovHeader tenant={tenant}>
        <div className="hidden items-center gap-4 md:flex">
          <PeriodFilter />
          <NavLink to="/trinh-chieu" className="btn-phu"><MonitorPlay size={16} aria-hidden />Trình chiếu</NavLink>
          <div className="text-right text-[13px] leading-tight">
            <div className="font-semibold">{me.ho_ten}</div>
            <div className="text-muc-nhat">{me.chuc_danh}</div>
          </div>
          <button type="button" onClick={logout} className="btn-phu" aria-label="Đăng xuất"><LogOut size={16} aria-hidden /></button>
        </div>
      </GovHeader>
      <div className="flex flex-1">
        <nav aria-label="Phân hệ" className="hidden w-64 shrink-0 border-r border-vien bg-be-mat py-3 lg:block">
          <ul>
            {items.map((n) => {
              const st = n.module ? tenant.modules[n.module] : undefined;
              return (
                <li key={n.to}>
                  <NavLink to={n.to} end={n.to === "/"}
                    className={({ isActive }) => `flex items-center gap-3 px-5 py-2.5 text-[14.5px] ${isActive ? "bg-nen font-semibold text-muc shadow-[inset_3px_0_0_var(--muc)]" : "text-muc-nhat hover:bg-be-mat-2 hover:text-muc"}`}>
                    <n.icon size={18} aria-hidden />
                    <span className="flex-1">{n.ten}</span>
                    {st === "dang_ket_noi" && <span title="Đang kết nối nguồn dữ liệu" className="h-2 w-2 rounded-full border border-thieu" />}
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </nav>
        <main className="min-w-0 flex-1 px-4 py-5 md:px-6">
          <Outlet />
        </main>
      </div>
      <Footer />
    </div>
  );
}
