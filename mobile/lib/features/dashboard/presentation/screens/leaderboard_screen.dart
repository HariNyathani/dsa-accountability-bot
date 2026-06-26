import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../core/services/haptic_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/cached_avatar.dart';
import '../../../../core/widgets/scroll_prefetch.dart';
import '../../../../core/widgets/spring_curve.dart';
import '../../data/models/leaderboard.dart';
import '../providers/leaderboard_provider.dart';

/// Full-screen leaderboard — pushed via [Navigator], not a tab.
///
/// Displays a ranked list of users with sort-key chips and
/// pull-to-refresh. Highlights the current user's row.
///
/// [userId] is injected by the caller rather than read from
/// [ProgressProvider], because pushed Navigator routes live above
/// [MainShell]'s inner [MultiProvider] and cannot see [ProgressProvider]
/// in their context.
///
/// ### Performance (P2 + P4 — June 2026)
/// - [Selector] used in both the sort-chip and list regions so the
///   AnimatedAlign capsule doesn't rebuild on every list scroll.
/// - All four sort variants are pre-fetched into memory after the
///   initial fetch (see [LeaderboardProvider.prefetchAllSorts]) so
///   tapping a different sort chip is instant.
/// - [PrefetchScrollController] (threshold 0.7) triggers a
///   background re-warm if the user scrolls past 70% before any
///   prefetch has completed.
class LeaderboardScreen extends StatefulWidget {
  const LeaderboardScreen({super.key, required this.userId});

  final String userId;

  @override
  State<LeaderboardScreen> createState() => _LeaderboardScreenState();
}

class _LeaderboardScreenState extends State<LeaderboardScreen> {
  late final PrefetchScrollController _scrollController;

  // Sort options: label → API value.
  static const _sortOptions = <String, String>{
    'Streak': 'streak',
    'Consistency': 'consistency',
    'Posts': 'posts',
    'Days': 'days',
  };

