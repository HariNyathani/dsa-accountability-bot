import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:mobile/core/theme/theme_provider.dart';
import 'package:mobile/core/widgets/cached_avatar.dart';
import 'package:mobile/core/widgets/glass_card.dart';
import 'package:mobile/core/widgets/skeleton_card.dart';
import 'package:mobile/core/widgets/spring_curve.dart';
import 'package:mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:mobile/features/dashboard/presentation/providers/progress_provider.dart';
import 'package:mobile/features/profile/presentation/providers/user_profile_provider.dart';
import 'package:mobile/core/services/haptic_service.dart';

/// Profile tab — user identity, vanity stats, linked platforms,
/// preferences, and account management.
class ProfileTab extends StatefulWidget {
  const ProfileTab({super.key});

  @override
  State<ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends State<ProfileTab> {
  // ── Local state ──────────────────────────────────────────────────────────
  bool _emailRemindersOn = false;
  final _emailController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final profile = context.read<UserProfileProvider>();
      if (profile.email != null && profile.email!.isNotEmpty) {
        _emailController.text = profile.email!;
        setState(() => _emailRemindersOn = true);
      }
    });
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }


  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    // P4: Selector replaces context.watch<UserProfileProvider>() so
    // the tab only rebuilds when one of the displayed profile fields
    // actually changes.
    final profileSnap = context.select<UserProfileProvider, _ProfileSnap>(
      (p) => (
        username: p.username,
        discordUsername: p.discordUsername,
        timezone: p.timezone,
        rank: p.leaderboardRank,
        isLoading: p.isLoading,
      ),
    );

    return SafeArea(
      bottom: false,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
        child: Column(
          children: [
            // ── 1. Identity Header ──────────────────────────────────────
            const SizedBox(height: 12),
            _buildAvatar(colorScheme, profileSnap),
            const SizedBox(height: 20),
            Text(
              profileSnap.discordUsername ?? 'User',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
            if (profileSnap.username != null &&
                profileSnap.username!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                '@${profileSnap.username}',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
            const SizedBox(height: 40),

            // ── 2. Vanity Stats Triptych ────────────────────────────────
            _buildVanityStats(theme, colorScheme, profileSnap),
            const SizedBox(height: 40),


            // ── 4. Preferences ──────────────────────────────────────────
            _sectionLabel(theme, 'Preferences'),
            const SizedBox(height: 12),
            _buildPreferences(theme, colorScheme, profileSnap),
            const SizedBox(height: 32),

            // ── 5. Account ──────────────────────────────────────────────
            _sectionLabel(theme, 'Account'),
            const SizedBox(height: 12),
            _buildAccountSection(theme, colorScheme, profileSnap),
            const SizedBox(height: 24),

            // ── 6. Version footer ───────────────────────────────────────
            Text(
              'v1.0.0',
              style: theme.textTheme.bodySmall?.copyWith(
                color: colorScheme.onSurfaceVariant.withValues(alpha: 0.25),
                fontSize: 10,
              ),
            ),
            const SizedBox(height: 32),
            const SizedBox(height: 112.0), // High-fidelity bottom dock cushion
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // 1. Avatar
  // ===========================================================================

  Widget _buildAvatar(ColorScheme colorScheme, _ProfileSnap snap) {
    // P3: CachedAvatar — wired to read profile.avatarUrl when the
    // backend starts surfacing Discord avatar URLs. Falls back to the
    // same initial-letter bubble (or person icon) as before.
    final initial = snap.discordUsername?.isNotEmpty == true
        ? snap.discordUsername![0].toUpperCase()
        : '?';

    return CachedAvatar(
      url: null, // wire up to profile.avatarUrl when backend exposes it
      fallbackInitial: initial,
      size: 80,
    );
  }

  // ===========================================================================
  // 2. Vanity Stats
  // ===========================================================================

  Widget _buildVanityStats(
    ThemeData theme,
    ColorScheme colorScheme,
    _ProfileSnap snap,
  ) {
    return Selector<ProgressProvider, ({int? totalMessages, int? longestStreak, bool isLoading})>(
      selector: (_, p) => (
        totalMessages: p.stats?.totalMessages,
        longestStreak: p.stats?.longestStreak,
        isLoading: p.isLoading,
      ),
      builder: (context, ps, _) {
        return GlassCard(
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: 8,
              vertical: 20,
            ),
            child: Row(
              children: [
                _statColumn(
                  theme,
                  colorScheme,
                  'Solved',
                  ps.isLoading || ps.totalMessages == null
                      ? null
                      : ps.totalMessages.toString(),
                ),
                _verticalDivider(colorScheme),
                _statColumn(
                  theme,
                  colorScheme,
                  'Best Streak',
                  ps.isLoading || ps.longestStreak == null
                      ? null
                      : '${ps.longestStreak}',
                ),
                _verticalDivider(colorScheme),
                _statColumn(
                  theme,
                  colorScheme,
                  'Rank',
                  snap.rank != null
                      ? '#${snap.rank}'
                      : (snap.isLoading ? null : '—'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }


  // ===========================================================================
  // 4. Preferences
  // ===========================================================================

  Widget _buildPreferences(
    ThemeData theme,
    ColorScheme colorScheme,
    _ProfileSnap snap,
  ) {
    return GlassCard(
      child: Column(
        children: [
          // Timezone row.
          InkWell(
            borderRadius:
                const BorderRadius.vertical(top: Radius.circular(24)),
            onTap: _showTimezoneSheet,
            child: Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Row(
                children: [
                  _prefIcon(colorScheme, Icons.language_rounded),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Timezone',
                            style: theme.textTheme.bodyLarge
                                ?.copyWith(fontWeight: FontWeight.w600)),
                        const SizedBox(height: 2),
                        Text(
                          snap.timezone,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right_rounded,
                      color: colorScheme.onSurfaceVariant, size: 22),
                ],
              ),
            ),
          ),
          Divider(height: 0, color: colorScheme.outline),

          // Email reminders row.
          Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              children: [
                Row(
                  children: [
                    _prefIcon(colorScheme, Icons.email_outlined),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Text('Email Reminders',
                          style: theme.textTheme.bodyLarge
                              ?.copyWith(fontWeight: FontWeight.w600)),
                    ),
                    Switch.adaptive(
                      value: _emailRemindersOn,
                      activeTrackColor: colorScheme.primary,
                      onChanged: (on) =>
                          setState(() => _emailRemindersOn = on),
                    ),
                  ],
                ),
                AnimatedCrossFade(
                  firstChild: const SizedBox(width: double.infinity, height: 0),
                  secondChild: Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        TextField(
                          controller: _emailController,
                          keyboardType: TextInputType.emailAddress,
                          decoration: InputDecoration(
                            hintText: 'your@email.com',
                            filled: true,
                            fillColor: colorScheme.onSurface.withValues(alpha: 0.05),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide:
                                  BorderSide(color: colorScheme.outline),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide:
                                  BorderSide(color: colorScheme.outline),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(
                                  color: colorScheme.primary, width: 1.5),
                            ),
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 14),
                          ),
                          onSubmitted: (value) {
                            if (value.trim().isNotEmpty) {
                              context
                                  .read<UserProfileProvider>()
                                  .updateEmail(value.trim());
                            }
                          },
                        ),
                        const SizedBox(height: 10),
                        Container(
                          width: double.infinity,
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            gradient: const LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [
                                Color(0xFF9E6F4A),
                                Color(0xFF7A5234),
                              ],
                            ),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.40),
                              width: 0.8,
                            ),
                          ),
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              borderRadius: BorderRadius.circular(12),
                              onTap: () {
                                final email = _emailController.text.trim();
                                if (email.isNotEmpty) {
                                  context
                                      .read<UserProfileProvider>()
                                      .updateEmail(email);
                                  FocusScope.of(context).unfocus();
                                }
                              },
                              child: Padding(
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                child: Center(
                                  child: Text(
                                    'Save Email',
                                    style: theme.textTheme.labelLarge?.copyWith(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  crossFadeState: _emailRemindersOn
                      ? CrossFadeState.showSecond
                      : CrossFadeState.showFirst,
                  duration: const Duration(milliseconds: 250),
                ),
              ],
            ),
          ),
          Divider(height: 0, color: colorScheme.outline),

          // Appearance row.
          Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _prefIcon(colorScheme, Icons.dark_mode_outlined),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Text('Appearance',
                          style: theme.textTheme.bodyLarge
                              ?.copyWith(fontWeight: FontWeight.w600)),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                _buildThemeSelector(theme, colorScheme),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildThemeSelector(ThemeData theme, ColorScheme colorScheme) {
    final currentMode = context.watch<ThemeProvider>().themeMode;
    final isDark = theme.brightness == Brightness.dark;

    final Alignment alignment = switch (currentMode) {
      ThemeMode.light => const Alignment(-1.0, 0.0),
      ThemeMode.system => const Alignment(1.0, 0.0),
      ThemeMode.dark => const Alignment(0.0, 0.0),
    };

    return Container(
      height: 48.0,
      decoration: BoxDecoration(
        color: colorScheme.onSurface.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(16.0),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16.0),
        child: Stack(
          children: [
            // Sliding Capsule Engine
            AnimatedAlign(
              alignment: alignment,
              duration: const Duration(milliseconds: 350),
              curve: SpringCurve.snap,
              child: FractionallySizedBox(
                widthFactor: 0.3333,
                heightFactor: 1.0,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: isDark
                        ? const LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              Color(0x23FFFFFF), // ~0.14 alpha — obsidian specular highlight
                              Color(0x05FFFFFF), // ~0.02 alpha — feather fade to AMOLED black
                            ],
                          )
                        : LinearGradient(
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                            colors: [
                              Colors.white.withValues(alpha: 0.60),
                              Colors.white.withValues(alpha: 0.25),
                            ],
                          ),
                    borderRadius: BorderRadius.circular(16.0),
                    border: isDark
                        ? Border.all(
                            color: Colors.white.withValues(alpha: 0.15),
                            width: 1.0,
                          )
                        : Border.all(
                            color: Colors.white.withValues(alpha: 0.65),
                            width: 0.8,
                          ),
                    boxShadow: isDark
                        ? null
                        : [
                            BoxShadow(
                              color: const Color(0xFF7A5234).withValues(alpha: 0.04),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                  ),
                ),
              ),
            ),
            // Interactivity Nodes
            Row(
              children: [
                _buildThemeSegment(ThemeMode.light, 'Light', currentMode, theme),
                _buildThemeSegment(ThemeMode.dark, 'Dark', currentMode, theme),
                _buildThemeSegment(ThemeMode.system, 'System', currentMode, theme),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildThemeSegment(ThemeMode mode, String label, ThemeMode currentMode, ThemeData theme) {
    final isSelected = mode == currentMode;
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () {
          if (!isSelected) {
            HapticService.lightTap();
            context.read<ThemeProvider>().setThemeMode(mode);
          }
        },
        child: Center(
          child: AnimatedDefaultTextStyle(
            duration: const Duration(milliseconds: 350),
            curve: SpringCurve.snap,
            style: theme.textTheme.bodyMedium!.copyWith(
              fontWeight: isSelected ? FontWeight.w800 : FontWeight.w500,
              color: theme.colorScheme.onSurface.withValues(alpha: isSelected ? 1.0 : 0.65),
            ),
            child: Text(label),
          ),
        ),
      ),
    );
  }

  static const _timezones = <String>[
    'Asia/Kolkata',
    'America/New_York',
    'UTC',
    'America/Los_Angeles',
    'Europe/London',
  ];

  void _showTimezoneSheet() {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      elevation: 0,
      builder: (ctx) => _TimezoneSheet(
        currentTimezone: context.read<UserProfileProvider>().timezone,
        timezones: _timezones,
        onSelected: (tz) {
          context.read<UserProfileProvider>().updateTimezone(tz);
          Navigator.pop(ctx);
        },
      ),
    );
  }

  Widget _prefIcon(ColorScheme colorScheme, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: colorScheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Icon(icon, color: colorScheme.primary, size: 20),
    );
  }

  // ===========================================================================
  // 5. Account
  // ===========================================================================

  Widget _buildAccountSection(
    ThemeData theme,
    ColorScheme colorScheme,
    _ProfileSnap snap,
  ) {
    return GlassCard(
      child: Column(
        children: [
          // Edit Username.
          InkWell(
            borderRadius:
                const BorderRadius.vertical(top: Radius.circular(24)),
            onTap: () =>
                _showUsernameSheet(context.read<UserProfileProvider>()),
            child: _accountRow(
              theme: theme,
              colorScheme: colorScheme,
              icon: Icons.edit_rounded,
              label: 'Edit Username',
              iconColor: colorScheme.primary,
              iconBgColor: colorScheme.primary.withValues(alpha: 0.08),
            ),
          ),
          Divider(height: 0, color: colorScheme.outline),

          // Export Data.
          InkWell(
            onTap: () async {
              final uri = Uri.parse(
                'https://dsabot.in/api/users/${context.read<UserProfileProvider>().userId}/export',
              );
              await launchUrl(uri, mode: LaunchMode.externalApplication);
            },
            child: _accountRow(
              theme: theme,
              colorScheme: colorScheme,
              icon: Icons.upload_rounded,
              label: 'Export Data',
              iconColor: colorScheme.primary,
              iconBgColor: colorScheme.primary.withValues(alpha: 0.08),
            ),
          ),
          Divider(height: 0, color: colorScheme.outline),

          // Sign Out.
          InkWell(
            onTap: () => context.read<AuthProvider>().logout(),
            borderRadius:
                const BorderRadius.vertical(bottom: Radius.circular(24)),
            child: _accountRow(
              theme: theme,
              colorScheme: colorScheme,
              icon: Icons.logout_rounded,
              label: 'Sign Out',
              iconColor: colorScheme.error,
              iconBgColor: colorScheme.error.withValues(alpha: 0.08),
              labelColor: colorScheme.error,
            ),
          ),
        ],
      ),
    );
  }

  Widget _accountRow({
    required ThemeData theme,
    required ColorScheme colorScheme,
    required IconData icon,
    required String label,
    required Color iconColor,
    required Color iconBgColor,
    Color? labelColor,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: iconBgColor,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: iconColor, size: 20),
          ),
          const SizedBox(width: 14),
          Text(
            label,
            style: theme.textTheme.bodyLarge?.copyWith(
              fontWeight: FontWeight.w600,
              color: labelColor,
            ),
          ),
          const Spacer(),
          Icon(Icons.chevron_right_rounded,
              color: colorScheme.onSurfaceVariant, size: 22),
        ],
      ),
    );
  }

  void _showUsernameSheet(UserProfileProvider profile) {
    final controller = TextEditingController(text: profile.username);

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => _UsernameSheet(
        controller: controller,
        profile: profile,
      ),
    );
  }

  // ===========================================================================
  // Shared helpers
  // ===========================================================================

  static Widget _sectionLabel(ThemeData theme, String text) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        text,
        style: theme.textTheme.titleSmall?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: 0.3,
        ),
      ),
    );
  }

  static Widget _statColumn(
    ThemeData theme,
    ColorScheme colorScheme,
    String label,
    String? value,
  ) {
    return Expanded(
      child: Column(
        children: [
          value == null
              ? const SkeletonLine(width: 40, height: 22)
              : Text(
                  value,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
          const SizedBox(height: 6),
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }

  static Widget _verticalDivider(ColorScheme colorScheme) {
    return Container(
      width: 0.5,
      height: 36,
      color: colorScheme.outline,
    );
  }
}

// =============================================================================
// P4: Internal typedef — the slim snapshot of UserProfileProvider
//      fields the profile tab actually displays. Selector emits this
//      record so unrelated mutations (e.g. error changes, rank changes
//      driven by other flows) don't rebuild the whole tab.
// =============================================================================

typedef _ProfileSnap = ({
  String? username,
  String? discordUsername,
  String timezone,
  int? rank,
  bool isLoading,
});

// =============================================================================
// Timezone bottom sheet — searchable list
// =============================================================================

class _TimezoneSheet extends StatefulWidget {
  const _TimezoneSheet({
    required this.currentTimezone,
    required this.timezones,
    required this.onSelected,
  });

  final String currentTimezone;
  final List<String> timezones;
  final ValueChanged<String> onSelected;

  @override
  State<_TimezoneSheet> createState() => _TimezoneSheetState();
}

class _TimezoneSheetState extends State<_TimezoneSheet> {
  String _filter = '';

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final filtered = widget.timezones
        .where((tz) => tz.toLowerCase().contains(_filter.toLowerCase()))
        .toList();

    final isDark = theme.brightness == Brightness.dark;

    return RepaintBoundary(
      child: Padding(
      padding: EdgeInsets.all(16).copyWith(
        bottom: 16 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16.0),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 16.0, sigmaY: 16.0),
          child: Container(
            decoration: BoxDecoration(
              color: isDark ? Colors.transparent : null,
              gradient: isDark
                  ? const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Color(0x0DFFFFFF), // 0.05
                        Color(0x02FFFFFF), // 0.01
                      ],
                    )
                  : LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Colors.white.withValues(alpha: 0.60),
                        Colors.white.withValues(alpha: 0.25),
                      ],
                    ),
              borderRadius: BorderRadius.circular(16.0),
              border: isDark
                  ? Border.all(
                      color: Colors.white.withValues(alpha: 0.15),
                      width: 1.0,
                    )
                  : Border.all(
                      color: Colors.white.withValues(alpha: 0.65),
                      width: 1.0,
                    ),
              boxShadow: isDark
                  ? null
                  : [
                      BoxShadow(
                        color: const Color(0xFF7A5234).withValues(alpha: 0.04),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
            ),
            child: SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(24, 24, 24, 16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Select Timezone',
              style: theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 16),
          TextField(
            autofocus: true,
            onChanged: (v) => setState(() => _filter = v),
            decoration: InputDecoration(
              hintText: 'Search…',
              filled: true,
              fillColor: colorScheme.onSurface.withValues(alpha: 0.05),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(color: colorScheme.outline),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(color: colorScheme.outline),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide:
                    BorderSide(color: colorScheme.primary, width: 1.5),
              ),
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            ),
          ),
          const SizedBox(height: 8),
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 300),
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: filtered.length,
              itemBuilder: (_, i) {
                final tz = filtered[i];
                final isSelected = tz == widget.currentTimezone;

                return ListTile(
                  title: Text(tz,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight:
                            isSelected ? FontWeight.w700 : FontWeight.w400,
                        color: isSelected
                            ? colorScheme.primary
                            : colorScheme.onSurface,
                      )),
                  trailing: isSelected
                      ? Icon(Icons.check_rounded,
                          color: colorScheme.primary, size: 20)
                      : null,
                  onTap: () => widget.onSelected(tz),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 8),
                );
              },
            ),
          ),
        ],
      ),
       )))))));
  }
}

