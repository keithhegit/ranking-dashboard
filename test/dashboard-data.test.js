import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { buildDashboardPayload } from '../src/dashboard-data.js';
import worker, { rankingRowPrioritySql } from '../src/worker.js';

test('buildDashboardPayload fills missing latest product-country pairs as pending', () => {
  const payload = buildDashboardPayload(
    [
      {
        date: '2026-06-14',
        brand: 'ugphone',
        country: 'TH',
        status: 'SUCCESS',
        data_origin: 'archive',
        revenue_rank_tools: '9',
      },
      {
        date: '2026-06-15',
        brand: 'ugphone',
        country: 'TH',
        status: 'SUCCESS',
        data_origin: 'sensor_tower',
        revenue_rank_tools: '2',
        tooltip_date: '2026-06-15',
        status_detail: 'Rank found in tooltip',
        source_url: 'https://example.test/app/ugphone',
        crawl_time: '2026-06-15T09:59:00.000Z',
        raw_tooltip_text: 'No. 2 in Tools',
        screenshot_path: 'screenshots/ugphone-th.png',
      },
      {
        date: '2026-06-15',
        brand: 'ldcloud',
        country: 'BR',
        status: 'FAILED',
        data_origin: 'sensor_tower',
        revenue_rank_tools: null,
      },
    ],
    [{ date: '2026-06-15', status: 'COMPLETED' }],
    '2026-06-15T10:00:00.000Z',
  );

  assert.equal(payload.generated_at, '2026-06-15T10:00:00.000Z');
  assert.equal(payload.latest_monitor_file_date, '2026-06-15');
  assert.deepEqual(payload.brands, ['ugphone', 'ldcloud', 'redfinger', 'vsphone']);
  assert.equal(payload.brand_labels.ugphone, 'UGPhone');
  assert.equal(payload.latest_rows.length, 80);

  const latestUgphoneThailand = payload.latest_rows[0];
  assert.equal(latestUgphoneThailand.date, '2026-06-15');
  assert.equal(latestUgphoneThailand.brand, 'ugphone');
  assert.equal(latestUgphoneThailand.country, 'TH');
  assert.equal(latestUgphoneThailand.status, 'SUCCESS');
  assert.equal(latestUgphoneThailand.data_origin, 'sensor_tower');
  assert.equal(latestUgphoneThailand.revenue_rank_tools, 2);
  assert.equal(latestUgphoneThailand.tooltip_date, '2026-06-15');
  assert.equal(latestUgphoneThailand.status_detail, 'Rank found in tooltip');
  assert.equal(latestUgphoneThailand.source_url, 'https://example.test/app/ugphone');
  assert.equal(latestUgphoneThailand.crawl_time, '2026-06-15T09:59:00.000Z');
  assert.equal(latestUgphoneThailand.raw_tooltip_text, 'No. 2 in Tools');
  assert.equal(latestUgphoneThailand.screenshot_path, 'screenshots/ugphone-th.png');

  assert.equal(payload.latest_rows[1].date, '2026-06-15');
  assert.equal(payload.latest_rows[1].brand, 'ugphone');
  assert.equal(payload.latest_rows[1].country, 'BR');
  assert.equal(payload.latest_rows[1].status, 'PENDING_TODAY');
  assert.equal(payload.latest_rows[1].data_origin, 'pending');
  assert.equal(payload.latest_rows[1].revenue_rank_tools, null);

  assert.equal(payload.latest_rows.at(-1).date, '2026-06-15');
  assert.equal(payload.latest_rows.at(-1).brand, 'vsphone');
  assert.equal(payload.latest_rows.at(-1).country, 'IN');
  assert.equal(payload.latest_rows.at(-1).status, 'PENDING_TODAY');
  assert.equal(payload.latest_rows.at(-1).data_origin, 'pending');
  assert.equal(payload.latest_rows.at(-1).revenue_rank_tools, null);

  assert.equal(payload.overview.success_count, 1);
  assert.equal(payload.overview.pending_count, 78);
  assert.equal(payload.overview.failed_count, 1);
  assert.equal(payload.overview.product_count, 4);
  assert.equal(payload.overview.country_count, 20);
  assert.equal(payload.overview.latest_monitor_date, '2026-06-15');
  assert.equal(payload.overview.last_run_status, 'COMPLETED');

  assert.equal(payload.series_rows.length, 3);
  assert.equal(payload.series_rows[0].revenue_rank_tools, 9);
  assert.equal(payload.series_rows.find((row) => row.date === '2026-06-15' && row.brand === 'ugphone').raw_tooltip_text, undefined);
});

