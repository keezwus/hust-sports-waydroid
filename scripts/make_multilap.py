#!/usr/bin/env python3
"""Build a multi-lap route from one hand-drawn lap.

Each lap gets a small lateral drift and GPS noise so the loops don't overlap
exactly. Stops at --distance metres.
"""
import argparse
import json
import math
import random

M_PER_DEG_LAT = 111320.0


def hav(a, b):
    r = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lap_json")
    ap.add_argument("out_json")
    ap.add_argument("--distance", type=float, default=2000.0)
    ap.add_argument("--noise", type=float, default=0.45)
    ap.add_argument("--drift", type=float, default=1.6)
    args = ap.parse_args()
    random.seed(20261024)

    lap = [tuple(p) for p in json.load(open(args.lap_json))]
    if hav(lap[0], lap[-1]) > 5:
        lap.append(lap[0])

    # local normal at each point
    normals = []
    for i in range(len(lap)):
        a = lap[max(0, i - 1)]
        b = lap[min(len(lap) - 1, i + 1)]
        dx = (b[1] - a[1]) * M_PER_DEG_LAT * math.cos(math.radians(a[0]))
        dy = (b[0] - a[0]) * M_PER_DEG_LAT
        L = math.hypot(dx, dy) or 1.0
        normals.append((-dy / L, dx / L))  # left normal (east, north)

    out = []
    total = 0.0
    lap_no = 0
    while total < args.distance:
        drift = args.drift * math.sin(lap_no * 1.7 + 0.4)
        for i, (lat, lon) in enumerate(lap):
            nx, ny = normals[i]
            off = drift + random.gauss(0, args.noise)
            lat2 = lat + ny * off / M_PER_DEG_LAT
            lon2 = lon + nx * off / (M_PER_DEG_LAT * math.cos(math.radians(lat)))
            if out:
                total += hav(out[-1], (lat2, lon2))
            out.append((lat2, lon2))
            if total >= args.distance:
                break
        lap_no += 1

    json.dump([[round(a, 7), round(b, 7)] for a, b in out], open(args.out_json, "w"))
    print("laps %d, points %d, distance %.1f m" % (lap_no, len(out), total))


if __name__ == "__main__":
    main()
