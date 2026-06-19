import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../../data/models/platform_log.dart';
import '../../data/models/user_stats.dart';

/// Async state controller for user progress data.
///
/// Fetches stats, heatmap, and activity from the backend via [ApiClient],
/// and exposes a manual problem-logging action (`POST /progress`).
///
/// State machine: `idle → loading → success | error`.
class ProgressProvider extends ChangeNotifier {
  ProgressProvider({required this.apiClient, required this.userId});

  final ApiClient apiClient;
  final String userId;

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _error;
  String? get error => _error;

  UserStats? _stats;
  UserStats? get stats => _stats;

  HeatmapData? _heatmap;
  HeatmapData? get heatmap => _heatmap;

  List<ActivityLog> _recentLogs = [];
  List<ActivityLog> get recentLogs => _recentLogs;

  UserTopics? _topics;
  UserTopics? get topics => _topics;

  UserDifficulty? _difficulty;
  UserDifficulty? get difficulty => _difficulty;

  bool get hasData => _stats != null;

  // ---------------------------------------------------------------------------
  // Fetch all dashboard data in parallel
  // ---------------------------------------------------------------------------

  /// Fetches stats, heatmap, and recent activity concurrently.
  ///
  /// Any individual sub-request failure is caught independently so partial
  /// data can still render.
  Future<void> fetchAll() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final results = await Future.wait([
        _fetchStats(),
        _fetchHeatmap(),
        _fetchActivity(),
        _fetchAggregate(),
      ], eagerError: false);

      _stats = results[0] as UserStats?;
      _heatmap = results[1] as HeatmapData?;
      _recentLogs = (results[2] as List<ActivityLog>?) ?? [];

      final aggregate = results[3] as DashboardAggregate?;
      if (aggregate != null) {
        _topics = aggregate.topics;
        _difficulty = aggregate.difficulty;
        // Also update stats from the aggregate if the dedicated fetch
        // returned null (resilient partial-failure path).
        _stats ??= aggregate.stats;
      }
    } on DioException catch (e) {
      _error = _humanError(e);
    } catch (e) {
      _error = 'Something went wrong. Pull to retry.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // ---------------------------------------------------------------------------
  // Individual fetchers (unwrap APIResponse envelope)
  // ---------------------------------------------------------------------------

  Future<UserStats?> _fetchStats() async {
    try {
      final res = await apiClient.dio.get('/users/$userId/stats');
      final data = res.data['data'] as Map<String, dynamic>?;
      return data != null ? UserStats.fromJson(data) : null;
    } on DioException {
      return null; // Partial failure — don't block other requests.
    }
  }

  Future<HeatmapData?> _fetchHeatmap() async {
    try {
      final res = await apiClient.dio.get('/users/$userId/heatmap');
      final data = res.data['data'] as Map<String, dynamic>?;
      return data != null ? HeatmapData.fromJson(data) : null;
    } on DioException {
      return null;
    }
  }

  Future<List<ActivityLog>?> _fetchActivity() async {
    try {
      final res = await apiClient.dio.get(
        '/users/$userId/activity',
        queryParameters: {'limit': 5},
      );
      final data = res.data['data'] as Map<String, dynamic>?;
      final logs = data?['recent_logs'] as List<dynamic>?;
      return logs
          ?.map((e) => ActivityLog.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return null;
    }
  }

  Future<DashboardAggregate?> _fetchAggregate() async {
    try {
      final res =
          await apiClient.dio.get('/users/$userId/dashboard-aggregate');
      final data = res.data['data'] as Map<String, dynamic>?;
      return data != null ? DashboardAggregate.fromJson(data) : null;
    } on DioException {
      return null; // Partial failure — charts simply remain empty.
    }
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  /// Submit a manual problem log (`POST /progress`).
  ///
  /// On success, triggers a full data refresh so listening views update.
  Future<LogProgressResponse?> logProgress(LogProgressRequest request) async {
    try {
      final res = await apiClient.dio.post(
        '/progress',
        data: request.toJson(),
      );
      final response = LogProgressResponse.fromJson(
        res.data as Map<String, dynamic>,
      );

      // Refresh all data after a successful log.
      if (response.success) {
        await fetchAll();
      }
      return response;
    } on DioException catch (e) {
      _error = _humanError(e);
      notifyListeners();
      return null;
    }
  }

  /// Submit a platform-resolved problem log (`POST /progress/platform`).
  ///
  /// The backend fuzzy-matches the [problemIdentifier] (numeric ID, URL,
  /// or partial title) against the given [platform]'s problem database.
  /// On success, triggers a full data refresh so listening views update.
  Future<PlatformLogResponse?> logPlatformProblem({
    required String platform,
    required String problemIdentifier,
  }) async {
    try {
      final res = await apiClient.dio.post(
        '/progress/platform',
        data: {
          'platform': platform.toLowerCase(),
          'problem_identifier': problemIdentifier,
        },
      );
      final response = PlatformLogResponse.fromJson(
        res.data as Map<String, dynamic>,
      );

      // Refresh all data after a successful log.
      if (response.success) {
        await fetchAll();
      }
      return response;
    } on DioException catch (e) {
      _error = _humanError(e);
      notifyListeners();
      return null;
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
    if (statusCode == 404) return 'User data not found.';
    if (statusCode != null && statusCode >= 500) {
      return 'Server error. Try again later.';
    }
    return 'Something went wrong. Pull to retry.';
  }
}
