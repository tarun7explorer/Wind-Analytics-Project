import { useMemo, useState } from 'react';
import { ArrowDownRight, ArrowUpRight, Clock3, Download, RefreshCw } from 'lucide-react';
import Header from '../components/Header.jsx';
import PeriodSelector from '../components/PeriodSelector.jsx';
import KpiGrid from '../components/KpiGrid.jsx';
import ForecastChart from '../components/ForecastChart.jsx';
import ErrorChart from '../components/ErrorChart.jsx';
import GenerationTable from '../components/GenerationTable.jsx';
import LoadingState from '../components/LoadingState.jsx';
import EmptyState from '../components/EmptyState.jsx';
import ErrorState from '../components/ErrorState.jsx';
import { CoverageNotice, SourceNotice } from '../components/SourceNotice.jsx';
import { useMonthlyAnalytics } from '../hooks/useMonthlyAnalytics.js';
import { formatDeliveryTime, monthTitle } from '../utils/dateUtils.js';
import { formatCount } from '../utils/formatters.js';
import { buildMonthlyCsv } from '../services/csvExport.js';

const DEFAULT_YEAR = 2026;
const DEFAULT_MONTH = 1;

function SummaryStrip({ summary }) {
  const hourly = summary.hourly_analysis;
  const exactCoverage = summary.expected_intervals ? summary.matched_intervals / summary.expected_intervals : 0;
  return (
    <div className="summary-strip">
      <div className="summary-item"><span className="summary-icon"><Clock3 size={15} /></span><span>Accuracy comparison <b>hourly</b></span></div>
      <div className="summary-item"><span className="summary-icon"><ArrowUpRight size={15} /></span><span><b>{formatCount(hourly.matched_periods)}</b> hourly pairs matched</span></div>
      <div className="summary-item"><span className="summary-icon"><ArrowDownRight size={15} /></span><span><b>{formatCount(hourly.eligible_actual_periods)}</b> hours with complete actuals</span></div>
      <div className="summary-right">Exact half-hour coverage <b>{(exactCoverage * 100).toFixed(1)}%</b></div>
    </div>
  );
}

function EmptyReport({ data, onRetry }) {
  const hasActual = data.summary.actual_intervals > 0;
  const hasForecast = data.summary.forecast_intervals > 0;
  if (hasActual || hasForecast) return null;
  return <EmptyState onRetry={onRetry} />;
}

export default function Dashboard() {
  const [year, setYear] = useState(DEFAULT_YEAR);
  const [month, setMonth] = useState(DEFAULT_MONTH);
  const { data, loading, error, retry } = useMonthlyAnalytics(year, month);
  const period = monthTitle(year, month);
  const hourlyCoverage = useMemo(() => {
    const hourly = data?.summary.hourly_analysis;
    if (!hourly || !hourly.expected_periods) return null;
    return hourly.eligible_actual_periods
      ? hourly.matched_periods / hourly.eligible_actual_periods
      : 0;
  }, [data]);

  const changePeriod = (newYear, newMonth) => {
    setYear(newYear);
    setMonth(newMonth);
  };

  const exportCsv = () => {
    if (!data?.hourlyRecords?.length) return;
    const csv = buildMonthlyCsv(data.hourlyRecords, 'hourly');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `wind-analytics-hourly-${year}-${String(month).padStart(2, '0')}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app-shell" id="top">
      <Header period={period} />
      <main className="dashboard-main">
        <section className="page-intro">
          <div>
            <div className="eyebrow intro-eyebrow">FORECAST INTELLIGENCE <span /> NATIONAL SYSTEM VIEW</div>
            <h1>Wind generation <span>performance</span></h1>
            <p className="intro-copy">A clear view of what the system expected, what it delivered, and how well the forecast held.</p>
          </div>
          <div className="intro-controls">
            <PeriodSelector year={year} month={month} onChange={changePeriod} />
            <button className="button button-export" onClick={exportCsv} disabled={!data?.hourlyRecords?.length || loading} aria-label="Export hourly comparison records as CSV">
              <Download size={15} /> Export hourly CSV
            </button>
          </div>
        </section>

        {error ? <ErrorState message={error} onRetry={retry} /> : null}
        {loading ? <LoadingState /> : null}

        {!loading && !error && data && (
          <>
            <SourceNotice status={data.summary.source_contract_status} />
            {data.summary.hourly_analysis.expected_periods > 0 && hourlyCoverage !== null && (
              <CoverageNotice coverage={hourlyCoverage} matched={data.summary.hourly_analysis.matched_periods} expected={data.summary.hourly_analysis.eligible_actual_periods} actualCompleteness={data.summary.hourly_analysis.actual_completeness_percent / 100} />
            )}
            <EmptyReport data={data} onRetry={retry} />
            {(data.summary.actual_intervals > 0 || data.summary.forecast_intervals > 0) && (
              <>
                <SummaryStrip summary={data.summary} />
                <KpiGrid summary={data.summary} records={data.hourlyRecords} />
                <div className="charts-grid">
                  <ForecastChart records={data.hourlyRecords} />
                  <ErrorChart records={data.hourlyRecords} />
                </div>
                <GenerationTable records={data.hourlyRecords} />
                <footer className="dashboard-footer">
                  <span>Forecast cutoff: {data.summary.decision_cutoff_rule}</span>
                  <span>BMRS report retrieved {formatDeliveryTime(data.summary.source_retrieved_at, { year: 'numeric' })}</span>
                  <span>Source contract: {data.summary.source_contract_status === 'unverified_live_contract' ? 'verification pending' : data.summary.source_contract_status}</span>
                  <button className="footer-retry" onClick={retry}><RefreshCw size={13} /> Refresh report</button>
                </footer>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
