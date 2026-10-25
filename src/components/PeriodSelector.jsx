import { CalendarDays, ChevronDown } from 'lucide-react';
import { MONTHS } from '../utils/dateUtils.js';

export default function PeriodSelector({ year, month, onChange }) {
  const currentYear = new Date().getFullYear();
  return (
    <div className="period-control" role="group" aria-label="Choose reporting period">
      <CalendarDays size={16} aria-hidden="true" />
      <label className="sr-only" htmlFor="report-month">Reporting month</label>
      <span className="select-wrap month-select">
        <select id="report-month" value={month} onChange={(event) => onChange(year, Number(event.target.value))}>
          {MONTHS.map((name, index) => <option key={name} value={index + 1}>{name}</option>)}
        </select>
        <ChevronDown size={14} aria-hidden="true" />
      </span>
      <label className="sr-only" htmlFor="report-year">Reporting year</label>
      <span className="select-wrap year-select">
        <select id="report-year" value={year} onChange={(event) => onChange(Number(event.target.value), month)}>
          {Array.from({ length: Math.max(currentYear - 1999, 1) }, (_, index) => currentYear - index).map((value) => (
            <option key={value} value={value}>{value}</option>
          ))}
        </select>
        <ChevronDown size={14} aria-hidden="true" />
      </span>
    </div>
  );
}
