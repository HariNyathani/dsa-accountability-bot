/**
 * Recharts theme — centralized so charts re-theme instantly and no inline hex
 * leaks into pages. Reads pixel values from CSS custom properties at call time
 * (so theme toggles flow through without remounting the util).
 */

/** Tooltip panel styled to match the glass popover surface. */
export const tooltipStyle: React.CSSProperties = {
  background: "color-mix(in srgb, var(--bg-elevated) 92%, var(--accent) 8%)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-strong)",
  borderRadius: "14px",
  fontSize: "13px",
  boxShadow: "0 16px 40px -8px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.06)",
  padding: "10px 14px",
  backdropFilter: "blur(12px)",
};

export const tooltipItemStyle = { color: "var(--text-primary)" };
export const tooltipLabelStyle = { color: "var(--text-secondary)", fontWeight: 600 };

export const axisTick = { fill: "var(--chart-axis)", fontSize: 11 };
export const axisTickBold = {
  fill: "var(--text-primary)",
  fontSize: 12,
  fontWeight: 700,
};

export const gridProps = {
  strokeDasharray: "3 3",
  stroke: "var(--chart-grid)",
  vertical: false,
};

/**
 * Categorical palette — curated around the champagne-bronze brand accent.
 * Warm metallics lead, balanced by muted sage / slate / mauve counterpoints.
 * Every tone is desaturated enough to sit on glass in both themes; no neon.
 */
export const PALETTE = [
  "#C98F5A", // molten bronze (brand)
  "#E3BC8C", // champagne
  "#7C93B5", // slate blue
  "#93AE8C", // sage
  "#B56D51", // terracotta clay
  "#A98293", // dusty mauve
  "#A8A06B", // olive gold
  "#6FA3A0", // patina teal
  "#9E5F63", // rosewood
  "#8C7F70", // warm taupe
  "#5B7B9E", // deep slate
  "#8A5A34", // espresso
];

export const ACCENT = "var(--accent)";
export const ACCENT_SOFT = "color-mix(in srgb, var(--accent) 60%, transparent)";

/** Gradient area fill id helper — keeps ids unique per usage. */
export function areaGradientId(id: string) {
  return `grad-${id}`;
}

/** Consistency bar ramp (red→amber→green) — Leaderboard & profiles. */
export function consistencyColor(pct: number): string {
  if (pct >= 80) return "var(--diff-easy)";
  if (pct >= 50) return "var(--diff-medium)";
  return "var(--diff-hard)";
}
