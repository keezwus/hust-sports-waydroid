#!/usr/bin/env python3
"""route_feeder.py —— Waydroid mock GPS 轨迹喂食器。

每秒推一个位置点，让只等 ~1s 的应用也能拿到定位；并沿路线移动，
让 App 看到的轨迹像真人跑步。

与旧版的区别：**改用 adb 而不是 `waydroid shell`**。
  - `waydroid shell` 需要 root + 容器 session 正常，重启后容易哑掉；
  - adb 通道（192.168.240.112:5555）稳定，且 adb shell 以 shell 用户身份运行，
    uiautomator 也不会因为 root 身份崩掉。
  - Android 13 的 LocationShellCommand 只认 --location/--accuracy/--time，
    没有 --velocity/--bearing，加了会整条命令报 Unknown option。

用法:
  route_feeder.py                          # 绕中操场跑道，2.2 m/s
  route_feeder.py --route route.json       # 指定折线
  route_feeder.py --laps 3                 # 绕圈几圈（配合 --route 用）
  route_feeder.py --speed 3.0 --radius 120
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys
import time

# 中心操场（OSM way/98865266）——华中科技大学主校区
CENTER = (30.5120376, 114.4135772)
M_PER_DEG_LAT = 111320.0

ADB_SERIAL = os.environ.get("WAYDROID_ADB", "192.168.240.112:5555")


def adb(args, timeout=8):
    """执行一条 adb 命令，返回 stdout（失败返回 ""）。"""
    try:
        p = subprocess.run(["adb", "-s", ADB_SERIAL] + args,
                           capture_output=True, text=True, timeout=timeout)
        return p.stdout
    except Exception:
        return ""


def adb_connect():
    try:
        subprocess.run(["adb", "connect", ADB_SERIAL],
                       capture_output=True, text=True, timeout=15)
    except Exception:
        pass


def shell(cmd, timeout=8):
    return adb(["shell", cmd], timeout=timeout)


def ensure_provider():
    """确保 mock gps provider 存在并已启用（容器重启后 provider 会丢）。"""
    shell("settings put secure location_mode 3")
    shell("cmd appops set android android:mock_location allow")
    out = shell("dumpsys location", timeout=12)
    if "gps provider" not in out:
        shell("cmd location providers add-test-provider gps "
              "--supportsAltitude --supportsSpeed --supportsBearing")
    shell("cmd location providers set-test-provider-enabled gps true")


def push(lat, lon, speed, bearing):
    """推一个位置点。"""
    acc = random.uniform(4.0, 12.0)
    shell("cmd location providers set-test-provider-location gps "
          "--location %.6f,%.6f --accuracy %.1f" % (lat, lon, acc))


def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing(lat1, lon1, lat2, lon2):
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2))
         - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.cos(math.radians(lon2 - lon1)))
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def circle_point(t, radius, speed):
    ang = (t * speed / radius) % (2 * math.pi)
    dlat = (radius * math.cos(ang)) / M_PER_DEG_LAT
    dlon = (radius * math.sin(ang)) / (M_PER_DEG_LAT * math.cos(math.radians(CENTER[0])))
    brg = (math.degrees(ang) + 90.0) % 360.0
    return CENTER[0] + dlat, CENTER[1] + dlon, brg


def route_point(route, dist):
    """沿折线走 dist 米，返回 lat, lon, bearing。"""
    total = 0.0
    for i in range(len(route) - 1):
        a, b = route[i], route[i + 1]
        seg = haversine(a[0], a[1], b[0], b[1])
        if dist <= total + seg or i == len(route) - 2:
            f = 0.0 if seg == 0 else max(0.0, min(1.0, (dist - total) / seg))
            return (a[0] + (b[0] - a[0]) * f,
                    a[1] + (b[1] - a[1]) * f,
                    bearing(a[0], a[1], b[0], b[1]))
        total += seg
    return route[-1][0], route[-1][1], 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", help="json: [[lat,lon],...]")
    ap.add_argument("--speed", type=float, default=2.2, help="m/s（默认约 8 km/h）")
    ap.add_argument("--radius", type=float, default=120.0, help="圆形半径(米)")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--laps", type=int, default=0, help="跑几圈，0=一直跑")
    ap.add_argument("--duration", type=float, default=0, help="跑多少秒后退出，0=不限")
    ap.add_argument("--distance", type=float, default=0, help="跑多少米后退出，0=不限")
    ap.add_argument("--jitter", type=float, default=0.0, help="坐标随机抖动(米)，模拟真实 GPS")
    args = ap.parse_args()

    route = None
    if args.route:
        with open(args.route, encoding="utf-8") as f:
            route = json.load(f)

    adb_connect()
    ensure_provider()
    print("feeder started: %s speed=%.2fm/s serial=%s" %
          ("route" if route else "circle r=%dm" % args.radius, args.speed, ADB_SERIAL),
          flush=True)

    t = 0.0
    dist = 0.0
    ticks = 0
    started = time.time()
    route_len = 0.0
    if route:
        for i in range(len(route) - 1):
            route_len += haversine(route[i][0], route[i][1],
                                   route[i + 1][0], route[i + 1][1])

    while True:
        if route:
            if args.distance and dist >= args.distance:
                print("feeder done: distance reached %.0f m" % dist, flush=True)
                break
            if route_len > 0 and dist > route_len:
                if args.laps == 0:
                    dist = 0.0                      # 无限循环
                else:
                    laps_done = dist // route_len
                    if laps_done >= args.laps:
                        print("feeder done: %d laps, %.0f m" % (args.laps, dist), flush=True)
                        break
                    dist = 0.0
            lat, lon, brg = route_point(route, dist)
            v = args.speed * (1.0 + 0.08 * math.sin(t / 45.0))
            dist += v * args.interval
            t += args.interval
        else:
            lat, lon, brg = circle_point(t, args.radius, args.speed)
            t += args.interval

        if args.jitter:
            lat += random.uniform(-args.jitter, args.jitter) / 111320.0
            lon += random.uniform(-args.jitter, args.jitter) / (111320.0 * math.cos(math.radians(lat)))
        push(lat, lon, args.speed, brg)
        ticks += 1
        if ticks % 15 == 0:
            ensure_provider()          # 容器重启后 mock provider 会丢，自愈
        if args.duration and (time.time() - started) > args.duration:
            print("feeder done: duration reached", flush=True)
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
