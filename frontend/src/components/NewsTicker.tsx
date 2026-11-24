import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink, Megaphone, Pause, Play, Plus } from "lucide-react";
import { api } from "@/lib/api";

export interface TinItem { nguon?: string; loai: "thong_bao" | "van_hanh" | "tin_ngoai"; id?: number; tieu_de: string; noi_dung?: string; lien_ket: string | null; muc_do: string; tu_ngay?: string; ghim?: boolean }
export interface BangTin { muc: TinItem[]; lien_ket: { ten: string; url: string }[]; co_quyen_dang: boolean }

const MAU: Record<string, string> = { khan: "var(--son)", quan_trong: "var(--tam-thoi)", thuong: "var(--chinh)" };

export function useBangTin() {
  return useQuery({ queryKey: ["bang-tin"], queryFn: () => api<BangTin>("/api/bang-tin"), refetchInterval: 120_000 });
}

function Item({ x, tabbable }: { x: TinItem; tabbable: boolean }) {
  const dot = <span aria-hidden className="mr-1.5 inline-block h-2 w-2 shrink-0 rounded-full" style={{ background: MAU[x.muc_do] ?? MAU.thuong }} />;
  const label = <>{x.muc_do === "khan" && <b className="mr-1 text-son">KHẨN:</b>}{x.loai === "tin_ngoai" && x.nguon && <span className="mr-1 opacity-70">{x.nguon}:</span>}{x.tieu_de}</>;
  const cls = "inline-flex items-center hover:underline";
  const tab = tabbable ? undefined : -1;
  const body = !x.lien_ket ? <span className="inline-flex items-center">{dot}{label}</span>
    : x.lien_ket.startsWith("/") ? <Link to={x.lien_ket} className={cls} tabIndex={tab}>{dot}{label}</Link>
    : <a href={x.lien_ket} target="_blank" rel="noopener noreferrer" className={cls} tabIndex={tab}>{dot}{label}<ExternalLink size={12} aria-hidden className="ml-1" /></a>;
  return <span className="mx-5 inline-flex items-center">{body}</span>;
}

/** Dải bản tin dưới đầu trang: thông báo điều hành + tin vận hành; dừng khi rê chuột/nhấn phím, có nút tạm dừng. */
export function NewsTicker({ dark = false, large = false }: { dark?: boolean; large?: boolean }) {
  const q = useBangTin();
  const [stop, setStop] = useState(false);
  const items = q.data?.muc ?? [];
  const links = q.data?.lien_ket ?? [];
  if (!q.data || (!items.length && !links.length && !q.data.co_quyen_dang)) return null;
  const len = items.reduce((n, x) => n + x.tieu_de.length, 0);
  const sec = Math.max(25, Math.round(len / 7));
  return (
    <div className={`flex items-stretch border-b ${large ? "text-[20px]" : "text-[13.5px]"} ${dark ? "border-white/10 bg-[#0b2340] text-white" : "border-vien bg-be-mat text-muc"}`}>
      <span className="flex shrink-0 items-center gap-1.5 bg-nhan-dien px-3 text-[12px] font-bold uppercase tracking-wide text-white"><Megaphone size={14} aria-hidden />Bản tin</span>
      <section aria-label="Bản tin điều hành" className="ban-tin relative min-w-0 flex-1 overflow-hidden py-1.5" data-dung={stop ? "1" : "0"}>
        {items.length === 0 ? <span className="px-4 text-muc-nhat">Không có thông báo mới.</span> : (
          <>
            {/* bản đọc cho trình đọc màn hình và bàn phím: danh sách tĩnh */}
            <ul className="sr-only">{items.map((x, i) => <li key={i}><Item x={x} tabbable /></li>)}</ul>
            <div aria-hidden className="ban-tin-track" style={{ ["--ban-tin-thoi-gian" as string]: `${sec}s` }}>
              {[0, 1].map((k) => <span key={k} className="inline-flex">{items.map((x, i) => <Item key={`${k}-${i}`} x={x} tabbable={false} />)}</span>)}
            </div>
          </>
        )}
      </section>
      {items.length > 0 && <button type="button" onClick={() => setStop(!stop)} aria-label={stop ? "Chạy bản tin" : "Tạm dừng bản tin"} className="shrink-0 px-2 opacity-70 hover:opacity-100">
        {stop ? <Play size={14} /> : <Pause size={14} />}</button>}
      {q.data.co_quyen_dang && <Link to="/quan-ly-du-lieu?bo=thong_bao" className="hidden shrink-0 items-center gap-1 border-l border-vien px-3 text-[12.5px] hover:underline md:flex"><Plus size={13} aria-hidden />Đăng thông báo</Link>}
      {links.length > 0 && (
        <nav aria-label="Liên kết nhanh" className="hidden shrink-0 items-center gap-3 border-l border-vien px-3 text-[12.5px] xl:flex">
          {links.map((l) => l.url.startsWith("/") ? <Link key={l.url} to={l.url} className="hover:underline">{l.ten}</Link>
            : <a key={l.url} href={l.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline">{l.ten}<ExternalLink size={11} aria-hidden /></a>)}
        </nav>
      )}
    </div>
  );
}

/** Dòng ngày giờ trên đầu trang, kiểu Cổng TTĐT: "Thứ Năm, 12/11/2026 08:18". */
export function DateLine() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 30_000); return () => clearInterval(t); }, []);
  const thu = ["Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"][now.getDay()];
  const d = now.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
  const h = now.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  return <time dateTime={now.toISOString()} className="whitespace-nowrap text-[12.5px] text-white/80">{thu}, {d} {h}</time>;
}
