#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE="${1:-$(date +%Y%m%d)}"
WORKER_URL="${CLOUDFLARE_WORKER_URL:-}"
INGEST_TOKEN="${CLOUDFLARE_INGEST_TOKEN:-}"
CSV_PATH="$ROOT/output/sensor_tower_multi_product_multi_country_$DATE.csv"

if [[ -z "$WORKER_URL" || -z "$INGEST_TOKEN" ]]; then
  echo "CLOUDFLARE_WORKER_URL and CLOUDFLARE_INGEST_TOKEN are required." >&2
  exit 1
fi

if [[ ! -f "$CSV_PATH" ]]; then
  echo "CSV not found: $CSV_PATH" >&2
  exit 1
fi

"$ROOT/.venv/bin/python" - "$CSV_PATH" "$DATE" "$WORKER_URL" "$INGEST_TOKEN" <<'PY'
import csv
import json
import sys
import urllib.request

csv_path, date_raw, worker_url, token = sys.argv[1:5]
date_iso = f"{date_raw[0:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
fields = [
    "brand",
    "package",
    "country",
    "tooltip_date",
    "revenue_rank_tools",
    "status",
    "status_detail",
    "source_url",
    "crawl_time",
    "raw_tooltip_text",
    "screenshot_path",
]

with open(csv_path, newline="", encoding="utf-8-sig") as f:
    rows = [{key: row.get(key, "") for key in fields} for row in csv.DictReader(f)]

body = json.dumps({"date": date_iso, "source": "linux-runner", "rows": rows}, ensure_ascii=False).encode("utf-8")
request = urllib.request.Request(
    worker_url.rstrip("/") + "/api/ingest",
    data=body,
    method="POST",
    headers={
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "user-agent": "ranking-dashboard-runner/1.0",
    },
)
with urllib.request.urlopen(request, timeout=120) as response:
    print(response.read().decode("utf-8"))
PY
