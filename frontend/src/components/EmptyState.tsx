import Button from "./Button";
import s from "./EmptyState.module.css";

interface Props {
  icon?: string;
  title: string;
  message: string;
}

export function EmptyState({ icon, title, message }: Props) {
  const displayIcon = icon ?? "📭";
  return (
    <div className={s.state}>
      <div className={s.icon}>{displayIcon}</div>
      <h3 className={s.title}>{title}</h3>
      <p className={s.msg}>{message}</p>
    </div>
  );
}

interface ErrorProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ message, onRetry }: ErrorProps) {
  return (
    <div className={`${s.state} ${s.error}`}>
      <div className={s.icon}>⚠️</div>
      <h3 className={s.title}>Something went wrong</h3>
      <p className={s.msg}>{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className={s.retry} onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}