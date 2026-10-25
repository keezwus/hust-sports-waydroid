#!/usr/bin/env python3
"""Generate a realistic 400 m stadium route around the HUST middle track.

Two straights + two semicircles, per-lap lane drift, slow sway and GPS noise,
so the uploaded trace is not a perfect ellipse.
"""
import json
import math
import random

CENTER = (30.511922, 114.413853)
M_PER_DEG_LAT = 111320.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(CENTER[0]))

L = 90.0      # straight length (m), north-south
R = 35.0      # semicircle radius (m)
LAPS = 5.15
STEP = 1.0    # point spacing (m)

random.seed(20261024)


def to_latlon(x, y):
    """x = east (m), y = north (m) relative to CENTER."""
    return [CENTER[0] + y / M_PER_DEG_LAT, CENTER[1] + x / M_PER_DEG_LON]


def stadium_point(s):
    """s in [0, 400): position on the stadium, starting at south end of west straight."""
    half = L / 2.0
    arc = math.pi * R
    if s < L:                      # west straight, south -> north
        return (-R, -half + s)
    s -= L
    if s < arc:                    # north semicircle, west -> east
        t = s / R
        return (-R * math.cos(t), half + R * math.sin(t))
    s -= arc
    if s < L:                      # east straight, north -> south
        return (R, half - s)
    s -= L
    t = s / R                      # south semicircle, east -> west
    return (R * math.cos(t), -half - R * math.sin(t))


pts = []
total = LAPS * 400.0
s = 0.0
while s < total:
    lap = int(s // 400)
    x, y = stadium_point(s % 400)
    # lane drift: slowly move between inner and outer lane over each lap
    drift = 1.4 * math.sin(2 * math.pi * (s % 400) / 400 + lap * 0.7)
    # slow body sway
    sway = 0.35 * math.sin(s / 37.0)
    # GPS noise
    nx = random.gauss(0, 0.55)
    ny = random.gauss(0, 0.55)
    r = math.hypot(x, y)
    if r > 1e-6:
        ux, uy = x / r, y / r
    else:
        ux, uy = 0.0, 0.0
    x2 = x + ux * (drift + sway) + nx
    y2 = y + uy * (drift + sway) + ny
    pts.append(to_latlon(x2, y2))
    s += STEP

# close the loop smoothly
pts.append(pts[0])
json.dump(pts, open(r"C:\Users\ASUS\Desktop\tmp\tiyu\02-脚本\route_stadium.json", "w"))
print("points", len(pts), "distance", total)
