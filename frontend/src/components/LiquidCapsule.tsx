import { useId, type ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { snapSpring } from "../styles/springs";
import s from "./LiquidCapsule.module.css";

export type CapsuleVariant = "nav" | "filter" | "compact";
export type CapsuleOrientation = "horizontal" | "vertical";

export interface CapsuleItem<T extends string | number> {
  key: T;
  label: ReactNode;
  icon?: ReactNode;
}

export interface LiquidCapsuleProps<T extends string | number> {
  items: readonly CapsuleItem<T>[];
  value: T;
  onChange: (v: T) => void;
  variant?: CapsuleVariant;
  orientation?: CapsuleOrientation;
  /** "fit" = size to content (widthFactor); "stretch" = fill parent elegantly. */
  layout?: "fit" | "stretch";
  className?: string;
  "aria-label"?: string;
}

/**
 * The Sliding Liquid Selection Capsule — the centerpiece mechanic of the app.
 *
 * Mirrors all 6 Flutter capsule instances via a single configurable primitive.
 * The sliding pill uses Framer Motion's shared-layout animation (`layoutId`):
 * it renders inside the *active* segment only; when `value` changes, motion
 * measures old + new rects and springs the element between them using the
 * exact physical params of SpringCurve.snap (spring_curve.dart:10-12).
 */
export default function LiquidCapsule<T extends string | number>({
  items,
  value,
  onChange,
  variant = "filter",
  orientation = "horizontal",
  layout = "stretch",
  className = "",
  ...rest
}: LiquidCapsuleProps<T>) {
  const layoutId = useId();
  const reduce = useReducedMotion();
  const size =
    variant === "nav"
      ? "nav"
      : items.length === 2
        ? "compact"
        : items.length === 3
          ? "tri"
          : items.length === 4
            ? "quad"
            : "penta";

  const spring = reduce ? { duration: 0 } : snapSpring;

  return (
    <div
      className={`${s.track}${layout === "fit" ? ` ${s.fit}` : ` ${s.stretch}`}${className ? ` ${className}` : ""
        }`}
      role="tablist"
      aria-label={rest["aria-label"]}
      data-variant={variant}
      data-size={size}
      data-orientation={orientation}
    >
      {items.map((it) => {
        const active = it.key === value;
        return (
          <button
            key={String(it.key)}
            type="button"
            role="tab"
            aria-selected={active}
            data-active={active ? "true" : "false"}
            className={s.segment}
            onClick={() => onChange(it.key)}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                className={s.pill}
                transition={spring}
                initial={false}
                style={{ borderRadius: "inherit" }}
              />
            )}
            {it.icon && <span className={s.icon}>{it.icon}</span>}
            <span className={s.label}>{it.label}</span>
          </button>
        );
      })}
    </div>
  );
}