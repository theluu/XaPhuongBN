import { useEffect, useRef, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Link } from "react-router-dom";
import { LangSwitch, useHostWard } from "@/features/public/PublicHome";
import { L, LangProvider } from "@/features/public/i18n";

interface Grecaptcha { render: (el: HTMLElement, o: { sitekey: string; hl?: string; callback: (t: string) => void; "expired-callback": () => void }) => number; reset: (id?: number) => void }
declare global { interface Window { grecaptcha?: Grecaptcha; __iocRecaptchaReady?: () => void } }

const SCRIPT_ID = "recaptcha-script";

function loadRecaptcha(): Promise<Grecaptcha> {
  return new Promise((resolve, reject) => {
    if (window.grecaptcha?.render) return resolve(window.grecaptcha);
    window.__iocRecaptchaReady = () => (window.grecaptcha ? resolve(window.grecaptcha) : reject());
    if (!document.getElementById(SCRIPT_ID)) {
      const s = Object.assign(document.createElement("script"), {
        id: SCRIPT_ID, async: true, defer: true, src: "https://www.google.com/recaptcha/api.js?onload=__iocRecaptchaReady&render=explicit&hl=vi",
      });
      s.onerror = () => reject(new Error("recaptcha"));
      document.head.appendChild(s);
    }
  });
}

/** Ô "Tôi không phải người máy" (Google reCAPTCHA v2) — chỉ hiện khi máy chủ bật. */
function Recaptcha({ siteKey, onToken, resetKey }: { siteKey: string; onToken: (t: string | null) => void; resetKey: number }) {
  const box = useRef<HTMLDivElement>(null);
  const widget = useRef<number | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let alive = true;
    loadRecaptcha().then((g) => {
      if (!alive || !box.current || widget.current !== null) return;
      widget.current = g.render(box.current, { sitekey: siteKey, hl: "vi", callback: (t) => onToken(t), "expired-callback": () => onToken(null) });
    }).catch(() => alive && setFailed(true));
    return () => { alive = false; };
  }, [siteKey, onToken]);
  useEffect(() => {
    if (resetKey && widget.current !== null) { window.grecaptcha?.reset(widget.current); onToken(null); }
  }, [resetKey, onToken]);
  return (
    <div className="mb-3">
      <div ref={box} data-testid="recaptcha" className="min-h-[78px]" />
      {failed && <p role="alert" className="text-sm text-son">Không tải được ô xác minh chống spam. Kiểm tra kết nối Internet rồi tải lại trang.</p>}
    </div>
  );
}

export function LoginPage() {
  return <LangProvider><LoginInner /></LangProvider>;
}

