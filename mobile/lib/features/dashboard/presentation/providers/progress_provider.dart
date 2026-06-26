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

  /// SRS revision-bank items that are due **today only** (days_remaining = 0).
  ///
  /// Populated by [_fetchDueReviews] which calls
  /// ``GET /progress/revision/due?filter_mode=today``.  Overdue items
  /// (days_remaining < 0) are intentionally **not** included here — they
  /// surface on the Revision tab's "Overdue" paginated view instead.
  ///
  /// Empty list means either no items are due today or the fetch hasn't
  /// completed.
  List<RevisionDueItem> _dueReviews = [];
  List<RevisionDueItem> get dueReviews => List.unmodifiable(_dueReviews);

  // ---------------------------------------------------------------------------
  // Revision Bank — paginated views, two filter modes
  // ---------------------------------------------------------------------------
  //
  // The paginated "All Problems" and "Overdue" views share the provider but
  // keep their page caches isolated so swapping between them never trashes
  // an already-loaded page.  An "active" filter mode ([_currentFilterMode])
  // determines which cache the public getters ([allRevisionItems],
  // [totalRevisionCount], [isLoadingRevision]) read from.

  /// Active filter mode for the paginated revision view.
  /// ``"all"``     → entire revision bank, ordered by LeetCode question_id.
  /// ``"overdue"`` → only items with ``next_review_at`` strictly before today,
  ///                  ordered most-overdue first.
  String _currentFilterMode = 'all';
  String get currentFilterMode => _currentFilterMode;

  /// Updates the active filter mode. Subsequent reads of [allRevisionItems],
  /// [totalRevisionCount], and [isLoadingRevision] reflect the new mode.
  /// Does **not** trigger a fetch — callers should follow up with
  /// [fetchAllRevisionItems] if the new mode's cache is cold.
  void setFilterMode(String mode) {
    if (mode != 'all' && mode != 'overdue') return;
    if (mode == _currentFilterMode) return;
    _currentFilterMode = mode;
    if (!_disposed) notifyListeners();
  }

  /// 1-based page index currently visible to the UI.
  int _currentRevisionPage = 1;

  /// Per-mode page caches: `page number (1-based) → items`.
  /// Populated on first access, served instantly on subsequent visits.
  /// Invalidated by [invalidateRevisionCache] after data mutations.
  final Map<int, List<RevisionBankItem>> _revisionPageCacheAll = {};
  final Map<int, List<RevisionBankItem>> _revisionPageCacheOverdue = {};

  /// Tracks which pages have a silent pre-fetch already in flight, per mode.
  final Set<int> _prefetchingPagesAll = {};
  final Set<int> _prefetchingPagesOverdue = {};

  /// Total pre-pagination counts, per mode.
  int _totalRevisionCountAll = 0;
  int _totalRevisionCountOverdue = 0;

  /// Per-mode loading flags for *visible* fetches (cache misses).
  /// Silent pre-fetches never set these to `true`.
  bool _isLoadingRevisionAll = false;
  bool _isLoadingRevisionOverdue = false;

  /// Returns the active page cache for [_currentFilterMode].
  Map<int, List<RevisionBankItem>> get _activePageCache =>
      _currentFilterMode == 'overdue'
          ? _revisionPageCacheOverdue
          : _revisionPageCacheAll;

  /// Cached items for [_currentRevisionPage] in the active mode.
  /// Returns an empty list if the page hasn't been fetched yet.
  List<RevisionBankItem> get allRevisionItems =>
      List.unmodifiable(_activePageCache[_currentRevisionPage] ?? const []);

  /// Total pre-pagination count in the active mode.
  int get totalRevisionCount => _currentFilterMode == 'overdue'
      ? _totalRevisionCountOverdue
      : _totalRevisionCountAll;

  /// Total pre-pagination count in the "all" mode (mode-independent).
  int get totalRevisionCountAll => _totalRevisionCountAll;

  /// Total pre-pagination count in the "overdue" mode (mode-independent).
  /// The Revision tab's "Overdue" stat card reads from here so the count is
  /// visible even before the user opens the paginated overdue view.
  int get totalRevisionCountOverdue => _totalRevisionCountOverdue;

  /// True while [fetchAllRevisionItems] is doing a *visible* network fetch
  /// in the active mode (i.e. a cache miss). Silent pre-fetches never set
  /// this to `true`.
  bool get isLoadingRevision => _currentFilterMode == 'overdue'
      ? _isLoadingRevisionOverdue
      : _isLoadingRevisionAll;

  /// Per-topic SRS confidence aggregates, sorted weakest-first (ASC).
  /// Shared between both filter modes (topic topology is independent of
  /// the "all vs overdue" filter), so a single field suffices.
  /// Populated alongside the revision items by [fetchAllRevisionItems].
  List<RevisionTopicStat> _revisionTopicStats = [];
  List<RevisionTopicStat> get revisionTopicStats =>
      List.unmodifiable(_revisionTopicStats);

  bool get hasData => _stats != null;

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Paginated revision fetch
  // ---------------------------------------------------------------------------

  /// Fetches a single page of the revision bank from the backend.
  /// Pure network call — no state mutation, no notifyListeners.
  ///
  /// [filterMode] selects which slice of the bank to load:
  /// - ``"all"`` (default) — entire bank, ordered by LeetCode question_id.
  /// - ``"overdue"``        — strictly overdue items, most-overdue first.
  Future<RevisionBankPage?> _fetchRevisionPage({
    required int page,
    required int limit,
    String filterMode = 'all',
  }) async {
    final res = await apiClient.dio.get(
      '/progress/revision/all',
      queryParameters: {
        'page': page,
        'limit': limit,
        'filter_mode': filterMode,
      },
    );
    return RevisionBankPage.fromJson(
      res.data as Map<String, dynamic>,
    );
  }

  /// Fetches the complete revision bank (paginated) and topic-confidence
  /// aggregates from `GET /progress/revision/all`.
  ///
  /// Called lazily from the Revision Tab's `initState` → `addPostFrameCallback`
  /// so the main dashboard startup path is not affected.
  ///
  /// ### Page cache (June 2026)
  /// Fetched pages are cached **per filter mode** in
  /// [_revisionPageCacheAll] and [_revisionPageCacheOverdue]. On a cache
  /// hit the items are emitted **instantly** with no loading state. On a
  /// cache miss the skeleton is shown, the page is fetched, cached, and
  /// emitted. After every successful load, [_silentPrefetch] fires for
  /// `page + 1` so the next page is ready before the user taps "Next".
  ///
  /// [page] is 1-based. [limit] caps at 100 (enforced server-side).
  /// [filterMode] is ``"all"`` or ``"overdue"`` and determines which cache
  /// is read/written. Topic stats are refreshed on every call so they stay
  /// current after a review submission changes the underlying confidence
  /// scores.
  Future<void> fetchAllRevisionItems({
    int page = 1,
    int limit = 10,
    String filterMode = 'all',
  }) async {
    _currentFilterMode = filterMode;
    _currentRevisionPage = page;

    final cache = filterMode == 'overdue'
        ? _revisionPageCacheOverdue
        : _revisionPageCacheAll;

    // ── Cache hit: emit instantly, no loading skeleton ──────────────────
    if (cache.containsKey(page)) {
      // Topic stats & total count are already set from the original fetch.
      // Just notify so the Selector picks up the (potentially new) page.
      if (!_disposed) notifyListeners();

      // Still silently prefetch the next page if it isn't cached yet.
      _silentPrefetch(page: page + 1, limit: limit, filterMode: filterMode);
      return;
    }

    // ── Cache miss: show skeleton, fetch from network ───────────────────
    if (filterMode == 'overdue') {
      _isLoadingRevisionOverdue = true;
    } else {
      _isLoadingRevisionAll = true;
    }
    if (!_disposed) notifyListeners();

    try {
      final pageData = await _fetchRevisionPage(
        page: page,
        limit: limit,
        filterMode: filterMode,
      );
      if (pageData != null) {
        cache[page] = pageData.items;
        if (filterMode == 'overdue') {
          _totalRevisionCountOverdue = pageData.totalCount;
        } else {
          _totalRevisionCountAll = pageData.totalCount;
        }
        _revisionTopicStats = pageData.topicStats;
      }
    } on DioException catch (e) {
      _error = _humanError(e);
    } catch (e) {
      _error = 'Could not load revision bank. Pull to retry.';
    } finally {
      if (filterMode == 'overdue') {
        _isLoadingRevisionOverdue = false;
      } else {
        _isLoadingRevisionAll = false;
      }
      if (!_disposed) notifyListeners();
    }

    // ── Silent prefetch: buffer the next page in the background ─────────
    _silentPrefetch(page: page + 1, limit: limit, filterMode: filterMode);
  }

  /// Silently fetches [page] in the background and stores it in the cache
  /// for [filterMode]. Does NOT set the visible loading flag or call
  /// [notifyListeners] — the UI remains completely unaware until the user
  /// actually navigates to that page and [fetchAllRevisionItems] finds the
  /// cache hit.
  void _silentPrefetch({
    required int page,
    required int limit,
    required String filterMode,
  }) {
    final cache = filterMode == 'overdue'
        ? _revisionPageCacheOverdue
        : _revisionPageCacheAll;
    final prefetching = filterMode == 'overdue'
        ? _prefetchingPagesOverdue
        : _prefetchingPagesAll;
    final totalCount = filterMode == 'overdue'
        ? _totalRevisionCountOverdue
        : _totalRevisionCountAll;

    // Don't prefetch if already cached, already in-flight, or past the end.
    if (cache.containsKey(page)) return;
    if (prefetching.contains(page)) return;
    if (totalCount > 0) {
      final lastPage = (totalCount / limit).ceil();
      if (page > lastPage) return;
    }

    prefetching.add(page);

    // Fire-and-forget — errors are silently swallowed since this is
    // speculative buffering; the user hasn't asked for this page yet.
    _fetchRevisionPage(
      page: page,
      limit: limit,
      filterMode: filterMode,
    ).then((pageData) {
      if (pageData != null && !_disposed) {
        cache[page] = pageData.items;
        // Also keep totalCount / topicStats fresh from the latest response.
        if (filterMode == 'overdue') {
          _totalRevisionCountOverdue = pageData.totalCount;
        } else {
          _totalRevisionCountAll = pageData.totalCount;
        }
        _revisionTopicStats = pageData.topicStats;
      }
    }).catchError((_) {
      // Silently ignore — prefetch is best-effort.
    }).whenComplete(() {
      prefetching.remove(page);
    });
  }

  /// Drops every page cache (both filter modes) so the next
  /// [fetchAllRevisionItems] call hits the network. Called after data
  /// mutations (log, review, refresh) to keep cached pages consistent with
  /// the backend.
  void invalidateRevisionCache() {
    _revisionPageCacheAll.clear();
    _revisionPageCacheOverdue.clear();
    _prefetchingPagesAll.clear();
    _prefetchingPagesOverdue.clear();
  }

  // ---------------------------------------------------------------------------
  // Fetch all dashboard data in parallel
  // ---------------------------------------------------------------------------

  /// Fetches stats, heatmap, recent activity, and due-today revision items
  /// concurrently, then eagerly pre-warms both paginated revision caches
  /// (page 1 of "all" and "overdue") so the Revision tab can show its
  /// "Overdue" stat and open either paginated view without a loading
  /// skeleton.
  ///
  /// Any individual sub-request failure is caught independently so partial
  /// data can still render.
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

      // Invalidate revision bank cache so stale pages aren't served after
      // a data mutation, then re-fetch page 1 of BOTH modes eagerly so the
      // Revision tab's "Overdue" count and "All Problems" view are warm
      // before the user even opens them.
      invalidateRevisionCache();
      await Future.wait([
        fetchAllRevisionItems(page: 1, limit: 10, filterMode: 'all'),
        fetchAllRevisionItems(page: 1, limit: 10, filterMode: 'overdue'),
      ]);
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

  /// Fetches the authenticated user's "due today" SRS queue.
  ///
  /// Hits ``GET /progress/revision/due?filter_mode=today`` so [_dueReviews]
  /// contains only items whose ``next_review_at::date`` is exactly today
  /// (i.e. ``days_remaining = 0``). Overdue items (days_remaining < 0) are
  /// **excluded** here — they live on the Revision tab's "Overdue" view.
  ///
  /// The backend returns a plain JSON array (not wrapped in `data`).
  /// On failure, returns an empty list so the rest of the dashboard
  /// renders normally.
  Future<List<RevisionDueItem>?> _fetchDueReviews() async {
    try {
      final res = await apiClient.dio.get(
        '/progress/revision/due',
        queryParameters: {'filter_mode': 'today'},
      );
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
  /// On success, the problem is **optimistically removed** from
  /// [_dueReviews] (the due-today queue) without forcing a full network
  /// refresh — keeps the UI snappy.  The two paginated caches are also
  /// patched in place:
  ///
  /// - "All" cache: the item stays (it remains in the revision bank) but
  ///   its `confidenceLast`, `lastReviewedAt`, and `reviewCount` are
  ///   updated.  `nextReviewAt` and `daysRemaining` stay as their old
  ///   (stale) values until the next fetch — the existing behaviour.
  /// - "Overdue" cache: the item is **removed** (it is no longer overdue)
  ///   and [_totalRevisionCountOverdue] is decremented.
  ///
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

      // Optimistic local update — remove the reviewed item from the
      // due-today queue (it just got rescheduled to a future date).
      _dueReviews = _dueReviews
          .where((item) => item.problemId != problemId)
          .toList();

      // Optimistic local update for the "all" cache — bump confidence,
      // lastReviewedAt, reviewCount in place.  Stays in the bank.
      for (final page in _revisionPageCacheAll.keys) {
        final items = _revisionPageCacheAll[page]!;
        final index = items.indexWhere((item) => item.problemId == problemId);
        if (index != -1) {
          final oldItem = items[index];
          items[index] = RevisionBankItem(
            problemId: oldItem.problemId,
            title: oldItem.title,
            titleSlug: oldItem.titleSlug,
            difficulty: oldItem.difficulty,
            topics: oldItem.topics,
            confidenceLast: confidence,
            nextReviewAt: oldItem.nextReviewAt,
            firstSolvedAt: oldItem.firstSolvedAt,
            lastReviewedAt: DateTime.now().toUtc().toIso8601String(),
            reviewCount: oldItem.reviewCount + 1,
            daysRemaining: oldItem.daysRemaining,
          );
          // Only need to update it once.
          break;
        }
      }

      // Optimistic local update for the "overdue" cache — remove the item
      // (a successful review reschedules it to a future date so it is no
      // longer overdue) and decrement the total.
      for (final page in _revisionPageCacheOverdue.keys) {
        final items = _revisionPageCacheOverdue[page]!;
        final index = items.indexWhere((item) => item.problemId == problemId);
        if (index != -1) {
          items.removeAt(index);
          if (_totalRevisionCountOverdue > 0) {
            _totalRevisionCountOverdue -= 1;
          }
          // Only need to remove it once.
          break;
        }
      }

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
