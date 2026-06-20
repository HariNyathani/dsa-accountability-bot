import 'dart:math' as math;

import 'package:flutter/material.dart';

/// A physics-based spring curve that produces a natural overshoot-and-settle
/// motion for capsule indicator sliding transitions.
///
/// ### Calibration (matches iOS 26 spring tokens)
/// ```
/// mass:      1.0   — single unit inertia
/// stiffness: 400.0 — crisp, snappy response without feeling rigid
/// damping:   28.0  — slight underdamp → one micro-overshoot, then settles
/// ```
///
/// ### Usage
/// Drop-in replacement for [Curves.easeInOutCubic] on any timed animation:
/// ```dart
/// AnimatedAlign(
///   curve: SpringCurve.snap,
///   duration: const Duration(milliseconds: 350),
///   ...
/// )
/// ```
///
/// ### How it works
/// Uses the analytical solution for a damped harmonic oscillator:
/// - ω₀ = √(k/m)            — natural angular frequency
/// - ζ  = c / (2√(km))      — damping ratio
/// - Under-damped (ζ < 1):  exponential decay × cosine oscillation
///
/// The output is normalised so t=0 → 0.0 and the asymptotic value → 1.0.
class SpringCurve extends Curve {
  const SpringCurve({
    this.mass = 1.0,
    this.stiffness = 400.0,
    this.damping = 28.0,
  });

  final double mass;
  final double stiffness;
  final double damping;

  /// Pre-built instance calibrated for capsule slides.
  /// Replace `Curves.easeInOutCubic` with `SpringCurve.snap` everywhere.
  static const SpringCurve snap = SpringCurve();

  @override
  double transformInternal(double t) {
    // Natural angular frequency.
    final omega0 = math.sqrt(stiffness / mass);
    // Damping ratio.
    final zeta = damping / (2.0 * math.sqrt(stiffness * mass));

    if (zeta < 1.0) {
      // Under-damped: exponential decay × cosine oscillation.
      final omegaD = omega0 * math.sqrt(1.0 - zeta * zeta);
      final decay = math.exp(-zeta * omega0 * t);
      final value = 1.0 -
          decay *
              (math.cos(omegaD * t) +
                  (zeta * omega0 / omegaD) * math.sin(omegaD * t));
      return value.clamp(0.0, 1.5); // allow overshoot beyond 1.0
    } else if (zeta == 1.0) {
      // Critically damped.
      final decay = math.exp(-omega0 * t);
      return 1.0 - decay * (1.0 + omega0 * t);
    } else {
      // Over-damped.
      final alpha = omega0 * math.sqrt(zeta * zeta - 1.0);
      final r1 = -zeta * omega0 + alpha;
      final r2 = -zeta * omega0 - alpha;
      final c2 = omega0 * omega0 / (alpha * 2.0);
      final c1 = 1.0 - c2;
      return 1.0 - (c1 * math.exp(r1 * t) + c2 * math.exp(r2 * t));
    }
  }
}
