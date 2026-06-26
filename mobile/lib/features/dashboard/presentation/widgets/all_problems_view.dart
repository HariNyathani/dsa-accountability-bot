import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../core/services/haptic_service.dart';
import '../../../../core/widgets/glass_card.dart';
import '../../../../core/widgets/skeleton_card.dart';
import '../../data/models/user_stats.dart';
import '../providers/progress_provider.dart';
import 'due_reviews_card.dart';

/// Full-screen paginated view of the user's entire revision bank.
///
/// Pushed via [Navigator.push] from [RevisionTab].
///
/// Performance rules (v2 — June 2026):
///   - Renders at most 10 items per page (GPU budget).
///   - [RepaintBoundary] wraps the item list and the pagination bar.
///   - Page transitions use [AnimatedSwitcher] with a composited
///     [FadeTransition] + slide so there are no blank frames.
///   - All async callbacks are guarded with `if (!context.mounted) return;`.
///   - **P1**: Date arithmetic eliminated from `build()` — uses the
///     server-computed `daysRemaining` field from [RevisionBankItem].
///   - **P2**: Star icons pre-built once per item, not per frame.
///   - **P3**: Root `Consumer` replaced with `Selector` to prevent
///     phantom rebuilds from unrelated provider mutations.
///   - **P4**: `const` promotions on all static layout primitives.
class AllProblemsView extends StatefulWidget {
  const AllProblemsView({super.key});

  @override
  State<AllProblemsView> createState() => _AllProblemsViewState();
}

class _AllProblemsViewState extends State<AllProblemsView> {
  int _currentPage = 1;
  static const int _pageSize = 10;

