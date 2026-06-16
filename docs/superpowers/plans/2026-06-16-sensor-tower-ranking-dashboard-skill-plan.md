# Sensor Tower Ranking Dashboard Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a reusable `sensor-tower-ranking-dashboard` Codex skill for building, operating, and debugging Playwright-based Sensor Tower ranking collectors with Windows or Ubuntu runners, evidence-preserving CSV output, HTML dashboards, and optional Cloudflare publishing.

**Architecture:** Treat collection as a stateful runner workflow. Keep Sensor Tower login state in a browser profile, serialize collection through a single queue, stop on first 429, persist partial progress, build local dashboard artifacts first, and publish only after a clean local result exists. Cloudflare is the publishing, storage, and dashboard layer; collection runs on a login-capable Windows desktop or Ubuntu host.

**Tech Stack:** Codex Skills, Python, Playwright, Chrome/Edge persistent profiles, Windows PowerShell/BAT, Ubuntu systemd, Xvfb, noVNC, CSV, screenshots, HTML dashboard generation, optional Cloudflare Worker/D1/R2, helper scripts for diagnostics.

---

## Practice Notes From The Ranking Dashboard Build

- The upstream repository was local-first: log in once through a browser profile, then run a daily script that collects app/country pairs and rebuilds `dashboard.html`.
- Full Cloudflare hosting is not appropriate for the collector when Sensor Tower requires a logged-in browser. Cloudflare should host the Worker/API, D1/R2 data, and dashboard assets.
- Ubuntu is a valid runner when it has Chrome, Xvfb, noVNC, a persistent browser profile, and systemd timers.
- `HTTP 429` / `RATE_LIMITED` must be treated as a global stop signal for the same account/session/IP. Continuing later batches pollutes the run.
- The skill must not recommend proxy pools, browser fingerprint spoofing, multi-account rotation, CAPTCHA bypass, cookie extraction, or ignoring `Retry-After`.
- Service success does not mean data success. Agents must report total rows, ranked rows, no-data rows, rate-limited rows, and status distribution.
- Some app/country pairs legitimately have no category ranking data. Represent them as `NO_CATEGORY_RANKING_DATA`, not as scrape failures.
- Cloudflare D1 ingest must not allow a later low-priority row such as `RATE_LIMITED` to overwrite a ranked row for the same date/brand/country.
- Long throttled runs need a systemd timeout longer than the default 2-hour window. In practice, 6 hours is safer for an 80-row daily run with cooldowns.

## File Structure

- Create skill folder later: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\`
- Create: `SKILL.md`
- Create: `references/app-config.md`
- Create: `references/runner-selection.md`
- Create: `references/windows-runner.md`
- Create: `references/ubuntu-runner.md`
- Create: `references/rate-limit-queue.md`
- Create: `references/data-contract.md`
- Create: `references/dashboard-generation.md`
- Create: `references/publishing-bridge.md`
- Create: `references/operations-debugging.md`
- Create: `scripts/summarize_ranking_csv.py`
- Create: `scripts/check_dashboard_api.py`

## Product Shape

The skill should guide an agent through this reusable pipeline:

```text
app definitions
  -> runner selection
  -> browser login profile
  -> single-worker Sensor Tower queue
  -> metric capture with screenshots/logs
  -> CSV + state + diagnostics
  -> dashboard.html generation
  -> optional Cloudflare Worker/D1/R2 publishing
  -> operations check after scheduled run
```

The skill must stay generic across apps. It may use UGPhone, LDCloud, Redfinger, VSPhone, and the 20-market list only as examples.

## Task 1: Write `SKILL.md`

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\SKILL.md`

- [ ] **Step 1: Create frontmatter**

Use this exact frontmatter:

```yaml
---
name: sensor-tower-ranking-dashboard
description: Build, operate, or debug Sensor Tower app ranking collection workflows that use Playwright with a logged-in browser profile, Windows or Ubuntu runners, noVNC login, rate-limit-safe queueing, CSV/screenshot/log evidence, HTML dashboard generation, and optional Cloudflare Worker/D1/R2 publishing. Use when a user asks to monitor Sensor Tower app rankings, generalize ranking-dashboard to other apps or markets, run scheduled browser collection, troubleshoot empty dashboards, inspect 429 behavior, or publish ranking dashboards.
---
```

- [ ] **Step 2: Add routing body**

Add these routing rules to the body:

