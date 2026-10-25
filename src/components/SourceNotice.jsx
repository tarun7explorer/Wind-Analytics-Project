import { AlertTriangle, Info } from 'lucide-react';

export function SourceNotice({ status }) {
  if (status !== 'unverified_live_contract') return null;
  return (
    <div className="source-notice" role="status">
      <span className="notice-icon"><AlertTriangle size={17} /></span>
      <div>
        <strong>Source integration is provisional</strong>
        <p>The backend has not verified Elexon’s live query contract or this period’s coverage. Treat any returned figures as unverified.</p>
      </div>
      <Info className="notice-info" size={17} aria-hidden="true" />
    </div>
  );
}

export function CoverageNotice({ coverage, matched, expected, actualCompleteness }) {
  if (coverage === null || (coverage >= 0.95 && actualCompleteness >= 0.95)) return null;
  return (
    <div className="coverage-notice" role="status">
      <AlertTriangle size={16} />
      <span>
        Hourly forecast coverage is {(coverage * 100).toFixed(1)}% ({matched.toLocaleString('en-GB')} of {expected.toLocaleString('en-GB')} eligible actual hours).
        Complete hourly actuals cover {(actualCompleteness * 100).toFixed(1)}% of expected hours. Accuracy KPIs are withheld below 95% matched coverage or actual completeness. Missing intervals remain missing.
      </span>
    </div>
  );
}