function LoginInner() {
  const { me, login } = useAuth();
  const cfg = useQuery({ queryKey: ["auth-config"], queryFn: () => api<{ recaptcha_site_key: string | null }>("/api/auth/config"), staleTime: Infinity, retry: 1 });
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [needOtp, setNeedOtp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [captcha, setCaptcha] = useState<string | null>(null);
  const [resetKey, setResetKey] = useState(0);
  const siteKey = cfg.data?.recaptcha_site_key ?? null;
  const ward = useHostWard().data?.don_vi ?? null;
  const lines = ward?.ten_co_quan ?? [L("Ủy ban nhân dân xã, phường", "Commune / ward People's Committee"), L("Trung tâm điều hành thông minh", "Intelligent operations centre")];
  if (me) return <Navigate to="/" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (siteKey && !captcha) { setError(L("Vui lòng đánh dấu ô “Tôi không phải người máy”", "Please tick “I’m not a robot”")); return; }
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password, otp, captcha ?? undefined);
    } catch (err) {
      const msg = err instanceof ApiError ? String(err.detail) : L("Không kết nối được máy chủ", "Cannot reach the server");
      if (msg.includes("xác thực 2 lớp")) setNeedOtp(true);
      setError(msg);
      if (siteKey) setResetKey((k) => k + 1); // mã reCAPTCHA chỉ dùng một lần
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-nen">
      <section className="relative overflow-hidden bg-[linear-gradient(115deg,#0f2a4d_0%,#0c2242_55%,#2a1d3d_100%)] pb-28 text-white sm:pb-32">
        <div aria-hidden className="flex h-[3px]"><div className="w-[62%] bg-nhan-dien" /><div className="flex-1 bg-[var(--vang)]" /></div>
        <div className="mx-auto max-w-6xl px-5 pt-5 sm:px-8">
          <div className="flex items-center gap-3 border-b border-white/10 pb-5">
            <img src="/brand/quoc-huy.svg" alt="Quốc huy nước Cộng hòa xã hội chủ nghĩa Việt Nam" className="h-11 sm:h-12" />
            <div className="min-w-0">
              <div className="truncate text-[13px] font-extrabold uppercase tracking-wide sm:text-[15px]">{lines[0]}</div>
              <div className="truncate text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--vang)] sm:text-[12.5px]">{lines[1]}</div>
            </div>
            <div className="ml-auto flex shrink-0 items-center gap-2"><LangSwitch dark /><Link to="/" className="rounded-full px-3 py-1.5 text-[13px] font-semibold text-white/80 hover:bg-white/10">← {L("Trang công khai", "Public page")}</Link></div>
          </div>
          <p className="mt-8 text-[11.5px] font-bold uppercase tracking-[0.16em] text-white/70 sm:mt-12">{L("Nền tảng điều hành số xã, phường", "Digital governance platform for communes and wards")}</p>
          <h1 id="tieu-de-trang" className="mt-3 max-w-3xl text-[32px] font-extrabold leading-[1.08] tracking-tight sm:text-[48px] lg:text-[56px]">
            {L("Tổng quan địa bàn.", "See the whole ward.")}<br /><span className="text-[var(--vang)]">{L("Chỉ đạo kịp thời.", "Act in time.")}</span>
          </h1>
          <p className="mt-4 max-w-2xl text-[14.5px] leading-relaxed text-white/80 sm:text-[16px]">{L("Theo dõi chỉ tiêu, phản ánh, nhiệm vụ và nguồn lực của phường trên một màn hình; giao việc, nhắn tin, gửi công văn và kiểm tra kết quả ngay khi có cảnh báo.", "Track targets, citizen feedback, tasks and resources on one screen; assign work, message, send directives and check results as soon as an alert appears.")}</p>
        </div>
      </section>
      <main className="relative z-10 -mt-20 flex flex-1 justify-center px-4 pb-10 sm:-mt-24">
        <form onSubmit={submit} className="khu h-fit w-full max-w-md p-6 sm:p-8" aria-labelledby="tieu-de">
          <p className="chu-nho-hoa">{L("Truy cập hệ thống", "System access")}</p>
          <h2 id="tieu-de" className="mt-1 text-[22px] font-extrabold text-muc">{L("Đăng nhập", "Sign in")}</h2>
          <p className="mb-5 mt-1 text-[14px] text-muc-nhat">{ward ? L(`Dành cho cán bộ ${ward.ten}`, `For staff of ${ward.ten}`) : L("Dùng tài khoản do đơn vị cấp", "Use the account issued by your unit")}</p>
          <label className="mb-3.5 block text-sm font-semibold">{L("Tên đăng nhập", "Username")}
            <input className="o-nhap mt-1.5 py-2.5" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label className="mb-3.5 block text-sm font-semibold">{L("Mật khẩu", "Password")}
            <input className="o-nhap mt-1.5 py-2.5" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {needOtp && (
            <label className="mb-3.5 block text-sm font-semibold">{L("Mã xác thực 2 lớp (6 số)", "Two-factor code (6 digits)")}
              <input className="o-nhap mt-1.5 py-2.5 tracking-widest" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={otp} onChange={(e) => setOtp(e.target.value)} />
            </label>
          )}
          {siteKey && <Recaptcha siteKey={siteKey} onToken={setCaptcha} resetKey={resetKey} />}
          {error && <p role="alert" className="mb-3 rounded-lg border border-[color-mix(in_srgb,var(--son)_30%,transparent)] bg-[color-mix(in_srgb,var(--son)_7%,var(--be-mat))] px-3 py-2 text-sm text-son">{error}</p>}
          <button type="submit" className="btn-chinh w-full py-2.5 text-[15px]" disabled={busy}>{busy ? L("Đang đăng nhập…", "Signing in…") : <>{L("Đăng nhập", "Sign in")}<span aria-hidden> →</span></>}</button>
          <p className="mt-4 text-center text-[12px] text-muc-nhat">{L("Mọi truy cập được ghi nhật ký theo quy định.", "All access is logged as required by regulations.")}</p>
        </form>
      </main>
      <footer className="px-6 py-4 text-center text-xs text-muc-nhat">{L("Phát triển bởi Thuận Thành", "Developed by Thuan Thanh")}</footer>
    </div>
  );
}
