#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISPLAY="${DISPLAY:-:99}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
BROWSER_PROFILE="${BROWSER_PROFILE:-$ROOT/runtime/browser_profile}"
START_URL="${1:-about:blank}"
LOG_DIR="$ROOT/logs/linux"

mkdir -p "$BROWSER_PROFILE" "$LOG_DIR"

if ! pgrep -f "Xvfb $DISPLAY" >/dev/null 2>&1; then
  nohup Xvfb "$DISPLAY" -screen 0 1920x1080x24 -nolisten tcp >"$LOG_DIR/xvfb.log" 2>&1 &
  sleep 1
fi

if ! DISPLAY="$DISPLAY" pgrep -f "fluxbox" >/dev/null 2>&1; then
  nohup env DISPLAY="$DISPLAY" fluxbox >"$LOG_DIR/fluxbox.log" 2>&1 &
fi

if ! pgrep -f "x11vnc.*$VNC_PORT" >/dev/null 2>&1; then
  if [[ -n "${VNC_PASSWORD:-}" ]]; then
    PASSFILE="$ROOT/runtime/x11vnc.pass"
    x11vnc -storepasswd "$VNC_PASSWORD" "$PASSFILE" >/dev/null
    nohup x11vnc -display "$DISPLAY" -rfbport "$VNC_PORT" -rfbauth "$PASSFILE" -forever -shared >"$LOG_DIR/x11vnc.log" 2>&1 &
  else
    nohup x11vnc -display "$DISPLAY" -rfbport "$VNC_PORT" -forever -shared -nopw >"$LOG_DIR/x11vnc.log" 2>&1 &
  fi
fi

if ! pgrep -f "novnc.*$NOVNC_PORT|websockify.*$NOVNC_PORT" >/dev/null 2>&1; then
  if command -v novnc_proxy >/dev/null 2>&1; then
    nohup novnc_proxy --listen "$NOVNC_PORT" --vnc "localhost:$VNC_PORT" >"$LOG_DIR/novnc.log" 2>&1 &
  elif [[ -x /usr/share/novnc/utils/novnc_proxy ]]; then
    nohup /usr/share/novnc/utils/novnc_proxy --listen "$NOVNC_PORT" --vnc "localhost:$VNC_PORT" >"$LOG_DIR/novnc.log" 2>&1 &
  else
    nohup websockify --web=/usr/share/novnc/ "$NOVNC_PORT" "localhost:$VNC_PORT" >"$LOG_DIR/novnc.log" 2>&1 &
  fi
fi

if ! curl -fsS "http://127.0.0.1:9222/json/version" >/dev/null 2>&1; then
  CHROME="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium || command -v chromium-browser)"
  nohup env DISPLAY="$DISPLAY" "$CHROME" \
    --remote-debugging-address=127.0.0.1 \
    --remote-debugging-port=9222 \
    --user-data-dir="$BROWSER_PROFILE" \
    --no-first-run \
    --no-default-browser-check \
    --disable-dev-shm-usage \
    "$START_URL" >"$LOG_DIR/chrome.log" 2>&1 &
fi

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:9222/json/version" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done

echo "Chrome CDP did not become ready on 127.0.0.1:9222. Check $LOG_DIR/chrome.log" >&2
exit 1
