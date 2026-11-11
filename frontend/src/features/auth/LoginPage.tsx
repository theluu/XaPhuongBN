import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function LoginPage() {
  const { me, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [needOtp, setNeedOtp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (me) return <Navigate to="/" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password, otp);
    } catch (err) {
      const msg = err instanceof ApiError ? String(err.detail) : "Không kết nối được máy chủ";
      if (msg.includes("xác thực 2 lớp")) setNeedOtp(true);
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-nen">
      <div aria-hidden className="flex h-1"><div className="flex-1 bg-[var(--co-do)]" /><div className="w-24 bg-[var(--co-vang)]" /></div>
      <main className="flex flex-1 items-center justify-center px-4">
        <form onSubmit={submit} className="khu w-full max-w-sm rounded-md p-7" aria-labelledby="tieu-de">
          <img src="/brand/quoc-huy.svg" alt="Quốc huy nước Cộng hòa xã hội chủ nghĩa Việt Nam" className="mx-auto h-16" />
          <h1 id="tieu-de" className="mt-3 text-center text-lg font-bold text-son">Hệ thống điều hành số xã/phường</h1>
          <p className="mb-5 text-center text-[14px] text-muc-nhat">Đăng nhập bằng tài khoản được đơn vị cấp</p>
          <label className="mb-3 block text-sm font-medium">Tên đăng nhập
            <input className="o-nhap mt-1" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
          <label className="mb-3 block text-sm font-medium">Mật khẩu
            <input className="o-nhap mt-1" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          {needOtp && (
            <label className="mb-3 block text-sm font-medium">Mã xác thực 2 lớp (6 số)
              <input className="o-nhap mt-1 tracking-widest" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={otp} onChange={(e) => setOtp(e.target.value)} />
            </label>
          )}
          {error && <p role="alert" className="mb-3 text-sm text-son">{error}</p>}
          <button type="submit" className="btn-chinh w-full justify-center" disabled={busy}>{busy ? "Đang đăng nhập…" : "Đăng nhập"}</button>
          <p className="mt-4 text-center text-[12px] text-muc-nhat">Mọi truy cập được ghi nhật ký theo quy định.</p>
        </form>
      </main>
      <footer className="px-6 py-3 text-center text-xs text-muc-nhat">Phát triển bởi Thuận Thành</footer>
    </div>
  );
}
