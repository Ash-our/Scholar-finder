import type { Feature, FeatureCollection, Geometry, Position } from "geojson";

export type CountryFeature = Feature<
  Geometry,
  { iso_a2: string | null; name: string }
>;
export type Countries = FeatureCollection<
  Geometry,
  { iso_a2: string | null; name: string }
>;

function inRing(point: Position, ring: Position[]): boolean {
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [ax, ay] = ring[j];
    const [bx, by] = ring[i];
    const cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax);
    if (
      Math.abs(cross) < 1e-9 &&
      x >= Math.min(ax, bx) &&
      x <= Math.max(ax, bx) &&
      y >= Math.min(ay, by) &&
      y <= Math.max(ay, by)
    )
      return true;
    if (ay > y !== by > y && x < ((bx - ax) * (y - ay)) / (by - ay) + ax)
      inside = !inside;
  }
  return inside;
}

function inPolygon(point: Position, polygon: Position[][]): boolean {
  return (
    !!polygon.length &&
    inRing(point, polygon[0]) &&
    !polygon.slice(1).some((hole) => inRing(point, hole))
  );
}

export function countryAtPoint(
  countries: Countries,
  lat: number,
  lon: number,
  preferred = "",
): string | null {
  const point: Position = [((((lon + 180) % 360) + 360) % 360) - 180, lat];
  function contains(feature: CountryFeature) {
    const geometry = feature.geometry;
    return geometry.type === "Polygon"
      ? inPolygon(point, geometry.coordinates)
      : geometry.type === "MultiPolygon" &&
          geometry.coordinates.some((polygon) => inPolygon(point, polygon));
  }
  const current = countries.features.find(
    (feature) => feature.properties.iso_a2 === preferred,
  );
  if (current && contains(current)) return preferred;
  return (
    countries.features.find(
      (feature) => feature.properties.iso_a2 && contains(feature),
    )?.properties.iso_a2 || null
  );
}
