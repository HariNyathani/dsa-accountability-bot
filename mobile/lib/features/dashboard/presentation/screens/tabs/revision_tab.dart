import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../../core/services/haptic_service.dart';
import '../../../../../core/widgets/glass_card.dart';
import '../../../../../core/widgets/skeleton_card.dart';
import '../../../data/models/user_stats.dart';
import '../../providers/progress_provider.dart';
import '../../widgets/all_problems_view.dart';
import '../../widgets/overdue_problems_view.dart';

/// Revision Bank tab — the user's spaced-repetition hub.
///
/// Lazy-loads its own data via [ProgressProvider.fetchAllRevisionItems] so it
/// never blocks the Dashboard startup path.
///
/// Sections:
///   1. Header ("Revision Bank")
///   2. Metrics row (Total / Due / Overdue)
///   3. Weakest Patterns (top-3 lowest-confidence topics + "All >" sheet)
///   4. "All Problems >" link → [AllProblemsView]
class RevisionTab extends StatefulWidget {
  const RevisionTab({super.key});

  @override
  State<RevisionTab> createState() => _RevisionTabState();
}

class _RevisionTabState extends State<RevisionTab> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!context.mounted) return;
      final provider = context.read<ProgressProvider>();
      // Warm both paginated caches so the OVERDUE count and All Problems
      // view are ready when the user first lands on this tab.  The
      // dashboard's fetchAll() also pre-warms these, but a user could
      // open this tab before fetchAll() finishes (e.g. when the initial
      // dashboard fetch failed) so we trigger an explicit warm here too.
      if (provider.allRevisionItems.isEmpty && !provider.isLoadingRevision) {
        provider.fetchAllRevisionItems();
      }
      if (provider.totalRevisionCountOverdue == 0 &&
          !provider.isLoadingRevision) {
        provider.fetchAllRevisionItems(filterMode: 'overdue');
      }
    });
  }

  Future<void> _refresh() async {
    if (!context.mounted) return;
    final provider = context.read<ProgressProvider>();
    // Pull-to-refresh re-warms BOTH paginated caches in parallel.
    await Future.wait([
      provider.fetchAllRevisionItems(filterMode: 'all'),
      provider.fetchAllRevisionItems(filterMode: 'overdue'),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;

    return SafeArea(
      bottom: false,
      child: Consumer<ProgressProvider>(
        builder: (context, provider, _) {
          return RefreshIndicator(
            onRefresh: _refresh,
            color: colorScheme.primary,
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 24, 16, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Header ────────────────────────────────────────────────
                  _buildHeader(theme, colorScheme, isDark),
                  const SizedBox(height: 24),

                  // ── Metrics Row ───────────────────────────────────────────
                  _buildMetricsRow(provider, theme, colorScheme, isDark),
                  const SizedBox(height: 28),

                  // ── Weakest Patterns ──────────────────────────────────────
                  RepaintBoundary(
                    child: _buildWeakestPatterns(provider, theme, colorScheme, isDark),
                  ),
                  const SizedBox(height: 28),

                  // ── All Problems link ─────────────────────────────────────
                  RepaintBoundary(
                    child: _buildAllProblemsLink(context, provider, theme, colorScheme, isDark),
                  ),
                  const SizedBox(height: 16),

                  // ── Overdue Problems link ─────────────────────────────────
                  RepaintBoundary(
                    child: _buildOverdueProblemsLink(context, provider, theme, colorScheme, isDark),
                  ),

                  // Nav bar clearance
                  const SizedBox(height: 112),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // ── Header ──────────────────────────────────────────────────────────────────

  Widget _buildHeader(ThemeData theme, ColorScheme colorScheme, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Text(
            'Revision Bank',
            style: theme.textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.w800,
              letterSpacing: -0.5,
              color: isDark ? Colors.white : colorScheme.primary,
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Spaced repetition · Track your recall',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant.withValues(alpha: 0.8),
            letterSpacing: 0.2,
          ),
        ),
      ],
    );
  }

  // ── Metrics Row ─────────────────────────────────────────────────────────────

  Widget _buildMetricsRow(
    ProgressProvider provider,
    ThemeData theme,
    ColorScheme colorScheme,
    bool isDark,
  ) {
    final total   = provider.totalRevisionCountAll;
    // Overdue count comes from the dedicated "overdue" cache, populated
    // eagerly during the dashboard's fetchAll() so the count is visible
    // before the user opens the paginated view.
    final overdue = provider.totalRevisionCountOverdue;

    // P4: aggregation moved to a model extension so this method
    // doesn't allocate a fold closure on every rebuild.
    final stats = provider.revisionTopicStats;
    final double avgConfidence = stats.averageConfidence;
    final String avgConfStr = '${avgConfidence.toStringAsFixed(1)} / 5';

    final loading = provider.isLoadingRevision;

    return Row(
      children: [
        Expanded(
          child: _MetricCard(
            icon: Icons.inventory_2_outlined,
            label: 'TOTAL',
            value: total.toString(),
            isLoading: loading,
            accentColor: colorScheme.primary,
            theme: theme,
            isDark: isDark,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _MetricCard(
            icon: Icons.star_outline_rounded,
            label: 'AVG CONFIDENCE',
            value: avgConfStr,
            isLoading: loading,
            accentColor: const Color(0xFF4CAF50),
            theme: theme,
            isDark: isDark,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _MetricCard(
            icon: Icons.warning_amber_rounded,
            label: 'OVERDUE',
            value: overdue.toString(),
            isLoading: loading,
            accentColor: const Color(0xFFE53935),
            theme: theme,
            isDark: isDark,
          ),
        ),
      ],
    );
  }

  /// Pushes the full-screen paginated [OverdueProblemsView] on top of the
  /// current route.  Reuses the same provider instance (via
  /// [ChangeNotifierProvider.value]) so the view shares the same paginated
  /// "overdue" cache that the metric count comes from.
  void _navigateToOverdue(ProgressProvider provider) {
    if (!mounted) return;
    HapticService.lightTap();

    Navigator.push(
      context,
      PageRouteBuilder<void>(
        pageBuilder: (_, _, _) =>
            ChangeNotifierProvider<ProgressProvider>.value(
          value: provider,
          child: const OverdueProblemsView(),
        ),
        transitionsBuilder: (_, animation, _, child) {
          return FadeTransition(
            opacity: CurvedAnimation(
              parent: animation,
              curve: Curves.easeOutQuint,
            ),
            child: child,
          );
        },
        transitionDuration: const Duration(milliseconds: 300),
      ),
    );
  }

  // ── Weakest Patterns ────────────────────────────────────────────────────────

  Widget _buildWeakestPatterns(
    ProgressProvider provider,
    ThemeData theme,
    ColorScheme colorScheme,
    bool isDark,
  ) {
    final stats   = provider.revisionTopicStats;
    final loading = provider.isLoadingRevision;
    final top3    = stats.take(3).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header with "All >" button
        Row(
          children: [
            Text(
              'WEAKEST PATTERNS',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.6,
                color: (isDark ? Colors.white : colorScheme.primary)
                    .withValues(alpha: 0.6),
              ),
            ),
            const Spacer(),
            GestureDetector(
              onTap: () {
                if (!context.mounted) return;
                HapticService.lightTap();
                _showAllPatternsSheet(context, stats, theme, colorScheme, isDark);
              },
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: colorScheme.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: colorScheme.primary.withValues(alpha: 0.20),
                    width: 0.8,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'All',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: colorScheme.primary,
                      ),
                    ),
                    const SizedBox(width: 2),
                    Icon(Icons.chevron_right_rounded,
                        size: 16, color: colorScheme.primary),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 14),

        // Pattern bars
        GlassCard(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: loading
                ? Column(
                    children: List.generate(
                      3,
                      (i) => Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const SkeletonLine(width: 120, height: 12),
                            const SizedBox(height: 8),
                            const SkeletonLine(width: double.infinity, height: 8),
                          ],
                        ),
                      ),
                    ),
                  )
                : stats.isEmpty
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 20),
                          child: Text(
                            'No revision data yet.\nLog a problem with a confidence score to begin.',
                            textAlign: TextAlign.center,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                      )
                    : Column(
                        children: top3.asMap().entries.map((entry) {
                          final idx  = entry.key;
                          final stat = entry.value;
                          return Padding(
                            padding: EdgeInsets.only(
                              bottom: idx < top3.length - 1 ? 18 : 0,
                            ),
                            child: _PatternBar(
                              stat: stat,
                              theme: theme,
                              colorScheme: colorScheme,
                              isDark: isDark,
                            ),
                          );
                        }).toList(),
                      ),
          ),
        ),
      ],
    );
  }

  // ── All Problems link ────────────────────────────────────────────────────────

  Widget _buildAllProblemsLink(
    BuildContext context,
    ProgressProvider provider,
    ThemeData theme,
    ColorScheme colorScheme,
    bool isDark,
  ) {
    return _ScalePressable(
      onTap: () {
        if (!context.mounted) return;
        HapticService.lightTap();

        // Capture the provider instance BEFORE pushing the route.
        // Navigator.push creates a new route that sits above the MainShell
        // MultiProvider in the widget tree, so AllProblemsView cannot walk up
        // to find ProgressProvider on its own.  Bridging with
        // ChangeNotifierProvider.value re-injects the *same* instance
        // (no duplication, no data loss) into the new route's subtree.
        final progressProvider = context.read<ProgressProvider>();

        Navigator.push(
          context,
          PageRouteBuilder<void>(
            pageBuilder: (_, _, _) => ChangeNotifierProvider<ProgressProvider>.value(
              value: progressProvider,
              child: const AllProblemsView(),
            ),
            transitionsBuilder: (_, animation, _, child) {
              return FadeTransition(
                opacity: CurvedAnimation(
                  parent: animation,
                  curve: Curves.easeOutQuint,
                ),
                child: child,
              );
            },
            transitionDuration: const Duration(milliseconds: 300),
          ),
        );
      },
      child: GlassCard(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: colorScheme.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  Icons.format_list_bulleted_rounded,
                  color: colorScheme.primary,
                  size: 22,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'All Problems',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      provider.totalRevisionCount > 0
                          ? '${provider.totalRevisionCount} problems tracked'
                          : 'View your full revision bank',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: colorScheme.onSurfaceVariant,
                size: 22,
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── Overdue Problems link ──────────────────────────────────────────────────

  Widget _buildOverdueProblemsLink(
    BuildContext context,
    ProgressProvider provider,
    ThemeData theme,
    ColorScheme colorScheme,
    bool isDark,
  ) {
    return _ScalePressable(
      onTap: () {
        if (!context.mounted) return;
        HapticService.lightTap();

        final progressProvider = context.read<ProgressProvider>();

        Navigator.push(
          context,
          PageRouteBuilder<void>(
            pageBuilder: (_, _, _) => ChangeNotifierProvider<ProgressProvider>.value(
              value: progressProvider,
              child: const OverdueProblemsView(),
            ),
            transitionsBuilder: (_, animation, _, child) {
              return FadeTransition(
                opacity: CurvedAnimation(
                  parent: animation,
                  curve: Curves.easeOutQuint,
                ),
                child: child,
              );
            },
            transitionDuration: const Duration(milliseconds: 300),
          ),
        );
      },
      child: GlassCard(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFFE53935).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(
                  Icons.warning_amber_rounded,
                  color: Color(0xFFE53935),
                  size: 22,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Overdue Problems',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      provider.totalRevisionCountOverdue > 0
                          ? '${provider.totalRevisionCountOverdue} problems overdue'
                          : 'No overdue problems',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: colorScheme.onSurfaceVariant,
                size: 22,
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ── All Patterns Bottom Sheet ────────────────────────────────────────────────

  void _showAllPatternsSheet(
    BuildContext context,
    List<RevisionTopicStat> stats,
    ThemeData theme,
    ColorScheme colorScheme,
    bool isDark,
  ) {
    if (stats.isEmpty) return;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        initialChildSize: 0.62,
        minChildSize: 0.40,
        maxChildSize: 0.92,
        builder: (sheetCtx, scrollController) {
          return Container(
            decoration: BoxDecoration(
              color: isDark
                  ? const Color(0xFF0D0D12).withValues(alpha: 0.96)
                  : const Color(0xFFF2E2DE).withValues(alpha: 0.96),
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(28)),
              border: Border(
                top: BorderSide(
                  color: Colors.white.withValues(alpha: isDark ? 0.12 : 0.60),
                  width: 0.8,
                ),
              ),
            ),
            child: Column(
              children: [
                // Handle nub
                const SizedBox(height: 12),
                Container(
                  width: 38,
                  height: 4,
                  decoration: BoxDecoration(
                    color: colorScheme.onSurface.withValues(alpha: 0.20),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(height: 18),

                // Header
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Row(
                    children: [
                      Text(
                        'All Patterns',
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                          color: isDark ? Colors.white : colorScheme.primary,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: colorScheme.primary.withValues(alpha: 0.10),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '${stats.length}',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                            color: colorScheme.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  child: Text(
                    'Sorted by confidence — weakest first',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // List
                Expanded(
                  child: ListView.separated(
                    controller: scrollController,
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                    itemCount: stats.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 10),
                    itemBuilder: (_, index) {
                      final stat = stats[index];
                      return _SheetPatternRow(
                        rank: index + 1,
                        stat: stat,
                        theme: theme,
                        colorScheme: colorScheme,
                        isDark: isDark,
                      );
                    },
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

// =============================================================================
// _MetricCard — compact GlassCard for the top metrics row
// =============================================================================

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.isLoading,
    required this.accentColor,
    required this.theme,
    required this.isDark,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final String value;
  final bool isLoading;
  final Color accentColor;
  final ThemeData theme;
  final bool isDark;

  /// Optional tap callback. When non-null the card is interactive and
  /// shows a subtle scale-press animation; when null the card is a
  /// static display tile.
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final card = GlassCard(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(
                    color: accentColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: accentColor, size: 16),
                ),
                // Tiny chevron on the right of the icon when tappable so
                // users get a subtle affordance hint.
                if (onTap != null) ...[
                  const Spacer(),
                  Icon(
                    Icons.chevron_right_rounded,
                    size: 14,
                    color: accentColor.withValues(alpha: 0.55),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 10),
            isLoading
                ? const SkeletonLine(width: 36, height: 22)
                : Text(
                    value,
                    style: theme.textTheme.displayMedium?.copyWith(
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                      color: isDark ? Colors.white : accentColor,
                      height: 1.1,
                    ),
                  ),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                fontSize: 9,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.4,
                color: accentColor.withValues(alpha: 0.65),
              ),
            ),
          ],
        ),
      ),
    );

    if (onTap == null) return card;
    return _ScalePressable(onTap: onTap!, child: card);
  }
}

// =============================================================================
// _PatternBar — horizontal confidence bar for the Weakest Patterns section
// =============================================================================

class _PatternBar extends StatelessWidget {
  const _PatternBar({
    required this.stat,
    required this.theme,
    required this.colorScheme,
    required this.isDark,
  });

  final RevisionTopicStat stat;
  final ThemeData theme;
  final ColorScheme colorScheme;
  final bool isDark;

  /// Interpolates a colour from red (1.0) → amber (3.0) → green (5.0).
  static Color _confidenceColor(double avg) {
    // Clamp to [1, 5] then normalise to [0, 1]
    final t = ((avg - 1.0) / 4.0).clamp(0.0, 1.0);
    const red   = Color(0xFFE53935);
    const amber = Color(0xFFF59E0B);
    const green = Color(0xFF4CAF50);

    if (t < 0.5) {
      return Color.lerp(red, amber, t * 2.0)!;
    } else {
      return Color.lerp(amber, green, (t - 0.5) * 2.0)!;
    }
  }

  @override
  Widget build(BuildContext context) {
    final barColor  = _confidenceColor(stat.avgConfidence);
    final fillRatio = (stat.avgConfidence / 5.0).clamp(0.0, 1.0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                stat.topic,
                style: theme.textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            Text(
              '${stat.avgConfidence.toStringAsFixed(1)} / 5',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: barColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        LayoutBuilder(
          builder: (_, constraints) {
            final fullWidth = constraints.maxWidth;
            return Stack(
              children: [
                // Track
                Container(
                  height: 7,
                  width: fullWidth,
                  decoration: BoxDecoration(
                    color: colorScheme.onSurface.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
                // Fill
                AnimatedContainer(
                  duration: const Duration(milliseconds: 600),
                  curve: Curves.easeOutQuint,
                  height: 7,
                  width: fullWidth * fillRatio,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        barColor.withValues(alpha: 0.7),
                        barColor,
                      ],
                    ),
                    borderRadius: BorderRadius.circular(4),
                    boxShadow: [
                      BoxShadow(
                        color: barColor.withValues(alpha: 0.35),
                        blurRadius: 6,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

// =============================================================================
// _SheetPatternRow — row inside the "All Patterns" bottom sheet
// =============================================================================

class _SheetPatternRow extends StatelessWidget {
  const _SheetPatternRow({
    required this.rank,
    required this.stat,
    required this.theme,
    required this.colorScheme,
    required this.isDark,
  });

  final int rank;
  final RevisionTopicStat stat;
  final ThemeData theme;
  final ColorScheme colorScheme;
  final bool isDark;

  static Color _confidenceColor(double avg) {
    final t = ((avg - 1.0) / 4.0).clamp(0.0, 1.0);
    const red   = Color(0xFFE53935);
    const amber = Color(0xFFF59E0B);
    const green = Color(0xFF4CAF50);
    if (t < 0.5) return Color.lerp(red, amber, t * 2.0)!;
    return Color.lerp(amber, green, (t - 0.5) * 2.0)!;
  }

  @override
  Widget build(BuildContext context) {
    final barColor  = _confidenceColor(stat.avgConfidence);
    final fillRatio = (stat.avgConfidence / 5.0).clamp(0.0, 1.0);

    return GlassCard(
      radius: 16,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            // Rank badge
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: barColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Text(
                  '#$rank',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: barColor,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),

            // Topic + bar
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    stat.topic,
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 5),
                  LayoutBuilder(builder: (_, c) {
                    return Stack(
                      children: [
                        Container(
                          height: 5,
                          width: c.maxWidth,
                          decoration: BoxDecoration(
                            color:
                                colorScheme.onSurface.withValues(alpha: 0.06),
                            borderRadius: BorderRadius.circular(3),
                          ),
                        ),
                        AnimatedContainer(
                          duration: const Duration(milliseconds: 500),
                          curve: Curves.easeOutQuint,
                          height: 5,
                          width: c.maxWidth * fillRatio,
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [
                                barColor.withValues(alpha: 0.7),
                                barColor,
                              ],
                            ),
                            borderRadius: BorderRadius.circular(3),
                          ),
                        ),
                      ],
                    );
                  }),
                ],
              ),
            ),
            const SizedBox(width: 10),

            // Score
            Text(
              '${stat.avgConfidence.toStringAsFixed(1)}/5',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: barColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// _ScalePressable — scales child to 0.98 on touch-down
// =============================================================================

class _ScalePressable extends StatefulWidget {
  const _ScalePressable({required this.onTap, required this.child});

  final VoidCallback onTap;
  final Widget child;

  @override
  State<_ScalePressable> createState() => _ScalePressableState();
}

class _ScalePressableState extends State<_ScalePressable> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onTap();
      },
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.98 : 1.0,
        duration: const Duration(milliseconds: 120),
        curve: Curves.easeOutCubic,
        child: widget.child,
      ),
    );
  }
}
