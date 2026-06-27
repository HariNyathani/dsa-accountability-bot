import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter/foundation.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/network/api_client.dart';
import '../../../../core/storage/secure_storage.dart';

/// Discrete authentication lifecycle states.
enum AuthStatus {
  /// App launched; token check has not yet completed.
  initial,

  /// A login request is in-flight.
  authenticating,

  /// A valid cached token exists — user may access protected surfaces.
  authenticated,

  /// No cached token — user must authenticate.
  unauthenticated,
}

/// Reactive state controller for the authentication lifecycle.
///
/// On [init], reads [SecureStorage] for a cached JWT and user ID. If both are
/// found, transitions to [AuthStatus.authenticated]. Otherwise, checks for a
/// cold-start deep link that may carry a token from a just-completed OAuth
/// flow before falling back to [AuthStatus.unauthenticated].
///
/// [login] opens the system browser to the Discord OAuth consent page.
/// On successful authorization, the browser redirects back to the app via
/// the `dsabot://auth/callback` deep link, which is captured by either the
/// cold-start handler ([AppLinks.getInitialLink]) or the runtime stream
/// listener ([AppLinks.uriLinkStream]).
///
/// A safety timeout ensures the UI never gets permanently stuck in the
/// [AuthStatus.authenticating] spinner if the callback never arrives.
class AuthProvider extends ChangeNotifier {
  AuthProvider({required this._storage})
      : _appLinks = AppLinks();

  final SecureStorage _storage;
  final AppLinks _appLinks;
  StreamSubscription<Uri>? _deepLinkSub;
  Timer? _authTimeout;

  /// Maximum wait for the deep link callback before resetting state.
  static const _authTimeoutDuration = Duration(minutes: 2);

  AuthStatus _status = AuthStatus.initial;
  String? _userId;

  /// The current authentication lifecycle state.
  AuthStatus get status => _status;

  /// The authenticated Discord user ID, or `null` if not yet authenticated.
  String? get userId => _userId;

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  /// Bootstrap — call once at app startup.
  ///
  /// 1. Reads the encrypted vault for an existing token and user ID.
  /// 2. If no cached session exists, checks for a cold-start deep link
  ///    (the app may have been launched by a `dsabot://` intent).
  /// 3. Starts the runtime deep link stream listener for warm-start events.
  Future<void> init() async {
    // ── 1. Check secure storage for a cached session. ──────────────────
    final token = await _storage.readToken();
    final storedUserId = await _storage.readUserId();

    if (token != null && token.isNotEmpty &&
        storedUserId != null && storedUserId.isNotEmpty) {
      _userId = storedUserId;
      _status = AuthStatus.authenticated;
      notifyListeners();
      _startDeepLinkListener();
      return;
    }

    // ── 2. No cached session — check for a cold-start deep link. ───────
    try {
      final initialLink = await _appLinks.getInitialLink();
      if (initialLink != null && await _handleDeepLink(initialLink)) {
        _startDeepLinkListener();
        return;
      }
    } catch (e) {
      debugPrint('[AuthProvider] Cold-start link check failed: $e');
    }

    // ── 3. No session and no cold-start link — unauthenticated. ────────
    _status = AuthStatus.unauthenticated;
    notifyListeners();
    _startDeepLinkListener();
  }

  // ---------------------------------------------------------------------------
  // Deep link subsystem
  // ---------------------------------------------------------------------------

  /// Subscribes to the runtime URI stream for warm-start deep links.
  ///
  /// Wraps the downstream handler in a defensive try/catch so that
  /// malformed URIs or storage errors don't crash the isolate.
  void _startDeepLinkListener() {
    _deepLinkSub?.cancel();
    _deepLinkSub = _appLinks.uriLinkStream.listen(
      (uri) async {
        try {
          await _handleDeepLink(uri);
        } catch (e) {
          debugPrint('[AuthProvider] Deep link processing error: $e');
          _resetToUnauthenticated();
        }
      },
      onError: (Object error) {
        debugPrint('[AuthProvider] Deep link stream error: $error');
      },
    );
  }

