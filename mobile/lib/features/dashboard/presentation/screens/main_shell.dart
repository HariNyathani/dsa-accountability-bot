import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'package:mobile/core/widgets/spring_curve.dart';

import 'package:mobile/features/analytics/presentation/screens/tabs/analytics_tab.dart';
import 'package:mobile/features/profile/presentation/screens/tabs/profile_tab.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/services/haptic_service.dart';
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
        extendBody: true,
        body: IndexedStack(index: _currentIndex, children: _tabs),

        // ── Logging FAB ──────────────────────────────────────────────────
        // Wrapped in Builder so that innerContext is a descendant of the
        // inner MultiProvider (and thus has ProgressProvider as an ancestor).
        // The outer build() context sits above that MultiProvider and cannot
        // see ProgressProvider — innerContext resolves it correctly.
        floatingActionButton: RepaintBoundary(
          child: Builder(
            builder: (innerContext) {
              final isDark = theme.brightness == Brightness.dark;
              return Container(
                height: 56.0,
                width: 56.0,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(28.0),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.05),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(28.0),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 16.0, sigmaY: 16.0),
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: isDark
                            ? LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  Colors.white.withValues(alpha: 0.08),
                                  Colors.white.withValues(alpha: 0.02),
                                ],
                              )
                            : LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  Colors.white.withValues(alpha: 0.50),
                                  Colors.white.withValues(alpha: 0.20),
                                ],
                              ),
                        border: Border.all(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.20)
                              : Colors.white.withValues(alpha: 0.60),
                          width: 1.0,
                        ),
                        borderRadius: BorderRadius.circular(28.0),
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: () {
                            HapticService.lightTap();
                            showLogProgressSheet(innerContext);
                          },
                          child: Center(
                            child: Icon(
                              Icons.add_rounded,
                              size: 28,
                              color: colorScheme.primary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        floatingActionButtonLocation: FloatingActionButtonLocation.endFloat,

        bottomNavigationBar: RepaintBoundary(
          child: Padding(
            padding: const EdgeInsets.only(left: 16, right: 16, bottom: 16),
            child: Container(
              height: 72.0,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(24.0),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.3),
                    blurRadius: 30,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24.0),
                child: Stack(
                  children: [
                    // Layer B: The Glass Pane
                    Positioned.fill(
                      child: BackdropFilter(
                        filter: ImageFilter.blur(sigmaX: 24.0, sigmaY: 24.0),
                        child: Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(24.0),
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                Colors.white.withValues(alpha: 0.07),
                                Colors.white.withValues(alpha: 0.02),
                              ],
                            ),
                            border: Border.all(
                              color: Colors.white.withValues(alpha: 0.22),
                              width: 0.8,
                            ),
                          ),
                        ),
                      ),
                    ),

                    // The Sliding Liquid Selection Capsule
                    AnimatedAlign(
                      alignment: Alignment(-1.0 + (_currentIndex * 1.0), 0.0),
                      duration: const Duration(milliseconds: 350),
                      curve: SpringCurve.snap,
                      child: FractionallySizedBox(
                        widthFactor: 0.33,
                        child: Padding(
                          padding: const EdgeInsets.all(6.0),
                          child: Container(
                            decoration: BoxDecoration(
                              color: theme.brightness == Brightness.dark ? Colors.transparent : null,
                              gradient: theme.brightness == Brightness.dark
                                  ? const LinearGradient(
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                      colors: [
                                        Color(0x23FFFFFF), // 0.14
                                        Color(0x05FFFFFF), // 0.02
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
                              borderRadius: BorderRadius.circular(18.0),
                              border: theme.brightness == Brightness.dark
                                  ? Border.all(
                                      color: colorScheme.primary.withValues(alpha: 0.3),
                                      width: 1.0,
                                    )
                                  : Border.all(
                                      color: Colors.white.withValues(alpha: 0.65),
                                      width: 0.8,
                                    ),
                              boxShadow: [
                                BoxShadow(
                                  color: colorScheme.primary.withValues(alpha: 0.10),
                                  blurRadius: 12,
                                  spreadRadius: 2,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),

                    // Interactive Items Row
                    Row(
                      children: [
                        _buildNavItem(0, Icons.space_dashboard_outlined, Icons.space_dashboard_rounded, 'Dashboard', theme, colorScheme),
                        _buildNavItem(1, Icons.analytics_outlined, Icons.analytics_rounded, 'Analytics', theme, colorScheme),
                        _buildNavItem(2, Icons.person_outline_rounded, Icons.person_rounded, 'Profile', theme, colorScheme),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ), // RepaintBoundary

      ), // Scaffold
    ); // MultiProvider
  }

  Widget _buildNavItem(
    int index,
    IconData iconOutline,
    IconData iconSolid,
    String label,
    ThemeData theme,
    ColorScheme colorScheme,
  ) {
    final isSelected = _currentIndex == index;
    return Expanded(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () {
          HapticService.lightTap();
          setState(() => _currentIndex = index);
        },
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              transitionBuilder: (child, animation) => FadeTransition(
                opacity: animation,
                child: ScaleTransition(scale: animation, child: child),
              ),
              child: Icon(
                isSelected ? iconSolid : iconOutline,
                key: ValueKey<bool>(isSelected),
                color: isSelected ? colorScheme.primary : colorScheme.onSurface.withValues(alpha: 0.65),
                size: 24,
              ),
            ),
            const SizedBox(height: 4),
            AnimatedDefaultTextStyle(
              duration: const Duration(milliseconds: 300),
              style: theme.textTheme.labelSmall!.copyWith(
                color: isSelected ? colorScheme.primary : colorScheme.onSurface.withValues(alpha: 0.65),
                fontWeight: isSelected ? FontWeight.w800 : FontWeight.w500,
                fontSize: 11,
              ),
              child: Text(label),
            ),
          ],
        ),
      ),
    );
  }
}
