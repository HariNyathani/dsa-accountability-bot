import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../../core/services/haptic_service.dart';
import '../../../../core/widgets/glass_card.dart';
import '../../data/models/user_stats.dart';
import '../providers/progress_provider.dart';

/// Dashboard section that displays SRS (spaced-repetition) items due for review.
///
/// Renders nothing when the user has no due items, preserving the existing
/// dashboard layout without adding any whitespace.
///
/// Design rules:
/// - Uses [GlassCard] — no raw [BackdropFilter] styling here.
/// - Wrapped in [RepaintBoundary] to isolate glass repaints from the
///   main scroll tree.
/// - Uses [Selector] so only [ProgressProvider.dueReviews] changes
///   trigger a rebuild (not the whole provider).
class DueReviewsCard extends StatelessWidget {
  const DueReviewsCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Selector<ProgressProvider, List<RevisionDueItem>>(
      selector: (_, provider) => provider.dueReviews,
      builder: (context, dueReviews, _) {
        if (dueReviews.isEmpty) return const SizedBox.shrink();

        final theme = Theme.of(context);
        final colorScheme = theme.colorScheme;
        final isDark = theme.brightness == Brightness.dark;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Section header ────────────────────────────────────────
            Row(
              children: [
                Icon(
                  Icons.auto_awesome_rounded,
                  size: 14,
                  color: const Color(0xFFF59E0B),
                ),
                const SizedBox(width: 6),
                Text(
                  'DUE FOR REVIEW',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.6,
                    color: (isDark ? Colors.white : colorScheme.primary)
                        .withValues(alpha: 0.6),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 7,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF59E0B).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    '${dueReviews.length}',
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFFF59E0B),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // ── Horizontal scroll list ────────────────────────────────
            // RepaintBoundary isolates the glass cards' backdrop filters
            // from the main scroll layer, preventing unnecessary repaints
            // of the surrounding widgets during scroll.
            RepaintBoundary(
              child: SizedBox(
                height: 132,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: EdgeInsets.zero,
                  itemCount: dueReviews.length,
                  separatorBuilder: (_, _) => const SizedBox(width: 12),
                  itemBuilder: (context, index) {
                    final item = dueReviews[index];
                    return _DueReviewItemCard(
                      item: item,
                      onTap: () => showReviewSheet(
                        context: context,
                        problemId: item.problemId,
                        title: item.title,
                        difficulty: item.difficulty,
                      ),
                    );
                  },
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        );
      },
    );
  }
}

/// Opens a lightweight modal bottom sheet that lets the user rate
/// their confidence (1–5 stars) and submit the review.
void showReviewSheet({
  required BuildContext context,
  required int problemId,
  required String title,
  required String difficulty,
}) {
  // Capture provider before the async gap so it resolves correctly
  // even if the calling context gets torn down during the sheet animation.
  final progressProvider = context.read<ProgressProvider>();

  showModalBottomSheet<void>(
    context: context,
    backgroundColor: Colors.transparent,
    barrierColor: Colors.black54,
    isScrollControlled: true,
    builder: (sheetContext) => ChangeNotifierProvider<ProgressProvider>.value(
      value: progressProvider,
      child: ReviewSheet(
        problemId: problemId,
        title: title,
        difficulty: difficulty,
      ),
    ),
  );
}

// =============================================================================
// _DueReviewItemCard — individual horizontally scrolling card
// =============================================================================

class _DueReviewItemCard extends StatelessWidget {
  const _DueReviewItemCard({
    required this.item,
    required this.onTap,
  });

  final RevisionDueItem item;
  final VoidCallback onTap;

  static const _difficultyColors = <String, Color>{
    'Easy': Color(0xFF4CAF50),
    'Medium': Color(0xFFFF9800),
    'Hard': Color(0xFFE53935),
  };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final diffColor =
        _difficultyColors[item.difficulty] ?? colorScheme.primary;

    return GestureDetector(
      onTap: onTap,
      child: SizedBox(
        width: 200,
        child: GlassCard(
          radius: 20,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ── Difficulty badge ─────────────────────────────
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: diffColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    item.difficulty,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: diffColor,
                    ),
                  ),
                ),
                const SizedBox(height: 8),

                // ── Problem title ────────────────────────────────
                Expanded(
                  child: Text(
                    item.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      height: 1.3,
                    ),
                  ),
                ),
                const SizedBox(height: 8),

