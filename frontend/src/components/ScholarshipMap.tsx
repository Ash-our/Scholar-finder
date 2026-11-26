import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { MarkerClusterGroup } from "leaflet.markercluster";
import {
  countryAtPoint,
  type Countries,
  type CountryFeature,
} from "../country-geometry";
import {
  GeoJSON,
  MapContainer,
  Marker,
  TileLayer,
  Tooltip,
  ZoomControl,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { Globe2, GraduationCap, LocateFixed } from "lucide-react";
import type { MapData, MapGroup } from "../types";
import { countryName, number } from "../labels";
import countryReference from "../../../data/countries.json";

const countryCenters = countryReference.countries as Record<
  string,
  { name: string; lat: number; lon: number }
>;

interface MapProps {
  data: MapData | undefined;
  overview: MapData | undefined;
  selectedCountry: string;
  selectedPlacement: string;
  focusRequest: { sequence: number; country: string } | null;
  hoveredId: string | null;
  onCountry: (code: string) => void;
  onSelect: (group: MapGroup) => void;
  onClear: () => void;
  onWorld: () => void;
}

function UniversityMarkers({
  groups,
  hoveredId,
  selectedPlacement,
  onSelect,
}: {
  groups: MapGroup[];
  hoveredId: string | null;
  selectedPlacement: string;
  onSelect: (group: MapGroup) => void;
}) {
  const map = useMap();
  const selection = useRef(onSelect);
  selection.current = onSelect;
  const markers = useRef<Map<string, { marker: L.Marker; group: MapGroup }>>(
    new Map(),
  );
  const key = JSON.stringify(groups);
  useEffect(() => {
    const rows = JSON.parse(key) as MapGroup[];
    const cluster = new MarkerClusterGroup({
      maxClusterRadius: 65,
      showCoverageOnHover: false,
      animate: false,
      spiderfyOnMaxZoom: true,
      spiderfyDistanceMultiplier: 1.6,
      clusterLabel: (c) =>
        number(c.getChildCount()) + " مواقع جامعات، اضغط للتقريب",
      iconCreateFunction: (c) =>
        L.divIcon({
          className: "scholar-marker university-cluster",
          html:
            '<span class="campus-cluster-badge"><b>' +
            c.getChildCount() +
            "</b><span>مواقع</span></span>",
          iconSize: [68, 40],
          iconAnchor: [34, 20],
        }),
    });
    const next = new Map<string, { marker: L.Marker; group: MapGroup }>();
    for (const group of rows) {
      const icon = L.divIcon({
        className: "scholar-marker university-pin",
        html:
          '<span class="pin"><span aria-hidden="true">⌂</span><b>' +
          group.scholarship_ids.length +
          "</b></span>",
        iconSize: [58, 37],
        iconAnchor: [29, 42],
        popupAnchor: [0, -38],
      });
      const marker = L.marker([group.lat, group.lon], {
        icon,
        title: group.name,
        bubblingMouseEvents: false,
      });
      const popup = document.createElement("div");
      popup.className = "map-popup";
      popup.dir = "rtl";
      const title = document.createElement("strong");
      title.dir = "auto";
      title.textContent = group.name;
      popup.appendChild(title);
      const precision = document.createElement("p");
      precision.textContent =
        number(group.scholarship_ids.length) +
        " إعلان · " +
        (group.precision === "campus" ? "موقع الحرم" : "موقع مدينة تقريبي");
      popup.appendChild(precision);
      const button = document.createElement("button");
      button.className = "text-button";
      button.textContent = "عرض منح هذه الجامعة";
      button.onclick = () => selection.current(group);
      popup.appendChild(button);
      marker.bindPopup(popup, { autoPan: false });
      marker.on("click", () => selection.current(group));
      cluster.addLayer(marker);
      next.set(group.key, { marker, group });
    }
    markers.current = next;
    // The plugin supports Leaflet1.9 at runtime; its2.x declarations use the
    // newer generic base-layer type. Keep that interoperability cast local.
    const layer = cluster as unknown as L.Layer;
    map.addLayer(layer);
    return () => {
      map.removeLayer(layer);
      markers.current.clear();
    };
  }, [map, key]);
  useEffect(() => {
    for (const { marker, group } of markers.current.values()) {
      const active =
        group.id === selectedPlacement ||
        (!!hoveredId && group.scholarship_ids.includes(hoveredId));
      marker.setZIndexOffset(active ? 2000 : 0);
      marker
        .getElement()
        ?.querySelector(".pin")
        ?.classList.toggle("pin-active", active);
    }
  }, [hoveredId, selectedPlacement, key]);
  return null;
}

function focusBounds(feature: CountryFeature): L.LatLngBounds {
  const full = L.geoJSON(feature).getBounds();
  if (
    feature.geometry.type !== "MultiPolygon" ||
    full.getEast() - full.getWest() < 35
  )
    return full;
  const parts = feature.geometry.coordinates.map((coordinates) =>
    L.geoJSON({
      ...feature,
      geometry: { type: "Polygon", coordinates },
    } as CountryFeature).getBounds(),
  );
  return (
    parts.sort(
      (a, b) =>
        (b.getEast() - b.getWest()) * (b.getNorth() - b.getSouth()) -
        (a.getEast() - a.getWest()) * (a.getNorth() - a.getSouth()),
    )[0] || full
  );
}

export default function ScholarshipMap(props: MapProps) {
  const [borders, setBorders] = useState<Countries>();
  const [error, setError] = useState("");
  const [tileError, setTileError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/data/countries.geojson", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("تعذر تحميل حدود الدول");
        return response.json();
      })
      .then((value: Countries) => {
        if (!controller.signal.aborted) setBorders(value);
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    return () => controller.abort();
  }, []);
  return (
    <section
      className="map-pane country-map"
      aria-label="خريطة الدول والجامعات"
      dir="ltr"
    >
      <MapContainer
        center={[25, 10]}
        zoom={2}
        minZoom={1}
        maxZoom={15}
        zoomControl={false}
        maxBounds={[
          [-85, -180],
          [85, 180],
        ]}
        maxBoundsViscosity={0.8}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={18}
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · <a href="https://www.naturalearthdata.com/">Natural Earth</a>'
          eventHandlers={{ tileerror: () => setTileError(true) }}
        />
        <ZoomControl position="topleft" />
        <CountryContent {...props} borders={borders} />
      </MapContainer>
      {(error || tileError) && (
        <p className="tile-warning" dir="rtl">
          {error || "تعذر تحميل بعض بلاطات الخريطة؛ القائمة تبقى متاحة."}
        </p>
      )}
      {props.selectedCountry && !borders && !error && (
        <p className="map-loading" dir="rtl">
          جارٍ تحميل حدود الدول…
        </p>
      )}
      <div className="map-legend" dir="rtl">
        <span className="legend-pin" />
        {props.selectedCountry
          ? "البنفسجي يحدد الدولة المختارة · مواقع الجامعات تقريبية بحسب المصدر"
          : "اختر دولة لعرض جامعاتها وفرصها"}
        {props.selectedCountry && <span>حدود مرجعية تقريبية</span>}
      </div>
    </section>
  );
}

