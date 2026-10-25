import { useMemo } from 'react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatDeliveryTime } from '../utils/dateUtils.js';
import { formatMw } from '../utils/formatters.js';

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  return (
    <div className="chart-tooltip">
      <strong>{formatDeliveryTime(label, { weekday: 'short', year: 'numeric' })} UK</strong>
      <div><i className="legend-dot actual-dot" /> Hourly actual mean <b>{row?.actual_mw == null ? 'Missing' : formatMw(row.actual_mw)}</b></div>
      <div><i className="legend-dot forecast-dot" /> Hourly forecast <b>{row?.forecast_mw == null ? 'Missing' : formatMw(row.forecast_mw)}</b></div>
      <small>Forecast published: {formatDeliveryTime(row?.forecast_published_at, { year: 'numeric' })}</small>
      <small>Decision cutoff: {formatDeliveryTime(row?.decision_cutoff, { year: 'numeric' })} UK</small>
    </div>
  );
}

export default function ForecastChart({ records }) {
  const data = useMemo(() => records.map((row) => ({
    delivery_time: row.delivery_time,
    actual_mw: row.actual_mw,
    forecast_mw: row.forecast_mw,
    forecast_published_at: row.forecast_published_at,
    decision_cutoff: row.decision_cutoff,
  })), [records]);
  const hasMeasurements = data.some((row) => row.actual_mw != null || row.forecast_mw != null);

  return (
    <section className="panel chart-panel" aria-labelledby="generation-chart-title">
      <div className="panel-heading">
        <div>
          <div className="eyebrow">GENERATION PROFILE</div>
          <h2 id="generation-chart-title">Forecast vs actual</h2>
          <p>Hourly actual mean vs hourly forecast (MW)</p>
        </div>
        <div className="chart-legend" aria-label="Chart series">
          <span><i className="legend-line actual-line" /> Hourly actual mean</span>
          <span><i className="legend-line forecast-line" /> Hourly forecast</span>
        </div>
      </div>
      {hasMeasurements ? (
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart accessibilityLayer data={data} margin={{ top: 12, right: 14, left: 6, bottom: 4 }}>
              <CartesianGrid stroke="#2b3730" strokeDasharray="3 5" vertical={false} />
              <XAxis dataKey="delivery_time" tickFormatter={(value) => formatDeliveryTime(value, { day: '2-digit', month: 'short' })} tick={{ fill: '#9aa79e', fontSize: 11 }} axisLine={{ stroke: '#3a473e' }} tickLine={false} minTickGap={32} interval="preserveStartEnd" />
              <YAxis tickFormatter={(value) => new Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 1 }).format(value)} tick={{ fill: '#9aa79e', fontSize: 11 }} axisLine={false} tickLine={false} width={48} label={{ value: 'MW', angle: -90, position: 'insideLeft', fill: '#9aa79e', fontSize: 10, offset: -1 }} />
              <Tooltip content={<ChartTooltip />} />
              <Line type="linear" dataKey="actual_mw" name="Actual generation" stroke="#b4e477" strokeWidth={2.2} connectNulls={false} dot={false} activeDot={{ r: 4, fill: '#b4e477', stroke: '#101512', strokeWidth: 2 }} isAnimationActive={false} />
              <Line type="linear" dataKey="forecast_mw" name="Forecast generation" stroke="#8bb5ff" strokeWidth={2} strokeDasharray="6 4" connectNulls={false} dot={false} activeDot={{ r: 4, fill: '#8bb5ff', stroke: '#101512', strokeWidth: 2 }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : <div className="chart-empty">No source measurements are available to plot.</div>}
      <div className="chart-footnote">Hourly actuals require both consecutive half-hour FUELHH values. Timestamps use Europe/London; gaps are not filled and zero MW remains a measurement.</div>
    </section>
  );
}
