import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, Bell, CheckCheck, CheckCircle2, ClipboardCheck, ClipboardList, Megaphone, MessageSquare, Stamp, X, XCircle } from "lucide-react";
import { api } from "@/lib/api";

export interface NotiItem { id: number; loai: string; tieu_de: string; noi_dung: string; lien_ket: string | null; muc_do: string; tao_luc: string; da_doc: boolean }

const KIEU: Record<string, { icon: LucideIcon; mau: string; ten: string }> = {
  giao_viec: { icon: ClipboardList, mau: "#1d4ed8", ten: "Giao việc" },
  ket_qua: { icon: CheckCircle2, mau: "#15803d", ten: "Kết quả" },
  cho_xac_nhan: { icon: ClipboardCheck, mau: "#a16207", ten: "Chờ xác nhận" },
  tu_choi: { icon: XCircle, mau: "#b91c1c", ten: "Bị từ chối" },
  tin_nhan: { icon: MessageSquare, mau: "#4f46e5", ten: "Tin nhắn" },
  cong_van: { icon: Stamp, mau: "#9f2026", ten: "Công văn" },
  canh_bao: { icon: AlertTriangle, mau: "#c2410c", ten: "Cảnh báo" },
  thong_bao: { icon: Megaphone, mau: "#123254", ten: "Thông báo" },
};

