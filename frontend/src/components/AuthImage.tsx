import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";

/** Ảnh tải qua API có xác thực (không lộ đường dẫn công khai). */
export function AuthImage({ fileKey, alt, className }: { fileKey: string; alt: string; className?: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let url: string | null = null;
    fetch(`/api/files/${encodeURIComponent(fileKey)}`, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } })
      .then((r) => (r.ok ? r.blob() : Promise.reject()))
      .then((b) => { url = URL.createObjectURL(b); setSrc(url); })
      .catch(() => setSrc(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [fileKey]);
  return src ? <img src={src} alt={alt} className={className} /> : <div className={`is-missing ${className ?? ""}`} role="img" aria-label={`${alt} (chưa tải được)`} />;
}
