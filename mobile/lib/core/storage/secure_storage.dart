import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Encrypted key-value vault for persisting sensitive authentication data.
///
/// Wraps [FlutterSecureStorage] behind a type-safe API surface scoped
/// exclusively to the JWT auth token and Discord user ID lifecycle.
class SecureStorage {
  SecureStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const String _tokenKey = 'auth_jwt_token';
  static const String _userIdKey = 'auth_user_id';

  final FlutterSecureStorage _storage;

  // ---------------------------------------------------------------------------
  // Token
  // ---------------------------------------------------------------------------

  /// Persist [token] into the encrypted vault.
  Future<void> saveToken(String token) =>
      _storage.write(key: _tokenKey, value: token);

  /// Read the cached token, or `null` if no token is stored.
  Future<String?> readToken() => _storage.read(key: _tokenKey);

  /// Remove the cached token from the vault.
  Future<void> clearToken() => _storage.delete(key: _tokenKey);

  // ---------------------------------------------------------------------------
  // User ID
  // ---------------------------------------------------------------------------

  /// Persist the Discord [userId] into the encrypted vault.
  Future<void> saveUserId(String userId) =>
      _storage.write(key: _userIdKey, value: userId);

  /// Read the cached Discord user ID, or `null` if none is stored.
  Future<String?> readUserId() => _storage.read(key: _userIdKey);

  /// Remove the cached Discord user ID from the vault.
  Future<void> clearUserId() => _storage.delete(key: _userIdKey);

  // ---------------------------------------------------------------------------
  // Bulk
  // ---------------------------------------------------------------------------

  /// Wipe every entry in the vault (full reset).
  Future<void> clearAll() => _storage.deleteAll();
}