test('buildDashboardPayload keeps series rows lightweight while latest rows keep detail fields', () => {
  const payload = buildDashboardPayload(
    [
      {
        date: '2026-06-14',
        brand: 'ugphone',
        country: 'TH',
        status: 'SUCCESS',
        data_origin: 'archive',
        revenue_rank_tools: '9',
        tooltip_date: 'Jun 14, 2026',
        status_detail: 'historical detail should stay out of series',
        source_url: 'https://example.test/historical',
        crawl_time: '2026-06-14T09:59:00.000Z',
        raw_tooltip_text: 'large historical tooltip text',
        screenshot_path: 'screenshots/history.png',
      },
      {
        date: '2026-06-15',
        brand: 'ugphone',
        country: 'TH',
        status: 'SUCCESS',
        data_origin: 'sensor_tower',
        revenue_rank_tools: '2',
        tooltip_date: 'Jun 15, 2026',
        status_detail: 'latest detail should stay available',
        source_url: 'https://example.test/latest',
        crawl_time: '2026-06-15T09:59:00.000Z',
        raw_tooltip_text: 'latest tooltip text',
        screenshot_path: 'screenshots/latest.png',
      },
    ],
    [{ date: '2026-06-15', status: 'COMPLETED' }],
    '2026-06-15T10:00:00.000Z',
  );

  const seriesRow = payload.series_rows.find((row) => row.date === '2026-06-14' && row.brand === 'ugphone' && row.country === 'TH');
  assert.deepEqual(Object.keys(seriesRow).sort(), ['brand', 'country', 'date', 'revenue_rank_tools', 'status']);

  const latestRow = payload.latest_rows.find((row) => row.brand === 'ugphone' && row.country === 'TH');
  assert.equal(latestRow.source_url, 'https://example.test/latest');
  assert.equal(latestRow.raw_tooltip_text, 'latest tooltip text');
  assert.equal(latestRow.screenshot_path, 'screenshots/latest.png');
});

test('buildDashboardPayload uses updated run timestamp for last run status', () => {
  const payload = buildDashboardPayload(
    [],
    [
      {
        date: '2026-06-15',
        source: 'scheduled',
        status: 'COMPLETED',
        created_at: '2026-06-15T01:00:00.000Z',
        updated_at: '2026-06-15T01:00:00.000Z',
      },
      {
        date: '2026-06-15',
        source: 'scheduled',
        status: 'FAILED',
        created_at: '2026-06-15T00:00:00.000Z',
        updated_at: '2026-06-15T02:00:00.000Z',
      },
    ],
    '2026-06-15T10:00:00.000Z',
  );

  assert.equal(payload.overview.last_run_status, 'FAILED');
});

test('buildDashboardPayload normalizes compact YYYYMMDD dates', () => {
  const payload = buildDashboardPayload(
    [
      {
        date: '20260615',
        brand: 'ugphone',
        country: 'US',
        status: 'SUCCESS',
        revenue_rank_tools: '385',
      },
    ],
    [{ date: '20260615', status: 'COMPLETED' }],
    '2026-06-15T10:00:00.000Z',
  );

  assert.equal(payload.latest_monitor_file_date, '2026-06-15');
  assert.equal(payload.overview.latest_monitor_date, '2026-06-15');
  assert.equal(payload.latest_rows.find((row) => row.brand === 'ugphone' && row.country === 'US').date, '2026-06-15');
});

test('buildDashboardPayload counts partial success with a rank as successful coverage', () => {
  const payload = buildDashboardPayload(
    [
      {
        date: '2026-06-15',
        brand: 'ugphone',
        country: 'US',
        status: 'PARTIAL_SUCCESS',
        revenue_rank_tools: '385',
      },
    ],
    [{ date: '2026-06-15', status: 'COMPLETED' }],
    '2026-06-15T10:00:00.000Z',
  );

  assert.equal(payload.overview.success_count, 1);
  assert.equal(payload.overview.failed_count, 0);
  assert.equal(payload.latest_rows.find((row) => row.brand === 'ugphone' && row.country === 'US').status, 'PARTIAL_SUCCESS');
});

