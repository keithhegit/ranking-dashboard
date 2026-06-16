#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE="${DATE:-$(date +%Y%m%d)}"
DATE_ISO="${DATE_ISO:-$(date +%Y-%m-%d)}"
SKIP_DASHBOARD="${SKIP_DASHBOARD:-0}"
SKIP_CLOUDFLARE_UPLOAD="${SKIP_CLOUDFLARE_UPLOAD:-0}"
COLLECT_ONLY="${COLLECT_ONLY:-0}"
UPLOAD_ONLY="${UPLOAD_ONLY:-0}"
OUTPUT="$ROOT/output"
BATCH_DIR="$OUTPUT/daily_queue_$DATE"
PYTHON="$ROOT/.venv/bin/python"
LOCK_FILE="${LOCK_FILE:-/tmp/competitor-monitor-sensortower.lock}"

mkdir -p "$OUTPUT" "$BATCH_DIR" "$ROOT/logs" "$ROOT/screenshots"

log() {
  local line
  line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$line" | tee -a "$BATCH_DIR/daily_all.log"
}

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "Another Sensor Tower collection is already running; exiting."
  exit 75
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "Python environment not found. Run linux/install_ubuntu.sh first." >&2
  exit 1
fi

if [[ "$UPLOAD_ONLY" != "1" ]]; then
  log "Daily Linux scrape start date=$DATE"
  "$ROOT/linux/start_browser_vnc.sh" "about:blank"
  QUEUE_RESULT="$(DATE="$DATE" DATE_ISO="$DATE_ISO" "$PYTHON" "$ROOT/linux/run_daily_queue.py" | tee -a "$BATCH_DIR/daily_all.log")"
  if echo "$QUEUE_RESULT" | grep -Eq '"(stopped_for_rate_limit|cooldown_active)": 1'; then
    SKIP_CLOUDFLARE_UPLOAD=1
    log "Cloudflare upload disabled for this run because Sensor Tower collection is rate-limited or cooling down"
  fi
else
  log "Upload-only mode: skipping Sensor Tower collection"
fi

if [[ "$SKIP_DASHBOARD" != "1" ]]; then
  "$PYTHON" "$ROOT/dashboard_builder.py" || log "Dashboard build failed"
fi

if [[ "$COLLECT_ONLY" != "1" && "$SKIP_CLOUDFLARE_UPLOAD" != "1" ]]; then
  if [[ -n "${CLOUDFLARE_WORKER_URL:-}" && -n "${CLOUDFLARE_INGEST_TOKEN:-}" ]]; then
    log "Cloudflare upload start"
    "$ROOT/linux/upload_daily_to_cloudflare.sh" "$DATE" | tee -a "$BATCH_DIR/daily_all.log"
    log "Cloudflare upload finished"
  else
    log "Cloudflare upload skipped: CLOUDFLARE_WORKER_URL and CLOUDFLARE_INGEST_TOKEN are not configured"
  fi
fi

log "Daily Linux scrape finished"
