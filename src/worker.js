import { buildDashboardPayload } from './dashboard-data.js';
import { COUNTRIES, PRODUCTS } from './config.js';

const JSON_HEADERS = {
  'content-type': 'application/json; charset=utf-8',
};
const ALLOWED_COUNTRIES = new Set(COUNTRIES);
const ALLOWED_PRODUCTS = new Set(PRODUCTS);
const DEFAULT_DASHBOARD_PASSWORD = 'makeuggreatagain';
const AUTH_COOKIE_NAME = 'ug_dashboard_auth';
const AUTH_TTL_SECONDS = 60 * 60 * 24 * 14;
const LOGIN_BANNER_URL = 'https://pub-c98d5902eedf42f6a9765dfad981fd88.r2.dev/Icon/roblox-650-80.jpg';
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

    if (request.method === 'POST' && url.pathname === '/api/login') {
      return handleLogin(request, env);
    }

    if (request.method === 'GET' && url.pathname === '/api/dashboard') {
      if (!(await isAuthenticated(request, env))) {
        return jsonResponse({ error: 'Authentication required' }, 401);
      }
      return handleDashboard(env);
    }

    if (request.method === 'POST' && url.pathname === '/api/ingest') {
      return handleIngest(request, env, ctx);
    }

    if (request.method === 'GET' && !url.pathname.startsWith('/api/')) {
      if (!(await isAuthenticated(request, env))) {
        return loginPage();
      }
      if (env.ASSETS) {
        return env.ASSETS.fetch(request);
      }
    }

    return jsonResponse({ error: 'Not found' }, 404);
  },

  scheduled(controller, env, ctx) {
    ctx.waitUntil(runScheduledIngest(controller, env));
  },
};

async function handleLogin(request, env) {
  const password = await readPassword(request);
  if (password !== dashboardPassword(env)) {
    return loginPage('密码不正确', 401);
  }

  return new Response(null, {
    status: 303,
    headers: {
      location: '/',
      'set-cookie': `${AUTH_COOKIE_NAME}=${await createAuthToken(env)}; Path=/; Max-Age=${AUTH_TTL_SECONDS}; HttpOnly; Secure; SameSite=Lax`,
    },
  });
}

async function readPassword(request) {
  const contentType = request.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      const body = await request.json();
      return String(body?.password || '');
    } catch {
      return '';
    }
  }

  try {
    const form = await request.formData();
    return String(form.get('password') || '');
  } catch {
    return '';
  }
}

async function isAuthenticated(request, env) {
  const token = cookieValue(request.headers.get('cookie') || '', AUTH_COOKIE_NAME);
  if (!token) {
    return false;
  }

  const [issuedAtText, signature] = token.split('.');
  const issuedAt = Number(issuedAtText);
  if (!Number.isFinite(issuedAt) || !signature) {
    return false;
  }

  const now = Math.floor(Date.now() / 1000);
  if (issuedAt > now + 60 || now - issuedAt > AUTH_TTL_SECONDS) {
    return false;
  }

  const expected = await signAuthValue(issuedAtText, authSecret(env));
  return constantTimeEqual(signature, expected);
}

async function createAuthToken(env) {
  const issuedAt = String(Math.floor(Date.now() / 1000));
  return `${issuedAt}.${await signAuthValue(issuedAt, authSecret(env))}`;
}

async function signAuthValue(value, secret) {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(value));
  return base64Url(signature);
}

function base64Url(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function constantTimeEqual(a, b) {
  if (a.length !== b.length) {
    return false;
  }
  let diff = 0;
  for (let index = 0; index < a.length; index += 1) {
    diff |= a.charCodeAt(index) ^ b.charCodeAt(index);
  }
  return diff === 0;
}

function cookieValue(header, name) {
  return header
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`))
    ?.slice(name.length + 1) || '';
}

function dashboardPassword(env) {
  return env.DASHBOARD_PASSWORD || DEFAULT_DASHBOARD_PASSWORD;
}

function authSecret(env) {
  return env.DASHBOARD_AUTH_SECRET || dashboardPassword(env);
}

function loginPage(errorMessage = '', status = 200) {
  return new Response(
    `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>竞品排名监测看板登录</title>
  <style>
    :root{--bg:#F5F7FB;--card:#FFFFFF;--line:#E5ECF6;--ink:#172448;--text:#334155;--muted:#64748B;--primary:#2F6BFF;--bad:#E11D48;--shadow:0 18px 44px rgba(23,36,72,.14)}
    *{box-sizing:border-box}
    body{margin:0;min-height:100vh;background:var(--bg);font-family:"Microsoft YaHei","PingFang SC",Arial,sans-serif;color:var(--text);display:grid;place-items:center;padding:24px}
    .shell{width:min(980px,100%);display:grid;grid-template-columns:minmax(0,1.1fr) 380px;background:var(--card);border:1px solid var(--line);border-radius:22px;box-shadow:var(--shadow);overflow:hidden}
    .visual{min-height:366px;background:linear-gradient(90deg,rgba(23,36,72,.18),rgba(23,36,72,.02)),url("${LOGIN_BANNER_URL}") center/cover no-repeat;position:relative}
    .visual:after{content:"";position:absolute;inset:auto 0 0 0;height:46%;background:linear-gradient(0deg,rgba(245,247,251,.92),rgba(245,247,251,0))}
    .panel{padding:42px 36px;display:flex;flex-direction:column;justify-content:center}
    .brand{display:flex;align-items:center;gap:14px;margin-bottom:28px}
    .logo{width:52px;height:52px;border-radius:14px;background:linear-gradient(135deg,#2F6BFF,#5B5CF6);color:#fff;display:grid;place-items:center;font-weight:900;font-size:19px}
    h1{margin:0;color:var(--ink);font-size:30px;line-height:1.15}
    .sub{margin:8px 0 0;color:var(--muted);font-size:14px}
    label{display:block;margin:0 0 8px;font-weight:800;color:var(--ink)}
    input{width:100%;height:48px;border:1px solid #D8E4F4;border-radius:12px;padding:0 14px;font-size:16px;outline:none;background:#FBFDFF;color:var(--ink)}
    input:focus{border-color:#98B8FF;box-shadow:0 0 0 4px #EAF1FF}
    button{width:100%;height:48px;margin-top:16px;border:0;border-radius:12px;background:var(--primary);color:#fff;font-size:17px;font-weight:900;cursor:pointer;box-shadow:0 10px 22px rgba(47,107,255,.22)}
    .error{min-height:20px;margin-top:12px;color:var(--bad);font-size:14px;font-weight:700}
    @media(max-width:820px){.shell{grid-template-columns:1fr}.visual{min-height:180px}.panel{padding:30px 24px}h1{font-size:25px}}
  </style>
</head>
<body>
  <main class="shell">
    <section class="visual" aria-hidden="true"></section>
    <section class="panel">
      <div class="brand"><div class="logo">ST</div><div><h1>竞品排名监测看板</h1><p class="sub">请输入访问密码</p></div></div>
      <form method="post" action="/api/login">
        <label for="password">访问密码</label>
        <input id="password" name="password" type="password" autocomplete="current-password" autofocus />
        <button type="submit">进入看板</button>
        <div class="error">${escapeHtml(errorMessage)}</div>
      </form>
    </section>
  </main>
</body>
</html>`,
    {
      status,
      headers: { 'content-type': 'text/html; charset=utf-8' },
    },
  );
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[char]);
}

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