  @override
  void initState() {
    super.initState();
    _scrollController = PrefetchScrollController(
      threshold: 0.7,
      onNearEnd: () {
        if (!mounted) return;
        // Fallback prefetch trigger — fires once if the user scrolls
        // to the end before the initState post-frame callback has
        // kicked off [prefetchAllSorts].
        context.read<LeaderboardProvider>().prefetchAllSorts();
      },
    );

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      final provider = context.read<LeaderboardProvider>();
      if (!provider.hasData && !provider.isLoading) {
        await provider.fetch();
      }
      if (!mounted) return;
      // ── P2: Warm the cache for all 4 sort variants in the
      //         background so sort-chip switching is instant.
      provider.prefetchAllSorts();
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Leaderboard')),
      body: SafeArea(
        child: Column(
          children: [
            // ── Sort chips ───────────────────────────────────────────────
            // P4: Selector isolates rebuilds to the chips region only.
            // The list below no longer drives AnimatedAlign's tick.
            _SortChipBar(
              sortOptions: _sortOptions,
              theme: theme,
              colorScheme: colorScheme,
            ),

            // ── Main list ────────────────────────────────────────────────
            Expanded(
              child: Selector<LeaderboardProvider,
                  ({LeaderboardData? data, bool isLoading, String? error})>(
                selector: (_, p) => (
                  data: p.data,
                  isLoading: p.isLoading,
                  error: p.error,
                ),
                builder: (context, snapshot, _) {
                  // Loading state.
                  if (snapshot.isLoading && snapshot.data == null) {
                    return _LoadingSpinner(colorScheme: colorScheme);
                  }

                  // Error state.
                  if (snapshot.error != null && snapshot.data == null) {
                    return _ErrorState(
                      message: snapshot.error!,
                      onRetry: () =>
                          context.read<LeaderboardProvider>().fetch(),
                      theme: theme,
                      colorScheme: colorScheme,
                    );
                  }

                  final data = snapshot.data;
                  if (data == null) return const SizedBox.shrink();

                  return RefreshIndicator(
                    onRefresh: () =>
                        context.read<LeaderboardProvider>().refreshCurrent(),
                    color: colorScheme.primary,
                    child: ListView.builder(
                      controller: _scrollController,
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(24, 4, 24, 24),
                      itemCount: data.entries.length + 1, // +1 for footer
                      itemBuilder: (context, index) {
                        // Footer.
                        if (index == data.entries.length) {
                          return Padding(
                            padding: const EdgeInsets.only(top: 20),
                            child: Text(
                              '${data.activeStreaks} active streaks · '
                              '${data.totalUsers} total users',
                              textAlign: TextAlign.center,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: colorScheme.onSurfaceVariant,
                              ),
                            ),
                          );
                        }

                        final entry = data.entries[index];
                        final isCurrentUser = entry.userId == widget.userId;

                        return _LeaderboardRow(
                          entry: entry,
                          isCurrentUser: isCurrentUser,
                          sortBy: data.sortBy,
                        );
                      },
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// P4: Hoisted gradient constants — no longer allocated per build.
// =============================================================================

const _kDarkCapsuleGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [
    Color(0x23FFFFFF), // ~0.14 alpha — obsidian specular highlight
    Color(0x05FFFFFF), // ~0.02 alpha — feather fade to AMOLED black
  ],
);

const _kDarkCapsuleBorder = Border(
  top: BorderSide(color: Color(0x26FFFFFF), width: 1.0),
  bottom: BorderSide(color: Color(0x26FFFFFF), width: 1.0),
  left: BorderSide(color: Color(0x26FFFFFF), width: 1.0),
  right: BorderSide(color: Color(0x26FFFFFF), width: 1.0),
);

const _kLightCapsuleBorder = Border(
  top: BorderSide(color: Color(0xA6FFFFFF), width: 0.8),
  bottom: BorderSide(color: Color(0xA6FFFFFF), width: 0.8),
  left: BorderSide(color: Color(0xA6FFFFFF), width: 0.8),
  right: BorderSide(color: Color(0xA6FFFFFF), width: 0.8),
);

const _kDarkRowGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [
    Color(0x0DFFFFFF), // 0.05
    Color(0x02FFFFFF), // 0.01
  ],
);

const _kDarkRowBorder = Border(
  top: BorderSide(color: Color(0x26FFFFFF), width: 1.0),
  bottom: BorderSide(color: Color(0x26FFFFFF), width: 1.0),
  left: BorderSide(color: Color(0x26FFFFFF), width: 1.0),
  right: BorderSide(color: Color(0x26FFFFFF), width: 1.0),
);

const _kLightRowBorder = Border(
  top: BorderSide(color: Color(0x80FFFFFF), width: 1.0),
  bottom: BorderSide(color: Color(0x80FFFFFF), width: 1.0),
  left: BorderSide(color: Color(0x80FFFFFF), width: 1.0),
  right: BorderSide(color: Color(0x80FFFFFF), width: 1.0),
);

const _kSheetDarkGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [
    Color(0x23FFFFFF), // ~0.14 alpha — obsidian specular highlight
    Color(0x05FFFFFF), // ~0.02 alpha — feather fade to AMOLED black
  ],
);

const _kSheetSoftShadow = BoxShadow(
  color: Color(0x0A7A5234), // ~0.04 alpha
  blurRadius: 16,
  offset: Offset(0, 4),
);

const _kSoftShadow = BoxShadow(
  color: Color(0x0A7A5234), // ~0.04 alpha — warm brown
  blurRadius: 12,
  offset: Offset(0, 4),
);

// =============================================================================
// P4: Sort chip bar — isolated Selector so capsule animation
//      doesn't rebuild the list on every chip tap.
// =============================================================================

class _SortChipBar extends StatelessWidget {
  const _SortChipBar({
    required this.sortOptions,
    required this.theme,
    required this.colorScheme,
  });

  final Map<String, String> sortOptions;
  final ThemeData theme;
  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    return Selector<LeaderboardProvider, String>(
      selector: (_, p) => p.sortBy,
      builder: (context, currentSort, _) {
        final isDark = theme.brightness == Brightness.dark;
        final keys = sortOptions.keys.toList();
        final values = sortOptions.values.toList();
        final selectedIndex =
            values.indexOf(currentSort).clamp(0, values.length - 1);

        final alignmentX = switch (selectedIndex) {
          0 => -1.0,
          1 => -0.33,
          2 => 0.33,
          3 => 1.0,
          _ => -1.0,
        };

        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          child: Container(
            height: 46.0,
            decoration: BoxDecoration(
              color: colorScheme.onSurface.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(16.0),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16.0),
              child: Stack(
                children: [
                  AnimatedAlign(
                    alignment: Alignment(alignmentX, 0.0),
                    duration: const Duration(milliseconds: 350),
                    curve: SpringCurve.snap,
                    child: FractionallySizedBox(
                      widthFactor: 0.24,
                      heightFactor: 1.0,
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: isDark
                              ? _kDarkCapsuleGradient
                              : const LinearGradient(
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                  colors: [
                                    Color(0x99FFFFFF), // ~0.60
                                    Color(0x40FFFFFF), // ~0.25
                                  ],
                                ),
                          borderRadius: BorderRadius.circular(16.0),
                          border: isDark
                              ? _kDarkCapsuleBorder
                              : _kLightCapsuleBorder,
                          boxShadow:
                              isDark ? null : const [_kSoftShadow],
                        ),
                      ),
                    ),
                  ),
                  Row(
                    children: List.generate(4, (index) {
                      final isSelected = index == selectedIndex;
                      final key = keys[index];
                      final val = values[index];
                      return Expanded(
                        child: GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTap: () {
                            if (!isSelected) {
                              HapticService.lightTap();
                              context
                                  .read<LeaderboardProvider>()
                                  .setSortBy(val);
                            }
                          },
                          child: Center(
                            child: AnimatedDefaultTextStyle(
                              duration: const Duration(milliseconds: 350),
                              curve: SpringCurve.snap,
                              style: theme.textTheme.labelMedium!.copyWith(
                                fontWeight: isSelected
                                    ? FontWeight.w800
                                    : FontWeight.w500,
                                color: theme.colorScheme.onSurface
                                    .withValues(alpha: isSelected ? 1.0 : 0.65),
                              ),
                              child: Text(key),
                            ),
                          ),
                        ),
                      );
                    }),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

// =============================================================================
// P4: Loading + Error states — small, static, const.
// =============================================================================

class _LoadingSpinner extends StatelessWidget {
  const _LoadingSpinner({required this.colorScheme});
  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: SizedBox(
        width: 28,
        height: 28,
        child: CircularProgressIndicator(
          strokeWidth: 2.5,
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({
    required this.message,
    required this.onRetry,
    required this.theme,
    required this.colorScheme,
  });

  final String message;
  final VoidCallback onRetry;
  final ThemeData theme;
  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.wifi_off_rounded, color: colorScheme.error, size: 32),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// Leaderboard row — single entry card
// =============================================================================

class _LeaderboardRow extends StatelessWidget {
  const _LeaderboardRow({
    required this.entry,
    required this.isCurrentUser,
    required this.sortBy,
  });

  final LeaderboardEntry entry;
  final bool isCurrentUser;
  final String sortBy;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final rankDisplay = switch (entry.rank) {
      1 => '🥇',
      2 => '🥈',
      3 => '🥉',
      _ => '#${entry.rank}',
    };

    final displayName = entry.username ??
        entry.discordUsername ??
        'User ${entry.userId.length >= 6 ? entry.userId.substring(0, 6) : entry.userId}';

    final subtitle = _subtitleForSort(entry, sortBy);

    final isDark = theme.brightness == Brightness.dark;
    final cardColor = isCurrentUser
        ? colorScheme.primary.withValues(alpha: 0.06)
        : _rankTint(entry.rank);

    // P3: Use CachedAvatar (falls back to the same initial-circle
    // design when no URL is present). The widget is sized in a
    // dedicated slot so layout never shifts on image load.
    final initial = (entry.discordUsername?.isNotEmpty == true)
        ? entry.discordUsername![0].toUpperCase()
        : displayName[0].toUpperCase();

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        decoration: BoxDecoration(
          gradient: isDark
              ? _kDarkRowGradient
              : const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0x73FFFFFF), // ~0.45
                    Color(0x26FFFFFF), // ~0.15
                  ],
                ),
          borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          border: isDark ? _kDarkRowBorder : _kLightRowBorder,
        ),
        child: Material(
          color: cardColor ?? Colors.transparent,
          borderRadius: BorderRadius.circular(AppTheme.cardRadius),
          child: InkWell(
            borderRadius: BorderRadius.circular(AppTheme.cardRadius), // 24 dp
            onTap: () {
              HapticService.lightTap();
              if (isCurrentUser) {
                _showCurrentUserSnack(context);
              } else {
                _showProfileSheet(context, entry);
              }
            },
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Row(
                children: [
                  // P3: Discord avatar with initial fallback.
                  CachedAvatar(
                    url: null, // wired up when backend exposes avatar_url
                    fallbackInitial: initial,
                    size: 36,
                  ),
                  const SizedBox(width: 12),

                  // Rank badge.
                  SizedBox(
                    width: 40,
                    child: Text(
                      rankDisplay,
                      style: entry.rank <= 3
                          ? theme.textTheme.titleLarge
                          : theme.textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                              color: colorScheme.onSurfaceVariant,
                            ),
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Name + subtitle.
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          displayName,
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontWeight:
                                isCurrentUser ? FontWeight.w700 : FontWeight.w600,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          subtitle,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // "You" badge for current user.
                  if (isCurrentUser)
                    Container(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: colorScheme.primary.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'You',
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: colorScheme.primary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),

                  // Stat pill for non-current-user rows.
                  if (!isCurrentUser)
                    Container(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: colorScheme.primary.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        _statPillLabel(entry, sortBy),
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: colorScheme.primary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ── Rank tint for top 3 ─────────────────────────────────────────────────

  static Color? _rankTint(int rank) {
    return switch (rank) {
      1 => const Color(0xFFFFD700).withValues(alpha: 0.06), // gold
      2 => const Color(0xFFC0C0C0).withValues(alpha: 0.06), // silver
      3 => const Color(0xFFCD7F32).withValues(alpha: 0.06), // bronze
      _ => null,
    };
  }

  // ── Stat pill label based on sort key ───────────────────────────────────

  static String _statPillLabel(LeaderboardEntry entry, String sortBy) {
    return switch (sortBy) {
      'consistency' => '${entry.consistencyPct.toStringAsFixed(0)}%',
      'posts' => '${entry.totalMessages} posts',
      'days' => '${entry.daysPosted}d',
      _ => '🔥 ${entry.currentStreak}',
    };
  }

  // ── Subtitle ────────────────────────────────────────────────────────────

  static String _subtitleForSort(LeaderboardEntry entry, String sortBy) {
    final streak = '${entry.currentStreak} day streak';
    final pct = '${entry.consistencyPct.toStringAsFixed(0)}%';
    return switch (sortBy) {
      'consistency' => '$pct consistency · $streak',
      'posts' => '${entry.totalMessages} posts · $streak',
      'days' => '${entry.daysPosted} days active · $streak',
      _ => '$streak · $pct',
    };
  }

  // ── Current user snack ──────────────────────────────────────────────────

  static void _showCurrentUserSnack(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('This is you! 🎉'),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  // ── Profile sheet ───────────────────────────────────────────────────────

  static void _showProfileSheet(BuildContext context, LeaderboardEntry entry) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;
    final sheetColor =
        isDark ? const Color(0xFF121212) : const Color(0xFFFDFBF7);

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black54,
      builder: (_) => _UserProfileSheet(
        entry: entry,
        sheetColor: sheetColor,
        theme: theme,
        colorScheme: colorScheme,
      ),
    );
  }
}

// =============================================================================
// User profile bottom sheet — shown on leaderboard row tap
// =============================================================================

class _UserProfileSheet extends StatelessWidget {
  const _UserProfileSheet({
    required this.entry,
    required this.sheetColor,
    required this.theme,
    required this.colorScheme,
  });

  final LeaderboardEntry entry;
  final Color sheetColor;
  final ThemeData theme;
  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    final displayName = entry.username ??
        entry.discordUsername ??
        'User ${entry.userId.length >= 6 ? entry.userId.substring(0, 6) : entry.userId}';

    final initial = (entry.discordUsername?.isNotEmpty == true)
        ? entry.discordUsername![0].toUpperCase()
        : displayName[0].toUpperCase();

    final rankDisplay = switch (entry.rank) {
      1 => '🥇 #1',
      2 => '🥈 #2',
      3 => '🥉 #3',
      _ => '#${entry.rank}',
    };

    final isDark = theme.brightness == Brightness.dark;

    return RepaintBoundary(
      child: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: ClipRRect(
          borderRadius: const BorderRadius.vertical(
            top: Radius.circular(AppTheme.cardRadius), // 24 dp
          ),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 20.0, sigmaY: 20.0),
            child: Container(
              decoration: BoxDecoration(
                gradient: isDark
                    ? _kSheetDarkGradient
                    : const LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          Color(0x99FFFFFF), // ~0.60
                          Color(0x40FFFFFF), // ~0.25
                        ],
                      ),
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(AppTheme.cardRadius), // 24 dp
                ),
                border: Border(
                  top: BorderSide(
                    color: isDark
                        ? const Color(0x26FFFFFF) // ~0.15 alpha
                        : const Color(0xA6FFFFFF), // ~0.65 alpha
                    width: isDark ? 1.0 : 0.8,
                  ),
                ),
                boxShadow:
                    isDark ? null : const [_kSheetSoftShadow],
              ),
              child: SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // ── Drag handle ─────────────────────────────────────
                      Center(
                        child: Container(
                          width: 36,
                          height: 4,
                          margin: const EdgeInsets.only(bottom: 24),
                          decoration: BoxDecoration(
                            color:
                                colorScheme.onSurface.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                      ),

                      // ── P3: CachedAvatar with larger size ─────────────
                      CachedAvatar(
                        url: null, // wired when backend exposes avatar_url
                        fallbackInitial: initial,
                        size: 72,
                      ),
                      const SizedBox(height: 16),

                      // ── Name ───────────────────────────────────────────
                      Text(
                        entry.discordUsername ?? displayName,
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.3,
                        ),
                      ),
                      if (entry.username != null && entry.username!.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          '@${entry.username}',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                      const SizedBox(height: 8),

                      // ── Rank badge ──────────────────────────────────────
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: colorScheme.primary.withValues(alpha: 0.10),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text(
                          'Rank $rankDisplay',
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: colorScheme.primary,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),

                      // ── Stats grid ──────────────────────────────────────
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 20,
                          ),
                          child: Column(
                            children: [
                              Row(
                                children: [
                                  _statColumn('Current\nStreak',
                                      '${entry.currentStreak}'),
                                  _verticalDivider(),
                                  _statColumn('Best\nStreak',
                                      '${entry.longestStreak}'),
                                ],
                              ),
                              const SizedBox(height: 16),
                              Divider(height: 0, color: colorScheme.outline),
                              const SizedBox(height: 16),
                              Row(
                                children: [
                                  _statColumn('Days\nActive',
                                      '${entry.daysPosted}'),
                                  _verticalDivider(),
                                  _statColumn('Consistency',
                                      '${entry.consistencyPct.toStringAsFixed(0)}%'),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _statColumn(String label, String value) {
    return Expanded(
      child: Column(
        children: [
          Text(
            value,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            label,
            textAlign: TextAlign.center,
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
              height: 1.3,
            ),
          ),
        ],
      ),
    );
  }

  Widget _verticalDivider() {
    return Container(
      width: 0.5,
      height: 36,
      color: colorScheme.outline,
    );
  }
}