  /// Unified deep link processor for both cold-start and runtime links.
  ///
  /// Validates the URI scheme/host, extracts the `token` and `user_id`
  /// query parameters, persists them to secure storage, and transitions
  /// the state machine to [AuthStatus.authenticated].
  ///
  /// Returns `true` if the link was a valid auth callback that was
  /// successfully processed; `false` if the URI was not ours to handle.
  Future<bool> _handleDeepLink(Uri uri) async {
    // Only handle our auth callback scheme + host.
    if (uri.scheme != 'dsabot' || uri.host != 'auth') return false;

    final token = uri.queryParameters['token'];
    final deepLinkUserId = uri.queryParameters['user_id'];

    if (token == null || token.isEmpty ||
        deepLinkUserId == null || deepLinkUserId.isEmpty) {
      debugPrint('[AuthProvider] Incomplete auth callback — '
          'missing token or user_id: $uri');
      _resetToUnauthenticated();
      return false;
    }

    await _finalizeAuth(token, deepLinkUserId);
    return true;
  }

  /// Commit credentials to secure storage and flip the state machine
  /// to [AuthStatus.authenticated].
  Future<void> _finalizeAuth(String token, String newUserId) async {
    _cancelAuthTimeout();
    await _storage.saveToken(token);
    await _storage.saveUserId(newUserId);
    _userId = newUserId;
    _status = AuthStatus.authenticated;
    notifyListeners();
  }

  /// Gracefully abort auth, clear partial state, and reset the UI.
  void _resetToUnauthenticated() {
    _cancelAuthTimeout();
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  // ---------------------------------------------------------------------------
  // Auth timeout
  // ---------------------------------------------------------------------------

  /// Starts a safety timer that resets the provider to
  /// [AuthStatus.unauthenticated] if no deep link callback arrives
  /// within [_authTimeoutDuration] after the browser was launched.
  void _startAuthTimeout() {
    _cancelAuthTimeout();
    _authTimeout = Timer(_authTimeoutDuration, () {
      if (_status == AuthStatus.authenticating) {
        debugPrint('[AuthProvider] Auth timeout — '
            'no callback received within $_authTimeoutDuration');
        _resetToUnauthenticated();
      }
    });
  }

  void _cancelAuthTimeout() {
    _authTimeout?.cancel();
    _authTimeout = null;
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  /// Opens the system browser to the Discord OAuth consent page.
  ///
  /// Authentication completion is handled asynchronously by
  /// [_handleDeepLink] when the browser redirects back via the
  /// `dsabot://auth/callback` deep link.
  ///
  /// A [_authTimeoutDuration] safety timer prevents the UI from getting
  /// permanently stuck in the loading state if the callback never arrives
  /// (e.g. user closes the browser, network failure, etc.).
  ///
  /// Note: We call [launchUrl] directly without a [canLaunchUrl] guard.
  /// On Android 11+, `canLaunchUrl` is unreliable due to package visibility
  /// restrictions and can return false even when a browser is available.
  Future<void> login() async {
    _status = AuthStatus.authenticating;
    notifyListeners();

    try {
      final url = Uri.parse('${ApiClient.baseUrl}/auth/login?mobile=true');
      await launchUrl(url, mode: LaunchMode.externalApplication);
      _startAuthTimeout();
    } catch (e) {
      debugPrint('[AuthProvider] Browser launch failed: $e');
      _resetToUnauthenticated();
    }
  }

  /// Clear all cached credentials and return to the unauthenticated gate.
  Future<void> logout() async {
    await _storage.clearToken();
    await _storage.clearUserId();
    _userId = null;
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  @override
  void dispose() {
    _deepLinkSub?.cancel();
    _cancelAuthTimeout();
    super.dispose();
  }
}
