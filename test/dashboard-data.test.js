import test from 'node:test';
import assert from 'node:assert/strict';

import { buildDashboardPayload } from '../src/dashboard-data.js';
import worker from '../src/worker.js';

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

  assert.deepEqual(payload.latest_rows[1], {
    date: '2026-06-15',
    brand: 'ugphone',
    country: 'BR',
    status: 'PENDING_TODAY',
    data_origin: 'pending',
    revenue_rank_tools: null,
  });

  assert.deepEqual(payload.latest_rows.at(-1), {
    date: '2026-06-15',
    brand: 'vsphone',
    country: 'IN',
    status: 'PENDING_TODAY',
    data_origin: 'pending',
    revenue_rank_tools: null,
  });

  assert.deepEqual(payload.overview, {
    success_count: 1,
    pending_count: 78,
    failed_count: 1,
    product_count: 4,
    country_count: 20,
    latest_monitor_date: '2026-06-15',
    last_run_status: 'COMPLETED',
  });

  assert.equal(payload.series_rows.length, 3);
  assert.equal(payload.series_rows[0].revenue_rank_tools, 9);
  assert.equal(
    payload.series_rows.find((row) => row.date === '2026-06-15' && row.brand === 'ugphone').raw_tooltip_text,
    'No. 2 in Tools',
  );
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

test('ingest rejects requests when INGEST_TOKEN is not configured', async () => {
  const db = new FakeDb();
  const response = await worker.fetch(ingestRequest(), { DB: db }, { waitUntil() {} });

  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: 'INGEST_TOKEN is not configured' });
  assert.equal(db.runs.length, 0);
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
