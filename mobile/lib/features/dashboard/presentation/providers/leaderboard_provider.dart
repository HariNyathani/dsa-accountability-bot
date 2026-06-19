import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../../data/models/leaderboard.dart';

/// Async state controller for the global leaderboard.
///
/// Fetches ranked user data from `GET /leaderboard` and exposes sort-key
/// switching. Mirrors the error-handling pattern of [ProgressProvider].
///
/// State machine: `idle → loading → success | error`.
class LeaderboardProvider extends ChangeNotifier {
  LeaderboardProvider({required this.apiClient});

  final ApiClient apiClient;

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _error;
  String? get error => _error;

  LeaderboardData? _data;
  LeaderboardData? get data => _data;

  String _sortBy = 'streak';
  String get sortBy => _sortBy;

  bool get hasData => _data != null;

  // ---------------------------------------------------------------------------
  // Fetch
  // ---------------------------------------------------------------------------

  /// Fetches leaderboard entries from the backend.
  ///
  /// Optionally overrides the current [sortBy] key for this request.
  Future<void> fetch({String? sortBy}) async {
    _isLoading = true;
    _error = null;
    if (sortBy != null) _sortBy = sortBy;
    notifyListeners();

    try {
      final res = await apiClient.dio.get(
        '/leaderboard',
        queryParameters: <String, dynamic>{
          'sort_by': _sortBy,
          'limit': 25,
        },
      );

      final rawData = res.data['data'] as Map<String, dynamic>?;
      _data = rawData != null ? LeaderboardData.fromJson(rawData) : null;
    } on DioException catch (e) {
      _error = _humanError(e);
    } catch (e, st) {
      // Log the full exception and stack trace so non-Dio errors (e.g.
      // ProviderNotFoundException, cast failures) are visible in the debug
      // console rather than being silently discarded.
      debugPrint('[LeaderboardProvider] Unexpected error: $e\n$st');
      _error = 'Something went wrong. Pull to retry.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Updates the active sort key and triggers a fresh fetch.
  void setSortBy(String sort) {
    if (sort == _sortBy && hasData) return;
    fetch(sortBy: sort);
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
    if (statusCode != null && statusCode >= 500) {
      return 'Server error. Try again later.';
    }
    return 'Something went wrong. Pull to retry.';
  }
}
