import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, BellRing, CalendarDays, FileStack, MessagesSquare, Network, Building2, ClipboardCheck, Database, Flag, FolderCog, Gauge, Globe, GraduationCap, HardHat, Landmark, ListChecks, LogOut, Map, MapPinned, Menu, X,
  Presentation, Settings, Target, Tv, Users, Wallet, Workflow } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { GovHeader } from "./GovHeader";
import { ChangePasswordDialog } from "@/features/auth/ChangePasswordDialog";
import { Footer } from "./Footer";
import { PeriodFilter } from "./PeriodFilter";
import { SampleBanner } from "./SampleBanner";
import { DateLine, NewsTicker } from "./NewsTicker";
import { NotificationBell } from "./NotificationBell";
import { useUnread } from "@/features/tin-nhan/MessagesPage";

interface NavItem { to: string; ten: string; icon: LucideIcon; nhom?: string | null; module?: string; needs?: "nhap" | "thi_diem" | "du_lieu" | "tin_nhan" | "cong_khai" }
const GROUPS: { ten: string; items: NavItem[] }[] = [
  { ten: "Điều hành", items: [
    { to: "/", ten: "Tổng quan điều hành", icon: Gauge },
    { to: "/phan-anh", ten: "Phản ánh hiện trường", icon: MapPinned, nhom: "tthc_pakn" },
    { to: "/canh-bao", ten: "Nhiệm vụ chỉ đạo", icon: BellRing, nhom: "canh_bao" },
    { to: "/tin-nhan", ten: "Tin nhắn", icon: MessagesSquare, needs: "tin_nhan" },
    { to: "/lich-cong-tac", ten: "Lịch công tác", icon: CalendarDays },
    { to: "/van-ban", ten: "Văn bản chỉ đạo", icon: FileStack },
    { to: "/ban-do", ten: "Bản đồ địa bàn", icon: Map },
    { to: "/bao-cao", ten: "Báo cáo", icon: BarChart3 },
    { to: "/co-cau-to-chuc", ten: "Cơ cấu tổ chức", icon: Network },
  ] },
  { ten: "Lĩnh vực", items: [
    { to: "/chi-tieu", ten: "Chỉ tiêu KT-XH & Nghị quyết", icon: Target, nhom: "ktxh", module: "ktxh" },
    { to: "/nhiem-vu", ten: "Nhiệm vụ trọng tâm", icon: ListChecks, nhom: "ktxh" },
    { to: "/kich-ban", ten: "Kịch bản điều hành", icon: Workflow },
    { to: "/dan-cu", ten: "Dân cư – an sinh", icon: Users, nhom: "dan_cu", module: "dan_cu" },
    { to: "/ngan-sach", ten: "Thu – chi ngân sách", icon: Wallet, nhom: "ngan_sach", module: "ngan_sach" },
    { to: "/dau-tu-cong", ten: "Đầu tư công", icon: Landmark, nhom: "dau_tu_cong", module: "dau_tu_cong" },
    { to: "/cong-trinh", ten: "Công trình – đô thị", icon: HardHat, nhom: "cong_trinh", module: "cong_trinh" },
    { to: "/hanh-chinh", ten: "Dịch vụ công – PAKN", icon: Building2, nhom: "tthc_pakn", module: "tthc_pakn" },
    { to: "/chat-luong-song", ten: "Giáo dục – Y tế – Môi trường", icon: GraduationCap, nhom: "gd_yt_mt", module: "gd_yt_mt" },
  ] },
  { ten: "Dữ liệu & hệ thống", items: [
    { to: "/quan-ly-du-lieu", ten: "Quản lý dữ liệu", icon: FolderCog, needs: "du_lieu" },
    { to: "/nhap-lieu", ten: "Nhập liệu & xác nhận", icon: ClipboardCheck, needs: "nhap" },
    { to: "/nguon-du-lieu", ten: "Nguồn dữ liệu", icon: Database },
    { to: "/cong-khai", ten: "Trang công khai", icon: Globe, needs: "cong_khai" },
    { to: "/thi-diem", ten: "Thí điểm & nghiệm thu", icon: Flag, needs: "thi_diem" },
    { to: "/quan-tri", ten: "Quản trị", icon: Settings, nhom: "quan_tri" },
  ] },
];

