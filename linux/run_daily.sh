#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE="${DATE:-$(date +%Y%m%d)}"
DATE_ISO="${DATE_ISO:-$(date +%Y-%m-%d)}"
BATCH_TIMEOUT_SECONDS="${BATCH_TIMEOUT_SECONDS:-600}"
RATE_LIMIT_COOLDOWN_SECONDS="${RATE_LIMIT_COOLDOWN_SECONDS:-300}"
SKIP_DASHBOARD="${SKIP_DASHBOARD:-0}"
SKIP_CLOUDFLARE_UPLOAD="${SKIP_CLOUDFLARE_UPLOAD:-0}"
OUTPUT="$ROOT/output"
BATCH_DIR="$OUTPUT/daily_all_$DATE"
PYTHON="$ROOT/.venv/bin/python"

PRODUCTS=(ugphone ldcloud redfinger vsphone)
COUNTRIES=(TH VN PH BR TR MY ID HK TW KR US MX SG JP PL DE GB IN IT FR)
COUNTRY_CHUNKS=("TH,VN,PH,BR" "TR,MY,ID,HK" "TW,KR,US,MX" "SG,JP,PL,DE" "GB,IN,IT,FR")

mkdir -p "$OUTPUT" "$BATCH_DIR" "$ROOT/logs" "$ROOT/screenshots"

log() {
  local line
  line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$line" | tee -a "$BATCH_DIR/daily_all.log"
}

if [[ ! -x "$PYTHON" ]]; then
  echo "Python environment not found. Run linux/install_ubuntu.sh first." >&2
  exit 1
fi

log "Daily Linux scrape start date=$DATE products=${PRODUCTS[*]}"
"$ROOT/linux/start_browser_vnc.sh" "about:blank"

batch_no=0
for product in "${PRODUCTS[@]}"; do
  for chunk_csv in "${COUNTRY_CHUNKS[@]}"; do
    batch_no=$((batch_no + 1))
    chunk_name="${chunk_csv//,/-}"
    name="$(printf '%02d_%s_%s' "$batch_no" "$product" "$chunk_name")"
    stdout="$BATCH_DIR/run_$name.out.log"
    stderr="$BATCH_DIR/run_$name.err.log"
    rm -f "$OUTPUT/sensor_tower_multi_product_multi_country_$DATE.csv" "$OUTPUT/sensor_tower_multi_product_summary_$DATE.csv"
    log "Batch start: $name product=$product countries=$chunk_csv"
    set +e
    ST_PRODUCTS="$product" ST_COUNTRIES="$chunk_csv" timeout "$BATCH_TIMEOUT_SECONDS" "$PYTHON" "$ROOT/sensor_tower_focus_fast.py" >"$stdout" 2>"$stderr"
    code=$?
    set -e
    [[ -f "$OUTPUT/sensor_tower_multi_product_multi_country_$DATE.csv" ]] && cp "$OUTPUT/sensor_tower_multi_product_multi_country_$DATE.csv" "$BATCH_DIR/detail_$name.csv"
    [[ -f "$OUTPUT/sensor_tower_multi_product_summary_$DATE.csv" ]] && cp "$OUTPUT/sensor_tower_multi_product_summary_$DATE.csv" "$BATCH_DIR/summary_$name.csv"
    log "Batch end: $name exit=$code"
    if [[ "$code" -eq 124 ]]; then
      log "Batch timeout: $name; cooling down before next batch"
      sleep 30
    elif [[ "$code" -ne 0 ]]; then
      log "Batch failed: $name exit=$code"
    fi
  done
done

"$PYTHON" - "$ROOT" "$DATE" "$DATE_ISO" <<'PY'
import csv
import glob
import os
import sys

root, date_raw, date_iso = sys.argv[1:4]
output = os.path.join(root, "output")
batch_dir = os.path.join(output, f"daily_all_{date_raw}")
products = ["ugphone", "ldcloud", "redfinger", "vsphone"]
countries = ["TH", "VN", "PH", "BR", "TR", "MY", "ID", "HK", "TW", "KR", "US", "MX", "SG", "JP", "PL", "DE", "GB", "IN", "IT", "FR"]
status_score = {"SUCCESS": 5, "PARTIAL_SUCCESS": 4, "RANK_CAPTURE_FAILED": 2, "RATE_LIMITED": 1, "PAGE_LOAD_FAILED": 1}
fields = [
    "brand", "package", "country", "tooltip_date", "app_name", "revenue_rank_tools", "revenue_rank_apps",
    "top_free_rank_tools", "source_url", "crawl_time", "status", "status_detail", "error_message",
    "candidate_tooltip_dates", "candidate_count", "selected_tooltip_date", "page_loaded_screenshot",
    "final_hover_screenshot", "retry_count", "screenshot_path", "selected_candidate_index",
    "selected_candidate_raw_text", "raw_tooltip_text", "selected_candidate_x", "selected_candidate_y",
    "all_candidates_json", "batch_file",
]

def score(row):
    rank = str(row.get("revenue_rank_tools", "")).strip()
    rank_score = 1000000 - int(rank) if rank.isdigit() else 0
    return status_score.get(row.get("status", ""), 0) * 1000000000000 + rank_score

best = {}
for path in sorted(glob.glob(os.path.join(batch_dir, "detail_*.csv"))):
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            brand = row.get("brand", "")
            country = row.get("country", "")
            if not brand or not country:
                continue
            row["batch_file"] = os.path.basename(path)
            key = (brand, country)
            if key not in best or score(row) > score(best[key]):
                best[key] = row

merged = []
for brand in products:
    for country in countries:
        row = dict(best.get((brand, country), {}))
        if not row:
            row = {
                "brand": brand,
                "package": "",
                "country": country,
                "tooltip_date": "",
                "app_name": "",
                "revenue_rank_tools": "",
                "source_url": "",
                "crawl_time": date_iso,
                "status": "MISSING",
                "status_detail": "not found in batch outputs",
            }
        row["revenue_rank_apps"] = ""
        row["top_free_rank_tools"] = ""
        merged.append({field: row.get(field, "") for field in fields})

detail_out = os.path.join(output, f"sensor_tower_multi_product_multi_country_{date_raw}.csv")
summary_out = os.path.join(output, f"sensor_tower_multi_product_summary_{date_raw}.csv")
with open(detail_out, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(merged)
with open(summary_out, "w", newline="", encoding="utf-8") as f:
    summary_fields = ["brand", "country", "tooltip_date", "revenue_rank_tools", "status", "status_detail", "batch_file"]
    writer = csv.DictWriter(f, fieldnames=summary_fields)
    writer.writeheader()
    writer.writerows([{key: row.get(key, "") for key in summary_fields} for row in merged])
print(f"[OK] merged rows={len(merged)} detail={detail_out}")
PY

if [[ "$SKIP_DASHBOARD" != "1" ]]; then
  "$PYTHON" "$ROOT/dashboard_builder.py" || log "Dashboard build failed"
fi

if [[ "$SKIP_CLOUDFLARE_UPLOAD" != "1" ]]; then
  if [[ -n "${CLOUDFLARE_WORKER_URL:-}" && -n "${CLOUDFLARE_INGEST_TOKEN:-}" ]]; then
    log "Cloudflare upload start"
    "$ROOT/linux/upload_daily_to_cloudflare.sh" "$DATE" | tee -a "$BATCH_DIR/daily_all.log"
    log "Cloudflare upload finished"
  else
    log "Cloudflare upload skipped: CLOUDFLARE_WORKER_URL and CLOUDFLARE_INGEST_TOKEN are not configured"
  fi
fi

log "Daily Linux scrape finished"
