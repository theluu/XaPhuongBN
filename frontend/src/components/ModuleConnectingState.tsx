import { PlugZap } from "lucide-react";

const TRANG_THAI: Record<string, string> = {
  dang_ket_noi: "đang kết nối",
  loi: "lỗi kết nối",
  khong_tra_du_lieu: "chưa trả dữ liệu",
  hoat_dong_mot_phan: "hoạt động một phần",
  hoat_dong: "hoạt động",
};

export function ModuleConnectingState({ title, sources = [] }: { title: string; sources?: { ten: string; trang_thai: string }[] }) {
  return (
    <section className="khu is-missing rounded-md p-8 text-center">
      <PlugZap aria-hidden className="mx-auto mb-3 text-thieu" size={36} />
      <h2 className="text-lg font-semibold">Đang kết nối nguồn dữ liệu</h2>
      <p className="mx-auto mt-1 max-w-prose text-[15px] text-muc-nhat">
        Phân hệ {title} sẽ hiển thị khi có nguồn dữ liệu được phép chia sẻ, hoặc khi phường nhập số liệu qua biểu mẫu Excel.
      </p>
      {sources.length > 0 && (
        <ul className="mx-auto mt-3 inline-block text-left text-[14px]">
          {sources.map((s) => (
            <li key={s.ten}>{s.ten}: {TRANG_THAI[s.trang_thai] ?? s.trang_thai}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