test('buildDashboardPayload treats known no-category markets as terminal non-failures', () => {
  const payload = buildDashboardPayload(
    [
      {
        date: '2026-06-15',
        brand: 'vsphone',
        country: 'US',
        status: 'NO_CATEGORY_RANKING_DATA',
        status_detail: 'Sensor Tower page shows no available category ranking data for this market',
      },
    ],
    [{ date: '2026-06-15', status: 'COMPLETED' }],
    '2026-06-15T10:00:00.000Z',
  );

  const latestVsphoneUnitedStates = payload.latest_rows.find((row) => row.brand === 'vsphone' && row.country === 'US');
  assert.equal(payload.overview.no_category_data_count, 1);
  assert.equal(payload.overview.failed_count, 0);
  assert.equal(payload.overview.review_count, 0);
  assert.equal(latestVsphoneUnitedStates.data_quality_status, 'verified');
});

test('buildDashboardPayload includes fields required by the original dashboard shell', () => {
  const payload = buildDashboardPayload(
    [
      {
        date: '2026-06-15',
        brand: 'ugphone',
        country: 'TH',
        status: 'PARTIAL_SUCCESS',
        data_origin: 'linux-runner',
        revenue_rank_tools: '2',
        tooltip_date: 'Jun 15, 2026',
        status_detail: 'selected tooltip has partial ranks',
        source_url: 'https://example.test/app/ugphone?country=TH',
        crawl_time: '2026-06-15 00:03:00',
        raw_tooltip_text: 'UgPhone 收入排行 - 工具 #2',
        screenshot_path: '/home/ubuntu/ranking-dashboard/screenshots/ugphone_TH.png',
      },
    ],
    [{ date: '2026-06-15', source: 'linux-runner', status: 'COMPLETED', row_count: 1 }],
    '2026-06-15T10:00:00.000Z',
  );

  assert.equal(payload.overview.partial_count, 1);
  assert.equal(payload.overview.today_crawled_count, 1);
  assert.equal(payload.overview.today_uncrawled_count, 79);
  assert.equal(payload.overview.history_fallback_count, 0);
  assert.equal(payload.overview.capture_failed_count, 0);
  assert.equal(payload.overview.review_count, 1);
  assert.equal(payload.overview.fetch_mode, '每日自动监测');
  assert.equal(payload.country_names.TH, '泰国');
  assert.ok(payload.market_tiers.focus.countries.includes('TH'));

  const latestUgphoneThailand = payload.latest_rows.find((row) => row.brand === 'ugphone' && row.country === 'TH');
  assert.equal(latestUgphoneThailand.package, 'com.tykeji.ugphone');
  assert.equal(latestUgphoneThailand.country_display, '泰国 TH');
  assert.equal(latestUgphoneThailand.market_tier, '重点市场');
  assert.equal(latestUgphoneThailand.latest_fetch_date, '2026-06-15');
  assert.equal(latestUgphoneThailand.fetch_mode, '每日自动监测');
  assert.equal(latestUgphoneThailand.data_quality_status, 'need_review');
  assert.equal(latestUgphoneThailand.data_quality_detail, 'selected tooltip has partial ranks');
  assert.equal(latestUgphoneThailand.review_reason, '排名日期非当日，需验证');
});

test('buildDashboardPayload computes review fields after copying source detail fields', () => {
  const payload = buildDashboardPayload(
    [
      {
        date: '2026-06-15',
        brand: 'ugphone',
        country: 'US',
        status: 'SUCCESS',
        revenue_rank_tools: '385',
        tooltip_date: 'Jun 14, 2026',
        status_detail: 'tooltip is stale',
      },
    ],
    [{ date: '2026-06-15', source: 'linux-runner', status: 'COMPLETED', row_count: 1 }],
    '2026-06-15T10:00:00.000Z',
  );

  const latestUgphoneUnitedStates = payload.latest_rows.find((row) => row.brand === 'ugphone' && row.country === 'US');
  assert.equal(latestUgphoneUnitedStates.data_quality_status, 'need_review');
  assert.equal(latestUgphoneUnitedStates.data_quality_detail, 'tooltip is stale');
  assert.equal(latestUgphoneUnitedStates.review_reason, '排名日期非当日，需验证');
  assert.equal(payload.overview.review_count, 1);
});

