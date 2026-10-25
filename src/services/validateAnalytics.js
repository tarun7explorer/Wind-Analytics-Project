function isNonNegativeInteger(value) { return Number.isInteger(value) && value >= 0; }
function isNullableFiniteNumber(value) { return value === null || (typeof value === 'number' && Number.isFinite(value)); }
function validDate(value) { return typeof value === 'string' && Number.isFinite(Date.parse(value)); }
function requireCondition(condition, message) {
  if (!condition) throw new Error(`The analytics API returned malformed data: ${message}`);
}

function validateRows(records, start, end, hourly = false) {
  requireCondition(Array.isArray(records), 'records list is missing');
  let prior = start - 1;
  const seen = new Set();
  records.forEach((row) => {
    requireCondition(row && validDate(row.delivery_time), 'record delivery timestamp is invalid');
    const delivery = Date.parse(row.delivery_time);
    requireCondition(delivery >= start && delivery < end, 'record falls outside the selected half-open month');
    requireCondition(delivery > prior && !seen.has(delivery), 'records are not strictly ordered or contain duplicate delivery intervals');
    prior = delivery;
    seen.add(delivery);
    for (const field of ['actual_mw', 'forecast_mw', 'signed_error_mw', 'absolute_error_mw', 'percentage_error']) {
      requireCondition(isNullableFiniteNumber(row[field]), `${field} must be finite or null`);
    }
    requireCondition(validDate(row.decision_cutoff), 'decision cutoff timestamp is invalid');
    requireCondition(row.forecast_published_at === null || validDate(row.forecast_published_at), 'forecast publication timestamp is invalid');
    requireCondition(typeof row.matched === 'boolean', 'record matched flag is invalid');
    if (hourly) {
      requireCondition(isNonNegativeInteger(row.actual_half_hour_count) && row.actual_half_hour_count <= 2, 'actual_half_hour_count must be between 0 and 2');
      requireCondition((row.actual_half_hour_count === 2) === (row.actual_mw !== null), 'hourly actual requires both half-hour source rows');
      requireCondition(row.forecast_published_at === null || Date.parse(row.forecast_published_at) <= Date.parse(row.decision_cutoff), 'selected forecast was published after the decision cutoff');
    }
    const shouldMatch = row.actual_mw !== null && row.forecast_mw !== null;
    requireCondition(row.matched === shouldMatch, 'matched flag disagrees with actual and forecast values');
    requireCondition((row.signed_error_mw !== null) === row.matched, 'error value disagrees with match status');
    if (row.matched) {
      requireCondition(Math.abs(row.signed_error_mw - (row.forecast_mw - row.actual_mw)) < 1e-7, 'signed error is inconsistent');
      requireCondition(Math.abs(row.absolute_error_mw - Math.abs(row.signed_error_mw)) < 1e-7, 'absolute error is inconsistent');
    }
  });
  return records;
}

/** Validate the monthly report and both explicitly distinct frequencies. */
export function validateAnalyticsReport(report, year, month) {
  requireCondition(report && typeof report === 'object', 'monthly report is missing');
  requireCondition(report.year === year && report.month === month, 'report period does not match the selection');
  requireCondition(validDate(report.source_retrieved_at), 'source retrieval timestamp is missing or invalid');
  requireCondition(validDate(report.period_start) && validDate(report.period_end_exclusive), 'month boundaries are invalid');
  const start = Date.parse(report.period_start);
  const end = Date.parse(report.period_end_exclusive);
  requireCondition(start < end && report.timezone === 'Europe/London' && report.unit === 'MW', 'period metadata is invalid');
  requireCondition(typeof report.source_contract_status === 'string' && typeof report.decision_cutoff_rule === 'string', 'source metadata is missing');
  const halfSummary = report;
  for (const field of ['expected_intervals', 'actual_intervals', 'forecast_intervals', 'matched_intervals']) {
    requireCondition(isNonNegativeInteger(halfSummary[field]), `${field} must be a non-negative integer`);
  }
  const sourceRows = validateRows(report.records, start, end, false);
  requireCondition(sourceRows.length === halfSummary.expected_intervals, 'half-hour source record count disagrees with summary');
  requireCondition(sourceRows.filter((row) => row.actual_mw !== null).length === halfSummary.actual_intervals, 'half-hour actual count disagrees with summary');
  requireCondition(sourceRows.filter((row) => row.forecast_mw !== null).length === halfSummary.forecast_intervals, 'half-hour forecast count disagrees with summary');
  requireCondition(sourceRows.filter((row) => row.matched).length === halfSummary.matched_intervals, 'half-hour match count disagrees with summary');
  requireCondition(halfSummary.metrics?.matched_intervals === halfSummary.matched_intervals, 'half-hour metric match count disagrees with summary');

  const hourly = report.hourly_analysis;
  requireCondition(hourly?.comparison_frequency === 'hourly', 'hourly comparison metadata is missing');
  for (const field of ['expected_periods', 'eligible_actual_periods', 'actual_incomplete_periods', 'forecast_periods', 'matched_periods', 'unmatched_periods', 'exact_half_hour_matched_periods', 'exact_half_hour_expected_periods']) {
    requireCondition(isNonNegativeInteger(hourly[field]), `hourly_analysis.${field} must be a non-negative integer`);
  }
  const hourlyRows = validateRows(report.hourly_records, start, end, true);
  requireCondition(hourlyRows.length === hourly.expected_periods, 'hourly record count disagrees with summary');
  const eligible = hourlyRows.filter((row) => row.actual_half_hour_count === 2).length;
  const forecastCount = hourlyRows.filter((row) => row.forecast_mw !== null).length;
  const matched = hourlyRows.filter((row) => row.matched).length;
  requireCondition(eligible === hourly.eligible_actual_periods && forecastCount === hourly.forecast_periods && matched === hourly.matched_periods, 'hourly record counts disagree with summary');
  requireCondition(hourly.unmatched_periods === hourly.expected_periods - matched, 'hourly unmatched count is inconsistent');
  requireCondition(hourly.actual_incomplete_periods === hourly.expected_periods - eligible, 'incomplete actual count is inconsistent');
  const expectedActualCoverage = hourly.expected_periods ? eligible / hourly.expected_periods * 100 : null;
  const expectedForecastCoverage = eligible ? matched / eligible * 100 : null;
  requireCondition(hourly.actual_completeness_percent === expectedActualCoverage, 'hourly actual completeness is inconsistent');
  requireCondition(hourly.forecast_coverage_percent === expectedForecastCoverage, 'hourly forecast coverage is inconsistent');
  requireCondition(hourly.exact_half_hour_expected_periods === sourceRows.length && hourly.exact_half_hour_matched_periods === sourceRows.filter((row) => row.matched).length, 'exact half-hour coverage disagrees with source records');
  requireCondition(hourly.metrics?.matched_intervals === matched, 'hourly metric match count disagrees with records');
  for (const field of ['mae_mw', 'rmse_mw', 'wape_percent']) requireCondition(isNullableFiniteNumber(hourly.metrics[field]), `hourly metrics.${field} must be finite or null`);
  return { summary: report, records: sourceRows, hourlyRecords: hourlyRows };
}
