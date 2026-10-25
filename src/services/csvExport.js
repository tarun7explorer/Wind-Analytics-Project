const columns = [
  ['delivery_time_utc', 'delivery_time'],
  ['actual_mw', 'actual_mw'],
  ['forecast_mw', 'forecast_mw'],
  ['signed_error_mw', 'signed_error_mw'],
  ['absolute_error_mw', 'absolute_error_mw'],
  ['percentage_error', 'percentage_error'],
  ['forecast_published_at_utc', 'forecast_published_at'],
  ['decision_cutoff_utc', 'decision_cutoff'],
  ['matched', 'matched'],
  ['data_status', 'status'],
];

function statusFor(row) {
  if (row.actual_half_hour_count != null && row.actual_half_hour_count < 2) return `Actual incomplete (${row.actual_half_hour_count}/2)`;
  if (row.actual_mw == null && row.forecast_mw == null) return 'No source data';
  if (row.actual_mw == null) return 'Actual missing';
  if (row.forecast_mw == null) return 'Forecast missing';
  return row.matched ? 'Matched' : 'Unmatched';
}

function quoteCsv(value) {
  return `"${String(value ?? '').replaceAll('"', '""')}"`;
}

/** Export one explicit frequency; blank stays blank and zero stays zero. */
export function buildMonthlyCsv(records, frequency = 'half-hour-source') {
  const selectedColumns = frequency === 'hourly'
    ? [
      ['delivery_time_utc', 'delivery_time'], ['actual_hourly_mean_mw', 'actual_mw'], ['forecast_hourly_mw', 'forecast_mw'],
      ['valid_fuelhh_half_hours', 'actual_half_hour_count'], ['signed_error_mw', 'signed_error_mw'],
      ['absolute_error_mw', 'absolute_error_mw'], ['percentage_error', 'percentage_error'],
      ['forecast_published_at_utc', 'forecast_published_at'], ['decision_cutoff_utc', 'decision_cutoff'],
      ['matched', 'matched'], ['data_status', 'status'],
    ]
    : columns;
  const headers = ['comparison_frequency', ...selectedColumns.map(([header]) => header)];
  const rows = records.map((record) => [quoteCsv(frequency), ...selectedColumns.map(([, field]) => (
    quoteCsv(field === 'status' ? statusFor(record) : record[field])
  ))].join(','));
  return [headers.join(','), ...rows].join('\r\n');
}
