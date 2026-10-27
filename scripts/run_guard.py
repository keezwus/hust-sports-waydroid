#!/usr/bin/env python3
"""Guarded fast run: abort immediately if the run does not enter/stay in SelfSportActivity."""
import os, re, subprocess, sys, time, datetime

ADB = ["adb", "-s", os.environ.get("ADB_SERIAL", "192.168.240.112:5555")]
PKG = "net.crigh.hzkjsport"
SPLASH = "net.crigh.cgsport.ui.activity.HzkjSplashActivity"
NODE = re.compile(r"<node[^>]*>")
LOG = os.path.expanduser("~/tiyu/run_guard.log")


def log(*a):
    line = "%s %s" % (datetime.datetime.now().strftime("%H:%M:%S"), " ".join(map(str, a)))
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(args, timeout=40):
    try:
        r = subprocess.run(ADB + args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        log("adb timeout:", args)
        return ""
    if r.returncode != 0 or not (r.stdout or "").strip():
        log("adb rc=%d err=%s args=%s" % (r.returncode, (r.stderr or "").strip()[:200], args))
    return r.stdout or ""


def shell(cmd, timeout=40):
    return sh(["shell", cmd], timeout)


def els():
    shell("uiautomator dump /sdcard/ui.xml", 40)
    xml = shell("cat /sdcard/ui.xml", 40)
    if len(xml) < 80:
        log("uiautomator dump failed len=%d" % len(xml))
    out = []
    for m in NODE.finditer(xml):
        s = m.group(0)
        d = {}
        for k in ("text", "resource-id", "clickable", "bounds"):
            mm = re.search(k + r'="([^"]*)"', s)
            d[k] = mm.group(1) if mm else ""
        out.append(d)
    return out


def center(b):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def find(kw, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        for a in els():
            if kw in " ".join([a["text"], a["resource-id"]]):
                c = center(a["bounds"])
                if c:
                    return a, c
        time.sleep(1)
    return None, None


def tap(c, label):
    log("tap", label, c)
    shell("input tap %d %d" % c)
    time.sleep(1.0)


def top():
    for _ in range(3):
        for l in shell("dumpsys activity activities").splitlines():
            if "topResumedActivity" in l:
                m = re.search(r"u0 (\S+)\}", l)
                return m.group(1).split("/")[-1] if m else "?"
        time.sleep(1.5)
    log("top failed; adb devices:", shell("devices").replace("\n", " "))
    return "?"


def shot(n):
    d = subprocess.run(ADB + ["exec-out", "screencap", "-p"], capture_output=True, timeout=40).stdout
    open("/tmp/%s.png" % n, "wb").write(d)
    log("shot", n, len(d))


LXC = ["sudo", "-n", "lxc-attach", "-P", "/var/lib/waydroid/lxc", "-n", "waydroid", "--"]


def open_sport():
    subprocess.run(LXC + ["am", "start", "-n",
                          "net.crigh.hzkjsport/net.crigh.cgsport.cgactivity.SportActivity"],
                   timeout=30)
    time.sleep(5)


def fresh_app():
    shell("am force-stop " + PKG)
    time.sleep(1)
    shell("am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n %s/%s -f 0x10000000" % (PKG, SPLASH))
    time.sleep(9)


log("== ensure gps ==")
subprocess.run(["python3", "-c",
                "import sys, os; sys.path.insert(0, os.path.expanduser('~/tiyu')); "
                "import route_feeder; route_feeder.ensure_provider()"], timeout=90)

log("== fresh app ==")
fresh_app()
log("top:", top())
# if an abnormal-record dialog is up, save it and restart fresh
b, bc = find("btn_negative", 3)
if b:
    tap(bc, "去保存")
    time.sleep(5)
    fresh_app()

log("== open SportActivity ==")
open_sport()
b, bc = find("btn_negative", 2)
if b:
    tap(bc, "去保存")
    time.sleep(5)
    fresh_app()
    open_sport()
log("top:", top())

for i in range(7):
    shell("input keyevent KEYCODE_DPAD_DOWN")
    time.sleep(0.4)
a, c = find("btn_start", 4)
if not a:
    log("!! no btn_start", top()); shot("g_nobtn"); sys.exit(1)
tap(c, "btn_start")
a, c = find("tv_free_movement", 15)
if not a:
    log("!! no free", top()); shot("g_nofree"); sys.exit(1)
tap(c, "自由运动")
a, c = find("tv_sport_type", 15)
if not a:
    log("!! no type", top()); shot("g_notype"); sys.exit(1)

# GPS first, then enter the run page
subprocess.run(["pkill", "-f", "route_feeder.py"])
time.sleep(1)
subprocess.Popen(["python3", os.path.expanduser("~/tiyu/route_feeder.py"),
                  "--route", os.path.expanduser("~/tiyu/route_hand.json"),
                  "--speed", "4.5", "--distance", "2500", "--jitter", "1.5"],
                 stdout=open("/tmp/feeder_guard.log", "a"), stderr=subprocess.STDOUT,
                 start_new_session=True)
# wait until a fix exists
for i in range(10):
    out = shell("dumpsys location", 10)
    if "last location=Location[gps" in out:
        log("gps fix ready")
        break
    time.sleep(1)

tap(c, "跑步-男生")
time.sleep(3)
if "Detail" in top():
    a, c = find("tv_sport_type", 5)
    if a:
        tap(c, "跑步-男生(2)")
time.sleep(8)
if not top().endswith("SelfSportActivity"):
    log("!! run page did not stay:", top())
    shot("g_abort")
    sys.exit(2)
log("run confirmed, top:", top())

log("sleep 560s @4.5m/s: feeder 2.5km -> app odometer ~2.1km")
time.sleep(560)
shot("g_end")
log("top:", top())

for attempt in (1, 2):
    tap((637, 551), "btn_finish")
    time.sleep(1.0)
    tap((512, 609), "btn_confirm")
    time.sleep(5)
    a, c = find("异常提醒", 1)
    if not a:
        break
    b, bc = find("确定", 2)
    if b:
        tap(bc, "确定")
        time.sleep(1)
    shell("input keyevent KEYCODE_BACK")
    time.sleep(1)

time.sleep(6)
shot("g_result")
for e in els():
    if e["text"]:
        log("  ", repr(e["text"]), e["resource-id"].split("/")[-1])
log("done top:", top())

# ---- notify via Hermes gateway ----
try:
    info = {}
    for e in els():
        rid = e["resource-id"].split("/")[-1]
        if rid in ("totaldistance", "txt_adjudgestatus", "txt_adjudge",
                   "tv_time", "tv_speed", "tv_pace"):
            info[rid] = e["text"]
    msg = "距离 %s km | %s | 时长 %s | 均速 %s | 配速 %s" % (
        info.get("totaldistance", "?"),
        info.get("txt_adjudgestatus", "?") + " " + info.get("txt_adjudge", ""),
        info.get("tv_time", "?"),
        info.get("tv_speed", "?"),
        info.get("tv_pace", "?"),
    )
    target = os.environ.get("QQ_TARGET", "")
    hermes = os.environ.get("HERMES_BIN", os.path.expanduser("~/.local/bin/hermes"))
    if not target:
        log("QQ_TARGET not set, skip notification")
        raise SystemExit(0)
    r = subprocess.run([hermes, "send", "--to", target,
                        "--subject", "[华中大体育] 跑步完成",
                        msg + "\nMEDIA:/tmp/g_result.png"],
                       capture_output=True, text=True, timeout=90)
    log("hermes send rc=%d %s%s" % (r.returncode, (r.stdout or "").strip(),
                                    (r.stderr or "").strip()))
    r2 = subprocess.run(["bash", os.path.expanduser("~/tiyu/notify_run.sh"),
                         target,
                         "/tmp/g_result.png", msg],
                        capture_output=True, text=True, timeout=120)
    log("qq image rc=%d %s%s" % (r2.returncode, (r2.stdout or "").strip(),
                                 (r2.stderr or "").strip()))

    # 本学期评分次数（课外锻炼页顶部，必要时向上滚）
    subprocess.run(["sudo", "-n", "lxc-attach", "-P", "/var/lib/waydroid/lxc",
                    "-n", "waydroid", "--", "am", "start", "-n",
                    "net.crigh.hzkjsport/net.crigh.cgsport.cgactivity.SportActivity"],
                   timeout=30)
    time.sleep(5)
    score = ""
    for _ in range(6):
        cur = els()
        has = any(e["resource-id"].split("/")[-1] in ("tv_value", "tv_under") for e in cur)
        if has:
            for e in cur:
                if e["resource-id"].split("/")[-1] == "tv_value":
                    score = e["text"]
            break
        shell("input swipe 500 250 500 650 700")
        time.sleep(1.5)
    time.sleep(1)
    shot("g_score")
    r3 = subprocess.run(["bash", os.path.expanduser("~/tiyu/notify_run.sh"),
                         target,
                         "/tmp/g_score.png", "本学期评分次数：%s 次" % (score or "?")],
                        capture_output=True, text=True, timeout=120)
    log("qq score rc=%d %s%s" % (r3.returncode, (r3.stdout or "").strip(),
                                  (r3.stderr or "").strip()))
except Exception as e:
    log("hermes notify failed:", e)