function CountryContent({
  data,
  overview,
  selectedCountry,
  selectedPlacement,
  focusRequest,
  hoveredId,
  onCountry,
  onSelect,
  onClear,
  onWorld,
  borders,
}: MapProps & { borders: Countries | undefined }) {
  const map = useMap();
  useMapEvents({
    click(event) {
      const target = event.originalEvent?.target as HTMLElement | null;
      if (
        target?.closest(
          ".leaflet-marker-icon,.leaflet-popup,.leaflet-control,.country-map-toolbar,.country-location-note,.map-legend",
        )
      )
        return;
      if (!borders) return;
      map.closePopup();
      const country = countryAtPoint(
        borders,
        event.latlng.lat,
        event.latlng.lng,
        selectedCountry,
      );
      if (country) onCountry(country);
      else onClear();
    },
  });
  const summaries = overview?.countries || data?.countries || [];
  const [zoom, setZoom] = useState(map.getZoom());
  useEffect(() => {
    const changed = () => setZoom(map.getZoom());
    map.on("zoomend", changed);
    return () => {
      map.off("zoomend", changed);
    };
  }, [map]);
  const tagPositions = useMemo(() => {
    const occupied: L.Point[] = [];
    const positions = new Map<string, L.LatLng>();
    // Reveal close neighbours as the user zooms in. Every visible tag stays
    // anchored to the country's real reference coordinate, never displaced.
    for (const row of [...summaries].sort(
      (a, b) =>
        b.listing_count - a.listing_count || a.country.localeCompare(b.country),
    )) {
      const center = countryCenters[row.country];
      if (!center) continue;
      const origin = map.project([center.lat, center.lon], zoom);
      if (
        occupied.some(
          (other) =>
            Math.abs(origin.x - other.x) < 70 &&
            Math.abs(origin.y - other.y) < 46,
        )
      )
        continue;
      occupied.push(origin);
      positions.set(row.country, L.latLng(center.lat, center.lon));
    }
    return positions;
  }, [summaries, map, zoom]);
  const counts = useMemo(
    () => new Map(summaries.map((row) => [row.country, row])),
    [summaries],
  );
  const universities = (overview?.groups || data?.groups || []).filter(
    (place) =>
      place.country === selectedCountry && place.precision !== "country",
  );
  const selected = counts.get(selectedCountry);
  const selectedFeature = borders?.features.find(
    (feature) => feature.properties.iso_a2 === selectedCountry,
  );
  function fitUniversities() {
    if (universities.length)
      map.fitBounds(L.latLngBounds(universities.map((p) => [p.lat, p.lon])), {
        padding: [55, 65],
        maxZoom: 11,
        animate: false,
      });
    else if (selectedFeature)
      map.fitBounds(focusBounds(selectedFeature), {
        padding: [35, 60],
        maxZoom: 9,
        animate: false,
      });
  }
  useEffect(() => {
    if (!focusRequest) return;
    const feature = borders?.features.find(
      (row) => row.properties.iso_a2 === focusRequest.country,
    );
    if (feature)
      map.fitBounds(focusBounds(feature), {
        padding: [35, 70],
        maxZoom: 9,
        animate: false,
      });
    else if (!focusRequest.country)
      map.setView([25, 10], 2, { animate: false });
  }, [focusRequest, borders, map]);
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return (
    <>
      {!selectedCountry &&
        summaries.map((row) => {
          const position = tagPositions.get(row.country);
          if (!position) return null;
          const label =
            countryName(row.country) +
            ": " +
            number(row.listing_count) +
            " إعلان";
          return (
            <Marker
              key={row.country}
              position={position}
              title={label}
              alt={label}
              riseOnHover
              icon={L.divIcon({
                className: "scholar-marker country-tag",
                html:
                  '<span class="pin" data-country-tag="' +
                  row.country +
                  '"><b>' +
                  number(row.listing_count) +
                  "</b><small>" +
                  row.country +
                  "</small></span>",
                iconSize: [62, 35],
                iconAnchor: [31, 39],
              })}
              eventHandlers={{ click: () => onCountry(row.country) }}
            >
              <Tooltip direction="top" className="country-tooltip">
                {label}
              </Tooltip>
            </Marker>
          );
        })}
      {selectedFeature && (
        <GeoJSON
          key={selectedCountry}
          data={selectedFeature}
          style={{
            color: "#793de0",
            weight: 3.5,
            fill: false,
            className: "country-boundary country-selected",
            interactive: false,
          }}
          onEachFeature={(_, layer) =>
            layer.on("add", () => {
              (layer as L.Path)
                .getElement()
                ?.setAttribute("data-country", selectedCountry);
            })
          }
        />
      )}
      {selectedCountry && (
        <UniversityMarkers
          groups={universities}
          hoveredId={hoveredId}
          selectedPlacement={selectedPlacement}
          onSelect={onSelect}
        />
      )}
      <div className="country-map-toolbar" dir="rtl">
        {selectedCountry ? (
          <>
            <button
              className="floating-button"
              onClick={onWorld}
              aria-label="كل الدول"
              title="عرض خريطة العالم"
            >
              <Globe2 size={17} />
              <span>كل الدول</span>
            </button>
            <div className="country-map-heading">
              <strong>{countryName(selectedCountry)}</strong>
              <span>
                {number(selected?.listing_count || 0)} إعلان ·{" "}
                {number(universities.length)} موقع جامعة أو جهة بحثية
              </span>
            </div>
            <button
              className="floating-button"
              onClick={fitUniversities}
              aria-label="إظهار الجامعات"
              title="إظهار الجامعات"
            >
              <LocateFixed size={17} />
              <span>إظهار الجامعات</span>
            </button>
          </>
        ) : (
          <>
            <button
              className="floating-button"
              onClick={onWorld}
              aria-label="عرض خريطة العالم"
            >
              <Globe2 size={17} />
            </button>
            <div className="country-map-heading">
              <strong>استكشف {number(summaries.length)} وجهة</strong>
              <span>اختر دولة من الخريطة · قرّب لإظهار الوسوم المتقاربة</span>
            </div>
          </>
        )}
      </div>
      {selectedCountry && (
        <div className="country-location-note" dir="rtl">
          <GraduationCap size={18} />
          {universities.length ? (
            <span>
              تظهر المواقع المعروفة فقط.{" "}
              {number(selected?.unlocated_count || 0)} إعلان لا يحدد جامعة
              بعينها؛ يظل متاحًا في القائمة.
            </span>
          ) : (
            <span>
              لا يتوفر موقع جامعة موثوق لهذه الاختيارات بعد. يمكنك تصفح فرص{" "}
              {countryName(selectedCountry)} في القائمة.
            </span>
          )}
        </div>
      )}
    </>
  );
}
