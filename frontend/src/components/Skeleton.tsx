import s from "./Skeleton.module.css";

export function Skeleton({ variant = "line", className = "" }: { variant?: "line" | "card" | "chart" | "row" | "block"; className?: string }) {
  return <div className={`${s.base} ${s[variant]}${className ? ` ${className}` : ""}`} aria-hidden />;
}

export function SkeletonCard() {
  return <Skeleton variant="chart" />;
}

export function SkeletonCards({ count = 6 }: { count?: number }) {
  return (
    <div className={s.grid}>
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} variant="card" />
      ))}
    </div>
  );
}

export function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <div>
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} variant="row" />
      ))}
    </div>
  );
}

export function SkeletonChart() {
  return <Skeleton variant="chart" />;
}