import 'package:flutter/material.dart';

import '../../../../core/widgets/skeleton_card.dart';
import '../../../dashboard/data/models/user_stats.dart';

/// Difficulty breakdown card — three metric columns + stacked bar.
///
/// Renders Easy / Medium / Hard counts with color-coded accent stripes
/// and a proportional horizontal bar below.
class DifficultyBreakdown extends StatelessWidget {
  const DifficultyBreakdown({
    super.key,
    required this.difficulty,
    required this.isLoading,
  });

  final UserDifficulty? difficulty;
  final bool isLoading;

  static const _easyColor = Color(0xFF4CAF50);
  static const _mediumColor = Color(0xFFFF9800);
  static const _hardColor = Color(0xFFE53935);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header ─────────────────────────────────────────────────
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: colorScheme.primary.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(
                    Icons.track_changes_rounded,
                    color: colorScheme.primary,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Text(
                  'Difficulty Breakdown',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // ── Three metric columns ───────────────────────────────────
            if (isLoading || difficulty == null) ...[
              Row(
                children: [
                  Expanded(child: _skeletonColumn()),
                  const SizedBox(width: 12),
                  Expanded(child: _skeletonColumn()),
                  const SizedBox(width: 12),
                  Expanded(child: _skeletonColumn()),
                ],
              ),
              const SizedBox(height: 20),
              const SkeletonLine(height: 20, borderRadius: 6),
            ] else ...[
              Row(
                children: [
                  Expanded(
                    child: _MetricColumn(
                      label: 'Easy',
                      count: difficulty!.easy,
                      accentColor: _easyColor,
                      theme: theme,
                      colorScheme: colorScheme,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _MetricColumn(
                      label: 'Medium',
                      count: difficulty!.medium,
                      accentColor: _mediumColor,
                      theme: theme,
                      colorScheme: colorScheme,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _MetricColumn(
                      label: 'Hard',
                      count: difficulty!.hard,
                      accentColor: _hardColor,
                      theme: theme,
                      colorScheme: colorScheme,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // ── Stacked bar ──────────────────────────────────────────
              _buildStackedBar(difficulty!, theme, colorScheme),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStackedBar(
    UserDifficulty diff,
    ThemeData theme,
    ColorScheme colorScheme,
  ) {
    final total = diff.easy + diff.medium + diff.hard;

    if (total == 0) {
      return Container(
        height: 20,
        decoration: BoxDecoration(
          color: colorScheme.onSurface.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Center(
          child: Text(
            'No data yet',
            style: theme.textTheme.labelSmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
              fontSize: 10,
            ),
          ),
        ),
      );
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(6),
      child: SizedBox(
        height: 20,
        child: Row(
          children: [
            if (diff.easy > 0)
              Expanded(
                flex: (diff.easy * 1000 ~/ total).clamp(1, 1000),
                child: Container(color: _easyColor),
              ),
            if (diff.medium > 0)
              Expanded(
                flex: (diff.medium * 1000 ~/ total).clamp(1, 1000),
                child: Container(color: _mediumColor),
              ),
            if (diff.hard > 0)
              Expanded(
                flex: (diff.hard * 1000 ~/ total).clamp(1, 1000),
                child: Container(color: _hardColor),
              ),
          ],
        ),
      ),
    );
  }

  static Widget _skeletonColumn() {
    return Column(
      children: const [
        SkeletonLine(width: 40, height: 4, borderRadius: 2),
        SizedBox(height: 12),
        SkeletonLine(width: 36, height: 24),
        SizedBox(height: 8),
        SkeletonLine(width: 48, height: 12),
      ],
    );
  }
}

// =============================================================================
// Metric column — single difficulty stat
// =============================================================================

class _MetricColumn extends StatelessWidget {
  const _MetricColumn({
    required this.label,
    required this.count,
    required this.accentColor,
    required this.theme,
    required this.colorScheme,
  });

  final String label;
  final int count;
  final Color accentColor;
  final ThemeData theme;
  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: colorScheme.outline,
          width: 0.5,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          // Colored accent stripe at top.
          Container(
            height: 4,
            color: accentColor,
          ),
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: 12,
              vertical: 16,
            ),
            child: Column(
              children: [
                Text(
                  count.toString(),
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  label,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
