import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";

interface Pack { ma: string; ten: string; phien_ban: number; so_chi_tieu: number }
interface Result { tenant_id: number; so_chi_tieu: number; so_tdp: number; lanh_dao: string; mat_khau_tam: string }

const STEPS = ["Đơn vị hành chính", "Gói mẫu", "Tổ dân phố", "Tài khoản lãnh đạo", "Xác nhận"];

export function OnboardWizard({ onDone }: { onDone: () => void }) {
  const packs = useQuery({ queryKey: ["packs"], queryFn: () => api<Pack[]>("/api/platform/packs") });
  const [step, setStep] = useState(0);
  const [f, setF] = useState({ ma_dvhc: "", ten: "", cap: "phuong", pack: "", so_tdp: 10, username: "", ho_ten: "", chuc_danh: "" });
  const [err, setErr] = useState<string | null>(null);
  const m = useMutation({
    mutationFn: () => api<Result>("/api/platform/onboard", { method: "POST", body: { ma_dvhc: f.ma_dvhc.trim(), ten: f.ten.trim(), cap: f.cap, pack: f.pack, so_tdp: f.so_tdp,
      lanh_dao: { username: f.username.trim(), ho_ten: f.ho_ten.trim(), chuc_danh: f.chuc_danh.trim() } } }),
    onError: (e) => setErr(e instanceof ApiError ? (typeof e.detail === "string" ? e.detail : "Dữ liệu chưa hợp lệ") : "Không khởi tạo được"),
  });
  const ok = [f.ma_dvhc.trim() && f.ten.trim(), f.pack, f.so_tdp >= 0, /^[a-zA-Z0-9_.-]{3,}$/.test(f.username) && f.ho_ten.trim(), true][step];
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: k === "so_tdp" ? Number(e.target.value) || 0 : e.target.value });

  if (m.data) {
    return (
      <div className="khu rounded-md p-5" role="status">
        <h3 className="text-lg font-semibold">Đã khởi tạo {f.ten}</h3>
        <p className="mt-1 text-[14.5px]">{m.data.so_chi_tieu} chỉ tiêu từ gói mẫu, {m.data.so_tdp} tổ dân phố. Các phân hệ hiển thị "Đang kết nối" cho tới khi có nguồn dữ liệu hoặc phường nhập số.</p>
        <p className="mt-3 text-[14.5px]">Tài khoản lãnh đạo: <b>{m.data.lanh_dao}</b>. Mật khẩu tạm (chỉ hiển thị một lần):</p>
        <p className="mt-1 inline-block rounded bg-nen px-3 py-1.5 font-mono text-lg tracking-wide">{m.data.mat_khau_tam}</p>
        <p className="mt-2 text-[13px] text-muc-nhat">Người dùng phải đổi mật khẩu ở lần đăng nhập đầu tiên.</p>
        <button type="button" className="btn-phu mt-4" onClick={onDone}>Đóng</button>
      </div>
    );
  }
  return (
    <form aria-label="Khởi tạo đơn vị" className="khu rounded-md p-5" onSubmit={(e) => { e.preventDefault(); if (step < 4) setStep(step + 1); else m.mutate(); }}>
      <ol className="mb-4 flex flex-wrap gap-2 text-[13px]" aria-hidden>
        {STEPS.map((s, i) => <li key={s} className={`rounded-full px-2.5 py-0.5 ${i === step ? "bg-muc text-be-mat" : i < step ? "bg-nen" : "border border-vien text-muc-nhat"}`}>{i + 1}. {s}</li>)}
      </ol>
      <h3 className="mb-3 font-semibold">Bước {step + 1}/5: {STEPS[step]}</h3>
      {step === 0 && (
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm font-medium">Mã đơn vị hành chính<input className="o-nhap mt-1" value={f.ma_dvhc} onChange={set("ma_dvhc")} /></label>
          <label className="text-sm font-medium">Tên đơn vị<input className="o-nhap mt-1" placeholder="Phường …" value={f.ten} onChange={set("ten")} /></label>
          <label className="text-sm font-medium">Cấp<select className="o-nhap mt-1" value={f.cap} onChange={set("cap")}><option value="phuong">Phường</option><option value="xa">Xã</option></select></label>
        </div>
      )}
      {step === 1 && (
        <fieldset className="space-y-2">
          <legend className="sr-only">Gói mẫu</legend>
          {(packs.data ?? []).map((p) => (
            <label key={p.ma} className="flex items-start gap-2 text-[14.5px]">
              <input type="radio" name="pack" value={p.ma} checked={f.pack === p.ma} onChange={set("pack")} className="mt-1" />
              <span>{p.ten} <span className="text-muc-nhat">({p.so_chi_tieu} chỉ tiêu, phiên bản {p.phien_ban})</span></span>
            </label>
          ))}
        </fieldset>
      )}
      {step === 2 && <label className="block max-w-xs text-sm font-medium">Số tổ dân phố<input type="number" min={0} className="o-nhap mt-1" value={f.so_tdp} onChange={set("so_tdp")} /></label>}
      {step === 3 && (
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-sm font-medium">Tên đăng nhập<input className="o-nhap mt-1" autoComplete="off" value={f.username} onChange={set("username")} /></label>
          <label className="text-sm font-medium">Họ tên<input className="o-nhap mt-1" value={f.ho_ten} onChange={set("ho_ten")} /></label>
          <label className="text-sm font-medium">Chức danh<input className="o-nhap mt-1" value={f.chuc_danh} onChange={set("chuc_danh")} /></label>
        </div>
      )}
      {step === 4 && (
        <dl className="grid grid-cols-[11rem_1fr] gap-y-1 text-[14.5px]">
          <dt className="nhan">Đơn vị</dt><dd>{f.ten} ({f.ma_dvhc})</dd>
          <dt className="nhan">Gói mẫu</dt><dd>{packs.data?.find((p) => p.ma === f.pack)?.ten}</dd>
          <dt className="nhan">Tổ dân phố</dt><dd>{f.so_tdp}</dd>
          <dt className="nhan">Lãnh đạo</dt><dd>{f.ho_ten}, {f.chuc_danh} ({f.username})</dd>
        </dl>
      )}
      {err && <p role="alert" className="mt-3 text-sm text-son">{err}</p>}
      <div className="mt-4 flex gap-2">
        {step > 0 && <button type="button" className="btn-phu" onClick={() => setStep(step - 1)}>Quay lại</button>}
        <button type="submit" className="btn-chinh" disabled={!ok || m.isPending}>{step < 4 ? "Tiếp tục" : "Khởi tạo"}</button>
      </div>
    </form>
  );
}
