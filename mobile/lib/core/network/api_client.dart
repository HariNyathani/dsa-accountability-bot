import 'package:dio/dio.dart';
import 'package:dio_cache_interceptor/dio_cache_interceptor.dart';

import '../storage/secure_storage.dart';
import 'cache_config.dart';

/// Centralized HTTP client layer targeting the DSA Accountability FastAPI
/// backend.
///
/// ### Interceptor stack (order matters)
/// 1. **Token injector** — reads the cached JWT from [SecureStorage] and
///    adds it as `Authorization: Bearer <token>` to every outgoing
///    request. Runs first so the cache interceptor can hash the full
///    headers (sans the auth header, see [CacheConfig]).
/// 2. **Cache interceptor** — implements stale-while-revalidate via
///    [CacheConfig]. GET responses are served from a Hive-backed
///    on-disk store instantly, while a background revalidation keeps
///    the payload fresh.
///
/// ### Usage
/// Direct Dio calls remain supported. Pass a [CacheOptions] override via
/// `options.extra['cache']` to bypass or force-refresh an individual
/// request (e.g. pull-to-refresh on the dashboard).
class ApiClient {
  ApiClient({required SecureStorage storage, Dio? dio})
      : _storage = storage,
        // ignore: prefer_initializing_formals
        dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: _baseUrl,
                connectTimeout: const Duration(seconds: 15),
                receiveTimeout: const Duration(seconds: 15),
                sendTimeout: const Duration(seconds: 15),
                headers: <String, dynamic>{
                  'Content-Type': 'application/json',
                  'Accept': 'application/json',
                },
              ),
            ) {
    _installInterceptors();
  }

  static const String _baseUrl = 'http://127.0.0.1:8000';

  final SecureStorage _storage;

  /// The underlying [Dio] instance. Exposed for direct use when the
  /// convenience wrappers on this class aren't sufficient.
  final Dio dio;

  // ---------------------------------------------------------------------------
  // Interceptor wiring
  // ---------------------------------------------------------------------------

  void _installInterceptors() {
    // 1. Token injector — runs first so cache keys can exclude it.
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: _onRequest,
      ),
    );

    // 2. Cache interceptor (stale-while-revalidate). Per-request
    //    overrides are picked up from `options.extra['cache']`.
    dio.interceptors.add(
      DioCacheInterceptor(options: _globalCacheOptions),
    );
  }

  /// Global cache options. Acts as the default for every request; can
  /// be overridden per-request by setting
  /// `RequestOptions.extra['cache']` to a [CacheOptions] instance.
  CacheOptions get _globalCacheOptions =>
      CacheConfig.defaultOptionsFor('');

  Future<void> _onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _storage.readToken();
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }

    // Attach the path-specific cache policy as the default for this
    // request. If a caller already provided a [CacheOptions] in
    // `extra['cache']`, respect their override.
    options.extra['cache'] ??= CacheConfig.defaultOptionsFor(options.path);

    handler.next(options);
  }
}
