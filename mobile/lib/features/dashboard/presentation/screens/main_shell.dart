import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/analytics/presentation/screens/tabs/analytics_tab.dart';
import 'package:mobile/features/profile/presentation/screens/tabs/profile_tab.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/services/haptic_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../../profile/presentation/providers/user_profile_provider.dart';
import '../providers/leaderboard_provider.dart';
import '../providers/progress_provider.dart';
import '../widgets/log_progress_sheet.dart';
import 'tabs/dashboard_tab.dart';

/// Main authenticated navigation shell.
///
/// Hosts an [IndexedStack] of 3 core feature tabs behind a
/// Material 3 [NavigationBar] styled to match our design tokens:
/// cream background, hairline top border, jade-green active indicator.
///
/// A premium FAB floats above the nav bar to trigger the manual
/// progress-logging bottom sheet drawer.
///
/// Data providers ([ProgressProvider], [LeaderboardProvider],
/// [UserProfileProvider]) are created here with the real authenticated
/// Discord user ID obtained from [AuthProvider].
class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  static const _tabs = <Widget>[
    DashboardTab(),
    AnalyticsTab(),
    ProfileTab(),
  ];

  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthProvider>();
    final userId = authProvider.userId ?? 'me';
    final apiClient = context.read<ApiClient>();

    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    // Provide user-specific data providers scoped to the authenticated shell.
    // These are only created once MainShell mounts (i.e. after auth succeeds).
    // LeaderboardProvider is intentionally omitted here — it lives at the root
    // MultiProvider in main.dart so it remains accessible from any Navigator
    // route context, including pushed screens like LeaderboardScreen.
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => ProgressProvider(
            apiClient: apiClient,
            userId: userId,
          ),
        ),
        ChangeNotifierProvider(
          create: (_) => UserProfileProvider(
            apiClient: apiClient,
            userId: userId,
          )..fetchProfile(),
        ),
      ],
      child: Scaffold(
        body: IndexedStack(index: _currentIndex, children: _tabs),

        // ── Logging FAB ──────────────────────────────────────────────────
        // Wrapped in Builder so that innerContext is a descendant of the
        // inner MultiProvider (and thus has ProgressProvider as an ancestor).
        // The outer build() context sits above that MultiProvider and cannot
        // see ProgressProvider — innerContext resolves it correctly.
        floatingActionButton: Builder(
          builder: (innerContext) => FloatingActionButton(
            onPressed: () {
              HapticService.lightTap();
              showLogProgressSheet(innerContext);
            },
            elevation: 0,
            highlightElevation: 0,
            backgroundColor: colorScheme.primary,
            foregroundColor: colorScheme.onPrimary,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppTheme.buttonRadius), // 16 dp
            ),
            child: const Icon(Icons.add_rounded, size: 28),
          ),
        ),
        floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,

        bottomNavigationBar: Container(
          decoration: BoxDecoration(
            // Hairline top border matching the design system.
            border: Border(
              top: BorderSide(color: colorScheme.outline, width: 0.5),
            ),
          ),
          child: NavigationBarTheme(
            data: NavigationBarThemeData(
              iconTheme: WidgetStateProperty.resolveWith((states) {
                final isSelected = states.contains(WidgetState.selected);
                return IconThemeData(
                  color: isSelected
                      ? colorScheme.primary
                      : colorScheme.onSurfaceVariant,
                  size: 24,
                );
              }),
              labelTextStyle: WidgetStateProperty.resolveWith((states) {
                final isSelected = states.contains(WidgetState.selected);
                return theme.textTheme.labelSmall!.copyWith(
                  color: isSelected
                      ? colorScheme.primary
                      : colorScheme.onSurfaceVariant,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  fontSize: 11,
                );
              }),
            ),
            child: NavigationBar(
              selectedIndex: _currentIndex,
              onDestinationSelected: (i) =>
                  setState(() => _currentIndex = i),
              backgroundColor: theme.scaffoldBackgroundColor,
              elevation: 0,
              surfaceTintColor: Colors.transparent,
              indicatorColor: colorScheme.primary.withValues(alpha: 0.10),
              height: 72,
              animationDuration: const Duration(milliseconds: 400),
              labelBehavior:
                  NavigationDestinationLabelBehavior.alwaysShow,
              destinations: const [
                NavigationDestination(
                  icon: Icon(Icons.space_dashboard_outlined),
                  selectedIcon: Icon(Icons.space_dashboard_rounded),
                  label: 'Dashboard',
                ),
                NavigationDestination(
                  icon: Icon(Icons.analytics_outlined),
                  selectedIcon: Icon(Icons.analytics_rounded),
                  label: 'Analytics',
                ),
                NavigationDestination(
                  icon: Icon(Icons.person_outline_rounded),
                  selectedIcon: Icon(Icons.person_rounded),
                  label: 'Profile',
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
