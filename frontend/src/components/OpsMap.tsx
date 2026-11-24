import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { CircleMarker, MapContainer, Tooltip, useMap } from "react-leaflet";
import { MapTiles } from "./MapTiles";

export interface OpsPoint { key: string; lat: number; lng: number; ten: string; mau: "khan" | "qua_han" | "thuong" | "du_an" | "cong_trinh"; nhan?: string }

const COLOR = { khan: "#b91c1c", qua_han: "#ea580c", thuong: "#1d4ed8", du_an: "#123254", cong_trinh: "#a16207" };

function FlyTo({ point }: { point: OpsPoint | undefined }) {
  const map = useMap();
  useEffect(() => { if (point) map.flyTo([point.lat, point.lng], Math.max(map.getZoom(), 16), { duration: 0.5 }); }, [point, map]);
  return null;
}

/** Bản đồ địa bàn (§2): bấm điểm → chọn dòng tương ứng; chọn dòng → định vị điểm. */
export function OpsMap({ points, center, zoom = 14, selected, onSelect, height = "100%", tileUrl, large = false }: {
  points: OpsPoint[]; center: [number, number]; zoom?: number; selected?: string | null; onSelect?: (key: string) => void;
  height?: number | string; tileUrl?: string; large?: boolean;
}) {
  const sel = points.find((p) => p.key === selected);
  return (
    <div style={{ height }} className="min-h-[320px] overflow-hidden rounded-md border border-vien" data-testid="ops-map">
      <MapContainer center={center} zoom={zoom} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
        <MapTiles tileUrl={tileUrl} theme={large ? "toi" : "sang"} />
        {points.map((p) => {
          const active = p.key === selected;
          return (
            <CircleMarker key={p.key} center={[p.lat, p.lng]} radius={(large ? 11 : 8) + (active ? 4 : 0)}
              pathOptions={{ color: active ? "#facc15" : "#fff", weight: active ? 4 : 2, fillColor: COLOR[p.mau], fillOpacity: 0.95 }}
              eventHandlers={{ click: () => onSelect?.(p.key) }}>
              <Tooltip permanent={large && p.mau === "khan"}>{p.nhan ? `${p.nhan}: ` : ""}{p.ten}</Tooltip>
            </CircleMarker>
          );
        })}
        <FlyTo point={sel} />
      </MapContainer>
    </div>
  );
}

export function OpsLegend({ items = ["khan", "qua_han", "thuong"] as (keyof typeof COLOR)[] }) {
  const TEN = { khan: "Khẩn cấp", qua_han: "Quá hạn", thuong: "Đang xử lý", du_an: "Dự án đầu tư công", cong_trinh: "Công trình" };
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12.5px] text-muc-nhat">
      {items.map((k) => <span key={k} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: COLOR[k] }} />{TEN[k]}</span>)}
    </div>
  );
}

export function pointColor(x: { khan_cap: boolean; qua_han_ngay: number | null }): OpsPoint["mau"] {
  return x.khan_cap ? "khan" : x.qua_han_ngay ? "qua_han" : "thuong";
}
