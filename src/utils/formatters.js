export const numberFormat = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 1 });
const preciseFormat = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });

export function formatMw(value, digits = 1) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  return `${new Intl.NumberFormat('en-GB', { maximumFractionDigits: digits }).format(Number(value))} MW`;
}

export function formatMetric(value, suffix = '', digits = 1) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  return `${new Intl.NumberFormat('en-GB', { maximumFractionDigits: digits }).format(Number(value))}${suffix}`;
}

export function formatCount(value) {
  return numberFormat.format(Number(value) || 0);
}

export function formatSignedMw(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  const amount = Number(value);
  return `${amount > 0 ? '+' : ''}${preciseFormat.format(amount)} MW`;
}
