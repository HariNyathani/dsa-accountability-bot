import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../../core/widgets/glass_card.dart';
import '../../../../../core/widgets/skeleton_card.dart';
import '../../../../dashboard/data/models/user_stats.dart';
import '../../../../dashboard/presentation/providers/progress_provider.dart';
import '../../widgets/difficulty_breakdown.dart';
import '../../widgets/one_month_heatmap.dart';
import '../../widgets/topic_distribution_chart.dart';

/// Analytics tab — wired to [ProgressProvider] for live heatmap and
/// distribution charts.
///
/// ### Performance (P4 — June 2026)
/// Uses [Selector] with a record tuple so the tab only rebuilds when
/// the specific fields consumed (stats, heatmap, topics, difficulty,
/// isLoading) change. Unrelated provider mutations (e.g. review
/// submissions) no longer ripple into this tab.
class AnalyticsTab extends StatelessWidget {
  const AnalyticsTab({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return SafeArea(
      bottom: false,
      child: Selector<ProgressProvider,
          ({UserStats? stats, HeatmapData? heatmap, UserTopics? topics,
              UserDifficulty? difficulty, bool isLoading})>(
        selector: (_, p) => (
          stats: p.stats,
          heatmap: p.heatmap,
          topics: p.topics,
          difficulty: p.difficulty,
          isLoading: p.isLoading,
        ),
        builder: (context, snap, _) {
          final stats = snap.stats;
          final heatmap = snap.heatmap;
          final isLoading = snap.isLoading;

          return RefreshIndicator(
            onRefresh: () =>
                context.read<ProgressProvider>().fetchAll(),
            color: colorScheme.primary,
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(24, 32, 24, 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Header ──────────────────────────────────────────────
                  Text(
                    'Analytics',
                    style: theme.textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Your coding consistency at a glance.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 28),

                  // ── Monthly Activity Heatmap ────────────────────────────
                  GlassCard(
                    child: Padding(
                      padding: const EdgeInsets.all(28),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  color: colorScheme.primary
                                      .withValues(alpha: 0.08),
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                child: Icon(
                                  Icons.calendar_month_rounded,
                                  color: colorScheme.primary,
                                  size: 22,
                                ),
                              ),
                              const SizedBox(width: 14),
                              Column(
                                crossAxisAlignment:
                                    CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Monthly Activity',
                                    style: theme.textTheme.titleMedium
                                        ?.copyWith(
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  isLoading || heatmap == null
                                      ? const SkeletonLine(
                                          width: 90, height: 12)
                                      : Text(
                                          '${heatmap.activeDays} active days',
                                          style: theme
                                              .textTheme.bodySmall
                                              ?.copyWith(
                                            color: colorScheme
                                                .onSurfaceVariant,
                                          ),
                                        ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 24),

                          // The real heatmap grid.
                          OneMonthHeatmap(
                            dates: heatmap?.dates ?? const {},
                            restDates: heatmap?.restDates ?? const [],
                            isLoading: isLoading,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // ── Topic Distribution ──────────────────────────────────
                  TopicDistributionChart(
                    topics: snap.topics,
                    isLoading: isLoading,
                  ),
                  const SizedBox(height: 24),

                  // ── Difficulty Breakdown ─────────────────────────────────
                  DifficultyBreakdown(
                    difficulty: snap.difficulty,
                    isLoading: isLoading,
                  ),
                  const SizedBox(height: 24),

                  // ── Footer Stats ────────────────────────────────────────
                  Row(
                    children: [
                      Expanded(
                        child: Card(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(Icons.send_rounded,
                                    color: colorScheme.primary, size: 20),
                                const SizedBox(height: 14),
                                isLoading || stats == null
                                    ? const SkeletonLine(
                                        width: 52, height: 22)
                                    : Text(
                                        stats.totalMessages.toString(),
                                        style: theme.textTheme.titleLarge
                                            ?.copyWith(
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                const SizedBox(height: 6),
                                Text(
                                  'Total Logs',
                                  style:
                                      theme.textTheme.bodySmall?.copyWith(
                                    color: colorScheme.onSurfaceVariant,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Card(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(Icons.pie_chart_outline_rounded,
                                    color: colorScheme.primary, size: 20),
                                const SizedBox(height: 14),
                                isLoading || stats == null
                                    ? const SkeletonLine(
                                        width: 52, height: 22)
                                    : Text(
                                        stats.totalDaysTracked.toString(),
                                        style: theme.textTheme.titleLarge
                                            ?.copyWith(
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                const SizedBox(height: 6),
                                Text(
                                  'Days Tracked',
                                  style:
                                      theme.textTheme.bodySmall?.copyWith(
                                    color: colorScheme.onSurfaceVariant,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 112.0), // Ensures complex charts can roll entirely clear of the dock
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}


