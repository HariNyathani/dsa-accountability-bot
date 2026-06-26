import s from "./Skeleton.module.css";

/** Single shimmer element — the atomic building block for all skeleton states.
 *  Composed by Loader.tsx into SkeletonCards / SkeletonRows / SkeletonChart. */
export function Skeleton({ variant = "line", className = "" }: { variant?: "line" | "card" | "chart" | "row" | "block"; className?: string }) {
  return <div className={`${s.base} ${s[variant]}${className ? ` ${className}` : ""}`} aria-hidden />;
}

/** Single chart-sized card shimmer — re-exported by Loader.tsx as SkeletonChart. */
export function SkeletonCard() {
  return <Skeleton variant="chart" />;
}