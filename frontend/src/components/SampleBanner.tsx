export function SampleBanner({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <div role="status" className="border-b border-[color-mix(in_srgb,var(--tam-thoi)_40%,transparent)] bg-[color-mix(in_srgb,var(--tam-thoi)_12%,var(--be-mat))] px-4 py-1 text-center text-[12.5px] font-semibold text-[color-mix(in_srgb,var(--tam-thoi)_75%,#000)] md:px-6">
      <span className="sm:hidden">Dữ liệu minh họa – không phải số liệu chính thức</span>
      <span className="hidden sm:inline">Dữ liệu minh họa – không phải số liệu chính thức. Phường nhập hoặc kết nối số liệu thật để thay thế.</span>
    </div>
  );
}
