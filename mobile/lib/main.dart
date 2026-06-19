import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'core/network/api_client.dart';
import 'core/storage/secure_storage.dart';
import 'core/theme/app_theme.dart';
import 'core/theme/theme_provider.dart';
import 'features/auth/presentation/providers/auth_provider.dart';
import 'features/auth/presentation/screens/login_screen.dart';
import 'features/dashboard/presentation/providers/leaderboard_provider.dart';
import 'features/dashboard/presentation/screens/main_shell.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  final storage = SecureStorage();
  final apiClient = ApiClient(storage: storage);

  runApp(
    MultiProvider(
      providers: [
        // Non-notifier dependency — makes ApiClient available to descendants
        // (e.g. MainShell) without being a ChangeNotifier.
        Provider<ApiClient>.value(value: apiClient),
        ChangeNotifierProvider(
          create: (_) => AuthProvider(storage: storage)..init(),
        ),
        ChangeNotifierProvider(
          create: (_) => ThemeProvider()..init(),
        ),
        // LeaderboardProvider is hoisted here (root level) so it remains
        // accessible from any Navigator route — including pushed screens
        // like LeaderboardScreen — regardless of which subtree they land in.
        ChangeNotifierProvider(
          create: (_) => LeaderboardProvider(apiClient: apiClient),
        ),
        // NOTE: ProgressProvider and UserProfileProvider remain in MainShell
        // because they require the real authenticated userId, which is only
        // available after the auth flow completes.
      ],
      child: const DSAAccountabilityApp(),
    ),
  );
}

/// Root widget for the DSA Accountability mobile application.
class DSAAccountabilityApp extends StatelessWidget {
  const DSAAccountabilityApp({super.key});

  @override
  Widget build(BuildContext context) {
    final currentThemeMode = context.watch<ThemeProvider>().themeMode;

    // Reactive status bar styling based on active theme mode.
    final isDark = currentThemeMode == ThemeMode.dark;
    SystemChrome.setSystemUIOverlayStyle(
      SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness:
            isDark ? Brightness.light : Brightness.dark,
        statusBarBrightness:
            isDark ? Brightness.dark : Brightness.light,
      ),
    );

    return MaterialApp(
      title: 'DSA Accountability',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: currentThemeMode,
      home: const _AuthGate(),
      builder: (context, child) {
        final mediaQuery = MediaQuery.of(context);
        return MediaQuery(
          data: mediaQuery.copyWith(
            textScaler: mediaQuery.textScaler.clamp(
              minScaleFactor: 0.85,
              maxScaleFactor: 1.15,
            ),
          ),
          child: child!,
        );
      },
    );
  }
}

// =============================================================================
// Auth Gate — routes based on AuthProvider state
// =============================================================================

/// Reactive routing shell that switches surfaces based on [AuthStatus].
class _AuthGate extends StatelessWidget {
  const _AuthGate();

  @override
  Widget build(BuildContext context) {
    final status = context.watch<AuthProvider>().status;

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 350),
      switchInCurve: Curves.easeOut,
      switchOutCurve: Curves.easeIn,
      child: switch (status) {
        AuthStatus.initial        => const _SplashScreen(key: ValueKey('splash')),
        AuthStatus.unauthenticated ||
        AuthStatus.authenticating  => const LoginScreen(key: ValueKey('login')),
        AuthStatus.authenticated   => const MainShell(key: ValueKey('shell')),
      },
    );
  }
}

// =============================================================================
// Splash — shown during initial token check
// =============================================================================

class _SplashScreen extends StatelessWidget {
  const _SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SizedBox(
          width: 28,
          height: 28,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(
              Theme.of(context).colorScheme.primary,
            ),
          ),
        ),
      ),
    );
  }
}
