import * as Dialog from "@radix-ui/react-dialog";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Bắt buộc đổi mật khẩu tạm ở lần đăng nhập đầu. */
export function ChangePasswordDialog() {
  const { me, logout } = useAuth();
  const [cu, setCu] = useState("");
  const [moi, setMoi] = useState("");
  const [lai, setLai] = useState("");
  const [err, setErr] = useState<string | null>(null);
  if (!me?.phai_doi_mat_khau) return null;
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (moi !== lai) return setErr("Mật khẩu nhập lại không khớp");
    try { await api("/api/auth/change-password", { method: "POST", body: { mat_khau_cu: cu, mat_khau_moi: moi } }); logout(); }
    catch (x) { setErr(x instanceof ApiError ? String(x.detail) : "Không đổi được mật khẩu"); }
  }
  return (
    <Dialog.Root open>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[rgba(15,36,54,0.5)]" />
        <Dialog.Content aria-describedby={undefined} className="fixed left-1/2 top-1/2 z-50 w-[min(440px,92vw)] -translate-x-1/2 -translate-y-1/2 rounded-md bg-be-mat p-6 shadow-2xl">
          <Dialog.Title className="text-lg font-bold">Đổi mật khẩu lần đầu</Dialog.Title>
          <p className="mb-3 text-[14px] text-muc-nhat">Mật khẩu ít nhất 10 ký tự, gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt.</p>
          <form onSubmit={submit} className="space-y-3">
            <label className="block text-sm font-medium">Mật khẩu tạm<input type="password" autoComplete="current-password" className="o-nhap mt-1" value={cu} onChange={(e) => setCu(e.target.value)} /></label>
            <label className="block text-sm font-medium">Mật khẩu mới<input type="password" autoComplete="new-password" className="o-nhap mt-1" value={moi} onChange={(e) => setMoi(e.target.value)} /></label>
            <label className="block text-sm font-medium">Nhập lại mật khẩu mới<input type="password" autoComplete="new-password" className="o-nhap mt-1" value={lai} onChange={(e) => setLai(e.target.value)} /></label>
            {err && <p role="alert" className="text-sm text-son">{err}</p>}
            <button type="submit" className="btn-chinh w-full justify-center" disabled={!cu || !moi}>Đổi mật khẩu và đăng nhập lại</button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
