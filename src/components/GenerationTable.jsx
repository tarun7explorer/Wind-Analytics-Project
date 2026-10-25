import { useEffect, useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from 'lucide-react';
import { formatDeliveryTime } from '../utils/dateUtils.js';
import { formatCount, formatMetric, formatMw, formatSignedMw } from '../utils/formatters.js';

const PAGE_SIZE = 24;

function rowStatus(row) {
  if (row.actual_half_hour_count != null && row.actual_half_hour_count < 2) return { label: `Actual incomplete (${row.actual_half_hour_count}/2)`, tone: 'warning' };
  if (row.actual_mw == null && row.forecast_mw == null) return { label: 'No source data', tone: 'muted' };
  if (row.actual_mw == null) return { label: 'Actual missing', tone: 'warning' };
  if (row.forecast_mw == null) return { label: 'Forecast missing', tone: 'warning' };
  if (!row.matched) return { label: 'Unmatched', tone: 'warning' };
  return { label: 'Matched', tone: 'success' };
}

function errorPercent(row) {
  if (row.percentage_error == null) {
    return row.matched && row.actual_mw === 0 ? 'N/A (actual is 0)' : 'Missing';
  }
  const value = Number(row.percentage_error);
  const formatted = formatMetric(Math.abs(value), '%', 2);
  return `${value > 0 ? '+' : value < 0 ? '−' : ''}${formatted}`;
}

function SortIcon({ active, direction }) {
  if (!active) return <ArrowUpDown size={13} aria-hidden="true" />;
  return direction === 'asc' ? <ArrowUp size={13} aria-hidden="true" /> : <ArrowDown size={13} aria-hidden="true" />;
}

function SortableHeader({ label, field, sort, onSort }) {
  const active = sort.key === field;
  const direction = active ? sort.direction : null;
  const ariaLabel = `Sort by ${label.toLowerCase()}${direction ? `, ${direction === 'asc' ? 'ascending' : 'descending'}` : ''}`;
  return (
    <th scope="col" aria-sort={direction === 'asc' ? 'ascending' : direction === 'desc' ? 'descending' : 'none'}>
      <button type="button" aria-label={ariaLabel} onClick={() => onSort(field)}>
        {label}<SortIcon active={active} direction={direction} />
      </button>
    </th>
  );
}

export default function GenerationTable({ records }) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [sort, setSort] = useState({ key: 'delivery_time', direction: 'asc' });
  const [page, setPage] = useState(0);

  useEffect(() => setPage(0), [records]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const rows = records.filter((row) => {
      const status = rowStatus(row);
      const statusPass = filter === 'all' || (filter === 'matched' ? row.matched : !row.matched);
      const searchPass = !normalizedQuery
        || status.label.toLowerCase().includes(normalizedQuery)
        || formatDeliveryTime(row.delivery_time, { year: 'numeric' }).toLowerCase().includes(normalizedQuery);
      return statusPass && searchPass;
    });
    rows.sort((a, b) => {
      const left = a[sort.key];
      const right = b[sort.key];
      if (left == null && right == null) return 0;
      if (left == null) return 1;
      if (right == null) return -1;
      const comparison = sort.key === 'delivery_time'
        ? new Date(left) - new Date(right)
        : Number(left) - Number(right);
      return sort.direction === 'asc' ? comparison : -comparison;
    });
    return rows;
  }, [records, query, filter, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const visible = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const toggleSort = (key) => {
    setSort((current) => current.key === key
      ? { key, direction: current.direction === 'asc' ? 'desc' : 'asc' }
      : { key, direction: key === 'delivery_time' ? 'asc' : 'desc' });
  };

  return (
    <section className="panel table-panel" aria-labelledby="records-title">
      <div className="panel-heading table-heading">
        <div>
          <div className="eyebrow">HOURLY COMPARISON DETAIL</div>
          <h2 id="records-title">Hourly generation records</h2>
          <p>Actual is the mean of both consecutive half-hour FUELHH values. Errors are hourly forecast minus hourly actual; missing differs from 0 MW.</p>
        </div>
        <div className="table-tools">
          <label className="search-box">
            <Search size={15} aria-hidden="true" />
            <span className="sr-only">Search delivery time or status</span>
            <input value={query} onChange={(event) => { setQuery(event.target.value); setPage(0); }} placeholder="Search records" />
          </label>
          <label className="sr-only" htmlFor="record-filter">Filter records</label>
          <select id="record-filter" className="table-filter" value={filter} onChange={(event) => { setFilter(event.target.value); setPage(0); }}>
            <option value="all">All intervals</option>
            <option value="matched">Matched</option>
            <option value="unmatched">Missing / unmatched</option>
          </select>
        </div>
      </div>

      <div className="table-scroll">
        <table>
          <caption className="sr-only">Hourly national wind forecast and actual comparison records for the selected month</caption>
          <thead>
            <tr>
              <SortableHeader label="Delivery time (UK)" field="delivery_time" sort={sort} onSort={toggleSort} />
              <SortableHeader label="Actual hourly mean (MW)" field="actual_mw" sort={sort} onSort={toggleSort} />
              <SortableHeader label="Forecast (MW)" field="forecast_mw" sort={sort} onSort={toggleSort} />
              <th scope="col">Valid FUELHH half-hours</th>
              <SortableHeader label="Signed error (MW)" field="signed_error_mw" sort={sort} onSort={toggleSort} />
              <SortableHeader label="Absolute error (MW)" field="absolute_error_mw" sort={sort} onSort={toggleSort} />
              <SortableHeader label="Error (%)" field="percentage_error" sort={sort} onSort={toggleSort} />
              <th scope="col">Forecast published (UK)</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => {
              const status = rowStatus(row);
              return (
                <tr key={row.delivery_time}>
                  <td className="time-cell">{formatDeliveryTime(row.delivery_time, { weekday: 'short', year: 'numeric' })}</td>
                  <td>{row.actual_mw == null ? <span className="missing-value">Missing</span> : formatMw(row.actual_mw)}</td>
                  <td>{row.forecast_mw == null ? <span className="missing-value">Missing</span> : formatMw(row.forecast_mw)}</td>
                  <td>{row.actual_half_hour_count} / 2</td>
                  <td className={row.signed_error_mw > 0 ? 'error-positive' : row.signed_error_mw < 0 ? 'error-negative' : ''}>{formatSignedMw(row.signed_error_mw)}</td>
                  <td>{row.absolute_error_mw == null ? <span className="missing-value">Missing</span> : formatMw(row.absolute_error_mw)}</td>
                  <td>{errorPercent(row)}</td>
                  <td className="published-cell">{row.forecast_published_at ? formatDeliveryTime(row.forecast_published_at, { year: 'numeric' }) : <span className="missing-value">Missing</span>}</td>
                  <td><span className={`status-pill ${status.tone}`}><i aria-hidden="true" />{status.label}</span></td>
                </tr>
              );
            })}
            {!visible.length && <tr><td className="no-rows" colSpan="9">No intervals match this filter.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="table-footer">
        <span>Showing {filtered.length ? formatCount(page * PAGE_SIZE + 1) : '0'}–{formatCount(Math.min((page + 1) * PAGE_SIZE, filtered.length))} of {formatCount(filtered.length)} filtered · {formatCount(records.length)} total</span>
        <div className="pagination" aria-label="Records pagination">
          <button type="button" className="button button-small" disabled={page === 0} onClick={() => setPage((value) => value - 1)} aria-label="Previous page">Previous</button>
          <span aria-live="polite">Page {page + 1} of {pageCount}</span>
          <button type="button" className="button button-small" disabled={page + 1 >= pageCount} onClick={() => setPage((value) => value + 1)} aria-label="Next page">Next</button>
        </div>
      </div>
    </section>
  );
}