  // Slide direction: +1 → next (slide left), -1 → prev (slide right)
  int _slideDirection = 1;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!context.mounted) return;
      _loadPage(1);
    });
  }

  void _loadPage(int page) {
    final provider = context.read<ProgressProvider>();
    provider.fetchAllRevisionItems(page: page, limit: _pageSize);
  }

  void _goNext() {
    final provider = context.read<ProgressProvider>();
    final total     = provider.totalRevisionCount;
    final lastPage  = math.max(1, (total / _pageSize).ceil());
    if (_currentPage >= lastPage) return;

    HapticService.lightTap();
    setState(() {
      _slideDirection = 1;
      _currentPage++;
    });
    _loadPage(_currentPage);
  }

  void _goPrev() {
    if (_currentPage <= 1) return;

    HapticService.lightTap();
    setState(() {
      _slideDirection = -1;
      _currentPage--;
    });
    _loadPage(_currentPage);
  }

  @override
  Widget build(BuildContext context) {
    final theme       = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark      = theme.brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('All Problems'),
        centerTitle: false,
      ),
      // ── P3: Selector instead of Consumer ────────────────────────────────
      // Only rebuilds when the specific triple (items, totalCount, loading)
      // changes — ignores unrelated provider mutations like submitReview().
      body: Selector<ProgressProvider,
          ({List<RevisionBankItem> items, int total, bool loading})>(
        selector: (_, p) => (
          items: p.allRevisionItems,
          total: p.totalRevisionCount,
          loading: p.isLoadingRevision,
        ),
        builder: (context, data, _) {
          final total    = data.total;
          final lastPage = math.max(1, (total / _pageSize).ceil());
          final loading  = data.loading;
          final items    = data.items;

          return Column(
            children: [
              // ── Paginated list ──────────────────────────────────────────
              //
              // Ghosting fix (June 2026):
              //   1. Composite key encodes (page, loading) so the skeleton
              //      and the loaded item list are distinct identities.
              //   2. layoutBuilder paints ONLY the incoming child — the
              //      outgoing child is removed immediately instead of
              //      lingering as a semi-transparent ghost behind the
              //      incoming FadeTransition.
              //   3. Duration shortened to 200ms to eliminate the visual
              //      window where both layers could overlap.
              Expanded(
                child: RepaintBoundary(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 200),
                    switchInCurve: Curves.easeOutCubic,
                    transitionBuilder: (child, animation) {
                      final slide = Tween<Offset>(
                        begin: Offset(_slideDirection * 0.08, 0),
                        end: Offset.zero,
                      ).animate(CurvedAnimation(
                        parent: animation,
                        curve: Curves.easeOutCubic,
                      ));
                      return FadeTransition(
                        opacity: animation,
                        child: SlideTransition(position: slide, child: child),
                      );
                    },
                    // Only paint the incoming child. The default
                    // layoutBuilder stacks both old and new in a Stack,
                    // causing the double-exposure ghosting.
                    layoutBuilder: (currentChild, previousChildren) {
                      return currentChild ?? const SizedBox.shrink();
                    },
                    child: loading
                        ? KeyedSubtree(
                            key: ValueKey<String>('skeleton_$_currentPage'),
                            child: _buildSkeletonList(colorScheme, theme),
                          )
                        : items.isEmpty
                            ? _buildEmptyState(theme, colorScheme)
                            : _buildItemList(
                                key: ValueKey<String>('page_$_currentPage'),
                                items: items,
                                theme: theme,
                                colorScheme: colorScheme,
                                isDark: isDark,
                              ),
                  ),
                ),
              ),

              // ── Pagination bar ──────────────────────────────────────────
              if (!loading || total > 0)
                RepaintBoundary(
                  child: _PaginationBar(
                    currentPage: _currentPage,
                    totalPages: lastPage,
                    onPrev: _currentPage > 1 ? _goPrev : null,
                    onNext: _currentPage < lastPage ? _goNext : null,
                    theme: theme,
                    colorScheme: colorScheme,
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  // ── Skeleton list ──────────────────────────────────────────────────────────

  Widget _buildSkeletonList(ColorScheme colorScheme, ThemeData theme) {
    return ListView.separated(
      key: const ValueKey<String>('skeleton'),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      itemCount: _pageSize,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (_, _) => GlassCard(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const SkeletonLine(width: 160, height: 13),
                  const Spacer(),
                  SkeletonLine(
                    width: 40,
                    height: 20,
                    borderRadius: 8,
                  ),
                ],
              ),
              const SizedBox(height: 10),
              const SkeletonLine(width: 90, height: 10),
              const SizedBox(height: 10),
              const SkeletonLine(width: double.infinity, height: 8),
            ],
          ),
        ),
      ),
    );
  }

  // ── Empty state ────────────────────────────────────────────────────────────

  Widget _buildEmptyState(ThemeData theme, ColorScheme colorScheme) {
    return Center(
      key: const ValueKey<String>('empty'),
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.inbox_outlined,
              size: 56,
              color: colorScheme.onSurfaceVariant.withValues(alpha: 0.4),
            ),
            const SizedBox(height: 16),
            Text(
              'No Problems Yet',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Log a LeetCode problem with a confidence\nscore to start building your revision bank.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── Item list ──────────────────────────────────────────────────────────────

  Widget _buildItemList({
    required Key key,
    required List<RevisionBankItem> items,
    required ThemeData theme,
    required ColorScheme colorScheme,
    required bool isDark,
  }) {
    return ListView.separated(
      key: key,
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      itemCount: items.length,
      separatorBuilder: (_, _) => const SizedBox(height: 10),
      itemBuilder: (_, index) => _ProblemCard(
        item: items[index],
        theme: theme,
        colorScheme: colorScheme,
        isDark: isDark,
      ),
    );
  }
}

// =============================================================================
// _ProblemCard — single revision-bank item card
// =============================================================================

/// ── P4: Shared const primitives ─────────────────────────────────────────────
/// Hoisted to file scope so every card instance shares the same canonical
/// objects. Eliminates ~20 redundant allocations per card per frame.
const _kCardPadding = EdgeInsets.all(14);
const _kPillPadding = EdgeInsets.symmetric(horizontal: 7, vertical: 3);
const _kPillRadius  = BorderRadius.all(Radius.circular(6));
const _kStarSize    = 14.0;
const _kAmberColor  = Color(0xFFF59E0B);

/// ── P4: Static platform badge ───────────────────────────────────────────────
/// The 'LC' badge never changes — extracted as a top-level const widget so it
/// is canonicalized once and reused across all card instances without any
/// per-frame allocation.
class _PlatformBadge extends StatelessWidget {
  const _PlatformBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: _kPillPadding,
      decoration: BoxDecoration(
        color: _kAmberColor.withValues(alpha: 0.14),
        borderRadius: _kPillRadius,
        border: Border.all(
          color: _kAmberColor.withValues(alpha: 0.30),
          width: 0.6,
        ),
      ),
      child: const Text(
        'LC',
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w800,
          color: _kAmberColor,
        ),
      ),
    );
  }
}

class _ProblemCard extends StatefulWidget {
  const _ProblemCard({
    required this.item,
    required this.theme,
    required this.colorScheme,
    required this.isDark,
  });

  final RevisionBankItem item;
  final ThemeData theme;
  final ColorScheme colorScheme;
  final bool isDark;

  @override
  State<_ProblemCard> createState() => _ProblemCardState();
}

class _ProblemCardState extends State<_ProblemCard> {
  bool _pressed = false;

  // ── P2: Pre-built star row ─────────────────────────────────────────────────
  // Built once in initState (and didUpdateWidget if the item changes) instead
  // of allocating 5 Icon + Color objects inside build() on every frame.
  late Widget _starRow;

  @override
  void initState() {
    super.initState();
    _starRow = _buildStarRow(widget.item.confidenceLast, widget.colorScheme);
  }

