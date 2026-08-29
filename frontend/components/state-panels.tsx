import { CloudOff, Inbox, RefreshCw, TriangleAlert } from "lucide-react";

export function LoadingState({ label = "Checking reviewed conditions…" }: { label?: string }) {
  return (
    <div className="statePanel loadingPanel" role="status">
      <span className="loadingMark" aria-hidden="true"><i /><i /><i /></span>
      <div><strong>{label}</strong><p>Profile facts and evidence are checked separately.</p></div>
    </div>
  );
}

export function EmptyState() {
  return (
    <div className="statePanel centeredState">
      <Inbox size={24} aria-hidden="true" />
      <strong>No reviewed matches yet</strong>
      <p>Tell us what support you need and where your farm is located.</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="statePanel errorPanel" role="alert">
      <TriangleAlert size={22} aria-hidden="true" />
      <div><strong>We couldn’t complete that check</strong><p>{message}</p></div>
      {onRetry && <button className="button buttonSmall buttonSecondary" type="button" onClick={onRetry}><RefreshCw size={15} />Retry</button>}
    </div>
  );
}

export function OfflineNotice() {
  return (
    <div className="offlineNotice" role="status">
      <CloudOff size={16} aria-hidden="true" />
      You’re offline. Your current profile remains visible; sending is paused.
    </div>
  );
}
