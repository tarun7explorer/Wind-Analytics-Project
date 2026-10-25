export default function LoadingState() {
  return (
    <div className="loading-stack" aria-label="Loading report" aria-busy="true">
      <div className="skeleton-kpis">{Array.from({ length: 6 }, (_, index) => <div className="skeleton skeleton-card" key={index} />)}</div>
      <div className="skeleton skeleton-chart" />
      <div className="skeleton skeleton-table" />
      <span className="sr-only">Loading the selected month’s analytics.</span>
    </div>
  );
}