- Read `references/app-config.md` for app/product/market definitions.
- Read `references/runner-selection.md` before choosing Windows, Ubuntu, or Cloudflare roles.
- Read `references/windows-runner.md` for local Windows collection.
- Read `references/ubuntu-runner.md` for remote Chrome, noVNC, browser profile, and systemd.
- Read `references/rate-limit-queue.md` for 429, cooldown, cache, and resume behavior.
- Read `references/data-contract.md` for CSV fields, statuses, and evidence semantics.
- Read `references/dashboard-generation.md` when rebuilding or preserving the dashboard.
- Read `references/publishing-bridge.md` for Cloudflare Worker/D1/R2 publishing.
- Read `references/operations-debugging.md` for service logs, empty dashboard, and efficiency checks.

Add these hard rules:

- Never ask for Sensor Tower passwords, 2FA codes, cookies, or exported browser profiles.
- Ask the user to log in through a browser/noVNC session.
- Do not propose proxy pools, fingerprint spoofing, multi-account rotation, CAPTCHA bypass, or ignoring `Retry-After`.
- Do not publish a daily run until local CSV/dashboard generation has completed, unless the user explicitly asks for partial publishing.
- Always report ranked row count and status distribution, not just "upload succeeded".

- [ ] **Step 3: Commit**

```bash
git add C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\SKILL.md
git commit -m "docs: add Sensor Tower ranking dashboard skill entrypoint"
```

## Task 2: Write App Configuration Reference

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\references\app-config.md`

- [ ] **Step 1: Add required configuration shape**

The file must define this schema:

```json
{
  "apps": [
    {
      "brand": "example_app",
      "label": "Example App",
      "app_id": "com.example.app",
      "store": "google_play",
      "sensor_tower_overview_id": "com.example.app"
    }
  ],
  "countries": ["US", "TH", "VN"],
  "metric": "revenue_rank_tools",
  "sensor_tower_tab": "category_rankings",
  "known_no_category_ranking_data": [
    { "brand": "example_app", "country": "US" }
  ]
}
```

- [ ] **Step 2: Add configuration rules**

Add these rules:

- Use Sensor Tower app/package IDs as source of truth.
- Keep dashboard market tiers separate from collection countries.
- Do not mix App Store and Google Play rows unless the data contract includes `store`.
- Do not mix different metrics into one stored ranking column.
- Represent known no-data pairs as `NO_CATEGORY_RANKING_DATA`.

- [ ] **Step 3: Add the validated ranking-dashboard example**

```json
{
  "apps": [
    { "brand": "ugphone", "label": "UGPhone", "app_id": "com.tykeji.ugphone" },
    { "brand": "ldcloud", "label": "LDCloud", "app_id": "com.ld.cph.gl" },
    { "brand": "redfinger", "label": "Redfinger", "app_id": "com.redfinger.global" },
    { "brand": "vsphone", "label": "VSPhone", "app_id": "com.vsphone.overseas" }
  ],
  "countries": ["TH", "VN", "PH", "BR", "TR", "MY", "ID", "HK", "TW", "KR", "US", "MX", "SG", "JP", "PL", "DE", "GB", "IN", "IT", "FR"],
  "known_no_category_ranking_data": [
    { "brand": "vsphone", "country": "US" },
    { "brand": "vsphone", "country": "JP" },
    { "brand": "vsphone", "country": "DE" }
  ]
}
```

## Task 3: Write Runner Selection Reference

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\references\runner-selection.md`

- [ ] **Step 1: Define runner decision rules**

Add:

- Use Windows local when the user wants desktop collection, the repo ships `.bat` or PowerShell scripts, and the user can manually log in to Sensor Tower.
- Use Ubuntu remote when the user does not want a Windows VPS and the host can run Chrome with Xvfb/noVNC/systemd.
- Do not choose Cloudflare Workers for the browser collector when Sensor Tower requires login.
- Use Cloudflare only for Worker API, D1/R2 storage, and dashboard hosting.

## Task 4: Write Windows Runner Reference

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\references\windows-runner.md`

- [ ] **Step 1: Define first-login flow**

Add:

1. Run the repository login script, such as `FIRST RUN LOGIN.bat`.
2. Let the script open the persistent browser profile.
3. Ask the user to log in to Sensor Tower manually.
4. Do not ask the user to paste credentials into chat.

- [ ] **Step 2: Define daily flow**

Add:

1. Run the repository daily script, such as `RUN_DAILY.bat`.
2. Keep the browser and command window open.
3. Wait for CSV/log/screenshot/dashboard generation.
4. Upload only after local output is complete.

- [ ] **Step 3: Define outputs**

Add:

- `output/`: daily CSV and batch logs.
- `logs/`: scraper diagnostics.
- `screenshots/`: capture evidence.
- `dashboard.html`: latest local dashboard.
- `runtime/browser_profile/`: login state. Never share this folder.

## Task 5: Write Ubuntu Runner Reference

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\references\ubuntu-runner.md`

