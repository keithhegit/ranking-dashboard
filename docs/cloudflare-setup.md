# Cloudflare Setup

This project now has a Cloudflare Worker backend, Workers Assets frontend, D1 storage, R2 raw snapshot archive, and a daily cron trigger.

## Important Runtime Boundary

The current Sensor Tower collector depends on `engine/sensor_tower_multi_product_multi_country_20260428.pyc`, a CPython 3.13 compiled module plus local browser login state. Cloudflare Workers cannot run that `.pyc` file or reuse the local browser profile. The Cloudflare workflow therefore supports two production-safe inputs:

1. `SENSOR_TOWER_FEED_URL`: the Worker cron fetches a JSON feed every day.
2. `scripts/upload_daily_to_cloudflare.ps1`: the existing Windows scraper uploads its generated CSV to Cloudflare after it runs.

If you can provide Sensor Tower API credentials or a legal JSON feed endpoint, wire it into `SENSOR_TOWER_FEED_URL` and the 00:00 workflow becomes fully Cloudflare-driven.

## Create Cloudflare Resources

```powershell
npm install
npx wrangler login
npx wrangler d1 create competitor-monitor-dashboard
npx wrangler r2 bucket create competitor-monitor-dashboard-snapshots
```

Copy the returned D1 `database_id` into `wrangler.toml`.

Apply the schema:

```powershell
npm run d1:migrations:apply
```

Set secrets:

```powershell
npx wrangler secret put INGEST_TOKEN
npx wrangler secret put SENSOR_TOWER_FEED_URL
```

`INGEST_TOKEN` is required for `POST /api/ingest`; the Worker rejects ingest requests when it is missing. `SENSOR_TOWER_FEED_URL` is optional. Leave it unset if you will upload CSV files from the existing scraper.

For local development, copy `.dev.vars.example` to `.dev.vars` and set the same `INGEST_TOKEN` there.

## Daily Schedule

Cloudflare Cron Triggers run on UTC. The configured cron is:

```toml
crons = ["0 16 * * *"]
```

That is 00:00 in Asia/Shanghai.

## Deploy

```powershell
npm test
npm run deploy
```

The Worker serves:

- `GET /` from `public/index.html`
- `GET /api/health`
- `GET /api/dashboard`
- `POST /api/ingest`

## Upload Existing Daily CSV

After the current Windows scraper creates `output/sensor_tower_multi_product_multi_country_YYYYMMDD.csv`, run:

```powershell
.\scripts\upload_daily_to_cloudflare.ps1 `
  -WorkerUrl "https://competitor-monitor-dashboard.<your-subdomain>.workers.dev" `
  -IngestToken "<same token as INGEST_TOKEN>" `
  -Date "20260615"
```

To make the existing Windows scraper path update Cloudflare automatically, pass the Worker details to the daily runner:

```powershell
.\run_daily.ps1 `
  -CloudflareWorkerUrl "https://competitor-monitor-dashboard.<your-subdomain>.workers.dev" `
  -CloudflareIngestToken "<same token as INGEST_TOKEN>"
```

For Windows Task Scheduler, create a daily trigger at `00:00` and use:

```text
Program/script: powershell.exe
Arguments: -NoProfile -ExecutionPolicy Bypass -File "D:\Game\Ranking_Dashboard\competitor-monitor-dashboard\run_daily.ps1" -CloudflareWorkerUrl "https://competitor-monitor-dashboard.<your-subdomain>.workers.dev" -CloudflareIngestToken "<same token as INGEST_TOKEN>"
Start in: D:\Game\Ranking_Dashboard\competitor-monitor-dashboard
```

The runner also reads `CLOUDFLARE_WORKER_URL` and `CLOUDFLARE_INGEST_TOKEN` from the environment, which is safer than storing the token directly in the scheduled task arguments.

## JSON Feed Contract

`SENSOR_TOWER_FEED_URL` and `POST /api/ingest` accept:

```json
{
  "date": "2026-06-15",
  "source": "sensortower",
  "rows": [
    {
      "brand": "ugphone",
      "country": "TH",
      "tooltip_date": "2026-06-15",
      "revenue_rank_tools": 12,
      "status": "SUCCESS",
      "status_detail": "",
      "source_url": "https://app.sensortower.com/..."
    }
  ]
}
```

Rows are upserted by `date + brand + country`, so retries are safe.
