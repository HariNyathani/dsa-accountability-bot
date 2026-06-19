import 'package:flutter/services.dart';

/// Native haptic feedback utility for tactile interaction tiers.
///
/// Wraps Flutter's [HapticFeedback] platform channels into semantically
/// named helpers that map to physical interaction intensities:
///
///   • [lightTap]     → Crisp click for counter adjustments, selections.
///   • [successBoom]  → Heavy double-pulse for successful submissions.
final class HapticService {
  const HapticService._();

  /// Crisp, lightweight click — use for every counter increment/decrement,
  /// chip selection, and minor interactive state change.
  static Future<void> lightTap() => HapticFeedback.lightImpact();

  /// Satisfying heavy double-pulse sequence — fires on successful
  /// `POST /progress` confirmation.
  ///
  /// The 120 ms gap between pulses creates a perceptible "thud-THUD"
  /// pattern that feels physically rewarding on modern Android haptic
  /// actuators.
  static Future<void> successBoom() async {
    await HapticFeedback.mediumImpact();
    await Future<void>.delayed(const Duration(milliseconds: 120));
    await HapticFeedback.mediumImpact();
  }
}