  @override
  void didUpdateWidget(covariant _ProblemCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.item.confidenceLast != widget.item.confidenceLast ||
        oldWidget.colorScheme != widget.colorScheme) {
      _starRow = _buildStarRow(widget.item.confidenceLast, widget.colorScheme);
    }
  }

  /// Builds the 5-star confidence meter once, reusable across frames.
  static Widget _buildStarRow(int confidence, ColorScheme cs) {
    final dimColor = cs.onSurface.withValues(alpha: 0.25);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(5, (i) {
        final filled = i < confidence;
        return Icon(
          filled ? Icons.star_rounded : Icons.star_outline_rounded,
          size: _kStarSize,
          color: filled ? _kAmberColor : dimColor,
        );
      }),
    );
  }

  static Color _difficultyColor(String d) => switch (d.toLowerCase()) {
        'easy'   => const Color(0xFF4CAF50),
        'medium' => const Color(0xFFFF9800),
        'hard'   => const Color(0xFFE53935),
        _        => const Color(0xFF9E9E9E),
      };

  // ── P1: Uses model's pre-computed daysRemaining ────────────────────────────
  // No more DateTime.now(), DateTime.tryParse(), .toLocal(), or midnight
  // truncation running in the build loop. The server already computes this.

  static String _daysLabel(int days) {
    if (days == 0) return 'Due Today';
    if (days == 1) return 'Due Tomorrow';
    if (days > 1) return 'Due in $days days';
    return 'Overdue by ${days.abs()} days';
  }

  static Color _daysColor(int days) {
    if (days == 0) return const Color(0xFFE53935);     // due today — red
    if (days == 1) return const Color(0xFFF59E0B);     // tomorrow — yellow
    if (days > 1) return const Color(0xFF9E9E9E);      // upcoming — neutral
    return const Color(0xFFB71C1C);                    // overdue — deep red
  }

  @override
  Widget build(BuildContext context) {
    final item      = widget.item;
    final theme     = widget.theme;
    final diffColor = _difficultyColor(item.difficulty);

    // ── P1: Server-computed field, zero per-frame cost ──────────────────────
    final int days  = item.daysRemaining.round();
    final daysColor = _daysColor(days);

    return GestureDetector(
      onTapDown: (_) => setState(() => _pressed = true),
      onTapUp: (_) => setState(() => _pressed = false),
      onTapCancel: () => setState(() => _pressed = false),
      onTap: () {
        HapticService.lightTap();
        showReviewSheet(
          context: context,
          problemId: item.problemId,
          title: item.title,
          difficulty: item.difficulty,
        );
      },
      child: AnimatedScale(
        scale: _pressed ? 0.98 : 1.0,
        duration: const Duration(milliseconds: 120),
        curve: Curves.easeOutCubic,
        child: GlassCard(
          child: Padding(
            padding: _kCardPadding,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ── Row 1: title + platform badge ─────────────────────────
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        item.title,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    // ── P4: Extracted const widget ──────────────────────────
                    const _PlatformBadge(),
                  ],
                ),
                const SizedBox(height: 8),

                // ── Row 2: difficulty pill + stars + days ticker ───────────
                Row(
                  children: [
                    // Difficulty pill
                    Container(
                      padding: _kPillPadding,
                      decoration: BoxDecoration(
                        color: diffColor.withValues(alpha: 0.12),
                        borderRadius: _kPillRadius,
                      ),
                      child: Text(
                        item.difficulty,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: diffColor,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),

                    // ── P2: Pre-built star row (no per-frame allocs) ────────
                    _starRow,

                    const Spacer(),

                    // Days ticker
                    Container(
                      padding: _kPillPadding,
                      decoration: BoxDecoration(
                        color: daysColor.withValues(alpha: 0.10),
                        borderRadius: _kPillRadius,
                      ),
                      child: Text(
                        _daysLabel(days),
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: daysColor,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// _PaginationBar — Prev / page-index / Next bar
// =============================================================================

class _PaginationBar extends StatelessWidget {
  const _PaginationBar({
    required this.currentPage,
    required this.totalPages,
    required this.onPrev,
    required this.onNext,
    required this.theme,
    required this.colorScheme,
  });

  final int currentPage;
  final int totalPages;
  final VoidCallback? onPrev;
  final VoidCallback? onNext;
  final ThemeData theme;
  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      child: GlassCard(
        radius: 18,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          child: Row(
            children: [
              // Prev button
              AnimatedOpacity(
                opacity: onPrev != null ? 1.0 : 0.35,
                duration: const Duration(milliseconds: 200),
                child: TextButton.icon(
                  onPressed: onPrev,
                  icon: const Icon(Icons.chevron_left_rounded, size: 18),
                  label: const Text('Prev'),
                  style: TextButton.styleFrom(
                    foregroundColor: colorScheme.primary,
                    textStyle: const TextStyle(
                        fontWeight: FontWeight.w700, fontSize: 13),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 8),
                  ),
                ),
              ),

              // Page indicator
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  child: Text(
                    '$currentPage / $totalPages pages',
                    key: ValueKey<int>(currentPage),
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: colorScheme.onSurface.withValues(alpha: 0.7),
                    ),
                  ),
                ),
              ),

              // Next button
              AnimatedOpacity(
                opacity: onNext != null ? 1.0 : 0.35,
                duration: const Duration(milliseconds: 200),
                child: TextButton.icon(
                  onPressed: onNext,
                  label: const Text('Next'),
                  icon: const Icon(Icons.chevron_right_rounded, size: 18),
                  iconAlignment: IconAlignment.end,
                  style: TextButton.styleFrom(
                    foregroundColor: colorScheme.primary,
                    textStyle: const TextStyle(
                        fontWeight: FontWeight.w700, fontSize: 13),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 12, vertical: 8),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
