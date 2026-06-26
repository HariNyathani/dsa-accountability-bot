import 'package:flutter/widgets.dart';

/// Callback signature for [PrefetchScrollController.onNearEnd].
typedef PrefetchCallback = void Function();

/// Drop-in [ScrollController] that invokes [onNearEnd] once when the
/// user scrolls past [threshold] (default 0.7) of the viewport's
/// scrollable extent.
///
/// Designed for paginated list prefetching — call [onNearEnd] to fetch
/// the next page *before* the user reaches the end, so the next page
/// is ready by the time they tap "Next" or auto-load triggers.
///
/// ### Usage
/// ```dart
/// final _scroll = PrefetchScrollController(
///   threshold: 0.7,
///   onNearEnd: () => provider.fetchNextPage(),
/// );
///
/// ListView.builder(controller: _scroll, ...);
/// ```
///
/// ### Resetting
/// After loading a new page, call [resetPrefetch] so the next scroll
/// to the threshold fires [onNearEnd] again.
class PrefetchScrollController extends ScrollController {
  PrefetchScrollController({
    this.threshold = 0.7,
    required this.onNearEnd,
  })  : assert(threshold > 0.0 && threshold <= 1.0,
            'threshold must be in (0, 1]');

  /// Scroll fraction (0.0–1.0) at which [onNearEnd] is invoked.
  final double threshold;

  /// Invoked when the user has scrolled past [threshold] of the
  /// viewport. Fires at most once per [resetPrefetch] call.
  final PrefetchCallback onNearEnd;

  bool _fired = false;

  @override
  void attach(ScrollPosition position) {
    super.attach(position);
    position.addListener(_onScroll);
  }

  @override
  void detach(ScrollPosition position) {
    position.removeListener(_onScroll);
    super.detach(position);
  }

  void _onScroll() {
    if (_fired || !hasClients) return;
    final pos = position;
    if (pos.maxScrollExtent <= 0) return;
    if (pos.pixels / pos.maxScrollExtent >= threshold) {
      _fired = true;
      onNearEnd();
    }
  }

  /// Reset the trigger so the next scroll past the threshold will
  /// fire [onNearEnd] again. Call this after a new page has loaded
  /// and the list extent has grown.
  void resetPrefetch() {
    _fired = false;
  }
}
