export const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export function monthTitle(year, month) {
  return `${MONTHS[month - 1]} ${year}`;
}

export function formatDeliveryTime(value, options = {}) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London',
    timeZoneName: 'short',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  }).format(date);
}

export function formatTimestamp(value) {
  if (!value) return 'No publication selected';
  return `${formatDeliveryTime(value, { year: 'numeric' })} UK`;
}
