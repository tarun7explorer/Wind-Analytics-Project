import { Activity, BarChart3, CheckCheck, Gauge, Wind, Zap } from 'lucide-react';
import { formatCount, formatMetric, formatMw } from '../utils/formatters.js';

function Card({ label, value, note, icon: Icon, accent, tooltip }) {
  return <article className={`kpi-card ${accent}`} title={tooltip}>
    <div className="kpi-topline"><span className="kpi-label">{label}</span><span className="kpi-icon"><Icon size={17} strokeWidth={1.8} /></span></div>
    <div className="kpi-value">{value}</div><div className="kpi-note">{note}</div>
  </article>;
}

function average(records, field) {
  const values = records.map((row) => row[field]).filter((value) => value !== null && value !== undefined && Number.isFinite(Number(value)));
  return values.length ? values.reduce((sum, value) => sum + Number(value), 0) / values.length : null;
}

export default function KpiGrid({ summary, records }) {
  const analysis = summary.hourly_analysis;
  const eligible = analysis.eligible_actual_periods;
  const coverage = eligible ? analysis.matched_periods / eligible * 100 : 0;
  const enoughMatches = eligible > 0 && coverage >= 95 && analysis.actual_completeness_percent >= 95 && analysis.matched_periods > 0;
  const matched = records.filter((row) => row.matched);
  const metrics = analysis.metrics;
  return <section className="kpi-grid" aria-label="Hourly generation and accuracy indicators">
    <Card label="Actual generation" value={formatMw(enoughMatches ? average(matched, 'actual_mw') : null)} note={enoughMatches ? 'Hourly mean; matched periods' : 'Insufficient hourly coverage'} icon={Wind} accent="kpi-green" tooltip="Hourly actual is the mean of both consecutive half-hour FUELHH values. Zero is a valid reading." />
    <Card label="Forecast generation" value={formatMw(enoughMatches ? average(matched, 'forecast_mw') : null)} note={enoughMatches ? 'Hourly forecast; matched periods' : 'Insufficient hourly coverage'} icon={Zap} accent="kpi-blue" tooltip="Hourly WINDFOR forecast selected at the documented day-ahead cutoff." />
    <Card label="Mean absolute error" value={enoughMatches ? formatMw(metrics.mae_mw, 2) : '—'} note={enoughMatches ? 'Hourly matched pairs only' : 'Requires ≥95% hourly coverage'} icon={Activity} accent="kpi-violet" />
    <Card label="Root mean squared error" value={enoughMatches ? formatMw(metrics.rmse_mw, 2) : '—'} note={enoughMatches ? 'Hourly; larger errors weigh more' : 'Requires ≥95% hourly coverage'} icon={Gauge} accent="kpi-orange" />
    <Card label="WAPE" value={enoughMatches ? formatMetric(metrics.wape_percent, '%', 2) : '—'} note={enoughMatches ? 'Hourly weighted absolute error' : 'Requires ≥95% hourly coverage'} icon={BarChart3} accent="kpi-pink" />
    <Card label="Hourly forecast coverage" value={eligible ? formatMetric(coverage, '%', 1) : '—'} note={`${formatCount(analysis.matched_periods)} / ${formatCount(eligible)} eligible actual hours`} icon={CheckCheck} accent="kpi-teal" />
  </section>;
}
