import 'package:dio/dio.dart';

import '../storage/secure_storage.dart';

/// Centralized HTTP client layer targeting the DSA Accountability FastAPI
/// backend.
///
/// Automatically injects the cached JWT bearer token into every outgoing
/// request via a [Dio] interceptor that reads from [SecureStorage].
class ApiClient {
  ApiClient({required this._storage, Dio? dio})
      : dio = dio ??
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

  static const String _baseUrl = 'https://api.dsabot.in';

  final SecureStorage _storage;

  /// The underlying [Dio] instance. Exposed for direct use when the
  /// convenience wrappers on this class aren't sufficient.
  final Dio dio;

  // ---------------------------------------------------------------------------
  // Interceptor wiring
  // ---------------------------------------------------------------------------

  void _installInterceptors() {
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: _onRequest,
      ),
    );
  }

  Future<void> _onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _storage.readToken();
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }
}
