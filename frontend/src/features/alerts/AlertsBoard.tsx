import * as Dialog from "@radix-ui/react-dialog";
import * as Tabs from "@radix-ui/react-tabs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { AssigneePicker, type Assignee } from "@/features/org/AssigneePicker";
import { Link, useSearchParams } from "react-router-dom";
import { RelatedDocs } from "@/features/van-ban/VanBanPage";
import { MessageButton } from "@/features/tin-nhan/MessagesPage";
import { X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";

export interface Case { id: number; chi_dao: string; co_quan_xu_ly: string; nguoi_phu_trach: string; nguyen_nhan: string; hanh_dong: string; han: string; trang_thai: string; ket_qua: string; lich_su: unknown[] }
export interface AlertRow { id: number; rule_ma: string; quy_tac: string; can_cu: string; loai: string; nhom: string; muc_do: string; tieu_de: string; mo_ta: string;
  link: string; ky: string; trang_thai: string; ghi_chu_chat_luong: string | null; phat_sinh_luc: string; ho_so: Case | null }

const COLS: [string, string][] = [["moi", "Mới"], ["da_giao", "Đã giao"], ["dang_xu_ly", "Đang xử lý"], ["hoan_thanh", "Hoàn thành"], ["gia_han", "Gia hạn"]];
const MUC: Record<string, string> = { cao: "Mức cao", trung_binh: "Mức trung bình", thap: "Mức thấp" };
const LOAI: Record<string, string> = { tien_do: "Tiến độ", qua_han: "Quá hạn cập nhật", lech_nguon: "Lệch nguồn", du_lieu: "Thiếu hồ sơ", chua_gui: "Chưa gửi dữ liệu" };

function errText(e: unknown) { return e instanceof ApiError ? String(e.detail) : "Không lưu được, thử lại"; }

function CaseDrawer({ alert, onClose }: { alert: AlertRow | null; onClose: () => void }) {
  const { can } = useAuth();
  const qc = useQueryClient();
  const c = alert?.ho_so ?? null;
  const [f, setF] = useState({ han: "", chi_dao: "" });
  const [who, setWho] = useState<Assignee>({ unitMa: "", unitTen: "", nguoi: "" });
  const [u, setU] = useState({ nguyen_nhan: c?.nguyen_nhan ?? "", hanh_dong: c?.hanh_dong ?? "", ket_qua: c?.ket_qua ?? "", han: "" });
  const [err, setErr] = useState<string | null>(null);
  const done = () => { qc.invalidateQueries({ queryKey: ["alerts"] }); onClose(); };
  const assign = useMutation({ mutationFn: () => api(`/api/alerts/${alert!.id}/assign`, { method: "POST", body: { co_quan_xu_ly: who.unitTen.trim(), nguoi_phu_trach: who.nguoi.trim(), ...f } }), onSuccess: done, onError: (e) => setErr(errText(e)) });
  const update = useMutation({
    mutationFn: (trang_thai: string) => api(`/api/cases/${c!.id}`, { method: "PATCH", body: { trang_thai, nguyen_nhan: u.nguyen_nhan, hanh_dong: u.hanh_dong, ket_qua: u.ket_qua, han: u.han || undefined } }),
    onSuccess: done, onError: (e) => setErr(errText(e)),
  });
  const canAssign = can("duyet", "canh_bao");
  return (
    <Dialog.Root open={!!alert} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[rgba(15,36,54,0.35)]" />
        <Dialog.Content aria-describedby={undefined} className="fixed inset-y-0 right-0 z-50 w-full max-w-[560px] overflow-y-auto bg-be-mat p-6 shadow-2xl">
          {alert && (
            <>
              <div className="flex items-start gap-3">
                <Dialog.Title className="flex-1 text-lg font-bold leading-snug">{alert.tieu_de}</Dialog.Title>
                <Dialog.Close className="btn-phu" aria-label="Đóng"><X size={16} /></Dialog.Close>
              </div>
              <p className="mt-1 text-[13px] text-muc-nhat">{alert.quy_tac}. Căn cứ Dự thảo mục {alert.can_cu}. {MUC[alert.muc_do]}.</p>
              {alert.mo_ta && <p className="mt-2 text-[14.5px]">{alert.mo_ta}</p>}
              {alert.ghi_chu_chat_luong && <p className="mt-2 rounded border border-vien bg-nen px-3 py-2 text-[13.5px]">{alert.ghi_chu_chat_luong}</p>}
              <div className="mt-2 flex flex-wrap items-center gap-3">
                {alert.link && <Link to={alert.link} className="text-[14px] underline">Mở dữ liệu liên quan</Link>}
                <MessageButton loai="canh_bao" id={alert.id} ten={alert.tieu_de} goiY={c?.nguoi_phu_trach} />
              </div>
              {err && <p role="alert" className="mt-3 text-sm text-son">{err}</p>}
              {!c ? (
                canAssign ? (
                  <form className="mt-5 space-y-3" onSubmit={(e) => { e.preventDefault(); assign.mutate(); }}>
                    <h3 className="font-semibold">Giao xử lý</h3>
                    <AssigneePicker value={who} onChange={setWho} nhom={alert.nhom} unitLabel="Cơ quan xử lý" />
                    <label className="block text-sm font-medium">Hạn xử lý<input type="date" className="o-nhap mt-1" min={new Date().toISOString().slice(0, 10)} value={f.han} onChange={(e) => setF({ ...f, han: e.target.value })} /></label>
                    <label className="block text-sm font-medium">Nội dung chỉ đạo<textarea className="o-nhap mt-1" rows={3} value={f.chi_dao} onChange={(e) => setF({ ...f, chi_dao: e.target.value })} /></label>
                    <button type="submit" className="btn-chinh" disabled={!who.unitTen.trim() || !who.nguoi.trim() || !f.han || assign.isPending}>Giao xử lý</button>
                  </form>
                ) : <p className="mt-5 text-[14px] text-muc-nhat">Cảnh báo chưa được giao xử lý.</p>
              ) : (
                <div className="mt-5 space-y-3">
                  <h3 className="font-semibold">Hồ sơ theo dõi</h3>
                  <dl className="grid grid-cols-[9rem_1fr] gap-y-1 text-[14px]">
                    <dt className="nhan">Cơ quan xử lý</dt><dd>{c.co_quan_xu_ly}</dd>
                    <dt className="nhan">Người phụ trách</dt><dd>{c.nguoi_phu_trach}</dd>
                    <dt className="nhan">Hạn</dt><dd>{formatDate(c.han)}</dd>
                    {c.chi_dao && (<><dt className="nhan">Chỉ đạo</dt><dd>{c.chi_dao}</dd></>)}
                  </dl>
                  <RelatedDocs caseId={c.id} />
                  <label className="block text-sm font-medium">Nguyên nhân<textarea className="o-nhap mt-1" rows={2} value={u.nguyen_nhan} onChange={(e) => setU({ ...u, nguyen_nhan: e.target.value })} /></label>
                  <label className="block text-sm font-medium">Hành động khắc phục<textarea className="o-nhap mt-1" rows={2} value={u.hanh_dong} onChange={(e) => setU({ ...u, hanh_dong: e.target.value })} /></label>
                  <label className="block text-sm font-medium">Kết quả xử lý<textarea className="o-nhap mt-1" rows={2} value={u.ket_qua} onChange={(e) => setU({ ...u, ket_qua: e.target.value })} /></label>
                  <div className="flex flex-wrap items-end gap-2">
                    <button type="button" className="btn-phu" onClick={() => update.mutate("dang_xu_ly")}>Lưu tiến độ xử lý</button>
                    <button type="button" className="btn-chinh" disabled={!u.ket_qua.trim()} onClick={() => update.mutate("hoan_thanh")}>Hoàn thành hồ sơ</button>
                    <label className="text-sm font-medium">Hạn mới<input type="date" className="o-nhap mt-1 w-auto" value={u.han} onChange={(e) => setU({ ...u, han: e.target.value })} /></label>
                    <button type="button" className="btn-phu" disabled={!u.han} onClick={() => update.mutate("gia_han")}>Gia hạn</button>
                  </div>
                </div>
              )}
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function AlertsBoard() {
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState("tat_ca");
  const q = useQuery({ queryKey: ["alerts"], queryFn: () => api<AlertRow[]>("/api/alerts") });
  const all = q.data ?? [];
  const shown = all.filter((a) => tab === "tat_ca" || (tab === "tien_do" ? a.loai === "tien_do" : a.loai !== "tien_do"));
  const openId = Number(params.get("id")) || null;
  const open = all.find((a) => a.id === openId) ?? null;
  return (
    <>
      <PageHeader title="Cảnh báo và hồ sơ theo dõi" desc="Cảnh báo sinh tự động hằng đêm và ngay khi số liệu được xác nhận. Từ mỗi cảnh báo, lãnh đạo giao cơ quan, người phụ trách và hạn xử lý." />
      <Tabs.Root value={tab} onValueChange={setTab}>
        <Tabs.List aria-label="Loại cảnh báo" className="mb-4 flex gap-1 border-b border-vien">
          {[["tat_ca", "Tất cả"], ["tien_do", "Tiến độ"], ["du_lieu", "Chất lượng dữ liệu"]].map(([k, t]) => (
            <Tabs.Trigger key={k} value={k} className="-mb-px border-b-2 border-transparent px-3 py-2 text-[14.5px] text-muc-nhat data-[state=active]:border-muc data-[state=active]:font-semibold data-[state=active]:text-muc">
              {t} ({all.filter((a) => k === "tat_ca" || (k === "tien_do" ? a.loai === "tien_do" : a.loai !== "tien_do")).length})
            </Tabs.Trigger>
          ))}
        </Tabs.List>
      </Tabs.Root>
      <div className="grid gap-3 lg:grid-cols-5">
        {COLS.map(([k, t]) => {
          const items = shown.filter((a) => a.trang_thai === k);
          return (
            <section key={k} aria-label={t} className="min-w-0 rounded-md bg-be-mat-2 p-2">
              <h2 className="px-1 pb-2 text-[14px] font-semibold">{t} <span className="text-muc-nhat">({items.length})</span></h2>
              <ul className="space-y-2">
                {items.map((a) => (
                  <li key={a.id}>
                    <button type="button" onClick={() => setParams({ id: String(a.id) })}
                      className={`khu w-full rounded p-2.5 text-left hover:border-muc ${a.muc_do === "cao" ? "border-l-[3px] border-l-son" : a.loai !== "tien_do" ? "is-missing" : ""}`}>
                      <span className="block text-[14px] font-medium leading-snug">{a.tieu_de}</span>
                      <span className="mt-1 block text-[12px] text-muc-nhat">{LOAI[a.loai]}. {MUC[a.muc_do]}{a.ho_so ? `. ${a.ho_so.nguoi_phu_trach}, hạn ${formatDate(a.ho_so.han)}` : ""}</span>
                      {a.ghi_chu_chat_luong && <span className="mt-1 block text-[12px] text-muc-nhat">{a.ghi_chu_chat_luong}</span>}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
      <CaseDrawer key={open?.id ?? 0} alert={open} onClose={() => setParams({})} />
    </>
  );
}
