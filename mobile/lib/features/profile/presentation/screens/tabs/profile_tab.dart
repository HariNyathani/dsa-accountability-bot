import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:mobile/core/theme/theme_provider.dart';
import 'package:mobile/core/widgets/skeleton_card.dart';
import 'package:mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:mobile/features/dashboard/presentation/providers/progress_provider.dart';
import 'package:mobile/features/profile/presentation/providers/user_profile_provider.dart';

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
    final profile = context.watch<UserProfileProvider>();

    return SafeArea(
      bottom: false,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
        child: Column(
          children: [
            // ── 1. Identity Header ──────────────────────────────────────
            const SizedBox(height: 12),
            _buildAvatar(colorScheme, profile),
            const SizedBox(height: 20),
            Text(
              profile.discordUsername ?? 'User',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
            if (profile.username != null &&
                profile.username!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                '@${profile.username}',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
            const SizedBox(height: 28),

            // ── 2. Vanity Stats Triptych ────────────────────────────────
            _buildVanityStats(theme, colorScheme, profile),
            const SizedBox(height: 32),


            // ── 4. Preferences ──────────────────────────────────────────
            _sectionLabel(theme, 'Preferences'),
            const SizedBox(height: 12),
            _buildPreferences(theme, colorScheme, profile),
            const SizedBox(height: 32),

            // ── 5. Account ──────────────────────────────────────────────
            _sectionLabel(theme, 'Account'),
            const SizedBox(height: 12),
            _buildAccountSection(theme, colorScheme, profile),
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
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // 1. Avatar
  // ===========================================================================

  Widget _buildAvatar(ColorScheme colorScheme, UserProfileProvider profile) {
    final initial = profile.discordUsername?.isNotEmpty == true
        ? profile.discordUsername![0].toUpperCase()
        : null;

    return Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        color: colorScheme.primary.withValues(alpha: 0.08),
        shape: BoxShape.circle,
      ),
      child: initial != null
          ? Center(
              child: Text(
                initial,
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                  color: colorScheme.primary,
                ),
              ),
            )
          : Icon(
              Icons.person_rounded,
              size: 38,
              color: colorScheme.primary,
            ),
    );
  }

  // ===========================================================================
  // 2. Vanity Stats
  // ===========================================================================

  Widget _buildVanityStats(
    ThemeData theme,
    ColorScheme colorScheme,
    UserProfileProvider profile,
  ) {
    return Consumer<ProgressProvider>(
      builder: (context, provider, _) {
        final stats = provider.stats;
        final isLoading = provider.isLoading;

        return Card(
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
                  isLoading || stats == null
                      ? null
                      : stats.totalMessages.toString(),
                ),
                _verticalDivider(colorScheme),
                _statColumn(
                  theme,
                  colorScheme,
                  'Best Streak',
                  isLoading || stats == null
                      ? null
                      : '${stats.longestStreak}',
                ),
                _verticalDivider(colorScheme),
                _statColumn(
                  theme,
                  colorScheme,
                  'Rank',
                  profile.leaderboardRank != null
                      ? '#${profile.leaderboardRank}'
                      : (profile.isLoading ? null : '—'),
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
    UserProfileProvider profile,
  ) {
    return Card(
      child: Column(
        children: [
          // Timezone row.
          InkWell(
            borderRadius:
                const BorderRadius.vertical(top: Radius.circular(24)),
            onTap: () => _showTimezoneSheet(profile),
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
                          profile.timezone,
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
                  firstChild: const SizedBox.shrink(),
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
                              profile.updateEmail(value.trim());
                            }
                          },
                        ),
                        const SizedBox(height: 10),
                        FilledButton(
                          onPressed: () {
                            final email = _emailController.text.trim();
                            if (email.isNotEmpty) {
                              profile.updateEmail(email);
                              FocusScope.of(context).unfocus();
                            }
                          },
                          style: FilledButton.styleFrom(
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                          child: const Text('Save Email'),
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

    return SizedBox(
      width: double.infinity,
      child: SegmentedButton<ThemeMode>(
        segments: const [
          ButtonSegment(
            value: ThemeMode.light,
            label: Text('Light'),
          ),
          ButtonSegment(
            value: ThemeMode.dark,
            label: Text('Dark'),
          ),
          ButtonSegment(
            value: ThemeMode.system,
            label: Text('System'),
          ),
        ],
        selected: {currentMode},
        showSelectedIcon: false,
        onSelectionChanged: (modes) {
          context.read<ThemeProvider>().setThemeMode(modes.first);
        },
        style: ButtonStyle(
          backgroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return colorScheme.primary;
            }
            return colorScheme.surface;
          }),
          foregroundColor: WidgetStateProperty.resolveWith((states) {
            if (states.contains(WidgetState.selected)) {
              return colorScheme.onPrimary;
            }
            return colorScheme.onSurface;
          }),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          side: WidgetStateProperty.all(
            BorderSide(color: colorScheme.outline, width: 0.5),
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

  void _showTimezoneSheet(UserProfileProvider profile) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => _TimezoneSheet(
        currentTimezone: profile.timezone,
        timezones: _timezones,
        onSelected: (tz) {
          profile.updateTimezone(tz);
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
    UserProfileProvider profile,
  ) {
    return Card(
      child: Column(
        children: [
          // Edit Username.
          InkWell(
            borderRadius:
                const BorderRadius.vertical(top: Radius.circular(24)),
            onTap: () => _showUsernameSheet(profile),
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
                'https://dsabot.in/api/users/${profile.userId}/export',
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
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: theme.scaffoldBackgroundColor,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) => _UsernameSheet(
        controller: controller,
        profile: profile,
        theme: theme,
        colorScheme: colorScheme,
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

    return Padding(
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
    );
  }
}

// =============================================================================
// Username bottom sheet — check & save
// =============================================================================

class _UsernameSheet extends StatefulWidget {
  const _UsernameSheet({
    required this.controller,
    required this.profile,
    required this.theme,
    required this.colorScheme,
  });

  final TextEditingController controller;
  final UserProfileProvider profile;
  final ThemeData theme;
  final ColorScheme colorScheme;

  @override
  State<_UsernameSheet> createState() => _UsernameSheetState();
}

class _UsernameSheetState extends State<_UsernameSheet> {
  bool _checking = false;
  bool? _available;
  String? _reason;

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
    return Padding(
      padding: EdgeInsets.fromLTRB(
        24,
        24,
        24,
        24 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Edit Username',
              style: widget.theme.textTheme.titleMedium
                  ?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 16),
          TextField(
            controller: widget.controller,
            autofocus: true,
            decoration: InputDecoration(
              hintText: 'Choose a username',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(color: widget.colorScheme.outline),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(color: widget.colorScheme.outline),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(
                    color: widget.colorScheme.primary, width: 1.5),
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
              style: widget.theme.textTheme.bodySmall?.copyWith(
                color: _available == true
                    ? const Color(0xFF4CAF50)
                    : const Color(0xFFE53935),
              ),
            ),
          ],
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton(
              onPressed: _checking ? null : _checkAndSave,
              child: _checking
                  ? SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          widget.colorScheme.onPrimary,
                        ),
                      ),
                    )
                  : const Text('Check & Save'),
            ),
          ),
        ],
      ),
    );
  }
}
