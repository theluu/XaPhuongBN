import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import { useNavigate } from "react-router-dom";

export interface MapFeature { type: "Feature"; geometry: { type: "Point"; coordinates: [number, number] }; properties: Record<string, unknown> }

const COLOR: Record<string, string> = { du_an: "#16324a", cong_trinh: "#b7791f", truong: "#1e7358", diem_moi_truong: "#3b7ea1", tram_y_te: "#b42318" };

/** Bản đồ điểm: chỉ vẽ các điểm có vị trí hợp lệ (máy chủ đã lọc). */
const DEFAULT_TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

/** tileUrl: nền bản đồ của đơn vị (VD máy chủ bản đồ nội bộ khi triển khai on-prem không có Internet). */
export function ProjectMap({ features, center, zoom = 14, height = 320, tileUrl }: { features: MapFeature[]; center: [number, number]; zoom?: number; height?: number; tileUrl?: string }) {
  const nav = useNavigate();
  return (
    <div style={{ height }} className="overflow-hidden rounded border border-vien">
      <MapContainer center={center} zoom={zoom} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
        <TileLayer attribution="&copy; OpenStreetMap" url={tileUrl || DEFAULT_TILES} />
        {features.map((f) => {
          const p = f.properties;
          const loai = String(p.loai ?? "du_an");
          return (
            <CircleMarker key={`${loai}-${String(p.ma ?? p.ten)}`} center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
              radius={loai === "du_an" ? 9 : 7} pathOptions={{ color: "#fff", weight: 2, fillColor: COLOR[loai] ?? "#16324a", fillOpacity: 0.95 }}
              eventHandlers={{ click: () => typeof p.link === "string" && nav(p.link) }}>
              <Tooltip>{String(p.ten)}</Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}

export function MapLegend({ items }: { items: { loai: string; ten: string }[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-4 text-[12.5px] text-muc-nhat">
      {items.map((i) => (
        <span key={i.loai} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: COLOR[i.loai] }} />{i.ten}</span>
      ))}
    </div>
  );
}