test('public dashboard keeps bootstrap data before loading dynamic API data', () => {
  const html = readFileSync(new URL('../public/index.html', import.meta.url), 'utf8');

  assert.doesNotMatch(html, /let DATA = null;/);
  assert.match(html, /let DATA = \{ countries: \[/);
  assert.match(html, /fetch\("\/api\/dashboard"/);
  assert.match(html, /RANK_CAPTURE_FAILED/);
  assert.match(html, /TOOLTIP_PARSE_FAILED/);
});

test('ingest rejects requests when INGEST_TOKEN is not configured', async () => {
  const db = new FakeDb();
  const response = await worker.fetch(ingestRequest(), { DB: db }, { waitUntil() {} });

  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: 'INGEST_TOKEN is not configured' });
  assert.equal(db.runs.length, 0);
});

test('worker returns empty favicon response instead of a noisy 404', async () => {
  const response = await worker.fetch(new Request('https://dashboard.test/favicon.ico'), {}, { waitUntil() {} });

  assert.equal(response.status, 204);
});

test('dashboard API requires login cookie', async () => {
  const response = await worker.fetch(new Request('https://dashboard.test/api/dashboard'), {}, { waitUntil() {} });

  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), { error: 'Authentication required' });
});

test('unauthenticated dashboard page renders the branded password form', async () => {
  const response = await worker.fetch(new Request('https://dashboard.test/'), {}, { waitUntil() {} });
  const html = await response.text();

  assert.equal(response.status, 200);
  assert.match(html, /竞品排名监测看板/);
  assert.match(html, /请输入访问密码/);
  assert.match(html, /roblox-650-80\.jpg/);
  assert.match(html, /type="password"/);
});

test('login rejects the wrong password', async () => {
  const response = await worker.fetch(
    new Request('https://dashboard.test/api/login', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ password: 'wrong' }),
    }),
    {},
    { waitUntil() {} },
  );
  const html = await response.text();

  assert.equal(response.status, 401);
  assert.match(html, /密码不正确/);
  assert.equal(response.headers.get('set-cookie'), null);
});

test('login accepts the configured password and allows dashboard API access', async () => {
  const loginResponse = await worker.fetch(
    new Request('https://dashboard.test/api/login', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ password: 'makeuggreatagain' }),
    }),
    {},
    { waitUntil() {} },
  );
  const cookie = loginResponse.headers.get('set-cookie');

  assert.equal(loginResponse.status, 303);
  assert.match(loginResponse.headers.get('location'), /^\//);
  assert.match(cookie, /ug_dashboard_auth=/);
  assert.match(cookie, /HttpOnly/);
  assert.match(cookie, /Secure/);

  const dashboardResponse = await worker.fetch(
    new Request('https://dashboard.test/api/dashboard', {
      headers: { cookie },
    }),
    {},
    { waitUntil() {} },
  );

  assert.equal(dashboardResponse.status, 200);
  assert.equal((await dashboardResponse.json()).latest_monitor_file_date, '');
});

test('authenticated page requests are served from static assets', async () => {
  const loginResponse = await worker.fetch(
    new Request('https://dashboard.test/api/login', {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ password: 'makeuggreatagain' }),
    }),
    {},
    { waitUntil() {} },
  );
  const cookie = loginResponse.headers.get('set-cookie');
  const assets = {
    fetch: async () => new Response('<!doctype html><title>asset dashboard</title>', { headers: { 'content-type': 'text/html' } }),
  };

  const response = await worker.fetch(new Request('https://dashboard.test/', { headers: { cookie } }), { ASSETS: assets }, { waitUntil() {} });

  assert.equal(response.status, 200);
  assert.match(await response.text(), /asset dashboard/);
});

test('ingest rejects requests with the wrong bearer token', async () => {
  const db = new FakeDb();
  const response = await worker.fetch(ingestRequest('wrong-token'), { DB: db, INGEST_TOKEN: 'secret' }, { waitUntil() {} });

  assert.equal(response.status, 401);
  assert.deepEqual(await response.json(), { error: 'Unauthorized' });
  assert.equal(db.runs.length, 0);
});