                // ── Footer: stars + review count ─────────────────
                Row(
                  children: [
                    // Last confidence stars (compact)
                    ...List.generate(5, (i) {
                      final filled = (i + 1) <= item.confidenceLast;
                      return Icon(
                        filled
                            ? Icons.star_rounded
                            : Icons.star_border_rounded,
                        size: 12,
                        color: filled
                            ? const Color(0xFFF59E0B)
                            : colorScheme.onSurface.withValues(alpha: 0.2),
                      );
                    }),
                    const Spacer(),
                    Icon(
                      Icons.replay_rounded,
                      size: 11,
                      color: colorScheme.onSurfaceVariant
                          .withValues(alpha: 0.5),
                    ),
                    const SizedBox(width: 2),
                    Text(
                      '×${item.reviewCount}',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: colorScheme.onSurfaceVariant
                            .withValues(alpha: 0.5),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// =============================================================================
// _ReviewSheet — bottom sheet for rating confidence and submitting
// =============================================================================

class ReviewSheet extends StatefulWidget {
  const ReviewSheet({
    super.key,
    required this.problemId,
    required this.title,
    required this.difficulty,
  });

  final int problemId;
  final String title;
  final String difficulty;

  @override
  State<ReviewSheet> createState() => _ReviewSheetState();
}

class _ReviewSheetState extends State<ReviewSheet> {
  int _confidence = 3; // default: Okay
  bool _isSubmitting = false;

  static const _confidenceLabels = [
    'Blackout 😵',
    'Hard 😤',
    'Okay 😌',
    'Easy 😎',
    'Confident 🔥',
  ];

  Future<void> _submit() async {
    if (_isSubmitting) return;
    setState(() => _isSubmitting = true);

    final provider = context.read<ProgressProvider>();
    final success = await provider.submitReview(
      problemId: widget.problemId,
      confidence: _confidence,
      context: context,
    );

    if (!mounted) return;

    if (success) {
      await HapticService.successBoom();
      // Show brief success feedback then dismiss.
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '\u2705 Reviewed: ${widget.title}',
          ),
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          duration: const Duration(seconds: 2),
        ),
      );
      Navigator.of(context).pop();
    } else {
      // Error snackbar already shown by submitReview — just reset.
      setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;

    return RepaintBoundary(
      child: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: ClipRRect(
          borderRadius: const BorderRadius.vertical(
            top: Radius.circular(24.0),
          ),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 20.0, sigmaY: 20.0),
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: isDark
                      ? [
                          Colors.white.withValues(alpha: 0.05),
                          Colors.white.withValues(alpha: 0.01),
                        ]
                      : [
                          Colors.white.withValues(alpha: 0.45),
                          Colors.white.withValues(alpha: 0.15),
                        ],
                ),
                border: Border(
                  top: BorderSide(
                    color: Colors.white.withValues(alpha: isDark ? 0.15 : 0.50),
                    width: 1.0,
                  ),
                  left: BorderSide(
                    color: Colors.white.withValues(alpha: isDark ? 0.15 : 0.50),
                    width: 1.0,
                  ),
                  right: BorderSide(
                    color: Colors.white.withValues(alpha: isDark ? 0.15 : 0.50),
                    width: 1.0,
                  ),
                ),
              ),
              child: SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ── Drag handle ────────────────────────────────────
                  Center(
                    child: Container(
                      width: 36,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: 20),
                      decoration: BoxDecoration(
                        color: colorScheme.onSurface.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),

                  // ── Problem title ──────────────────────────────────
                  Text(
                    widget.title,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.2,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${widget.difficulty}  ·  #${widget.problemId}',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 24),

                  // ── Confidence label ───────────────────────────────
                  Text(
                    'How well did you recall it?',
                    style: theme.textTheme.labelMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.4,
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _confidenceLabels[_confidence - 1],
                    style: theme.textTheme.bodyLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),

                  // ── 5-star picker ──────────────────────────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(5, (i) {
                      final starIndex = i + 1;
                      final isFilled = starIndex <= _confidence;
                      return GestureDetector(
                        onTap: () {
                          HapticService.lightTap();
                          setState(() => _confidence = starIndex);
                        },
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 6),
                          child: AnimatedSwitcher(
                            duration: const Duration(milliseconds: 180),
                            switchInCurve: Curves.easeOut,
                            switchOutCurve: Curves.easeIn,
                            child: Icon(
                              isFilled
                                  ? Icons.star_rounded
                                  : Icons.star_border_rounded,
                              key: ValueKey('star_${starIndex}_$isFilled'),
                              size: 40,
                              color: isFilled
                                  ? const Color(0xFFF59E0B)
                                  : colorScheme.onSurface
                                      .withValues(alpha: 0.20),
                            ),
                          ),
                        ),
                      );
                    }),
                  ),
                  const SizedBox(height: 32),

                  // ── Submit button ──────────────────────────────────
                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        gradient: isDark
                            ? null
                            : const LinearGradient(
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                                colors: [
                                  Color(0xFF9E6F4A),
                                  Color(0xFF7A5234),
                                ],
                              ),
                        border: isDark
                            ? Border.all(
                                color:
                                    Colors.white.withValues(alpha: 0.15),
                                width: 1.0,
                              )
                            : Border.all(
                                color:
                                    Colors.white.withValues(alpha: 0.40),
                                width: 0.8,
                              ),
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: _isSubmitting ? null : _submit,
                          borderRadius: BorderRadius.circular(16),
                          child: Center(
                            child: _isSubmitting
                                ? SizedBox(
                                    width: 22,
                                    height: 22,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2.5,
                                      valueColor:
                                          AlwaysStoppedAnimation<Color>(
                                        colorScheme.onPrimary,
                                      ),
                                    ),
                                  )
                                : Text(
                                    'Submit Review',
                                    style: theme.textTheme.titleSmall
                                        ?.copyWith(
                                      color: colorScheme.onPrimary,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  ),
);
  }
}