// =============================================================================
// Username bottom sheet — check & save
// =============================================================================

class _UsernameSheet extends StatefulWidget {
  const _UsernameSheet({
    required this.controller,
    required this.profile,
  });

  final TextEditingController controller;
  final UserProfileProvider profile;

  @override
  State<_UsernameSheet> createState() => _UsernameSheetState();
}

class _UsernameSheetState extends State<_UsernameSheet> {
  bool _checking = false;
  bool? _available;
  String? _reason;

  @override
  void dispose() {
    // The controller is created in _showUsernameSheet() and transferred to
    // this sheet as widget.controller. Since no other owner calls dispose(),
    // we must do it here to avoid the TextEditingController leak.
    widget.controller.dispose();
    super.dispose();
  }

  Future<void> _checkAndSave() async {
    final name = widget.controller.text.trim();
    if (name.isEmpty) return;

    setState(() {
      _checking = true;
      _available = null;
      _reason = null;
    });

    final result = await widget.profile.checkUsername(name);
    final isAvailable = result['available'] as bool? ?? false;
    final reason = result['reason']?.toString();

    if (isAvailable) {
      final success = await widget.profile.updateUsername(name);
      if (mounted) {
        if (success) {
          Navigator.pop(context);
        } else {
          setState(() {
            _checking = false;
            _available = false;
            _reason = widget.profile.error ?? 'Failed to update';
          });
        }
      }
    } else {
      if (mounted) {
        setState(() {
          _checking = false;
          _available = false;
          _reason = reason ?? 'Username unavailable';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;

    return Padding(
      padding: EdgeInsets.fromLTRB(
        16, 16, 16,
        16 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20.0),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 16.0, sigmaY: 16.0),
          child: Container(
            decoration: BoxDecoration(
              gradient: isDark
                  ? const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Color(0x0DFFFFFF), // 0.05 — obsidian glass
                        Color(0x02FFFFFF), // 0.01 — feather fade
                      ],
                    )
                  : LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Colors.white.withValues(alpha: 0.60),
                        Colors.white.withValues(alpha: 0.25),
                      ],
                    ),
              borderRadius: BorderRadius.circular(20.0),
              border: Border.all(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.15)
                    : Colors.white.withValues(alpha: 0.55),
                width: 1.0,
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 24, 24, 24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Edit Username',
                      style: theme.textTheme.titleMedium
                          ?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 16),
                  TextField(
                    controller: widget.controller,
                    autofocus: true,
                    style: theme.textTheme.bodyMedium,
                    decoration: InputDecoration(
                      hintText: 'Choose a username',
                      filled: true,
                      fillColor: colorScheme.onSurface.withValues(alpha: 0.05),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(color: colorScheme.outline),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(color: colorScheme.outline),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide(
                            color: colorScheme.primary, width: 1.5),
                      ),
                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                      suffixIcon: _available == null
                          ? null
                          : _available!
                              ? const Icon(Icons.check_circle_rounded,
                                  color: Color(0xFF4CAF50))
                              : const Icon(Icons.cancel_rounded,
                                  color: Color(0xFFE53935)),
                    ),
                  ),
                  if (_reason != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      _reason!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: _available == true
                            ? const Color(0xFF4CAF50)
                            : const Color(0xFFE53935),
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  Builder(
                    builder: (context) {
                      final isEnabled = !_checking;

                      return Container(
                        width: double.infinity,
                        height: 48,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(12),
                          color: !isEnabled
                              ? colorScheme.onSurface.withValues(alpha: 0.08)
                              : (isDark ? Colors.transparent : null),
                          gradient: isEnabled && !isDark
                              ? const LinearGradient(
                                  begin: Alignment.topCenter,
                                  end: Alignment.bottomCenter,
                                  colors: [
                                    Color(0xFF9E6F4A),
                                    Color(0xFF7A5234),
                                  ],
                                )
                              : null,
                          border: isEnabled
                              ? (isDark
                                  ? Border.all(
                                      color: Colors.white.withValues(alpha: 0.15),
                                      width: 1.0,
                                    )
                                  : Border.all(
                                      color: Colors.white.withValues(alpha: 0.40),
                                      width: 0.8,
                                    ))
                              : null,
                        ),
                        child: Material(
                          color: Colors.transparent,
                          child: InkWell(
                            borderRadius: BorderRadius.circular(12),
                            onTap: isEnabled ? _checkAndSave : null,
                            child: Center(
                              child: _checking
                                  ? SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        valueColor: AlwaysStoppedAnimation<Color>(
                                          colorScheme.onSurface.withValues(alpha: 0.35),
                                        ),
                                      ),
                                    )
                                  : Text(
                                      'Check & Save',
                                      style: theme.textTheme.labelLarge?.copyWith(
                                        color: !isEnabled
                                            ? colorScheme.onSurface.withValues(alpha: 0.35)
                                            : Colors.white,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}


