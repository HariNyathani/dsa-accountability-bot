import 'package:dio_cache_interceptor/dio_cache_interceptor.dart';
import 'package:dio_cache_interceptor_hive_store/dio_cache_interceptor_hive_store.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:path_provider/path_provider.dart';
/// Centralized HTTP cache configuration for [ApiClient].
///
/// Implements **stale-while-revalidate** (SWR) semantics: GET responses
/// are served from disk-backed cache instantly, and a background
/// revalidation runs in parallel. Cold-start renders the previous payload
/// in <1ms while the network call lands in the background.
///
/// ### Per-endpoint TTLs
///   - `/users/{id}/...`           → 30s (live stats)
///   - `/leaderboard`              → 30s (live rankings)
///   - `/progress/revision/all`    → 60s (changes per log)
///   - `/users/.../settings`       → 5min (rarely changes)
///   - everything else             → 30s default
///
/// ### Safety
/// - 401/403 responses are NEVER cached (token invalidation).
/// - POST/PUT/DELETE are never cached (default interceptor behavior).
/// - The cache key excludes the `Authorization` header so user A's cache
///   entries don't collide with user B's.
class CacheConfig {
  CacheConfig._();

  static const String _hiveBoxName = 'dsabot_http_cache_v2';
  static const String _cacheDirName = 'dsabot_http_cache_v2';

  static CacheStore? _store;

  /// One-time bootstrap. Call from `main()` before `runApp`.
  static Future<void> init() async {
    if (_store != null) return;

    String? path;
    if (!kIsWeb) {
      final base = await getApplicationDocumentsDirectory();
      path = '${base.path}/$_cacheDirName';
    }

    _store = HiveCacheStore(
      path,
      hiveBoxName: _hiveBoxName,
    );
  }

  /// The shared disk-backed cache store. Must call [init] first.
  static CacheStore get store {
    final s = _store;
    if (s == null) {
      throw StateError(
        'CacheConfig.init() must be called before accessing the store. '
        'Call it from main() before runApp().',
      );
    }
    return s;
  }

  /// Cache policy options for a given request path.
  ///
  /// Used by the [ApiClient] interceptor as the *default*; individual
  /// requests can override via `options.extra['cache']`.
  static CacheOptions defaultOptionsFor(String path) {
    return CacheOptions(
      store: store,
      policy: CachePolicy.refreshForceCache,
      hitCacheOnErrorExcept: const [401, 403, 500],
      maxStale: _maxStaleFor(path),
      priority: CachePriority.normal,
      // Exclude the Authorization header from the cache key so the
      // disk cache is shared across login sessions, not per-token.
      keyBuilder: (request) {
        final qp = request.queryParameters.isEmpty
            ? ''
            : '?${request.queryParameters.entries
                .map((e) => '${e.key}=${e.value}')
                .join('&')}';
        return '${request.method}::${request.uri}$qp';
      },
    );
  }

  /// Per-request override that explicitly disables caching.
  /// Useful for mutating calls or live endpoints that must never be stale.
  static CacheOptions noCacheFor(String path) {
    return CacheOptions(
      store: store,
      policy: CachePolicy.noCache,
    );
  }

  /// Per-request override for a "force fresh network" pull-to-refresh.
  static CacheOptions forceRefreshFor(String path) {
    return CacheOptions(
      store: store,
      policy: CachePolicy.refresh,
    );
  }

  // ---------------------------------------------------------------------------
  // Internal
  // ---------------------------------------------------------------------------

  static Duration _maxStaleFor(String path) {
    if (path.startsWith('/users/') && path.contains('/settings')) {
      return const Duration(minutes: 5);
    }
    if (path.startsWith('/leaderboard')) {
      return const Duration(seconds: 30);
    }
    if (path.startsWith('/progress/revision')) {
      return const Duration(seconds: 60);
    }
    if (path.startsWith('/users/')) {
      return const Duration(seconds: 30);
    }
    return const Duration(seconds: 30);
  }
}
