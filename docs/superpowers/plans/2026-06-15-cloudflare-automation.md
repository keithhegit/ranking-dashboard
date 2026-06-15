# Cloudflare Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Cloudflare-hosted frontend/backend workflow that refreshes ranking data every day at 00:00 Asia/Shanghai.

**Architecture:** Keep the existing Windows/Python scraper intact because its core engine is a CPython 3.13 `.pyc` that cannot run inside Cloudflare Workers. Add a Cloudflare Worker scheduled backend that can ingest normalized ranking rows from a configured feed or authenticated upload, store queryable data in D1, archive raw snapshots in R2, and serve a Pages-compatible dashboard frontend.

**Tech Stack:** Cloudflare Workers, Wrangler, D1, R2, static Pages assets, Node.js built-in test runner.

---

### Task 1: Worker Data Model And API

**Files:**
- Create: `src/config.js`
- Create: `src/dashboard-data.js`
- Create: `src/worker.js`
- Create: `migrations/0001_init.sql`
- Test: `test/dashboard-data.test.js`

- [x] **Step 1: Write failing tests for dashboard assembly**

Create tests that verify dashboard rows are grouped by latest monitor date, missing configured product/country pairs become `PENDING_TODAY`, and overview counts are derived from rank statuses.

- [x] **Step 2: Implement pure dashboard assembly**

Implement constants for products/countries and pure helpers that turn D1 rows into the JSON payload consumed by the frontend.

- [x] **Step 3: Implement Worker endpoints**

Add `GET /api/health`, `GET /api/dashboard`, `POST /api/ingest`, and scheduled execution. `POST /api/ingest` requires `Authorization: Bearer <INGEST_TOKEN>`.

- [x] **Step 4: Add D1 schema**

Create tables for run metadata and ranking rows. Use idempotent inserts so repeated daily runs can be retried.

- [x] **Step 5: Verify**

Run `npm test`.

### Task 2: Cloudflare Project Configuration

**Files:**
- Create: `package.json`
- Create: `wrangler.toml`
- Create: `.dev.vars.example`
- Modify: `.gitignore`

- [x] **Step 1: Add npm scripts**

Add scripts for `test`, `dev`, `deploy`, `d1:migrations:apply`, and `d1:migrations:apply:local`.

- [x] **Step 2: Add Worker bindings**

Configure D1 binding `DB`, R2 binding `SNAPSHOTS`, static asset directory `public`, and cron trigger `0 16 * * *` because Cloudflare cron uses UTC and Asia/Shanghai midnight is 16:00 UTC.

- [x] **Step 3: Add local env template**

Document `INGEST_TOKEN` and optional `SENSOR_TOWER_FEED_URL`.

### Task 3: Pages Frontend

**Files:**
- Create: `public/index.html`

- [x] **Step 1: Build API-driven dashboard shell**

Create a static dashboard that fetches `/api/dashboard`, renders overview counters, latest rank matrix, and run metadata.

- [x] **Step 2: Add empty/error states**

Show actionable states for no data, pending rows, and API errors.

### Task 4: Existing Scraper Bridge And Documentation

**Files:**
- Create: `scripts/upload_daily_to_cloudflare.ps1`
- Create: `docs/cloudflare-setup.md`
- Modify: `README.md`

- [x] **Step 1: Add upload bridge**

Create a PowerShell script that reads the existing generated daily CSV and uploads it to `POST /api/ingest`.

- [x] **Step 2: Document setup**

Document D1/R2 creation, required Wrangler secrets, Pages/Worker deployment, cron timezone, and the current limitation that Sensor Tower browser automation cannot run directly inside Workers.

- [x] **Step 3: Verify**

Run `npm test` and a local Worker smoke test if dependencies are installed.

### Deployment Verification

- [x] Applied remote D1 migration to `competitor-monitor-dashboard` (`be38c2d0-f596-46ba-8aee-22c324826f63`).
- [x] Deployed Worker Assets to `https://competitor-monitor-dashboard.keithhe2021.workers.dev`.
- [x] Configured `INGEST_TOKEN` Worker secret and Ubuntu runner `/etc/competitor-monitor.env`.
- [x] Verified Ubuntu CSV upload returns `accepted:1` and archives to R2 bucket `competitor-monitor-dashboard-snapshots`.
- [x] Verified dashboard API reports UGPhone US rank `#385` from `linux-runner` for `2026-06-15`.
- [x] Verified `competitor-monitor.timer` and `competitor-monitor-browser.service` are active on the Ubuntu runner.
