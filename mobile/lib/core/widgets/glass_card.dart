import 'package:flutter/material.dart';

/// Shared frosted-glass surface widget used throughout the app.
///
/// Replaces the four independent `_GlassCard` copies that had drifted across
/// `dashboard_tab.dart`, `analytics_tab.dart`, `profile_tab.dart`, and the
/// leaderboard row widgets. All glass surfaces now reference this single source
/// of truth, guaranteeing visual consistency across every mode.
///
/// ### Performance (v2 — June 2026)
/// The original implementation used a per-card `BackdropFilter` with
/// `ImageFilter.blur(sigma: 18)`, which forced the Skia/Impeller rasterizer
/// into a `saveLayer` → blur → composite pipeline **per card, per frame**.
/// In scrolling lists (10+ cards visible), this saturated the mobile GPU and
/// caused severe frame drops on mid-range devices.
///
/// The current implementation replaces the blur with a visually equivalent
/// semi-transparent gradient fill + specular border. The result is
/// indistinguishable on dark AMOLED backgrounds (where the blur had nothing
/// visible to diffuse anyway) and renders in a single compositing pass.
///
/// ### Parameters
/// - [radius] — Corner radius. Defaults to `24.0` (consensus value). Pass
///   `AppTheme.cardRadius` (32.0) for leaderboard rows and modal sheet cards.
/// - [blurSigma] — Retained for API compatibility. Previously controlled the
///   Gaussian blur strength; now a no-op since the blur has been removed.
///
/// ### Dark mode
/// Uses a very low-alpha `0.05 → 0.01` gradient so the AMOLED black backdrop
/// bleeds through. The specular border at `0.15` alpha provides the only edge
/// definition. Light mode uses `0.35 → 0.10` with a `0.50` alpha border.
class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.radius = 24.0,
    this.blurSigma = 18.0,
  });

  final Widget child;
  final double radius;

  /// Retained for API compatibility with existing call sites.
  /// Previously controlled `ImageFilter.blur` sigma; now unused.
  final double blurSigma;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return RepaintBoundary(
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(radius),
          // Soft ambient shadow — identical to the original.
          boxShadow: [
            BoxShadow(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.02)
                  : const Color(0xFF7A5234).withValues(alpha: 0.04),
              blurRadius: isDark ? 20 : 12,
              offset: const Offset(0, 4),
            ),
          ],
          // Semi-transparent gradient fill replaces the BackdropFilter blur.
          // On dark AMOLED surfaces the blur was diffusing near-black pixels
          // anyway, so a solid low-alpha gradient is visually identical.
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isDark
                ? [
                    Colors.white.withValues(alpha: 0.05),
                    Colors.white.withValues(alpha: 0.01),
                  ]
                : [
                    Colors.white.withValues(alpha: 0.35),
                    Colors.white.withValues(alpha: 0.10),
                  ],
          ),
          // Specular border — unchanged from the original.
          border: Border.all(
            color: isDark
                ? Colors.white.withValues(alpha: 0.15)
                : Colors.white.withValues(alpha: 0.50),
            width: 1.0,
          ),
        ),
        // Clip child content to the rounded corners.
        clipBehavior: Clip.antiAlias,
        child: Material(
          type: MaterialType.transparency,
          child: child,
        ),
      ),
    );
  }
}