- [ ] **Step 1: Define required services**

Add:

- Google Chrome.
- Python virtual environment.
- Playwright dependencies.
- Xvfb display.
- x11vnc + noVNC.
- Persistent `runtime/browser_profile`.
- Browser service, usually `competitor-monitor-browser.service`.
- Daily oneshot service, usually `competitor-monitor.service`.
- Daily timer, usually `competitor-monitor.timer`.

- [ ] **Step 2: Define noVNC login procedure**

Add:

1. Start or verify the browser/noVNC service.
2. Create an SSH tunnel from the operator machine to remote `127.0.0.1:6080`.
3. Open `http://127.0.0.1:6080/vnc.html` locally.
4. Ask the user to log in to Sensor Tower inside that browser.
5. Verify `runtime/browser_profile` is persistent.

- [ ] **Step 3: Add systemd timeout guidance from practice**

Add this command block:

```bash
systemctl cat competitor-monitor.service --no-pager
systemctl show competitor-monitor.service -p TimeoutStartUSec --no-pager
sudo mkdir -p /etc/systemd/system/competitor-monitor.service.d
cat >/tmp/competitor-monitor-timeout.conf <<'EOF'
[Service]
TimeoutStartSec=21600
EOF
sudo mv /tmp/competitor-monitor-timeout.conf /etc/systemd/system/competitor-monitor.service.d/timeout.conf
sudo systemctl daemon-reload
systemctl show competitor-monitor.service -p TimeoutStartUSec --no-pager
```

Explain that 6 hours is safer for an 80-row run with 45-120 second sleeps and 10-20 minute cooldowns.

## Task 6: Write Rate Limit And Queue Reference

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\references\rate-limit-queue.md`

- [ ] **Step 1: Define 429 policy**

Add:

- Treat `HTTP 429`, `RATE_LIMITED`, or clear throttling page content as a global stop signal.
- Use a single Sensor Tower worker.
- Add process-level locking such as `flock`.
- Persist detail output after every app-country task.
- Skip same-day rows that already have a numeric rank.
- Skip known `NO_CATEGORY_RANKING_DATA` rows.
- Stop the queue on first `RATE_LIMITED`.
- Write `cooldown_until_epoch` to state.
- Suppress Cloudflare upload when the run is rate-limited or cooling down.
- Resume later from cached successes and pending/rate-limited rows.

- [ ] **Step 2: Define safe default timing**

Add:

```text
concurrency: 1
sleep after success: 45-120 seconds
hard cooldown: 10-20 minutes after every 10 successes
first 429 cooldown: 30-60 minutes when Retry-After is unavailable
consecutive 429 limit: 1 for the current run
systemd timeout: 6 hours for 80-row runs
```

- [ ] **Step 3: Define merge priority**

Add:

```text
numeric rank > SUCCESS/PARTIAL_SUCCESS > NO_CATEGORY_RANKING_DATA > capture failures > RATE_LIMITED > PENDING/MISSING
```

Add the rule: never let a later `RATE_LIMITED` row overwrite a row that already has a numeric rank.

## Task 7: Write Data Contract Reference

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\references\data-contract.md`

- [ ] **Step 1: Define core CSV fields**

Add this field list:

```text
date
brand
package
country
tooltip_date
app_name
revenue_rank_tools
revenue_rank_apps
top_free_rank_tools
source_url
crawl_time
status
status_detail
error_message
candidate_tooltip_dates
candidate_count
selected_tooltip_date
page_loaded_screenshot
final_hover_screenshot
retry_count
screenshot_path
selected_candidate_index
selected_candidate_raw_text
raw_tooltip_text
selected_candidate_x
selected_candidate_y
all_candidates_json
batch_file
```

- [ ] **Step 2: Define status semantics**

Add:

