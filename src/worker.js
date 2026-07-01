import { buildDashboardPayload } from './dashboard-data.js';
import { COUNTRIES, PRODUCTS } from './config.js';

const JSON_HEADERS = {
  'content-type': 'application/json; charset=utf-8',
};
const ALLOWED_COUNTRIES = new Set(COUNTRIES);
const ALLOWED_PRODUCTS = new Set(PRODUCTS);
const DETAIL_FIELDS = [
  'tooltip_date',
  'status_detail',
  'source_url',
  'crawl_time',
  'raw_tooltip_text',
  'screenshot_path',
];

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === 'GET' && url.pathname === '/api/health') {
      return jsonResponse({ ok: true });
    }

    if (request.method === 'GET' && url.pathname === '/favicon.ico') {
      return new Response(null, { status: 204 });
    }

    if (request.method === 'GET' && url.pathname === '/api/dashboard') {
      return handleDashboard(env);
    }

    if (request.method === 'POST' && url.pathname === '/api/ingest') {
      return handleIngest(request, env, ctx);
    }

    return jsonResponse({ error: 'Not found' }, 404);
  },

  scheduled(controller, env, ctx) {
    ctx.waitUntil(runScheduledIngest(controller, env));
  },
};

export async function runScheduledIngest(controller, env) {
  const date = shanghaiDate(controller?.scheduledTime);

  if (!env.SENSOR_TOWER_FEED_URL) {
    await recordRun(env.DB, {
      date,
      source: 'scheduled',
      status: 'NO_DATA_SOURCE',
      row_count: 0,
      message: 'SENSOR_TOWER_FEED_URL is not configured.',
    });
    return { status: 'NO_DATA_SOURCE', accepted: 0 };
  }

  try {
    const response = await fetch(env.SENSOR_TOWER_FEED_URL);
    if (!response.ok) {
      throw new Error(`Feed returned HTTP ${response.status}`);
    }

    const payload = await response.json();
    const result = await ingestPayload(env, {
      date: payload.date || date,
      rows: Array.isArray(payload.rows) ? payload.rows : [],
      source: payload.source || 'sensor_tower_feed',
      raw: payload,
    });
    if (result.archivePromise) {
      await result.archivePromise;
    }
    return result;
  } catch (error) {
    await recordRun(env.DB, {
      date,
      source: 'sensor_tower_feed',
      status: 'FAILED',
      row_count: 0,
      message: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

async function handleDashboard(env) {
  if (!env.DB) {
    return jsonResponse(buildDashboardPayload([], []));
  }

  const latestDateResult = await env.DB.prepare(`SELECT MAX(date) AS latest_date FROM ranking_rows`).first();
  const latestDate = latestDateResult?.latest_date || '';

  const [seriesResult, latestRowsResult, runsResult] = await Promise.all([
    env.DB.prepare(
      `SELECT
        date,
        brand,
        country,
        status,
        data_origin,
        revenue_rank_tools,
        tooltip_date
       FROM ranking_rows
       ORDER BY date, brand, country`,
    ).all(),
    latestDate
      ? env.DB.prepare(
          `SELECT
            date,
            brand,
            country,
            status,
            data_origin,
            revenue_rank_tools,
            tooltip_date,
            status_detail,
            source_url,
            crawl_time,
            raw_tooltip_text,
            screenshot_path
           FROM ranking_rows
           WHERE date = ?
           ORDER BY date, brand, country`,
        )
          .bind(latestDate)
          .all()
      : Promise.resolve({ results: [] }),
    env.DB.prepare(
      `SELECT date, source, status, row_count, message, created_at, updated_at
       FROM update_runs
       ORDER BY date, updated_at`,
    ).all(),
  ]);

  const rows = mergeLatestDetailRows(seriesResult.results || [], latestRowsResult.results || []);
  return jsonResponse(buildDashboardPayload(rows, runsResult.results || []));
}

function mergeLatestDetailRows(seriesRows, latestRows) {
  if (!latestRows.length) {
    return seriesRows;
  }

  const latestByKey = new Map(latestRows.map((row) => [`${row.date}:${row.brand}:${row.country}`, row]));
  return seriesRows.map((row) => latestByKey.get(`${row.date}:${row.brand}:${row.country}`) || row);
}

async function handleIngest(request, env, ctx) {
  if (!env.INGEST_TOKEN) {
    return jsonResponse({ error: 'INGEST_TOKEN is not configured' }, 503);
  }

  if (request.headers.get('authorization') !== `Bearer ${env.INGEST_TOKEN}`) {
    return jsonResponse({ error: 'Unauthorized' }, 401);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: 'Invalid JSON body' }, 400);
  }

  if (!body || !body.date || !Array.isArray(body.rows)) {
    return jsonResponse({ error: 'Expected JSON body with date and rows' }, 400);
  }

  const result = await ingestPayload(env, {
    date: body.date,
    rows: body.rows,
    source: body.source || 'manual_ingest',
    raw: body,
  });

  if (result.archivePromise) {
    await result.archivePromise;
  }

  return jsonResponse({ accepted: result.accepted, snapshot_key: result.snapshot_key || null });
}

async function ingestPayload(env, payload) {
  const date = normalizeDateString(payload.date);
  const source = String(payload.source || 'unknown');
  const rows = payload.rows.map((row) => normalizeIngestRow(row, date, source)).filter(Boolean);
  const snapshotKey = env.SNAPSHOTS ? `snapshots/${date}/${Date.now()}.json` : null;
  const archivePromise = snapshotKey
    ? env.SNAPSHOTS.put(snapshotKey, JSON.stringify(payload.raw || payload), {
        httpMetadata: { contentType: 'application/json; charset=utf-8' },
      })
    : null;

  if (env.DB) {
    await recordRun(env.DB, {
      date,
      source,
      status: 'COMPLETED',
      row_count: rows.length,
      raw_snapshot_key: snapshotKey,
    });

    for (const row of rows) {
      const excludedPriority = rankingRowPrioritySql('excluded');
      const currentPriority = rankingRowPrioritySql('ranking_rows');
      await env.DB.prepare(
        `INSERT INTO ranking_rows
          (
            date,
            brand,
            country,
            status,
            data_origin,
            revenue_rank_tools,
            source,
            tooltip_date,
            status_detail,
            source_url,
            crawl_time,
            raw_tooltip_text,
            screenshot_path,
            updated_at
          )
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
         ON CONFLICT(date, brand, country) DO UPDATE SET
          status = excluded.status,
          data_origin = excluded.data_origin,
          revenue_rank_tools = excluded.revenue_rank_tools,
          source = excluded.source,
          tooltip_date = excluded.tooltip_date,
          status_detail = excluded.status_detail,
          source_url = excluded.source_url,
          crawl_time = excluded.crawl_time,
          raw_tooltip_text = excluded.raw_tooltip_text,
          screenshot_path = excluded.screenshot_path,
          updated_at = CURRENT_TIMESTAMP
         WHERE ${excludedPriority} >= ${currentPriority}`,
      )
        .bind(
          row.date,
          row.brand,
          row.country,
          row.status,
          row.data_origin,
          row.revenue_rank_tools,
          row.source,
          row.tooltip_date,
          row.status_detail,
          row.source_url,
          row.crawl_time,
          row.raw_tooltip_text,
          row.screenshot_path,
        )
        .run();
    }
  }

  if (archivePromise && !env.DB) {
    await archivePromise;
  }

  return {
    accepted: rows.length,
    snapshot_key: snapshotKey,
    archivePromise,
  };
}

export function rankingRowPrioritySql(alias) {
  return `(CASE
            WHEN ${alias}.revenue_rank_tools IS NOT NULL THEN 100
            WHEN ${alias}.status IN ('SUCCESS', 'PARTIAL_SUCCESS') THEN 90
            WHEN ${alias}.status = 'NO_CATEGORY_RANKING_DATA' THEN 80
            WHEN ${alias}.status IN ('RATE_LIMITED', 'PENDING_TODAY') THEN 10
            ELSE 20
          END)`;
}

function normalizeIngestRow(row, date, source) {
  const brand = String(row.brand ?? row.product ?? '').trim().toLowerCase();
  const country = String(row.country ?? '').trim().toUpperCase();
  if (!ALLOWED_PRODUCTS.has(brand) || !ALLOWED_COUNTRIES.has(country)) {
    return null;
  }

  const revenueRankTools = normalizeRank(row.revenue_rank_tools);
  const normalized = {
    date,
    brand,
    country,
    status: row.status ? String(row.status).toUpperCase() : revenueRankTools === null ? 'FAILED' : 'SUCCESS',
    data_origin: row.data_origin || source,
    revenue_rank_tools: revenueRankTools,
    source,
  };

  for (const field of DETAIL_FIELDS) {
    normalized[field] = row[field] ?? null;
  }

  return normalized;
}

function normalizeRank(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  const rank = Number(value);
  return Number.isFinite(rank) ? rank : null;
}

function normalizeDateString(value) {
  const date = String(value ?? '').trim();
  if (/^\d{8}$/.test(date)) {
    return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`;
  }
  return date.slice(0, 10);
}

async function recordRun(db, run) {
  if (!db) {
    return;
  }

  const source = run.source || 'unknown';
  const idempotencyKey = `${run.date}:${source}:${run.status}`;

  await db
    .prepare(
      `INSERT INTO update_runs
        (idempotency_key, date, source, status, row_count, message, raw_snapshot_key, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
       ON CONFLICT(idempotency_key) DO UPDATE SET
        row_count = excluded.row_count,
        message = excluded.message,
        raw_snapshot_key = COALESCE(excluded.raw_snapshot_key, update_runs.raw_snapshot_key),
        updated_at = CURRENT_TIMESTAMP`,
    )
    .bind(
      idempotencyKey,
      run.date,
      source,
      run.status,
      run.row_count || 0,
      run.message || null,
      run.raw_snapshot_key || null,
    )
    .run();
}

function shanghaiDate(time) {
  const date = time ? new Date(time) : new Date();
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date);
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: JSON_HEADERS,
  });
}
