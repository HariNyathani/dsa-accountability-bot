import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../../core/widgets/glass_card.dart';
import '../../../../../core/widgets/skeleton_card.dart';
import '../../../../profile/presentation/providers/user_profile_provider.dart';
import '../../providers/leaderboard_provider.dart';
import '../../providers/progress_provider.dart';
import '../leaderboard_screen.dart';

/// Dashboard tab — authenticated user's primary landing surface.
///
/// Reads from [ProgressProvider] and renders real data when available,
/// falling back to [SkeletonLine] placeholders while loading.
class DashboardTab extends StatefulWidget {
  const DashboardTab({super.key});

  @override
  State<DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<DashboardTab> {
  @override
  void initState() {
    super.initState();
    // Kick off data fetch if not already loaded.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final provider = context.read<ProgressProvider>();
      if (!provider.hasData && !provider.isLoading) {
        provider.fetchAll();
      }
      // Also prime the leaderboard data for the gateway card.
      final lb = context.read<LeaderboardProvider>();
      if (!lb.hasData && !lb.isLoading) {
        lb.fetch();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDarkMode = theme.brightness == Brightness.dark;

    // Read the user's claimed vanity handle / Discord username so the greeting
    // shows a real name. UserProfileProvider is registered in MainShell's inner
    // MultiProvider, so it is always in scope here.
    final profileProvider = context.watch<UserProfileProvider>();
    final displayName =
        profileProvider.username ?? profileProvider.discordUsername ?? 'User';
    final timeGreeting = _greeting();

    return SafeArea(
      bottom: false,
      child: Consumer<ProgressProvider>(
        builder: (context, provider, _) {
          final stats = provider.stats;
          final isLoading = provider.isLoading;
          final error = provider.error;

          return RefreshIndicator(
            onRefresh: () async {
              await provider.fetchAll();
              if (context.mounted) {
                await context.read<LeaderboardProvider>().fetch();
              }
            },
            color: colorScheme.primary,
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 24, 16, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Welcome header ──────────────────────────────────────
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      FittedBox(
                        fit: BoxFit.scaleDown,
                        child: Text(
                          stats != null && stats.postedToday
                              ? 'You\'re on fire! 🔥'
                              : '$timeGreeting, $displayName! 👋',
                          style: theme.textTheme.headlineMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.5,
                            color: isDarkMode ? Colors.white : colorScheme.primary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Your daily accountability digest',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: colorScheme.onSurfaceVariant.withValues(alpha: 0.8),
                          letterSpacing: 0.2,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),

                  // ── Error banner ────────────────────────────────────────
                  if (error != null && !isLoading) ...[
                    GlassCard(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Row(
                          children: [
                            Icon(Icons.wifi_off_rounded,
                                color: colorScheme.error, size: 20),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Text(
                                error,
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: colorScheme.error,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                  ],

                  // ── Current Streak ──────────────────────────────────────
                  _sectionLabel(theme, 'Current Streak'),
                  const SizedBox(height: 12),
                  GlassCard(
                    child: Padding(
                      padding: const EdgeInsets.all(18),
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
                                  Icons.local_fire_department_rounded,
                                  color: colorScheme.primary,
                                  size: 22,
                                ),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: isLoading || stats == null
                                    ? const Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          SkeletonLine(
                                              width: 80, height: 20),
                                          SizedBox(height: 6),
                                          SkeletonLine(
                                              width: 130, height: 12),
                                        ],
                                      )
                                    : Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            '${stats.currentStreak}',
                                            style: theme.textTheme.displayMedium?.copyWith(
                                              fontSize: 30,
                                              fontWeight: FontWeight.w900,
                                              color: isDarkMode ? Colors.white : colorScheme.primary,
                                              height: 1.1,
                                            ),
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            'BEST STREAK: ${stats.longestStreak}',
                                            style: TextStyle(
                                              fontSize: 10,
                                              fontWeight: FontWeight.w800,
                                              letterSpacing: 1.2,
                                              color: (isDarkMode ? Colors.white : colorScheme.primary).withValues(alpha: 0.6),
                                            ),
                                          ),
                                        ],
                                      ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 18),
                          Divider(color: colorScheme.primary.withValues(alpha: 0.1), thickness: 0.5),
                          const SizedBox(height: 14),
                          isLoading || stats == null
                              ? const SkeletonLine(width: 180, height: 12)
                              : Text(
                                  stats.postedToday
                                      ? '✅ You\'ve posted today'
                                      : '⏳ No submission yet today',
                                  style:
                                      theme.textTheme.bodySmall?.copyWith(
                                    color: colorScheme.onSurfaceVariant,
                                  ),
                                ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // ── Overview Stats Row ──────────────────────────────────
                  _sectionLabel(theme, 'Overview'),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: _StatCard(
                          icon: Icons.check_circle_outline_rounded,
                          label: 'Days Active',
                          value: stats?.daysPosted.toString(),
                          isLoading: isLoading,
                          theme: theme,
                          colorScheme: colorScheme,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _StatCard(
                          icon: Icons.trending_up_rounded,
                          label: 'Consistency',
                          value: stats != null
                              ? '${stats.consistencyPct.toStringAsFixed(0)}%'
                              : null,
                          isLoading: isLoading,
                          theme: theme,
                          colorScheme: colorScheme,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),

                  // ── Leaderboard Gateway ─────────────────────────────────
                  _sectionLabel(theme, 'Leaderboard'),
                  const SizedBox(height: 12),
                  _LeaderboardGatewayCard(
                    userId: provider.userId,
                  ),
                  const SizedBox(height: 24),

                  // ── Recent Activity ─────────────────────────────────────
                  _sectionLabel(theme, 'Recent Activity'),
                  const SizedBox(height: 12),
                  GlassCard(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      child: isLoading
                          ? Column(
                              children: List.generate(
                                  3, (i) => _skeletonRow(colorScheme, i)),
                            )
                          : provider.recentLogs.isEmpty
                              ? Padding(
                                  padding: const EdgeInsets.symmetric(
                                      vertical: 24),
                                  child: Center(
                                    child: Text(
                                      'No activity yet. Start solving!',
                                      style: theme.textTheme.bodySmall
                                          ?.copyWith(
                                        color:
                                            colorScheme.onSurfaceVariant,
                                      ),
                                    ),
                                  ),
                                )
                              : Column(
                                  children: List.generate(
                                    provider.recentLogs.length,
                                    (i) => _activityRow(
                                      theme,
                                      colorScheme,
                                      provider.recentLogs[i],
                                      isLast: i ==
                                          provider.recentLogs.length - 1,
                                    ),
                                  ),
                                ),
                    ),
                  ),
                  const SizedBox(height: 112.0), // High-fidelity clearance spacer for floating nav block
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  static String _greeting() {
    final hour = DateTime.now().hour;
    if (hour >= 6 && hour < 12) return 'Good morning';
    if (hour >= 12 && hour < 16) return 'Good afternoon';
    if (hour >= 16) return 'Good evening';
    return 'Night owl grind'; // 00:00–05:59
  }

  static Widget _sectionLabel(ThemeData theme, String text) {
    final isDark = theme.brightness == Brightness.dark;
    return Text(
      text.toUpperCase(),
      style: TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w800,
        letterSpacing: 1.6,
        color: (isDark ? Colors.white : theme.colorScheme.primary).withValues(alpha: 0.6),
      ),
    );
  }

  static Widget _skeletonRow(ColorScheme colorScheme, int index) {
    return Column(
      children: [
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 14),
          child: Row(
            children: [
              SkeletonLine(width: 36, height: 36, borderRadius: 10),
              SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 140, height: 13),
                    SizedBox(height: 6),
                    SkeletonLine(width: 90, height: 10),
                  ],
                ),
              ),
              SkeletonLine(width: 44, height: 10),
            ],
          ),
        ),
        if (index < 2) Divider(height: 0, color: colorScheme.primary.withValues(alpha: 0.1), thickness: 0.5),
      ],
    );
  }

  /// Extracts difficulty from log.parsedFields JSON string.
  ///
  /// Expects `parsedFields` to be a JSON string containing an `entries`
  /// array with objects that may have a `difficulty` field.
  static String? _extractDifficulty(dynamic log) {
    final raw = log.parsedFields;
    if (raw == null || raw.isEmpty) return null;
    try {
      final parsed = jsonDecode(raw);
      if (parsed is Map && parsed['entries'] is List) {
        final entries = parsed['entries'] as List;
        if (entries.isNotEmpty && entries[0] is Map) {
          final diff = entries[0]['difficulty']?.toString();
          if (diff != null && diff.isNotEmpty) return diff;
        }
      }
      // Fallback: top-level difficulty key.
      if (parsed is Map && parsed['difficulty'] != null) {
        return parsed['difficulty'].toString();
      }
    } catch (_) {
      // Malformed JSON — gracefully ignore.
    }
    return null;
  }

  static Color? _difficultyColor(String? difficulty) {
    return switch (difficulty?.toLowerCase()) {
      'easy' => const Color(0xFF4CAF50),
      'medium' => const Color(0xFFFF9800),
      'hard' => const Color(0xFFE53935),
      _ => null,
    };
  }

  static Widget _activityRow(
    ThemeData theme,
    ColorScheme colorScheme,
    dynamic log, {
    required bool isLast,
  }) {
    final topics = log.topics?.toString() ?? '';
    final type = log.messageType.toString();
    final difficulty = _extractDifficulty(log);
    final diffColor = _difficultyColor(difficulty);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 14),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: colorScheme.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  type == 'rest'
                      ? Icons.bedtime_rounded
                      : Icons.code_rounded,
                  color: colorScheme.primary,
                  size: 18,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      topics.isNotEmpty ? topics : type.toUpperCase(),
                      style: theme.textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      _relativeTime(log.postedAt),
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              // Difficulty pill (if available).
              if (difficulty != null && diffColor != null) ...[
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: diffColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    difficulty,
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: diffColor,
                      fontWeight: FontWeight.w600,
                      fontSize: 10,
                    ),
                  ),
                ),
                const SizedBox(width: 6),
              ],
              // Type pill.
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: colorScheme.primary.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  type,
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: colorScheme.primary,
                    fontWeight: FontWeight.w600,
                    fontSize: 10,
                  ),
                ),
              ),
            ],
          ),
        ),
        if (!isLast) Divider(height: 0, color: colorScheme.primary.withValues(alpha: 0.1), thickness: 0.5),
      ],
    );
  }

  static String _relativeTime(String isoString) {
    try {
      final date = DateTime.parse(isoString);
      final diff = DateTime.now().difference(date);
      if (diff.inMinutes < 1) return 'Just now';
      if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
      if (diff.inHours < 24) return '${diff.inHours}h ago';
      if (diff.inDays < 7) return '${diff.inDays}d ago';
      return '${date.day}/${date.month}';
    } catch (_) {
      return '';
    }
  }
}

