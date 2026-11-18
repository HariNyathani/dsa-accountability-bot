import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';

import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/cache_config.dart';
import 'package:mobile/core/storage/secure_storage.dart';
import 'package:mobile/core/theme/theme_provider.dart';
import 'package:mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:mobile/features/dashboard/presentation/providers/leaderboard_provider.dart';
import 'package:mobile/main.dart';

/// Serves real Plus Jakarta Sans TTFs, cached under `test/fixtures/fonts/` and
/// keyed by the SHA-256 in the request URL. google_fonts verifies the hash and
/// length of every download, so a synthetic body would fail; using the genuine
/// bytes is what lets the themed widget tree build in a network-less test
/// without surfacing a font-load exception as a test failure.
http.Client _localFontClient() {
  return MockClient((request) async {
    final segments = request.url.pathSegments;
    final file = segments.isEmpty ? '' : segments.last;
    final candidate = File('test/fixtures/fonts/$file');
    if (candidate.existsSync()) {
      return http.Response.bytes(candidate.readAsBytesSync(), 200);
    }
    // Any font not vendored: let google_fonts take its handled no-op path.
    return http.Response('', 404);
  });
}

void main() {
  setUpAll(() {
    // The app's theme is built with GoogleFonts.plusJakartaSans*, which fetches
    // TTFs at runtime. Point it at the vendored fixture copies instead of the
    // network. Test-process only; app behaviour is unchanged.
    GoogleFonts.config.httpClient = _localFontClient();

    // These plugins have no test implementation, and an unanswered channel call
    // hangs the widget test rather than failing it:
    //  - path_provider: used by CacheConfig.init()
    //  - flutter_secure_storage: read by AuthProvider.init()
    //  - app_links: cold-start deep-link lookup in AuthProvider.init()
    TestWidgetsFlutterBinding.ensureInitialized();
    final messenger =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(
        const MethodChannel('plugins.flutter.io/path_provider'),
        (_) async => Directory.systemTemp.path);
    messenger.setMockMethodCallHandler(
        const MethodChannel('plugins.flutter.io/path_provider_android'),
        (_) async => Directory.systemTemp.path);
    messenger.setMockMethodCallHandler(
        const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
        (_) async => null);
    messenger.setMockMethodCallHandler(
        const MethodChannel('com.llfbandit.app_links/messages'),
        (_) async => null);
  });

  testWidgets('Auth gate renders login screen when unauthenticated',
      (WidgetTester tester) async {
    // main() awaits CacheConfig.init() before building the root providers;
    // ApiClient's cache interceptor needs the store to exist.
    await CacheConfig.init();

    final storage = SecureStorage();
    final authProvider = AuthProvider(storage: storage)..init();
    final apiClient = ApiClient(storage: storage);

    await tester.pumpWidget(
      // Mirror the root provider set that main() installs, so the tree under
      // test matches production. DSAAccountabilityApp reads ThemeProvider
      // directly; root-level screens read ApiClient and LeaderboardProvider.
      MultiProvider(
        providers: [
          Provider<ApiClient>.value(value: apiClient),
          ChangeNotifierProvider<AuthProvider>.value(value: authProvider),
          ChangeNotifierProvider<ThemeProvider>(
            create: (_) => ThemeProvider()..init(),
          ),
          ChangeNotifierProvider<LeaderboardProvider>(
            create: (_) => LeaderboardProvider(apiClient: apiClient),
          ),
        ],
        child: const DSAAccountabilityApp(),
      ),
    );

    // pumpAndSettle is not usable here: the app hosts periodic/indeterminate
    // animations, so it never settles. Pump a fixed number of long frames so
    // AuthProvider.init() resolves and the splash's AnimatedSwitcher finishes.
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 500));
    }

    // Let google_fonts finish any in-flight loads before teardown.
    await GoogleFonts.pendingFonts();

    // The login CTA should be visible.
    expect(find.text('Connect with Discord'), findsOneWidget);
  });
}
