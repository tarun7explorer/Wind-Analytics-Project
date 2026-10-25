import { validateAnalyticsReport } from './validateAnalytics.js';

const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '');

async function requestJson(path, signal) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Could not reach the analytics API. Check that the FastAPI server is running.');
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : `Request failed (${response.status}).`;
    throw new Error(detail);
  }
  if (!payload || typeof payload !== 'object') {
    throw new Error('The analytics API returned an unreadable response.');
  }
  return payload;
}

export async function fetchMonthlyAnalytics(year, month, signal) {
  const query = `year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`;
  const report = await requestJson(`/api/analytics/report?${query}`, signal);
  return validateAnalyticsReport(report, year, month);
}
