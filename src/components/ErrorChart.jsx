import { useMemo } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatDeliveryTime } from '../utils/dateUtils.js';
import { formatSignedMw } from '../utils/formatters.js';

function ErrorTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{formatDeliveryTime(label, { weekday: 'short', year: 'numeric' })} UK</strong>
      <div>Forecast error <b>{row.signed_error_mw == null ? 'Unmatched' : formatSignedMw(row.signed_error_mw)}</b></div>
      <small>Positive means the forecast exceeded actual generation.</small>
    </div>
  );
}

export default function ErrorChart({ records }) {
  const data = useMemo(() => records.filter((row) => row.matched && row.signed_error_mw != null), [records]);
  const errorExtent = Math.max(1, ...data.map((row) => Math.abs(row.signed_error_mw)));

  return (
    <section className="panel error-chart-panel" aria-labelledby="error-chart-title">
      <div className="panel-heading compact-heading">
        <div>
          <div className="eyebrow">HOURLY DEVIATION</div>
          <h2 id="error-chart-title">Forecast error</h2>
          <p>Hourly forecast minus hourly actual mean (MW)</p>
        </div>
        <span className="small-stat">{data.length.toLocaleString('en-GB')} matched</span>
      </div>
      {data.length ? (
        <>
          <div className="error-chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart accessibilityLayer data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
                <CartesianGrid stroke="#2b3730" strokeDasharray="3 5" vertical={false} />
                <XAxis dataKey="delivery_time" tickFormatter={(value) => formatDeliveryTime(value, { day: '2-digit', month: 'short' })} tick={{ fill: '#9aa79e', fontSize: 10 }} axisLine={{ stroke: '#3a473e' }} tickLine={false} minTickGap={36} interval="preserveStartEnd" />
                <YAxis domain={[-errorExtent, errorExtent]} tick={{ fill: '#9aa79e', fontSize: 10 }} axisLine={false} tickLine={false} width={58} label={{ value: 'MW error', angle: -90, position: 'insideLeft', fill: '#9aa79e', fontSize: 10, offset: -2 }} />
                <ReferenceLine y={0} stroke="#d0d8d2" strokeWidth={1.3} />
                <Tooltip content={<ErrorTooltip />} cursor={{ fill: 'rgba(180,228,119,.06)' }} />
                <Bar dataKey="signed_error_mw" name="Forecast error" radius={[2, 2, 0, 0]} maxBarSize={12} isAnimationActive={false}>
                  {data.map((row) => <Cell key={row.delivery_time} fill={row.signed_error_mw >= 0 ? '#e6aa71' : '#83b4ff'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="error-chart-key" aria-label="Error sign legend">
            <span><i className="error-key-over" /> Forecast above actual</span>
            <span><i className="error-key-under" /> Forecast below actual</span>
          </div>
        </>
      ) : <div className="chart-empty error-empty">No matched intervals are available for the error chart.</div>}
    </section>
  );
}
