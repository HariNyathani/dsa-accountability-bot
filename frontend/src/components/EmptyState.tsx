interface Props {
  icon?: string;
  title: string;
  message?: string;
}

export function EmptyState({ icon = "📭", title, message }: Props) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <h3>{title}</h3>
      {message && <p>{message}</p>}
    </div>
  );
}

interface ErrorProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorProps) {
  return (
    <div className="error-state">
      <div className="error-icon">⚠️</div>
      <h3>Something went wrong</h3>
      <p>{message}</p>
      {onRetry && (
        <button className="retry-btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
