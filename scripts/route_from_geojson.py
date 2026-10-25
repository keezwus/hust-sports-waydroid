#!/usr/bin/env python3
"""Convert a hand-drawn GeoJSON LineString into route_track.json.

Usage:
  python route_from_geojson.py drawn.geojson [out.json] [--spacing 1.0]

Draw the line on https://geojson.io (or Google My Maps / 高德足迹), export
GeoJSON, then run this. Coordinates are [lon, lat] in GeoJSON; we output
[[lat, lon], ...] resampled every `spacing` metres so route_feeder can
interpolate smoothly.
"""
import json
import math
import sys

M_PER_DEG_LAT = 111320.0


def haversine(a, b):
    r = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def extract_line(obj):
    if obj.get("type") == "FeatureCollection":
        for f in obj.get("features", []):
            g = f.get("geometry") or {}
            if g.get("type") == "LineString":
                return g["coordinates"]
    if obj.get("type") == "Feature":
        g = obj.get("geometry") or {}
        if g.get("type") == "LineString":
            return g["coordinates"]
    if obj.get("type") == "LineString":
        return obj["coordinates"]
    raise SystemExit("no LineString found")


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "route_drawn.json"
    spacing = 1.0
    if "--spacing" in sys.argv:
        spacing = float(sys.argv[sys.argv.index("--spacing") + 1])

    obj = json.load(open(src, encoding="utf-8"))
    coords = [(c[1], c[0]) for c in extract_line(obj)]  # lat, lon

    pts = []
    for i in range(len(coords) - 1):
        a, b = coords[i], coords[i + 1]
        d = haversine(a, b)
        n = max(1, int(d / spacing))
        for k in range(n):
            t = k / n
            pts.append([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t])
    pts.append(coords[-1])

    total = sum(haversine(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    json.dump(pts, open(out, "w"), ensure_ascii=False)
    print("points", len(pts), "distance %.1f m ->" % total, out)


if __name__ == "__main__":
    main()