// =============================================================================
// Leaderboard gateway card — tappable entry point
// =============================================================================

class _LeaderboardGatewayCard extends StatelessWidget {
  const _LeaderboardGatewayCard({required this.userId});

  final String userId;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Consumer<LeaderboardProvider>(
      builder: (context, lb, _) {
        // Determine subtitle text.
        String subtitle = 'View rankings';
        if (lb.hasData && lb.data != null) {
          final myEntry = lb.data!.entries.where((e) => e.userId == userId);
          if (myEntry.isNotEmpty) {
            subtitle =
                'You\'re #${myEntry.first.rank} of ${lb.data!.totalUsers} active';
          } else {
            subtitle = '${lb.data!.totalUsers} users ranked';
          }
        }

        return GlassCard(
          child: InkWell(
            borderRadius: BorderRadius.circular(24),
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute<void>(
                  builder: (_) => LeaderboardScreen(userId: userId),
                ),
              );
            },
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
                      Icons.emoji_events_rounded,
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
                          'Leaderboard',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 2),
                        lb.isLoading
                            ? const SkeletonLine(width: 120, height: 12)
                            : Text(
                                subtitle,
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
      },
    );
  }
}

// =============================================================================
// Small stat card — overview row
// =============================================================================

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.icon,
    required this.label,
    this.value,
    required this.isLoading,
    required this.theme,
    required this.colorScheme,
  });

  final IconData icon;
  final String label;
  final String? value;
  final bool isLoading;
  final ThemeData theme;
  final ColorScheme colorScheme;

  @override
  Widget build(BuildContext context) {
    final isDark = theme.brightness == Brightness.dark;
    return GlassCard(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: colorScheme.primary, size: 20),
            const SizedBox(height: 12),
            isLoading || value == null
                ? const SkeletonLine(width: 56, height: 28)
                : Text(
                    value!,
                    style: theme.textTheme.displayMedium?.copyWith(
                      fontSize: 28,
                      fontWeight: FontWeight.w900,
                      color: isDark ? Colors.white : colorScheme.primary,
                      height: 1.1,
                    ),
                  ),
            const SizedBox(height: 4),
            Text(
              label.toUpperCase(),
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.6,
                color: (isDark ? Colors.white : colorScheme.primary).withValues(alpha: 0.6),
              ),
            ),
          ],
        ),
      ),
    );
  }
}


