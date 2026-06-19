import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';

/// Reactive state controller for the authenticated user's profile.
///
/// Fetches profile data from `GET /users/{id}` and exposes update methods
/// for timezone, email, and username. Also resolves leaderboard rank.
///
/// State machine: `idle → loading → success | error`.
class UserProfileProvider extends ChangeNotifier {
  UserProfileProvider({required this.apiClient, required this.userId});

  final ApiClient apiClient;
  final String userId;

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _error;
  String? get error => _error;

  String? _discordUsername;
  String? get discordUsername => _discordUsername;

  String? _username;
  String? get username => _username;

  String? _email;
  String? get email => _email;

  String _timezone = 'Asia/Kolkata';
  String get timezone => _timezone;

  int? _leaderboardRank;
  int? get leaderboardRank => _leaderboardRank;

  bool get hasData => _discordUsername != null || _username != null;

  // ---------------------------------------------------------------------------
  // Fetch profile + rank
  // ---------------------------------------------------------------------------

  /// Fetches the user profile and leaderboard rank concurrently.
  Future<void> fetchProfile() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final results = await Future.wait([
        _fetchUserDetail(),
        _fetchRank(),
      ], eagerError: false);

      // User detail.
      final detail = results[0] as Map<String, dynamic>?;
      if (detail != null) {
        _discordUsername = detail['discord_username']?.toString();
        _username = detail['username']?.toString();
        _email = detail['email']?.toString();
        _timezone = detail['timezone']?.toString() ?? 'Asia/Kolkata';
      }

      // Rank.
      _leaderboardRank = results[1] as int?;
    } on DioException catch (e) {
      _error = _humanError(e);
    } catch (_) {
      _error = 'Something went wrong.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<Map<String, dynamic>?> _fetchUserDetail() async {
    try {
      final res = await apiClient.dio.get('/users/$userId');
      return res.data['data'] as Map<String, dynamic>?;
    } on DioException {
      return null;
    }
  }

  Future<int?> _fetchRank() async {
    try {
      final res = await apiClient.dio.get(
        '/leaderboard',
        queryParameters: <String, dynamic>{
          'sort_by': 'streak',
          'limit': 100,
        },
      );
      final data = res.data['data'] as Map<String, dynamic>?;
      final entries = data?['entries'] as List<dynamic>?;
      if (entries != null) {
        for (final entry in entries) {
          if (entry is Map<String, dynamic> &&
              entry['user_id']?.toString() == userId) {
            return (entry['rank'] as num?)?.toInt();
          }
        }
      }
      return null;
    } on DioException {
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Update actions
  // ---------------------------------------------------------------------------

  /// Updates the user's timezone on the backend.
  Future<bool> updateTimezone(String tz) async {
    try {
      await apiClient.dio.put(
        '/users/$userId/timezone',
        data: <String, dynamic>{'timezone': tz},
      );
      _timezone = tz;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _error = _humanError(e);
      notifyListeners();
      return false;
    }
  }

  /// Updates the user's email on the backend.
  Future<bool> updateEmail(String email) async {
    try {
      await apiClient.dio.put(
        '/users/$userId/email',
        data: <String, dynamic>{'email': email},
      );
      _email = email;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _error = _humanError(e);
      notifyListeners();
      return false;
    }
  }

  /// Updates the user's custom username.
  Future<bool> updateUsername(String newUsername) async {
    try {
      await apiClient.dio.put(
        '/users/settings/username',
        data: <String, dynamic>{'user_id': userId, 'username': newUsername},
      );
      _username = newUsername;
      notifyListeners();
      return true;
    } on DioException catch (e) {
      _error = _humanError(e);
      notifyListeners();
      return false;
    }
  }

  /// Checks whether a username is available.
  ///
  /// Returns `{available: bool, reason: String}`.
  Future<Map<String, dynamic>> checkUsername(String name) async {
    try {
      final res =
          await apiClient.dio.get('/users/check-username/$name');
      return (res.data['data'] as Map<String, dynamic>?) ??
          <String, dynamic>{'available': false, 'reason': 'Unknown error'};
    } on DioException {
      return <String, dynamic>{
        'available': false,
        'reason': 'Network error',
      };
    }
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  static String _humanError(DioException e) {
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return 'Connection timed out. Check your network.';
    }
    if (e.type == DioExceptionType.connectionError) {
      return 'No internet connection.';
    }
    final statusCode = e.response?.statusCode;
    if (statusCode == 401) return 'Session expired. Please sign in again.';
    if (statusCode == 404) return 'User not found.';
    if (statusCode != null && statusCode >= 500) {
      return 'Server error. Try again later.';
    }
    return 'Something went wrong.';
  }
}
