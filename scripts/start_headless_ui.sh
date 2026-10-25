#!/bin/bash
# Headless Weston for Waydroid: no visible desktop window, adb automation only.
set -u
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0

pkill -f "weston --backend=" 2>/dev/null
sleep 1
waydroid session stop >/dev/null 2>&1
sleep 2

weston --backend=headless-backend.so --socket=wayland-0 --width=1024 --height=736 --idle-time=0 &
WESTON_PID=$!
sleep 3

setsid nohup waydroid session start >/tmp/headless_session.log 2>&1 < /dev/null &
wait "$WESTON_PID"
