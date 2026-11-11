export function SampleBanner({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <div role="status" className="border-b border-[var(--tam-thoi)] bg-[color-mix(in_srgb,var(--tam-thoi)_12%,var(--be-mat))] px-4 py-1.5 text-center text-[13px] font-medium text-muc md:px-6">
      Dữ liệu minh họa – không phải số liệu chính thức. Phường nhập hoặc kết nối số liệu thật để thay thế.
    </div>
  );
}
