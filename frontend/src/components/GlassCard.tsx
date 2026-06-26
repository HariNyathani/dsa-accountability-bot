import type { CSSProperties, ReactNode } from "react";
import s from "./GlassCard.module.css";

/**
 * Frosted-glass surface — 1:1 port of mobile/lib/core/widgets/glass_card.dart.
 *
 * Reproduces the app's gradient fill (white 0.35→0.10 light / 0.05→0.01 dark),
 * 1px specular border, and soft ambient shadow. NO backdrop-filter — the Flutter
 * team removed it for perf and found it visually identical on both themes.
 */
export default function GlassCard({
  children,
  radius = 24,
  glow = false,
  padded = false,
  pad = "md",
  fill = false,
  className = "",
  style,
}: {
  children: ReactNode;
  /** Corner radius in px (defaults to 24, the consensus value; pass 32 for
   * leaderboard rows & modal cards — AppTheme.cardRadius). */
  radius?: number;
  /** Adds the subtle inset specular sheen line. */
  glow?: boolean;
  /** Convenience: apply internal padding. */
  padded?: boolean;
  /** Padding scale when `padded`. */
  pad?: "md" | "lg";
  /** Stretch to fill the parent flex/grid cell and become a flex-column so
   * inner content can distribute vertically. Use for bento cells that must
   * share equal heights. */
  fill?: boolean;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={`${s.glass}${padded ? ` ${pad === "lg" ? s.pLg : s.p}` : ""}${
        glow ? ` ${s.glow}` : ""
      }${fill ? ` ${s.fill}` : ""}${className ? ` ${className}` : ""}`}
      data-radius={radius >= 32 ? "lg" : undefined}
      data-glow={glow ? "true" : undefined}
      style={
        radius !== 24 && radius !== 32
          ? { borderRadius: `${radius}px`, ...style }
          : style
      }
    >
      {children}
    </div>
  );
}