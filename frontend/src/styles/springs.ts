/**
 * Spring configurations — byte-accurate ports of
 * mobile/lib/core/widgets/spring_curve.dart (SpringCurve.snap).
 *
 * Physics: mass 1, stiffness 400, damping 28  →  zeta ≈ 0.7 (underdamped),
 * producing one micro-overshoot then settle. Flutter duration is 350ms;
 * Framer Motion (motion) derives the duration from these same physical params.
 *
 * spring_curve.dart:10-12
 */
export const snapSpring = {
  type: "spring" as const,
  stiffness: 400, // spring_curve.dart:11
  damping: 28, // spring_curve.dart:12
  mass: 1, // spring_curve.dart:10
};

/** Gentler entrance — login_screen.dart: ~900ms easeOut. */
export const enterSpring = {
  type: "spring" as const,
  stiffness: 220,
  damping: 30,
  mass: 1,
};

/** Snappier micro-interaction (icon swaps, counters): 200ms easeOutCubic-ish. */
export const quickSpring = {
  type: "spring" as const,
  stiffness: 520,
  damping: 34,
  mass: 1,
};

/** Elastic pop — log_progress_sheet.dart checkmark: Curves.elasticOut 500ms. */
export const popSpring = {
  type: "spring" as const,
  stiffness: 280,
  damping: 12,
  mass: 1,
};