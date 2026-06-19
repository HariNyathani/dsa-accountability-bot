import 'package:flutter/material.dart';

// =============================================================================
// Pulse wrapper — shared animation primitive
// =============================================================================

/// Wraps [child] in a gentle opacity pulse animation.
///
/// Use directly for custom skeleton shapes, or reach for the
/// convenience widgets [SkeletonCard] and [SkeletonLine] below.
class SkeletonPulse extends StatefulWidget {
  const SkeletonPulse({
    super.key,
    required this.child,
    this.minOpacity = 0.35,
    this.maxOpacity = 0.75,
  });

  final Widget child;
  final double minOpacity;
  final double maxOpacity;

  @override
  State<SkeletonPulse> createState() => _SkeletonPulseState();
}

class _SkeletonPulseState extends State<SkeletonPulse>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final range = widget.maxOpacity - widget.minOpacity;

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) => Opacity(
        opacity:
            widget.minOpacity + Curves.easeInOut.transform(_controller.value) * range,
        child: child,
      ),
      child: widget.child,
    );
  }
}

// =============================================================================
// SkeletonCard — full card-shaped placeholder
// =============================================================================

/// Renders a card-shaped skeleton matching the 24 dp radius design system.
///
/// Uses a hairline border and the ambient `colorScheme.surface` fill
/// to exactly mirror the real [Card] widget's visual footprint.
class SkeletonCard extends StatelessWidget {
  const SkeletonCard({
    super.key,
    this.width,
    this.height = 120,
    this.borderRadius = 24.0,
  });

  final double? width;
  final double height;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return SkeletonPulse(
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: colorScheme.surface,
          borderRadius: BorderRadius.circular(borderRadius),
          border: Border.all(color: colorScheme.outline, width: 0.5),
        ),
      ),
    );
  }
}

// =============================================================================
// SkeletonLine — inline content placeholder
// =============================================================================

/// Renders a small rounded bar used inside cards to represent
/// text lines, avatar circles, or data cells while loading.
class SkeletonLine extends StatelessWidget {
  const SkeletonLine({
    super.key,
    this.width,
    this.height = 14,
    this.borderRadius = 7,
  });

  final double? width;
  final double height;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return SkeletonPulse(
      minOpacity: 0.30,
      maxOpacity: 0.70,
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: colorScheme.onSurface.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(borderRadius),
        ),
      ),
    );
  }
}