export function AppShell() {
  const { me, tenant, can, logout, exitTenant } = useAuth();
  const navigate = useNavigate();
  const unread = useUnread();
  const chuaDoc = unread.data?.tong ?? 0;
  const [menu, setMenu] = useState(false);
  const sample = useQuery({ queryKey: ["sample-flag"], queryFn: () => api<{ co_du_lieu_minh_hoa: boolean }>("/api/sample-flag") });
  if (!tenant || !me) return null;
  const canNhap = Object.values(me.quyen).some((q) => q.includes("nhap") || q.includes("duyet"));
  const platformAdmin = me.roles.includes("quan_tri_nen_tang");
  const visible = (n: NavItem) => {
    if (platformAdmin) return n.to === "/quan-tri" || n.to === "/nguon-du-lieu";
    if (n.needs === "tin_nhan") return !me.roles.includes("man_hinh_tv");
    if (n.needs === "cong_khai") return me.roles.includes("lanh_dao") || me.roles.includes("quan_tri_don_vi");
    if (n.needs === "du_lieu") return canNhap || can("doc", "quan_tri");
    if (n.needs === "thi_diem") return can("doc", "quan_tri") || can("duyet", "canh_bao");
    if (n.needs) return canNhap;
    if (n.module && tenant.modules[n.module] === "tat") return false;
    return !n.nhom || can("doc", n.nhom);
  };
  const initials = me.ho_ten.split(" ").filter(Boolean).slice(-2).map((w) => w[0]).join("").toUpperCase();
  const hbtn = "btn relative h-10 border border-white/20 bg-white/5 px-2.5 text-white hover:bg-white/15";
  const msgBtn = !platformAdmin && (
    <NavLink to="/tin-nhan" className={hbtn} aria-label={chuaDoc ? `Tin nhắn, ${chuaDoc} chưa đọc` : "Tin nhắn"}>
      <MessagesSquare size={18} aria-hidden />{chuaDoc > 0 && <span className="absolute -right-1.5 -top-1.5 min-w-[19px] rounded-full bg-[var(--son)] px-1 text-center text-[11px] font-bold leading-[19px] text-white ring-2 ring-[var(--dieu-huong)]">{chuaDoc > 99 ? "99+" : chuaDoc}</span>}</NavLink>
  );
  const navList = (onPick?: () => void) => GROUPS.map((g) => {
    const items = g.items.filter(visible);
    if (!items.length) return null;
    return (
      <div key={g.ten} className="mb-3">
        <div className="px-3 pb-1.5 pt-1 text-[10.5px] font-bold uppercase tracking-[0.12em] text-white/45">{g.ten}</div>
        <ul className="space-y-0.5">
          {items.map((n) => {
            const st = n.module ? tenant.modules[n.module] : undefined;
            return (
              <li key={n.to}>
                <NavLink to={n.to} end={n.to === "/"} onClick={onPick}
                  className={({ isActive }) => `flex items-center gap-2.5 rounded-[10px] px-3 py-2 text-[13.5px] transition ${isActive ? "bg-white font-semibold text-[#0f2a4d] shadow-[0_4px_14px_rgba(0,0,0,.18)]" : "text-white/80 hover:bg-white/10 hover:text-white"}`}>
                  <n.icon size={17} aria-hidden className="shrink-0" />
                  <span className="flex-1 leading-tight">{n.ten}</span>
                  {st === "dang_ket_noi" && <span title="Đang kết nối nguồn dữ liệu" className="h-2 w-2 rounded-full border border-current opacity-60" />}
                  {n.to === "/tin-nhan" && chuaDoc > 0 && <span className="rounded-full bg-[var(--son)] px-1.5 text-[11px] font-bold text-white">{chuaDoc}</span>}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </div>
    );
  });
  return (
    <div className="flex min-h-screen flex-col">
      {me.dai_dien && (
        <div role="status" className="flex flex-wrap items-center gap-x-3 gap-y-1 bg-[var(--tam-thoi)] px-4 py-1.5 text-[13px] text-white">
          <span className="flex-1">Bạn đang quản trị nội dung <b>{tenant.ten}</b> bằng tài khoản quản trị nền tảng ({me.username}). Có đủ quyền xem, nhập, xác nhận, quản trị; mọi thao tác được ghi nhật ký của đơn vị.</span>
          <button type="button" className="rounded-full border border-white/60 px-3 py-0.5 font-semibold hover:bg-white/15" onClick={() => { exitTenant(); navigate("/quan-tri"); }}>Về quản trị nền tảng</button>
        </div>
      )}
      <SampleBanner show={!!sample.data?.co_du_lieu_minh_hoa} />
      <GovHeader tenant={tenant} lead={
        <button type="button" className={`${hbtn} lg:hidden`} aria-label="Mở menu" aria-expanded={menu} onClick={() => setMenu(true)}><Menu size={19} aria-hidden /></button>}>
        <div className="flex items-center gap-2">
          <span className="hidden xl:inline"><DateLine /></span>
          <span className="hidden lg:inline"><PeriodFilter onDark /></span>
          {!platformAdmin && <NotificationBell />}
          {msgBtn}
          <NavLink to="/man-hinh-tv" className={`${hbtn} hidden lg:inline-flex`} title="Màn hình TV"><Tv size={17} aria-hidden /><span className="hidden 2xl:inline">Màn hình TV</span></NavLink>
          <NavLink to="/trinh-chieu" className={`${hbtn} hidden lg:inline-flex`} title="Giao ban"><Presentation size={17} aria-hidden /><span className="hidden 2xl:inline">Giao ban</span></NavLink>
          <div className="ml-1 hidden items-center gap-2.5 rounded-full border border-white/15 bg-white/5 py-1 pl-1 pr-3 lg:flex">
            <span aria-hidden className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--vang)] text-[12px] font-extrabold text-[#0f2a4d]">{initials}</span>
            <span className="max-w-[170px] text-[12.5px] leading-tight"><span className="block truncate font-semibold">{me.ho_ten}</span><span className="block truncate text-white/65">{me.chuc_danh}</span></span>
          </div>
          <button type="button" onClick={logout} className={`${hbtn} hidden lg:inline-flex`} aria-label="Đăng xuất" title="Đăng xuất"><LogOut size={17} aria-hidden /></button>
        </div>
      </GovHeader>
      {!platformAdmin && <NewsTicker />}
      <div className="flex flex-1">
        <nav aria-label="Phân hệ" className="sticky top-0 hidden h-screen w-[244px] shrink-0 overflow-y-auto bg-[linear-gradient(180deg,#0f2a4d_0%,#0b2140_100%)] px-2.5 py-4 text-white lg:block">
          {navList()}
        </nav>
        <main className="min-w-0 flex-1 px-3 py-4 sm:px-4 md:px-6 md:py-6">
          <div className="mx-auto w-full max-w-[1680px]"><Outlet /></div>
        </main>
      </div>
      <Footer />
      <ChangePasswordDialog />
      <Dialog.Root open={menu} onOpenChange={setMenu}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-[rgba(8,20,40,.55)] backdrop-blur-[2px] lg:hidden" />
          <Dialog.Content aria-describedby={undefined} className="menu-truot fixed inset-y-0 left-0 z-50 flex w-[86vw] max-w-[330px] flex-col bg-[linear-gradient(180deg,#0f2a4d_0%,#0b2140_100%)] text-white shadow-2xl lg:hidden">
            <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
              <span aria-hidden className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--vang)] text-[13px] font-extrabold text-[#0f2a4d]">{initials}</span>
              <div className="min-w-0 flex-1"><Dialog.Title className="truncate text-[14px] font-bold">{me.ho_ten}</Dialog.Title><p className="truncate text-[12px] text-white/65">{me.chuc_danh}</p></div>
              <Dialog.Close className="rounded-lg p-2 hover:bg-white/10" aria-label="Đóng menu"><X size={19} /></Dialog.Close>
            </div>
            <div className="space-y-3 border-b border-white/10 px-4 py-3">
              <PeriodFilter onDark />
              <div className="grid grid-cols-2 gap-2">
                <NavLink to="/man-hinh-tv" onClick={() => setMenu(false)} className={`${hbtn} w-full`}><Tv size={16} aria-hidden />Màn hình TV</NavLink>
                <NavLink to="/trinh-chieu" onClick={() => setMenu(false)} className={`${hbtn} w-full`}><Presentation size={16} aria-hidden />Giao ban</NavLink>
              </div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto px-2.5 py-3">{navList(() => setMenu(false))}</div>
            <button type="button" onClick={logout} className="m-3 flex items-center justify-center gap-2 rounded-[10px] border border-white/20 py-2.5 text-[14px] font-semibold hover:bg-white/10"><LogOut size={17} aria-hidden />Đăng xuất</button>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
