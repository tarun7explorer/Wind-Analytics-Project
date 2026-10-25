import { Activity, Wind } from 'lucide-react';

export default function Header({ period }) {
  return (
    <header className="topbar">
      <a className="brand" href="#top" aria-label="Wind Analytics home">
        <span className="brand-mark"><Wind size={20} strokeWidth={2.1} /></span>
        <span className="brand-copy">
          <strong>Wind<span> Analytics</span></strong>
          <small>UK ENERGY SYSTEMS</small>
        </span>
      </a>
      <div className="topbar-context">
        <span className="context-icon"><Activity size={15} /></span>
        <span>UK national wind</span>
        <span className="context-divider" aria-hidden="true" />
        <span className="context-period">{period}</span>
      </div>
      <div className="topbar-live"><span className="status-dot" /> Monthly analysis</div>
    </header>
  );
}
