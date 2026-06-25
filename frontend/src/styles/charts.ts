/**
 * Recharts theme — centralized so charts re-theme instantly and no inline hex
 * leaks into pages. Reads pixel values from CSS custom properties at call time
 *(so theme toggles flow through without remounting the util).
 */
const TOKEN = (name: string) =>
  (typeof window !== "undefined"
    ? getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    : "") || "var(--accent)";

/** Tooltip panel styled to match the glass popover surface. */
export const tooltipStyle: React.CSSProperties = {
  background: "var(--bg-elevated)",
  color: "var(--text-primary)",
  border: "1px solid var(--border-strong)",
  borderRadius: "14px",
  fontSize: "13px",
  boxShadow: "0 12px 32px rgba(0,0,0,0.35)",
  padding: "8px 12px",
};

export const tooltipItemStyle = { color: "var(--text-primary)" };
export const tooltipLabelStyle = { color: "var(--text-primary)" };

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
 * Categorical palette anchored on Chestnut Espresso + warm companions.
 * The accent (#7A5234) leads, with a curated set of complementary tones —
 * avoiding generic neon. Confidence/status ramp derived from difficulty tokens.
 */
export const PALETTE = [
  "#7A5234", // Deep Chestnut Espresso
  "#9E6F4A",
  "#C99A6E",
  "#5B7B9E",
  "#6D8AB0",
  "#A8B5A0",
  "#8C6A4A",
  "#B08968",
  "#4A7A5C",
  "#7A6A5A",
  "#9E7B5A",
  "#6A5234",
];

export const ACCENT = "var(--accent)";
export const ACCENT_SOFT = "rgba(122,82,52,0.6)";

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