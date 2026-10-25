#!/bin/bash
# Preflight check for the HUST sports autopilot.
# Usage: ~/tiyu/check.sh
set +e
ok=0; bad=0
say() { printf "%-32s %s\n" "$1" "$2"; }
pass() { say "$1" "OK"; ok=$((ok+1)); }
fail() { say "$1" "FAIL"; bad=$((bad+1)); }

TIYU="${TIYU_DIR:-$HOME/tiyu}"
ADB_SERIAL="${ADB_SERIAL:-192.168.240.112:5555}"

if waydroid status 2>/dev/null | grep -q "Session:.*RUNNING"; then
  pass "waydroid session"
else
  fail "waydroid session"
fi

if adb connect "$ADB_SERIAL" >/dev/null 2>&1 && adb -s "$ADB_SERIAL" get-state 2>/dev/null | grep -q device; then
  pass "adb $ADB_SERIAL"
else
  fail "adb $ADB_SERIAL"
fi

if adb -s "$ADB_SERIAL" shell pm list packages 2>/dev/null | grep -q net.crigh.hzkjsport; then
  pass "app installed"
else
  fail "app installed"
fi

token=$(sudo -n cat /data/data/net.crigh.hzkjsport/shared_prefs/HEADER.xml 2>/dev/null | grep -c 'name="TOKEN"')
if [ "${token:-0}" -gt 0 ]; then
  pass "logged in"
else
  fail "logged in"
fi

if adb -s "$ADB_SERIAL" shell dumpsys location 2>/dev/null | grep -q "gps provider"; then
  pass "mock gps provider"
else
  fail "mock gps provider"
fi

if [ -f "$TIYU/route_hand.json" ]; then
  pass "route_hand.json"
else
  fail "route_hand.json"
fi

hhmm=$(date +%H%M)
if [ "$hhmm" -ge 0600 ] && [ "$hhmm" -le 2300 ]; then
  pass "time window"
else
  fail "time window"
fi

echo
echo "passed=$ok failed=$bad"
[ "$bad" -eq 0 ]
