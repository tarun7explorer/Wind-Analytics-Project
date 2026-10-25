import test from 'node:test';
import assert from 'node:assert/strict';
import { validateAnalyticsReport } from '../src/services/validateAnalytics.js';
import { fetchMonthlyAnalytics } from '../src/services/api.js';
import { buildMonthlyCsv } from '../src/services/csvExport.js';

function report(overrides = {}) {
  const source = {
    delivery_time: '2026-01-01T00:00:00Z', forecast_mw: 0, actual_mw: 0,
    signed_error_mw: 0, absolute_error_mw: 0, percentage_error: null,
    forecast_published_at: '2025-12-31T11:00:00Z', decision_cutoff: '2025-12-31T12:00:00Z', matched: true,
  };
  const hourly = { ...source, actual_half_hour_count: 2 };
  return {
    year: 2026, month: 1,
    period_start: '2026-01-01T00:00:00Z', period_end_exclusive: '2026-02-01T00:00:00Z',
    source_retrieved_at: '2026-10-25T12:00:00Z',
    timezone: 'Europe/London', unit: 'MW', source_contract_status: 'verified_live_contract',
    decision_cutoff_rule: '12:00 Europe/London on the day before each delivery date',
    expected_intervals: 1, actual_intervals: 1, forecast_intervals: 1, matched_intervals: 1,
    unmatched_intervals: 0, missing_actual_intervals: 0, missing_forecast_intervals: 0,
    metrics: { matched_intervals: 1, mae_mw: 0, rmse_mw: 0, wape_percent: null },
    hourly_analysis: {
      comparison_frequency: 'hourly', actual_method: 'mean of both half-hours',
      expected_periods: 1, eligible_actual_periods: 1, actual_incomplete_periods: 0,
      forecast_periods: 1, matched_periods: 1, unmatched_periods: 0,
      actual_completeness_percent: 100, forecast_coverage_percent: 100,
      exact_half_hour_matched_periods: 1, exact_half_hour_expected_periods: 1,
      exact_half_hour_coverage_percent: 100,
      metrics: { matched_intervals: 1, mae_mw: 0, rmse_mw: 0, wape_percent: null },
    },
    records: [source], hourly_records: [hourly], ...overrides,
  };
}

test('accepts matched zero-MW hourly values without treating zero as missing', () => {
  const valid = validateAnalyticsReport(report(), 2026, 1);
  assert.equal(valid.hourlyRecords[0].actual_mw, 0);
  assert.equal(valid.hourlyRecords[0].forecast_mw, 0);
});

test('accepts incomplete half-hour actual provenance only with null hourly actual', () => {
  const value = report({
    hourly_analysis: {
      ...report().hourly_analysis, eligible_actual_periods: 0, actual_incomplete_periods: 1,
      forecast_periods: 1, matched_periods: 0, unmatched_periods: 1,
      actual_completeness_percent: 0, forecast_coverage_percent: null,
      metrics: { matched_intervals: 0, mae_mw: null, rmse_mw: null, wape_percent: null },
    },
    hourly_records: [{ ...report().hourly_records[0], actual_mw: null, actual_half_hour_count: 1,
      signed_error_mw: null, absolute_error_mw: null, percentage_error: null, matched: false }],
  });
  assert.equal(validateAnalyticsReport(value, 2026, 1).hourlyRecords[0].actual_mw, null);
});

test('rejects forecast publication after day-ahead cutoff', () => {
  const value = report({ hourly_records: [{ ...report().hourly_records[0], forecast_published_at: '2025-12-31T12:00:01Z' }] });
  assert.throws(() => validateAnalyticsReport(value, 2026, 1), /after the decision cutoff/);
});

test('rejects records crossing the exclusive selected-month boundary', () => {
  const value = report({ hourly_records: [{ ...report().hourly_records[0], delivery_time: '2026-02-01T00:00:00Z' }] });
  assert.throws(() => validateAnalyticsReport(value, 2026, 1), /outside the selected half-open month/);
});

test('requests one full report for the selected year and month', async () => {
  const originalFetch = globalThis.fetch;
  const requested = [];
  let requestOptions;
  globalThis.fetch = async (url, options) => {
    requested.push(String(url));
    requestOptions = options;
    return { ok: true, json: async () => report() };
  };
  try {
    const result = await fetchMonthlyAnalytics(2026, 1);
    assert.equal(result.hourlyRecords.length, 1);
    assert.deepEqual(requested, ['/api/analytics/report?year=2026&month=1']);
    assert.equal(requestOptions.cache, 'no-store');
  } finally { globalThis.fetch = originalFetch; }
});

test('hourly CSV labels hourly mean, provenance and preserves blank versus zero', () => {
  const csv = buildMonthlyCsv([
    { ...report().hourly_records[0] },
    { ...report().hourly_records[0], delivery_time: '2026-01-01T01:00:00Z', actual_mw: null,
      actual_half_hour_count: 1, forecast_mw: null, signed_error_mw: null, absolute_error_mw: null,
      percentage_error: null, forecast_published_at: null, matched: false },
  ], 'hourly');
  const [header, zero, missing] = csv.split('\r\n');
  assert.equal(header, 'comparison_frequency,delivery_time_utc,actual_hourly_mean_mw,forecast_hourly_mw,valid_fuelhh_half_hours,signed_error_mw,absolute_error_mw,percentage_error,forecast_published_at_utc,decision_cutoff_utc,matched,data_status');
  assert.match(zero, /^"hourly","2026-01-01T00:00:00Z","0","0","2","0","0","","2025-12-31T11:00:00Z"/);
  assert.match(missing, /"hourly","2026-01-01T01:00:00Z","","","1","","","","","2025-12-31T12:00:00Z","false","Actual incomplete \(1\/2\)"$/);
});
