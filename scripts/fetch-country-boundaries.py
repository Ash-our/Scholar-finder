"""Natural Earth v5.1.2, public-domain reference geometry, bundled for the map."""
from hashlib import sha256
import json
from pathlib import Path

import httpx
import pycountry

ROOT = Path(__file__).resolve().parents[1]
URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_admin_0_countries.geojson"


def rounded(value):
    if isinstance(value, list):
        return [rounded(part) for part in value]
    return round(value, 4) if isinstance(value, float) else value


def simplify_ring(points,tolerance=0.025):
    def distance(p,a,b):
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
        return (p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2
    def dp(values):
        if len(values)<=2:return values
        index=max(range(1,len(values)-1),key=lambda i:distance(values[i],values[0],values[-1]))
        if distance(values[index],values[0],values[-1])<=tolerance*tolerance:return [values[0],values[-1]]
        return dp(values[:index+1])[:-1]+dp(values[index:])
    simplified=dp(points)
    return simplified if len(simplified)>=4 else points


def simplified_coordinates(geometry):
    if geometry["type"]=="Polygon":return [simplify_ring(ring) for ring in geometry["coordinates"]]
    return [[simplify_ring(ring) for ring in polygon] for polygon in geometry["coordinates"]]


def main():
    response = httpx.get(URL, timeout=60, follow_redirects=True)
    response.raise_for_status()
    raw = response.json()
    features = []
    for feature in raw["features"]:
        props = feature["properties"]
        code = next((props.get(key) for key in ["ISO_A2_EH", "ISO_A2"]
                     if pycountry.countries.get(alpha_2=str(props.get(key, "")))), None)
        if not code:
            match = pycountry.countries.get(alpha_3=props.get("ADM0_A3", ""))
            code = match.alpha_2 if match else None
        features.append({"type": "Feature", "properties": {"iso_a2": code, "name": props.get("ADMIN", "")},
                         "geometry": {"type": feature["geometry"]["type"], "coordinates": rounded(simplified_coordinates(feature["geometry"]))}})
    destination = ROOT / "frontend" / "public" / "data"
    destination.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"), ensure_ascii=False)
    (destination / "countries.geojson").write_text(payload, encoding="utf8", newline="\n")
    (ROOT / "data" / "country-boundaries-provenance.json").write_text(json.dumps({
        "source_url": URL, "source_sha256": sha256(response.content).hexdigest(),
        "asset_sha256": sha256(payload.encode()).hexdigest(), "features": len(features),
        "license": "Public domain", "terms_url": "https://www.naturalearthdata.com/about/terms-of-use/",
        "note": "Reference boundaries simplified with Douglas-Peucker tolerance0.025 degrees and rounded to4 decimals; not a legal or political boundary authority. Tiny rings retained when simplification would collapse them.",
    }, indent=2) + "\n", encoding="utf8")
    print(f"Saved {len(features)} country/territory reference features, {len(payload.encode())} bytes")


if __name__ == "__main__":
    main()
