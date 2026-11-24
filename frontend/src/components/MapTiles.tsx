import { useEffect, useRef, useState } from "react";
import { TileLayer, useMap } from "react-leaflet";

/** Nguồn nền bản đồ không cần khóa API, theo thứ tự ưu tiên. tile.openstreetmap.org bị chặn ở một số mạng tại Việt Nam;
 *  CARTO đã bắt buộc khóa (trả ảnh "API KEY REQUIRED"). Lỗi liên tục thì tự chuyển nguồn tiếp theo.
 *  Đơn vị có máy chủ bản đồ riêng (on-prem) khai báo tile_url trong Cấu hình đơn vị — luôn được ưu tiên. */
const OSM_FR = { url: "https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png", attribution: "&copy; OpenStreetMap, OSM France", subdomains: "abc" };
const ESRI_STREET = { url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", attribution: "&copy; Esri, HERE, OpenStreetMap", subdomains: "abc" };
const ESRI_DARK = { url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", attribution: "&copy; Esri", subdomains: "abc" };
const OSM = { url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", attribution: "&copy; OpenStreetMap", subdomains: "abc" };
export const DEFAULT_TILE_URL = OSM_FR.url;
const SOURCES = { sang: [OSM_FR, ESRI_STREET, OSM], toi: [ESRI_DARK, OSM_FR] };
/** Địa chỉ nền cũ đã ngừng dùng được (cần khóa) → bỏ qua, dùng mặc định. */
const BLOCKED = /basemaps\.cartocdn\.com/;

/** Báo Leaflet tính lại kích thước khi khung chứa đổi cỡ (mở khung chi tiết, đổi bố cục) — tránh nền xám. */
function AutoResize() {
  const map = useMap();
  useEffect(() => {
    const el = map.getContainer();
    const fix = () => map.invalidateSize({ pan: false });
    const t = window.setTimeout(fix, 50);
    if (typeof ResizeObserver === "undefined") return () => window.clearTimeout(t);
    const ro = new ResizeObserver(fix);
    ro.observe(el);
    return () => { window.clearTimeout(t); ro.disconnect(); };
  }, [map]);
  return null;
}

export function MapTiles({ tileUrl, theme = "sang" }: { tileUrl?: string; theme?: "sang" | "toi" }) {
  const custom = tileUrl && !BLOCKED.test(tileUrl) && theme === "sang";
  const list = custom ? [{ url: tileUrl, attribution: "Bản đồ nền của đơn vị", subdomains: "abc" }, ...SOURCES[theme]] : SOURCES[theme];
  const [i, setI] = useState(0);
  const errors = useRef(0);
  const ok = useRef(false);
  const src = list[Math.min(i, list.length - 1)];
  return (
    <>
      <TileLayer key={src.url} url={src.url} attribution={src.attribution} subdomains={src.subdomains} maxZoom={19}
        eventHandlers={{
          tileload: () => { ok.current = true; },
          tileerror: () => {
            errors.current += 1;
            if (!ok.current && errors.current >= 4 && i < list.length - 1) { errors.current = 0; setI(i + 1); }
          },
        }} />
      <AutoResize />
    </>
  );
}
