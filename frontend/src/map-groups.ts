import type { MapGroup } from "./types";
import L from "leaflet";

export function clusterGroups(groups: MapGroup[], zoom: number): MapGroup[] {
  if (zoom >= 5) return groups;
  const buckets = new Map<string, MapGroup[]>();
  for (const group of groups) {
    const bucket = buckets.get(group.country) || [];
    bucket.push(group);
    buckets.set(group.country, bucket);
  }
  const countries: MapGroup[] = [...buckets.entries()].map(
    ([country, points]) => {
      const ids = [
        ...new Set(points.flatMap((point) => point.scholarship_ids)),
      ];
      const confirmed = [
        ...new Set(points.flatMap((point) => point.confirmed_scholarship_ids)),
      ];
      return {
        ...points[0],
        id: `cluster-${country}`,
        key: `cluster-${country}`,
        country,
        lat: points.reduce((sum, point) => sum + point.lat, 0) / points.length,
        lon: points.reduce((sum, point) => sum + point.lon, 0) / points.length,
        precision: "country",
        scholarship_ids: ids,
        confirmed_scholarship_ids: confirmed,
        confirmed_count: confirmed.length,
        unverified_count: ids.length - confirmed.length,
      };
    },
  );
  if (zoom >= 4) return countries;
  const regions: MapGroup[][] = [];
  for (const point of countries) {
    const pixel = L.CRS.EPSG3857.latLngToPoint(
      L.latLng(point.lat, point.lon),
      zoom,
    );
    const nearby = regions.find((region) => {
      const center = L.CRS.EPSG3857.latLngToPoint(
        L.latLng(
          region.reduce((sum, p) => sum + p.lat, 0) / region.length,
          region.reduce((sum, p) => sum + p.lon, 0) / region.length,
        ),
        zoom,
      );
      return center.distanceTo(pixel) < 65;
    });
    if (nearby) nearby.push(point);
    else regions.push([point]);
  }
  return regions.map((points) => {
    if (points.length === 1) return points[0];
    const codes = points.map((p) => p.country).sort();
    const ids = [...new Set(points.flatMap((p) => p.scholarship_ids))];
    const confirmed = [
      ...new Set(points.flatMap((p) => p.confirmed_scholarship_ids)),
    ];
    return {
      ...points[0],
      id: `region-${codes.join("-")}`,
      key: `region-${codes.join("-")}`,
      lat: points.reduce((sum, p) => sum + p.lat, 0) / points.length,
      lon: points.reduce((sum, p) => sum + p.lon, 0) / points.length,
      cluster_countries: codes,
      cluster_bounds: [
        [
          Math.min(...points.map((p) => p.lat)),
          Math.min(...points.map((p) => p.lon)),
        ],
        [
          Math.max(...points.map((p) => p.lat)),
          Math.max(...points.map((p) => p.lon)),
        ],
      ] as [[number, number], [number, number]],
      scholarship_ids: ids,
      confirmed_scholarship_ids: confirmed,
      confirmed_count: confirmed.length,
      unverified_count: ids.length - confirmed.length,
    };
  });
}
