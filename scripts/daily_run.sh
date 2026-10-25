#!/bin/bash
set -e
LOG=$HOME/tiyu/logs/daily_$(date +%Y%m%d_%H%M).log
mkdir -p $HOME/tiyu/logs
exec >>"$LOG" 2>&1
echo "=== $(date '+%F %T') daily run start ==="

export DISPLAY=:0
export XAUTHORITY="$HOME/.Xauthority"
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

if ! waydroid status 2>/dev/null | grep -q "Session:.*RUNNING"; then
  echo "session not running, starting"
  setsid nohup waydroid session start >/tmp/daily_session.log 2>&1 < /dev/null &
  sleep 15
fi

adb connect 192.168.240.112:5555 >/dev/null 2>&1
sleep 2

cd $HOME/tiyu
python3 run_guard.py
rc=$?
if [ "$rc" -ne 0 ]; then
  ${HERMES_BIN:-$HOME/.local/bin/hermes} send --to "${QQ_TARGET:?set QQ_TARGET}" \
    --subject "[华中大体育] 自动跑未完成" \
    "本次自动跑未完成（rc=$rc），可能登录失效或 Waydroid 异常，请检查。"
fi
echo "=== $(date '+%F %T') daily run done rc=$rc ==="
