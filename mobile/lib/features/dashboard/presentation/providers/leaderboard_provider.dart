import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../../../../core/network/api_client.dart';
import '../../data/models/leaderboard.dart';

/// Async state controller for the global leaderboard.
///
/// ### Caching strategy (June 2026 — P2 enhancement)
/// Each `sortBy` variant is cached separately in [_cacheBySort]. The
/// first time a sort is requested, it is fetched. Subsequent requests
/// (or pre-fetches for the other three variants) read from this map,
/// making sort-chip switching instant. The on-disk HTTP cache
/// ([ApiClient]) provides the cold-start persistence layer; this
/// in-memory map provides warm-start speed for the current session.
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

  /// The currently-presented sort's data.
  LeaderboardData? _data;
  LeaderboardData? get data => _data;

  String _sortBy = 'streak';
  String get sortBy => _sortBy;

  bool get hasData => _data != null;

  // ---------------------------------------------------------------------------
  // P2: Per-sort in-memory cache
  // ---------------------------------------------------------------------------

  /// Keyed by sortBy (`streak` | `consistency` | `posts` | `days`).
  /// Populated lazily by [fetch] and eagerly by [prefetchAllSorts].
  final Map<String, LeaderboardData> _cacheBySort = <String, LeaderboardData>{};

  /// The set of sort keys currently being prefetched. Prevents duplicate
  /// background requests.
  final Set<String> _prefetchingSorts = <String>{};

  /// True after a [prefetchAllSorts] call has successfully warmed
  /// the cache for all 4 sort variants. Used for one-shot scheduling.
  bool _didPrefetchAll = false;

  /// Public, read-only view of which sorts are cached (e.g. for tests
  /// or future debug UI).
  Set<String> get cachedSorts => Set<String>.unmodifiable(_cacheBySort.keys);

  // ---------------------------------------------------------------------------
  // Fetch
  // ---------------------------------------------------------------------------

  /// Fetches leaderboard entries for [sortBy] (defaults to current).
  ///
  /// Cache hit path: emits instantly with no loading state.
  /// Cache miss path: shows the loading state, fetches, caches, emits.
  Future<void> fetch({String? sortBy}) async {
    if (sortBy != null) _sortBy = sortBy;
    final key = _sortBy;

    // ── P2: Cache hit — emit instantly, no spinner ─────────────────────
    if (_cacheBySort.containsKey(key)) {
      _data = _cacheBySort[key];
      _error = null;
      notifyListeners();
      return;
    }

    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final res = await apiClient.dio.get(
        '/leaderboard',
        queryParameters: <String, dynamic>{
          'sort_by': key,
          'limit': 25,
        },
      );

      final rawData = res.data['data'] as Map<String, dynamic>?;
      final parsed = rawData != null ? LeaderboardData.fromJson(rawData) : null;
      if (parsed != null) {
        _cacheBySort[key] = parsed;
        _data = parsed;
      }
    } on DioException catch (e) {
      _error = _humanError(e);
    } catch (e, st) {
      debugPrint('[LeaderboardProvider] Unexpected error: $e\n$st');
      _error = 'Something went wrong. Pull to retry.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Updates the active sort key and triggers a fresh fetch.
  ///
  /// With P2 caching this is **instant** when the requested sort is
  /// already in [_cacheBySort] (typical case after a single
  /// [prefetchAllSorts] call).
  void setSortBy(String sort) {
    if (sort == _sortBy && hasData) return;
    fetch(sortBy: sort);
  }

  // ---------------------------------------------------------------------------
  // P2: Multi-sort prefetch
  // ---------------------------------------------------------------------------

  /// All four sort keys the UI exposes. Kept in sync with the
  /// `_sortOptions` map in `leaderboard_screen.dart`.
  static const List<String> allSorts = <String>[
    'streak',
    'consistency',
    'posts',
    'days',
  ];

  /// Eagerly populates [_cacheBySort] for every sort variant not yet
  /// cached. Fire-and-forget — errors are silently swallowed per
  /// variant so a single backend hiccup doesn't block the others.
  ///
  /// Safe to call multiple times; the second call is a no-op once
  /// all four sorts are warm.
  Future<void> prefetchAllSorts() async {
    if (_didPrefetchAll && _cacheBySort.length == allSorts.length) return;

    final missing = allSorts
        .where((s) => !_cacheBySort.containsKey(s) && !_prefetchingSorts.contains(s))
        .toList();

    if (missing.isEmpty) {
      _didPrefetchAll = true;
      return;
    }

    for (final sort in missing) {
      _prefetchingSorts.add(sort);
    }

    await Future.wait(
      missing.map((sort) => _silentFetchSort(sort)),
      eagerError: false,
    );

    _didPrefetchAll = _cacheBySort.length == allSorts.length;
  }

  /// Background fetch for a single sort key. Stores in [_cacheBySort]
  /// and updates [_data] *only* if it matches the active sort, so the
  /// UI never sees a flicker from a background variant landing.
  Future<void> _silentFetchSort(String sort) async {
    try {
      final res = await apiClient.dio.get(
        '/leaderboard',
        queryParameters: <String, dynamic>{
          'sort_by': sort,
          'limit': 25,
        },
      );
      final rawData = res.data['data'] as Map<String, dynamic>?;
      if (rawData == null) return;
      final parsed = LeaderboardData.fromJson(rawData);
      _cacheBySort[sort] = parsed;
      // If the user has since switched to this sort, keep [_data] in sync.
      if (_sortBy == sort) {
        _data = parsed;
        notifyListeners();
      }
    } catch (e) {
      debugPrint('[LeaderboardProvider] Silent prefetch failed for $sort: $e');
    } finally {
      _prefetchingSorts.remove(sort);
    }
  }

  /// Force a network refresh of the current sort, bypassing the
  /// in-memory cache. Wired to pull-to-refresh.
  Future<void> refreshCurrent() async {
    _cacheBySort.remove(_sortBy);
    _didPrefetchAll = false;
    await fetch();
    // Re-warm the other variants in the background.
    prefetchAllSorts();
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
