import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:mobile/core/storage/secure_storage.dart';
import 'package:mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:mobile/main.dart';

void main() {
  testWidgets('Auth gate renders login screen when unauthenticated',
      (WidgetTester tester) async {
    final storage = SecureStorage();
    final authProvider = AuthProvider(storage: storage)..init();

    await tester.pumpWidget(
      ChangeNotifierProvider<AuthProvider>.value(
        value: authProvider,
        child: const DSAAccountabilityApp(),
      ),
    );

    // Allow async init to settle.
    await tester.pumpAndSettle();

    // The login CTA should be visible.
    expect(find.text('Connect with Discord'), findsOneWidget);
  });
}