test('ingest writes optional CSV detail fields to D1 ranking rows', async () => {
  const db = new FakeDb();
  const response = await worker.fetch(
    ingestRequest('secret'),
    { DB: db, INGEST_TOKEN: 'secret' },
    { waitUntil() {} },
  );

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { accepted: 1, snapshot_key: null });

  const rankingInsert = db.runs.find((run) => run.sql.includes('INSERT INTO ranking_rows'));
  assert.ok(rankingInsert.sql.includes('tooltip_date'));
  assert.ok(rankingInsert.sql.includes('status_detail'));
  assert.ok(rankingInsert.sql.includes('source_url'));
  assert.ok(rankingInsert.sql.includes('crawl_time'));
  assert.ok(rankingInsert.sql.includes('raw_tooltip_text'));
  assert.ok(rankingInsert.sql.includes('screenshot_path'));
  assert.deepEqual(rankingInsert.values, [
    '2026-06-15',
    'ugphone',
    'TH',
    'SUCCESS',
    'csv_upload',
    2,
    'csv_upload',
    '2026-06-15',
    'Rank found in tooltip',
    'https://example.test/app/ugphone',
    '2026-06-15T09:59:00.000Z',
    'No. 2 in Tools',
    'screenshots/ugphone-th.png',
  ]);

  const runUpsert = db.runs.find((run) => run.sql.includes('INSERT INTO update_runs'));
  assert.ok(runUpsert.sql.includes('idempotency_key'));
  assert.ok(runUpsert.sql.includes('ON CONFLICT(idempotency_key) DO UPDATE SET'));
  assert.deepEqual(runUpsert.values, [
    '2026-06-15:csv_upload:COMPLETED',
    '2026-06-15',
    'csv_upload',
    'COMPLETED',
    1,
    null,
    null,
  ]);
});

test('ingest normalizes compact YYYYMMDD dates before writing D1 rows', async () => {
  const db = new FakeDb();
  const response = await worker.fetch(
    ingestRequest('secret', '20260615'),
    { DB: db, INGEST_TOKEN: 'secret' },
    { waitUntil() {} },
  );

  assert.equal(response.status, 200);

  const rankingInsert = db.runs.find((run) => run.sql.includes('INSERT INTO ranking_rows'));
  assert.equal(rankingInsert.values[0], '2026-06-15');

  const runUpsert = db.runs.find((run) => run.sql.includes('INSERT INTO update_runs'));
  assert.equal(runUpsert.values[0], '2026-06-15:csv_upload:COMPLETED');
  assert.equal(runUpsert.values[1], '2026-06-15');
});

test('ingest ignores rows outside configured products and countries', async () => {
  const db = new FakeDb();
  const response = await worker.fetch(
    new Request('https://dashboard.test/api/ingest', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: 'Bearer secret' },
      body: JSON.stringify({
        date: '2026-06-15',
        source: 'csv_upload',
        rows: [
          { brand: 'unknown', country: 'TH', revenue_rank_tools: '1' },
          { brand: 'ugphone', country: 'ZZ', revenue_rank_tools: '2' },
        ],
      }),
    }),
    { DB: db, INGEST_TOKEN: 'secret' },
    { waitUntil() {} },
  );

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { accepted: 0, snapshot_key: null });
  assert.equal(db.runs.filter((run) => run.sql.includes('INSERT INTO ranking_rows')).length, 0);
});

test('ingest SQL prevents RATE_LIMITED rows from overwriting ranked rows', async () => {
  const db = new FakeDb();
  const response = await worker.fetch(
    new Request('https://dashboard.test/api/ingest', {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: 'Bearer secret' },
      body: JSON.stringify({
        date: '2026-06-15',
        source: 'csv_upload',
        rows: [{ brand: 'ugphone', country: 'US', status: 'RATE_LIMITED', revenue_rank_tools: '' }],
      }),
    }),
    { DB: db, INGEST_TOKEN: 'secret' },
    { waitUntil() {} },
  );

  assert.equal(response.status, 200);
  const rankingInsert = db.runs.find((run) => run.sql.includes('INSERT INTO ranking_rows'));
  assert.ok(rankingInsert.sql.includes('WHERE'));
  assert.ok(rankingInsert.sql.includes(rankingRowPrioritySql('excluded')));
  assert.ok(rankingInsert.sql.includes(rankingRowPrioritySql('ranking_rows')));
});

function ingestRequest(token, date = '2026-06-15') {
  const headers = { 'content-type': 'application/json' };
  if (token) {
    headers.authorization = `Bearer ${token}`;
  }

  return new Request('https://dashboard.test/api/ingest', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      date,
      source: 'csv_upload',
      rows: [
        {
          brand: 'ugphone',
          country: 'TH',
          revenue_rank_tools: '2',
          tooltip_date: '2026-06-15',
          status_detail: 'Rank found in tooltip',
          source_url: 'https://example.test/app/ugphone',
          crawl_time: '2026-06-15T09:59:00.000Z',
          raw_tooltip_text: 'No. 2 in Tools',
          screenshot_path: 'screenshots/ugphone-th.png',
        },
      ],
    }),
  });
}

class FakeDb {
  runs = [];

  prepare(sql) {
    return {
      bind: (...values) => ({
        run: async () => {
          this.runs.push({ sql, values });
        },
      }),
      all: async () => ({ results: [] }),
    };
  }
}
