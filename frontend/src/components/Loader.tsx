import { Skeleton as Sk, SkeletonCard } from "./Skeleton";
import s from "./Loader.module.css";

export function Loader() {
  return (
    <div className={s.center}>
      <div className={s.spinner} />
    </div>
  );
}

export function SkeletonCards({ count = 6, cols = 6 }: { count?: number; cols?: 6 | 4 }) {
  return (
    <div className={s.grid} data-cols={cols}>
      {Array.from({ length: count }).map((_, i) => (
        <Sk key={i} variant="card" className={undefined} />
      ))}
    </div>
  );
}

export { SkeletonCard as SkeletonChart };

export function SkeletonRows({ count = 6 }: { count?: number }) {
  return (
    <div>
      {Array.from({ length: count }).map((_, i) => (
        <Sk key={i} variant="row" />
      ))}
    </div>
  );
}

export { SkeletonCard };