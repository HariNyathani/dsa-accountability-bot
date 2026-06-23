import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../../../core/network/api_client.dart';
import '../../data/models/platform_log.dart';
import '../../data/models/user_stats.dart';

/// Async state controller for user progress data.
///
/// Fetches stats, heatmap, activity, and the SRS revision queue from the
/// backend via [ApiClient], and exposes manual problem-logging actions.
///
/// State machine: `idle → loading → success | error`.
class ProgressProvider extends ChangeNotifier {
  ProgressProvider({required this.apiClient, required this.userId});

  final ApiClient apiClient;
  final String userId;

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  bool _disposed = false;

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

  /// SRS revision-bank items that are currently due for review.
  /// Empty list means either no items are due or the fetch hasn't completed.
  List<RevisionDueItem> _dueReviews = [];
  List<RevisionDueItem> get dueReviews => List.unmodifiable(_dueReviews);

  // ---------------------------------------------------------------------------
  // All Revision Items (full bank, paginated) — lazy loaded by RevisionTab
  // ---------------------------------------------------------------------------

  /// Full revision bank — includes items not yet due. Populated by
  /// [fetchAllRevisionItems]; empty until the Revision Tab is first opened.
  List<RevisionBankItem> _allRevisionItems = [];
  List<RevisionBankItem> get allRevisionItems =>
      List.unmodifiable(_allRevisionItems);

  /// Total count of items in the revision bank (pre-pagination).
  int _totalRevisionCount = 0;
  int get totalRevisionCount => _totalRevisionCount;

  /// Per-topic SRS confidence aggregates, sorted weakest-first (ASC).
  /// Populated alongside [_allRevisionItems] by [fetchAllRevisionItems].
  List<RevisionTopicStat> _revisionTopicStats = [];
  List<RevisionTopicStat> get revisionTopicStats =>
      List.unmodifiable(_revisionTopicStats);

  /// True while [fetchAllRevisionItems] is in flight.
  bool _isLoadingRevision = false;
  bool get isLoadingRevision => _isLoadingRevision;

  bool get hasData => _stats != null;

  // ---------------------------------------------------------------------------
  // Fetch all dashboard data in parallel
  // ---------------------------------------------------------------------------

  /// Fetches stats, heatmap, recent activity, and due revision items
  /// concurrently.  Any individual sub-request failure is caught independently
  /// so partial data can still render.
  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Lazy fetch — Revision Tab only
  // ---------------------------------------------------------------------------

  /// Fetches the complete revision bank (paginated) and topic-confidence
  /// aggregates from `GET /progress/revision/all`.
  ///
  /// Called lazily from the Revision Tab's `initState` \u2192 `addPostFrameCallback`
  /// so the main dashboard startup path is not affected.
  ///
  /// [page] is 1-based. [limit] caps at 100 (enforced server-side).
  /// Topic stats are refreshed on every call so they stay current after a
  /// review submission changes the underlying confidence scores.
  Future<void> fetchAllRevisionItems({int page = 1, int limit = 10}) async {
    _isLoadingRevision = true;
    if (!_disposed) notifyListeners();

    try {
      final res = await apiClient.dio.get(
        '/progress/revision/all',
        queryParameters: {'page': page, 'limit': limit},
      );
      final pageData = RevisionBankPage.fromJson(
        res.data as Map<String, dynamic>,
      );
      _allRevisionItems   = pageData.items;
      _totalRevisionCount = pageData.totalCount;
      _revisionTopicStats = pageData.topicStats; // sorted ASC by backend
    } on DioException catch (e) {
      _error = _humanError(e);
    } catch (e) {
      _error = 'Could not load revision bank. Pull to retry.';
    } finally {
      _isLoadingRevision = false;
      if (!_disposed) notifyListeners();
    }
  }

  Future<void> fetchAll() async {
    _isLoading = true;
    _error = null;
    if (!_disposed) notifyListeners();

    try {
      final results = await Future.wait([
        _fetchStats(),
        _fetchHeatmap(),
        _fetchActivity(),
        _fetchAggregate(),
        _fetchDueReviews(),
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

      _dueReviews = (results[4] as List<RevisionDueItem>?) ?? [];

      // Invalidate revision bank items to keep data synchronous across tabs
      if (_allRevisionItems.isNotEmpty || true) {
        await fetchAllRevisionItems(page: 1, limit: 10);
      }
    } on DioException catch (e) {
      _error = _humanError(e);
    } catch (e) {
      _error = 'Something went wrong. Pull to retry.';
    } finally {
      _isLoading = false;
      if (!_disposed) notifyListeners();
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

  /// Fetches the authenticated user's SRS revision queue.
  ///
  /// The backend returns a plain JSON array (not wrapped in `data`).
  /// On failure, returns an empty list so the rest of the dashboard
  /// renders normally.
  Future<List<RevisionDueItem>?> _fetchDueReviews() async {
    try {
      final res = await apiClient.dio.get('/progress/revision/due');
      final list = res.data as List<dynamic>?;
      return list
          ?.map((e) => RevisionDueItem.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return null; // Non-fatal — SRS queue will just be empty.
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
      if (!_disposed) notifyListeners();
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
    int? confidence,
    bool isReview = false,
  }) async {
    try {
      final res = await apiClient.dio.post(
        '/progress/platform',
        data: {
          'platform': platform.toLowerCase(),
          'problem_identifier': problemIdentifier,
          if (confidence != null) 'confidence': confidence,
          if (isReview) 'is_review': true,
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
      if (!_disposed) notifyListeners();
      return null;
    }
  }

  /// Submit a spaced-repetition review (`POST /progress/revision/review`).
  ///
  /// On success, the problem is **optimistically removed** from [dueReviews]
  /// without forcing a full network refresh — keeps the UI snappy.
  /// On failure, the item is NOT removed and a [SnackBar] is shown via
  /// [scaffoldMessengerKey] so the user can retry.
  ///
  /// Returns `true` on success, `false` on failure.
  Future<bool> submitReview({
    required int problemId,
    required int confidence,
    required BuildContext context,
  }) async {
    try {
      await apiClient.dio.post(
        '/progress/revision/review',
        data: {
          'problem_id': problemId,
          'confidence': confidence,
        },
      );

      // Optimistic local update — remove the reviewed item from the queue.
      _dueReviews = _dueReviews
          .where((item) => item.problemId != problemId)
          .toList();
      if (!_disposed) notifyListeners();
      return true;
    } on DioException catch (e) {
      // Non-fatal: do NOT remove from list; let user retry.
      if (!_disposed) {
        final detail =
            (e.response?.data as Map<String, dynamic>?)?['detail']
                as String?;
        final message = (detail != null && detail.isNotEmpty)
            ? detail
            : 'Review submission failed. Please try again.';
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(message),
              behavior: SnackBarBehavior.floating,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          );
        }
      }
      return false;
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



