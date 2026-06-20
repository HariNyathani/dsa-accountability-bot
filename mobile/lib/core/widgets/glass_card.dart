import 'dart:ui';

import 'package:flutter/material.dart';

/// Shared frosted-glass surface widget used throughout the app.
///
/// Replaces the four independent `_GlassCard` copies that had drifted across
/// `dashboard_tab.dart`, `analytics_tab.dart`, `profile_tab.dart`, and the
/// leaderboard row widgets. All glass surfaces now reference this single source
/// of truth, guaranteeing visual consistency across every mode.
///
/// ### Parameters
/// - [radius] — Corner radius. Defaults to `24.0` (consensus value). Pass
///   `AppTheme.cardRadius` (32.0) for leaderboard rows and modal sheet cards.
/// - [blurSigma] — Gaussian blur strength. Defaults to `18.0`. Increase for
///   surfaces that sit directly over rich content (e.g. nav dock at 24.0).
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
  final double blurSigma;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return RepaintBoundary(
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(radius),
          boxShadow: [
            BoxShadow(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.02)
                  : const Color(0xFF7A5234).withValues(alpha: 0.04),
              blurRadius: isDark ? 20 : 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(radius),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
            child: Container(
              decoration: BoxDecoration(
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
                borderRadius: BorderRadius.circular(radius),
                border: Border.all(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.15)
                      : Colors.white.withValues(alpha: 0.50),
                  width: 1.0,
                ),
              ),
              child: Material(
                type: MaterialType.transparency,
                child: child,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