export function ago(s: string): string {
  const d = new Date(s);
  const m = Math.round((Date.now() - d.getTime()) / 60000);
  if (m < 1) return "vừa xong";
  if (m < 60) return `${m} phút trước`;
  const h = Math.round(m / 60);
  if (h < 24 && new Date().toDateString() === d.toDateString()) return `${h} giờ trước`;
  const y = new Date(); y.setDate(y.getDate() - 1);
  if (y.toDateString() === d.toDateString()) return `hôm qua, ${d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`;
  return d.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function NotiIcon({ loai, size = 38 }: { loai: string; size?: number }) {
  const k = KIEU[loai] ?? KIEU.thong_bao;
  return (
    <span aria-hidden className="flex shrink-0 items-center justify-center rounded-full" style={{ width: size, height: size, background: `color-mix(in srgb, ${k.mau} 13%, transparent)`, color: k.mau }}>
      <k.icon size={Math.round(size * 0.5)} strokeWidth={2.2} />
    </span>
  );
}

function Row({ n, onOpen }: { n: NotiItem; onOpen: (n: NotiItem) => void }) {
  const k = KIEU[n.loai] ?? KIEU.thong_bao;
  return (
    <li>
      <button type="button" onClick={() => onOpen(n)} aria-label={`${n.da_doc ? "" : "Chưa đọc. "}${k.ten}: ${n.tieu_de}`}
        className={`group flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-[color-mix(in_srgb,var(--chinh)_6%,var(--be-mat))] ${n.da_doc ? "" : "bg-[color-mix(in_srgb,var(--chinh)_5%,var(--be-mat))]"}`}>
        <NotiIcon loai={n.loai} />
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5 text-[11.5px] font-semibold uppercase tracking-wide" style={{ color: k.mau }}>{k.ten}
            {n.muc_do === "khan" && <span className="rounded bg-[var(--son)] px-1.5 py-px text-[10.5px] font-bold text-white">KHẨN</span>}
            {n.muc_do === "quan_trong" && <span className="rounded bg-[color-mix(in_srgb,var(--tam-thoi)_18%,transparent)] px-1.5 py-px text-[10.5px] font-bold text-[var(--tam-thoi)]">QUAN TRỌNG</span>}</span>
          <span className={`mt-0.5 block text-[14px] leading-snug ${n.da_doc ? "text-muc" : "font-semibold text-muc"}`}>{n.tieu_de}</span>
          {n.noi_dung && <span className="mt-0.5 line-clamp-2 block text-[13px] leading-snug text-muc-nhat">{n.noi_dung}</span>}
          <span className="mt-1 block text-[12px] text-muc-nhat">{ago(n.tao_luc)}</span>
        </span>
        {!n.da_doc && <span aria-hidden className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-[var(--chinh)]" />}
      </button>
    </li>
  );
}

/** Chuông thông báo trên đầu trang: số chưa đọc, bảng thông báo, hộp nổi khi có việc mới. */
export function NotificationBell() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [toast, setToast] = useState<NotiItem | null>(null);
  const [ring, setRing] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const prev = useRef<number | null>(null);
  const count = useQuery({ queryKey: ["noti-dem"], queryFn: () => api<{ chua_doc: number; moi_nhat: NotiItem | null }>("/api/noti/dem"), refetchInterval: 20_000 });
  const list = useQuery({ queryKey: ["noti-list", unreadOnly], queryFn: () => api<{ chua_doc: number; muc: NotiItem[] }>("/api/noti", { params: { chi_chua_doc: unreadOnly ? "true" : undefined } }), enabled: open });
  const n = count.data?.chua_doc ?? 0;
  // Có thông báo mới (số chưa đọc tăng) → rung chuông + hộp nổi
  useEffect(() => {
    if (count.data === undefined) return;
    if (prev.current !== null && n > prev.current && count.data.moi_nhat && !open) {
      setToast(count.data.moi_nhat); setRing(true);
      setTimeout(() => setRing(false), 1200);
    }
    prev.current = n;
  }, [count.data]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 7000); return () => clearTimeout(t); }, [toast]);
  useEffect(() => {
    if (!open) return;
    const click = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", click); document.addEventListener("keydown", key);
    return () => { document.removeEventListener("mousedown", click); document.removeEventListener("keydown", key); };
  }, [open]);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["noti-dem"] }); qc.invalidateQueries({ queryKey: ["noti-list"] }); };
  const readAll = useMutation({ mutationFn: () => api("/api/noti/doc-het", { method: "POST" }), onSuccess: refresh });
  async function openItem(x: NotiItem) {
    setOpen(false); setToast(null);
    if (!x.da_doc) { try { await api(`/api/noti/${x.id}/doc`, { method: "POST" }); } catch { /* bỏ qua */ } refresh(); }
    if (x.lien_ket) navigate(x.lien_ket);
  }
  const items = list.data?.muc ?? [];
  const today = new Date().toDateString();
  const groups = [["Hôm nay", items.filter((x) => new Date(x.tao_luc).toDateString() === today)], ["Trước đó", items.filter((x) => new Date(x.tao_luc).toDateString() !== today)]] as const;
  return (
    <div ref={box} className="relative">
      <button type="button" onClick={() => setOpen(!open)} aria-haspopup="dialog" aria-expanded={open}
        aria-label={n ? `Thông báo, ${n} chưa đọc` : "Thông báo"}
        className={`btn relative border border-white/25 px-2.5 text-white hover:bg-white/10 ${open ? "bg-white/15" : ""}`}>
        <Bell size={18} aria-hidden className={ring ? "chuong-rung" : ""} />
        {n > 0 && <span className="absolute -right-1.5 -top-1.5 min-w-[19px] rounded-full bg-[var(--son)] px-1 text-center text-[11px] font-bold leading-[19px] text-white shadow ring-2 ring-[var(--dieu-huong)]">{n > 99 ? "99+" : n}</span>}
      </button>
      {open && (
        <div role="dialog" aria-label="Thông báo" className="absolute right-0 top-[calc(100%+10px)] z-[60] w-[420px] max-w-[calc(100vw-24px)] overflow-hidden rounded-xl border border-vien bg-be-mat text-muc shadow-2xl">
          <div className="flex items-center gap-2 border-b border-vien px-4 py-3">
            <h2 className="flex-1 text-[16px] font-bold">Thông báo {n > 0 && <span className="ml-1 rounded-full bg-[var(--son)] px-2 py-0.5 text-[12px] font-bold text-white">{n} mới</span>}</h2>
            <button type="button" className="inline-flex items-center gap-1 rounded px-2 py-1 text-[12.5px] font-medium text-[var(--chinh)] hover:bg-be-mat-2 disabled:opacity-40"
              disabled={!n || readAll.isPending} onClick={() => readAll.mutate()}><CheckCheck size={15} aria-hidden />Đánh dấu đã đọc tất cả</button>
          </div>
          <div role="tablist" aria-label="Lọc thông báo" className="flex gap-1 border-b border-vien px-3 py-2">
            {([[false, "Tất cả"], [true, "Chưa đọc"]] as const).map(([v, t]) => (
              <button key={t} type="button" role="tab" aria-selected={unreadOnly === v} onClick={() => setUnreadOnly(v)}
                className={`rounded-full px-3 py-1 text-[13px] font-medium ${unreadOnly === v ? "bg-[var(--chinh)] text-white" : "text-muc-nhat hover:bg-be-mat-2"}`}>{t}</button>
            ))}
          </div>
          <div className="max-h-[min(62vh,560px)] overflow-y-auto">
            {list.isLoading && <p className="px-4 py-8 text-center text-[13.5px] text-muc-nhat">Đang tải…</p>}
            {list.data && items.length === 0 && (
              <div className="flex flex-col items-center gap-2 px-4 py-10 text-center text-muc-nhat">
                <span className="flex h-14 w-14 items-center justify-center rounded-full bg-be-mat-2"><Bell size={26} aria-hidden /></span>
                <p className="text-[14px] font-medium text-muc">{unreadOnly ? "Bạn đã đọc hết thông báo" : "Chưa có thông báo"}</p>
                <p className="text-[13px]">Việc được giao, số liệu chờ xác nhận, tin nhắn và công văn mới sẽ hiện ở đây.</p>
              </div>
            )}
            {groups.map(([ten, xs]) => xs.length > 0 && (
              <section key={ten} aria-label={ten}>
                <h3 className="sticky top-0 z-10 bg-be-mat px-4 pb-1 pt-3 text-[11.5px] font-semibold uppercase tracking-wider text-muc-nhat">{ten}</h3>
                <ul className="divide-y divide-[var(--vien)]">{xs.map((x) => <Row key={x.id} n={x} onOpen={openItem} />)}</ul>
              </section>
            ))}
          </div>
        </div>
      )}
      {toast && (
        <div role="status" aria-live="polite" className="toast-vao fixed right-4 top-20 z-[70] w-[380px] max-w-[calc(100vw-32px)] overflow-hidden rounded-xl border border-vien bg-be-mat text-muc shadow-2xl">
          <div className="h-1" style={{ background: (KIEU[toast.loai] ?? KIEU.thong_bao).mau }} />
          <div className="flex items-start gap-3 p-3.5">
            <NotiIcon loai={toast.loai} size={40} />
            <button type="button" className="min-w-0 flex-1 text-left" onClick={() => openItem(toast)}>
              <span className="block text-[12px] font-semibold uppercase tracking-wide" style={{ color: (KIEU[toast.loai] ?? KIEU.thong_bao).mau }}>
                {(KIEU[toast.loai] ?? KIEU.thong_bao).ten}{toast.muc_do === "khan" && " · KHẨN"}</span>
              <span className="mt-0.5 block text-[14px] font-semibold leading-snug">{toast.tieu_de}</span>
              {toast.noi_dung && <span className="mt-0.5 line-clamp-2 block text-[13px] text-muc-nhat">{toast.noi_dung}</span>}
              <span className="mt-1 block text-[12.5px] font-medium text-[var(--chinh)]">Xem ngay →</span>
            </button>
            <button type="button" aria-label="Đóng thông báo nổi" className="rounded p-1 text-muc-nhat hover:bg-be-mat-2" onClick={() => setToast(null)}><X size={16} /></button>
          </div>
        </div>
      )}
    </div>
  );
}
