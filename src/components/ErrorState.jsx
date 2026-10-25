import { CircleAlert, RefreshCw } from 'lucide-react';

export default function ErrorState({ message, onRetry }) {
  return (
    <div className="state-panel error-state" role="alert">
      <span className="state-icon"><CircleAlert size={24} /></span>
      <h2>Report couldn’t load</h2>
      <p>{message}</p>
      <button className="button button-primary" onClick={onRetry}><RefreshCw size={15} /> Retry report</button>
    </div>
  );
}
