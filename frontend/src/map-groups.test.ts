import { describe, expect, it } from "vitest";
import { clusterGroups } from "./map-groups";
import type { MapGroup } from "./types";

describe("map clusters", () => {
  it("counts an opportunity once when it has two placements in a country", () => {
    const base: MapGroup = {
      id: "a",
      key: "DE:a",
      name: "A",
      country: "DE",
      lat: 52,
      lon: 13,
      precision: "city",
      source_url: "https://ror.org/example",
      scholarship_ids: ["award"],
      confirmed_scholarship_ids: ["award"],
      confirmed_count: 1,
      unverified_count: 0,
    };
    const result = clusterGroups(
      [base, { ...base, id: "b", key: "DE:b", lat: 50 }],
      3,
    );
    expect(result).toHaveLength(1);
    expect(result[0].scholarship_ids).toEqual(["award"]);
    expect(result[0].confirmed_count).toBe(1);
    expect(
      clusterGroups([base, { ...base, id: "b", key: "DE:b" }], 7),
    ).toHaveLength(2);
  });

  it("combines nearby country pins at world scale without duplicating scholarships", () => {
    const point = (country: string, lat: number, lon: number): MapGroup => ({
      id: country,
      key: country,
      name: country,
      country,
      lat,
      lon,
      precision: "country",
      source_url: "https://example.org",
      scholarship_ids: ["shared"],
      confirmed_scholarship_ids: ["shared"],
      confirmed_count: 1,
      unverified_count: 0,
    });
    const result = clusterGroups(
      [point("DE", 51, 10), point("NL", 52, 5), point("US", 38, -97)],
      3,
    );
    expect(result).toHaveLength(2);
    const regional = result.find(
      (group) => group.cluster_countries?.length === 2,
    );
    expect(regional?.cluster_countries?.sort()).toEqual(["DE", "NL"]);
    expect(regional?.scholarship_ids).toEqual(["shared"]);
  });
});