- `SUCCESS`: target ranking metric captured with complete expected evidence.
- `PARTIAL_SUCCESS`: target ranking metric captured but ancillary fields are incomplete.
- `NO_CATEGORY_RANKING_DATA`: Sensor Tower page shows no category ranking data for this app-country pair.
- `RANK_CAPTURE_FAILED`: page loaded but rank/tooltip capture failed.
- `PAGE_LOAD_FAILED`: page did not load enough to inspect.
- `RATE_LIMITED`: collection hit Sensor Tower throttling.
- `PENDING_TODAY`: dashboard placeholder before a daily row exists.
- `MISSING`: merge expected a row but no detail file provided one.

State explicitly: `NO_CATEGORY_RANKING_DATA` is a terminal non-failure. It counts as crawled but not ranked.

- [ ] **Step 3: Define required summaries**

Require dashboard/API summaries to include:

- latest monitor date
- total expected rows
- crawled rows
- ranked rows
- status distribution
- rate-limited count
- no-category-data count

## Task 8: Write Dashboard Generation Reference

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\references\dashboard-generation.md`

- [ ] **Step 1: Define dashboard behavior**

Add:

- Read latest daily CSV and historical CSV files.
- Build latest app x country matrix.
- Build competitive alerts.
- Build app-specific focus cards.
- Build trend chart from historical series.
- Build raw data and review table.
- Preserve existing dashboard shell when the user says the team is used to it.

- [ ] **Step 2: Add single-day trend chart rule**

Add:

- If a trend chart has only one date, do not imply a line trend.
- Render it as a single-day ranking snapshot.
- Keep the y-axis and brand legend.
- Add the note: `当前仅有 1 个监测日，趋势将在积累 2 天后自动连线。`
- When two or more dates exist, switch back to the line chart automatically.

## Task 9: Write Publishing Bridge Reference

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\references\publishing-bridge.md`

- [ ] **Step 1: Define Cloudflare roles**

Add:

- Worker receives ingest requests and serves dashboard API.
- D1 stores normalized ranking rows and run history.
- R2 stores raw JSON snapshots and optional evidence bundles.
- Pages or Workers Assets serve the HTML dashboard.
- Do not run the Sensor Tower browser collector inside Cloudflare Workers.

- [ ] **Step 2: Define ingest safety**

Add:

- Authenticate with a bearer token.
- Accept date, source, and rows.
- Archive raw payload to R2 when available.
- Upsert normalized rows into D1.
- Protect existing ranked rows from being overwritten by lower-priority rows.

Add D1 priority:

```text
numeric rank > SUCCESS/PARTIAL_SUCCESS > NO_CATEGORY_RANKING_DATA > other failures > RATE_LIMITED
```

- [ ] **Step 3: Define upload retry behavior**

Add:

```bash
UPLOAD_ONLY=1 /home/ubuntu/ranking-dashboard/linux/run_daily.sh
```

Explain that upload retry must not trigger a new Sensor Tower collection.

## Task 10: Write Operations And Debugging Reference

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\references\operations-debugging.md`

- [ ] **Step 1: Add service inspection commands**

```bash
systemctl status competitor-monitor.service --no-pager
systemctl list-timers --all --no-pager | grep competitor-monitor
journalctl -u competitor-monitor.service --since today --no-pager -n 260
systemctl status competitor-monitor-browser.service --no-pager
systemctl show competitor-monitor.service -p TimeoutStartUSec --no-pager
```

- [ ] **Step 2: Add queue and CSV inspection commands**

```bash
cd /home/ubuntu/ranking-dashboard
ls -lah output/daily_queue_YYYYMMDD
tail -n 120 output/daily_queue_YYYYMMDD/daily_all.log
cat output/daily_queue_YYYYMMDD/state.json 2>/dev/null || true
.venv/bin/python scripts/summarize_ranking_csv.py output/daily_queue_YYYYMMDD/detail_*.csv
.venv/bin/python scripts/summarize_ranking_csv.py output/sensor_tower_multi_product_multi_country_YYYYMMDD.csv
```

- [ ] **Step 3: Add online dashboard inspection**

```bash
python scripts/check_dashboard_api.py https://ug-ranking-dashboard.keithhe.com/api/dashboard
```

Add interpretation rules:

- If online latest date is old but service is still running, wait for local collection and upload.
- If local CSV has rows but online date is old, debug upload/Cloudflare.
- If online rows are accepted but ranked rows are zero, debug collector/capture.
- If `RATE_LIMITED` appears, verify queue stopped and upload was skipped.

- [ ] **Step 4: Add incident patterns**

Add all-failed capture pattern:

```text
service result: success
merged rows: 80
Cloudflare accepted: 80
D1 rows: 80
status distribution: RANK_CAPTURE_FAILED=80
ranked rows: 0
common detail: hover finished but no tooltip text was captured
```

Add 429 pollution pattern:

```text
first 15-25 rows have ranks
later rows are RATE_LIMITED
subsequent batches continue to fail
```

Interpretation: add global queue stop, cooldown state, same-day success cache, and upload suppression.

## Task 11: Write Diagnostic Scripts

**Files:**
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\scripts\summarize_ranking_csv.py`
- Create: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\scripts\check_dashboard_api.py`

- [ ] **Step 1: Create CSV summarizer**

```python
#!/usr/bin/env python3
import csv
import glob
import json
import os
import sys
from collections import Counter

