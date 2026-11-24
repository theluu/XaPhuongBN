import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, useMapEvents } from "react-leaflet";
import { MapTiles } from "./MapTiles";

function Clicker({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onPick(Number(e.latlng.lat.toFixed(6)), Number(e.latlng.lng.toFixed(6))) });
  return null;
}

/** Bấm lên bản đồ để xác định vị trí hiện trường. */
export function LocationPicker({ value, center, onChange, tileUrl }: {
  value: { lat: number; lng: number } | null; center: [number, number]; onChange: (v: { lat: number; lng: number } | null) => void; tileUrl?: string;
}) {
  return (
    <div>
      <div className="h-56 overflow-hidden rounded-md border border-vien" data-testid="location-picker">
        <MapContainer center={value ? [value.lat, value.lng] : center} zoom={15} style={{ height: "100%", width: "100%" }}>
          <MapTiles tileUrl={tileUrl} />
          <Clicker onPick={(lat, lng) => onChange({ lat, lng })} />
          {value && <CircleMarker center={[value.lat, value.lng]} radius={9} pathOptions={{ color: "#fff", weight: 2, fillColor: "#b91c1c", fillOpacity: 1 }} />}
        </MapContainer>
      </div>
      <div className="mt-1 flex items-center justify-between text-[12.5px] text-muc-nhat">
        <span>{value ? `Vĩ độ ${value.lat}, kinh độ ${value.lng}` : "Bấm lên bản đồ để chọn vị trí. Có thể bỏ trống nếu chưa xác định."}</span>
        {value && <button type="button" className="lien-ket" onClick={() => onChange(null)}>Bỏ vị trí</button>}
      </div>
    </div>
  );
}
