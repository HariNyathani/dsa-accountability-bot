import 'package:flutter/material.dart';

import '../../../../../core/widgets/skeleton_card.dart';

/// Calendar month heatmap grid.
///
/// Renders the current calendar month aligned under `M T W T F S S` column
/// headers, with blank leading cells so day 1 lands on its correct weekday —
/// identical to the LeetCode consistency chart layout.
///
/// Each real-day cell is color-coded by submission depth:
///   • 0 problems  → biscuit beige (light) / dark graphite (dark) + outline
///   • rest day    → soft tertiary tint (blue-grey)
///   • 1 problem   → 25% accent intensity
///   • 2 problems  → 50% accent intensity
///   • 3 problems  → 75% accent intensity
///   • 4+ problems → full accent (jade green / neon green)
///
/// The grid is dimensioned for a 6-inch portrait viewport (~312 dp usable
/// width with 24 dp horizontal padding on each side).
class OneMonthHeatmap extends StatelessWidget {
  const OneMonthHeatmap({
    super.key,
    required this.dates,
    this.restDates = const [],
    this.isLoading = false,
  });

  /// Map of `"YYYY-MM-DD" → question_count` from the backend.
  final Map<String, int> dates;

  /// List of `"YYYY-MM-DD"` strings that are rest days.
  final List<String> restDates;

  /// When true, cells render as pulsing skeletons.
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;

    // ── Calendar month layout ───────────────────────────────────────────────
    // Build the grid for the *current* calendar month so day 1 always lands
    // under its correct M-T-W-T-F-S-S column, matching the LeetCode layout.
    final now = DateTime.now();
    final daysInMonth = DateTime(now.year, now.month + 1, 0).day;

    // Dart weekday: Monday = 1 … Sunday = 7.
    // paddingCount = blank leading cells before day 1.
    final paddingCount = DateTime(now.year, now.month, 1).weekday - 1;
    final totalItems   = paddingCount + daysInMonth;

    // Pre-build _CellData for every real day in O(n).
    final restSet = restDates.toSet();
    final cells = List.generate(daysInMonth, (i) {
      final day = i + 1;
      final key =
          '${now.year}-${now.month.toString().padLeft(2, '0')}-${day.toString().padLeft(2, '0')}';
      return _CellData(
        date: DateTime(now.year, now.month, day),
        dateKey: key,
        count: dates[key] ?? 0,
        isRest: restSet.contains(key),
      );
    });

    // Accent color tiers.
    final accent = colorScheme.primary;
    final baseEmpty = isDark
        ? const Color(0xFF1A1A1A) // Slightly lighter than pure black.
        : const Color(0xFFF5F2EB); // Biscuit beige.

    // Pre-compute colour tiers once per build so itemBuilder doesn't call
    // Color.lerp on every cell. On a 35-cell grid this avoids ~105 lerp
    // computations per frame.
    final tier1 = Color.lerp(baseEmpty, accent, 0.25)!;
    final tier2 = Color.lerp(baseEmpty, accent, 0.50)!;
    final tier3 = Color.lerp(baseEmpty, accent, 0.75)!;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Day-of-week column headers.
        Row(
          children: ['M', 'T', 'W', 'T', 'F', 'S', 'S']
              .map(
                (d) => Expanded(
                  child: Center(
                    child: Text(
                      d,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
        ),
        const SizedBox(height: 8),

        // Grid — calendar month view.
        GridView.builder(
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 7,
            mainAxisSpacing: 4,
            crossAxisSpacing: 4,
          ),
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: totalItems,
          itemBuilder: (_, index) {
            // Blank leading cell — keeps day 1 on the correct column.
            if (index < paddingCount) return const SizedBox.shrink();

            final cell = cells[index - paddingCount];

            if (isLoading) {
              return SkeletonPulse(
                child: Container(
                  decoration: BoxDecoration(
                    color: colorScheme.onSurface.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(6),
                  ),
                ),
              );
            }

            // Rest days: soft tertiary tint, visually distinct from both
            // empty (beige/graphite) and active (green ramp) cells.
            if (cell.isRest) {
              return Container(
                decoration: BoxDecoration(
                  color: colorScheme.tertiary.withValues(alpha: 0.30),
                  borderRadius: BorderRadius.circular(6),
                ),
              );
            }

            // Active and empty problem-day cells.
            final isEmpty = cell.count == 0;
            return Container(
              decoration: BoxDecoration(
                color: _cellColor(cell.count, accent, baseEmpty, tier1, tier2, tier3),
                borderRadius: BorderRadius.circular(6),
                // Subtle outline on empty cells so the grid matrix reads
                // clearly on white/light backgrounds.
                border: isEmpty
                    ? Border.all(
                        color: colorScheme.outlineVariant
                            .withValues(alpha: 0.40),
                        width: 0.5,
                      )
                    : null,
              ),
              child: cell.count > 0
                  ? Center(
                      child: Text(
                        '${cell.count}',
                        style: theme.textTheme.labelSmall?.copyWith(
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          color: cell.count >= 3
                              ? colorScheme.onPrimary
                              : colorScheme.onSurface
                                  .withValues(alpha: 0.7),
                        ),
                      ),
                    )
                  : null,
            );
          },
        ),

        const SizedBox(height: 14),

        // Unified legend row: "Rest day" swatch on the left,
        // "Less → More" intensity ramp on the right — both on the same line.
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Left: Rest-day swatch.
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 14,
                  height: 14,
                  decoration: BoxDecoration(
                    color: colorScheme.tertiary.withValues(alpha: 0.30),
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  'Rest day',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                    fontSize: 10,
                  ),
                ),
              ],
            ),

            // Right: Less → More intensity ramp.
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Less',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                    fontSize: 10,
                  ),
                ),
                const SizedBox(width: 6),
                ...List.generate(5, (i) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 1.5),
                    child: Container(
                      width: 14,
                      height: 14,
                      decoration: BoxDecoration(
                        color: _cellColor(i, accent, baseEmpty, tier1, tier2, tier3),
                        borderRadius: BorderRadius.circular(3),
                        border: i == 0
                            ? Border.all(
                                color: colorScheme.outlineVariant
                                    .withValues(alpha: 0.40),
                                width: 0.5,
                              )
                            : null,
                      ),
                    ),
                  );
                }),
                const SizedBox(width: 6),
                Text(
                  'More',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                    fontSize: 10,
                  ),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }

  // ── Color mapping ─────────────────────────────────────────────────────────

  /// Maps submission count → color intensity tier.
  static Color _cellColor(
    int count,
    Color accent,
    Color empty,
    Color tier1,
    Color tier2,
    Color tier3,
  ) {
    if (count <= 0) return empty;
    if (count == 1) return tier1;
    if (count == 2) return tier2;
    if (count == 3) return tier3;
    return accent; // 4+
  }
}

// =============================================================================
// Internal cell data
// =============================================================================

class _CellData {
  const _CellData({
    required this.date,
    required this.dateKey,
    required this.count,
    this.isRest = false,
  });

  final DateTime date;
  final String dateKey;
  final int count;

  /// True when this date appears in [OneMonthHeatmap.restDates].
  final bool isRest;
}