paths = []
for pattern in sys.argv[1:]:
    paths.extend(glob.glob(pattern))

rows = []
for path in sorted(paths):
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row["_file"] = os.path.basename(path)
            rows.append(row)

status_counts = Counter((row.get("status") or "") for row in rows)
ranked_rows = sum(1 for row in rows if (row.get("revenue_rank_tools") or "").strip().isdigit())
rate_limited_rows = [
    row for row in rows
    if (row.get("status") or "").upper() == "RATE_LIMITED"
    or "429" in (row.get("status_detail") or "")
    or "rate limit" in (row.get("status_detail") or "").lower()
]

print(json.dumps({
    "files": len(set(row["_file"] for row in rows)),
    "rows": len(rows),
    "ranked_rows": ranked_rows,
    "status_counts": dict(status_counts),
    "rate_limited_rows": len(rate_limited_rows),
    "latest_rows": [
        {
            "file": row.get("_file"),
            "brand": row.get("brand"),
            "country": row.get("country"),
            "status": row.get("status"),
            "rank": row.get("revenue_rank_tools"),
            "crawl_time": row.get("crawl_time"),
        }
        for row in rows[-10:]
    ],
}, ensure_ascii=False, indent=2))
```

- [ ] **Step 2: Create dashboard API checker**

```python
#!/usr/bin/env python3
import json
import sys
import urllib.request
from collections import Counter

url = sys.argv[1]
request = urllib.request.Request(
    url,
    headers={
        "accept": "application/json",
        "user-agent": "ranking-dashboard-checker/1.0",
    },
)
with urllib.request.urlopen(request, timeout=60) as response:
    payload = json.loads(response.read().decode("utf-8"))

rows = payload.get("latest_rows", [])
print(json.dumps({
    "latest_monitor_file_date": payload.get("latest_monitor_file_date"),
    "generated_at": payload.get("generated_at"),
    "overview": payload.get("overview", {}),
    "row_count": len(rows),
    "status_counts": dict(Counter(row.get("status") for row in rows)),
    "ranked_rows": sum(1 for row in rows if isinstance(row.get("revenue_rank_tools"), (int, float))),
}, ensure_ascii=False, indent=2))
```

- [ ] **Step 3: Run script syntax checks**

```bash
python -m py_compile scripts/summarize_ranking_csv.py scripts/check_dashboard_api.py
```

Expected: no output and exit code 0.

## Task 12: Validate The Skill Folder

**Files:**
- Validate: `C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard\`

- [ ] **Step 1: Run skill validation**

```bash
python C:\Users\Og\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard
```

Expected: validation passes.

- [ ] **Step 2: Forward-test with a fresh subagent**

Use this realistic prompt:

```text
Use the sensor-tower-ranking-dashboard skill at C:\Users\Og\.codex\skills\sensor-tower-ranking-dashboard to inspect a remote Ubuntu Sensor Tower ranking runner after its daily timer fired. Report whether the run is still collecting, whether 429 appeared, how many rows are ranked, and whether the online dashboard is updated.
```

Expected: the subagent reads only needed references, uses safe read-only commands, reports service state, queue summary, CSV status distribution, and dashboard API date.

## Self-Review

- Spec coverage: The revised plan covers app configuration, Windows runner, Ubuntu runner, noVNC login, 429-safe queueing, same-day cache, no-category markets, CSV/status semantics, dashboard generation, Cloudflare publishing, D1 overwrite protection, and operations debugging.
- Placeholder scan: No task uses placeholder-only instructions.
- Type consistency: Skill name, reference paths, status names, and script names are consistent.
- Practice alignment: The plan reflects the validated ranking-dashboard implementation: 77 ranked rows, 3 `NO_CATEGORY_RANKING_DATA` rows, zero `RATE_LIMITED` rows after upload, and a 6-hour systemd timeout for long throttled runs.
