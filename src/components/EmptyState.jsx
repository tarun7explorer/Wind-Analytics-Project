import { CloudOff } from 'lucide-react';

export default function EmptyState({ onRetry }) {
  return (
    <div className="state-panel empty-state" role="status">
      <span className="state-icon"><CloudOff size={24} /></span>
      <h2>No source data returned</h2>
      <p>The API returned no actual or forecast measurements for this period. No values or accuracy scores are shown.</p>
      <button className="button button-secondary" onClick={onRetry}>Try again</button>
    </div>
  );
}
