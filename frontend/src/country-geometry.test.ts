import { describe, expect, it } from "vitest";
import { countryAtPoint, type Countries } from "./country-geometry";

const countries: Countries = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { iso_a2: "AA", name: "A" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [0, 0],
            [10, 0],
            [10, 10],
            [0, 10],
            [0, 0],
          ],
          [
            [3, 3],
            [5, 3],
            [5, 5],
            [3, 5],
            [3, 3],
          ],
        ],
      },
    },
    {
      type: "Feature",
      properties: { iso_a2: "BB", name: "B" },
      geometry: {
        type: "MultiPolygon",
        coordinates: [
          [
            [
              [10, 0],
              [20, 0],
              [20, 10],
              [10, 10],
              [10, 0],
            ],
          ],
          [
            [
              [-30, -30],
              [-28, -30],
              [-28, -28],
              [-30, -28],
              [-30, -30],
            ],
          ],
        ],
      },
    },
  ],
};

describe("country background selection", () => {
  it("distinguishes the current country, another country, water and holes", () => {
    expect(countryAtPoint(countries, 2, 2, "AA")).toBe("AA");
    expect(countryAtPoint(countries, 2, 12, "AA")).toBe("BB");
    expect(countryAtPoint(countries, 40, 40, "AA")).toBeNull();
    expect(countryAtPoint(countries, 4, 4, "AA")).toBeNull();
  });
  it("finds islands and keeps the current country on a shared boundary", () => {
    expect(countryAtPoint(countries, -29, -29)).toBe("BB");
    expect(countryAtPoint(countries, 2, 10, "BB")).toBe("BB");
    expect(countryAtPoint(countries, 2, 10, "AA")).toBe("AA");
  });
});
