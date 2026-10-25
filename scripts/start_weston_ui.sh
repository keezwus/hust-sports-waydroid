#!/bin/bash
# Persistent Weston (X11) + Waydroid UI for the visible desktop.
set -u
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0

pkill -f "weston --backend=x11-backend.so" 2>/dev/null
sleep 1
# detach any stale session bound to the old wayland socket
waydroid session stop >/dev/null 2>&1
sleep 2
weston --backend=x11-backend.so --socket=wayland-0 --width=1024 --height=768 --idle-time=0 &
WESTON_PID=$!
sleep 3

# session + show-full-ui + keepalive
bash $HOME/tiyu/cage-waydroid.sh &
CHILD=$!

# if weston dies, exit so systemd restarts the unit
wait "$WESTON_PID"
kill "$CHILD" 2>/dev/null
exit 0
