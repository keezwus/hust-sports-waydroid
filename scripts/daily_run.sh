#!/bin/bash
# Daily run entry: session check -> adb preflight -> run_guard -> always notify on failure.
set -u
LOG="$HOME/tiyu/logs/daily_$(date +%Y%m%d_%H%M).log"
mkdir -p "$HOME/tiyu/logs"

# a previous run may have left a root-owned 0600 log; move it aside so we can write
if [ -e "$LOG" ] && [ ! -w "$LOG" ]; then
  mv "$LOG" "$LOG.old" 2>/dev/null || true
fi
umask 022
exec >>"$LOG" 2>&1
chmod 644 "$LOG" 2>/dev/null || true
echo "=== $(date '+%F %T') daily run start ==="

export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
[ -f "$HOME/.config/tiyu/notify.env" ] && . "$HOME/.config/tiyu/notify.env"

SERIAL="${ADB_SERIAL:-192.168.240.112:5555}"
TARGET="${QQ_TARGET:?set QQ_TARGET in ~/.config/tiyu/notify.env}"
HERMES="${HERMES_BIN:-$HOME/.local/bin/hermes}"

notify() {
  local msg="$1"
  echo "!! notify: $msg"
  if "$HERMES" send --to "$TARGET" --subject "[华中大体育] 自动跑未完成" "$msg" >>"$LOG" 2>&1; then
    echo "notify: hermes ok"
  else
    echo "notify: hermes failed"
    python3 "$HOME/tiyu/qq_send_text.py" "$msg" "$TARGET" >>"$LOG" 2>&1 && echo "notify: qq ok"
  fi
}

if ! waydroid status 2>/dev/null | grep -q "Session:.*RUNNING"; then
  echo "session not running, starting"
  setsid nohup waydroid session start >/tmp/daily_session.log 2>&1 < /dev/null &
  sleep 20
fi

echo "== adb preflight =="
adb kill-server >>"$LOG" 2>&1
adb start-server >>"$LOG" 2>&1
echo "connect: $(adb connect "$SERIAL" 2>&1)"
if ! timeout 30 adb -s "$SERIAL" wait-for-device >>"$LOG" 2>&1; then
  notify "adb 设备未就绪（wait-for-device 超时）"
  exit 1
fi

boot=""
for i in $(seq 1 60); do
  boot=$(adb -s "$SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')
  [ "$boot" = "1" ] && break
  sleep 2
done
echo "boot_completed=${boot:-?}"
if [ "$boot" != "1" ]; then
  notify "Android 未启动完成（boot_completed=${boot:-?}）"
  exit 1
fi

if ! adb -s "$SERIAL" shell true >/dev/null 2>&1; then
  echo "adb devices: $(adb devices 2>&1 | tr '\n' ' ')"
  notify "adb shell 不可用"
  exit 1
fi

cd "$HOME/tiyu"
python3 run_guard.py
rc=$?
if [ "$rc" -ne 0 ]; then
  notify "本次自动跑未完成（rc=$rc），可能登录失效、界面异常或 Waydroid 异常，请检查。"
fi
echo "=== $(date '+%F %T') daily run done rc=$rc ==="
exit "$rc"
