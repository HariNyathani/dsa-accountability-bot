import 'package:flutter/material.dart';

import '../../../../core/widgets/skeleton_card.dart';
import '../../../dashboard/data/models/user_stats.dart';

/// Topic distribution chart — segmented horizontal bar with legend.
///
/// Renders a proportional color bar showing how many times each DSA topic
/// has been mentioned, plus an expandable legend below.
class TopicDistributionChart extends StatefulWidget {
  const TopicDistributionChart({
    super.key,
    required this.topics,
    required this.isLoading,
  });

  final UserTopics? topics;
  final bool isLoading;

  @override
  State<TopicDistributionChart> createState() =>
      _TopicDistributionChartState();
}

class _TopicDistributionChartState extends State<TopicDistributionChart> {
  bool _showAll = false;

  // Predefined palette for known topics.
  static const _topicColors = <String, Color>{
    'Arrays': Color(0xFF2E6F40),
    'DP': Color(0xFF5B8C5A),
    'Graphs': Color(0xFF3D5A80),
    'Trees': Color(0xFFE07A5F),
    'Binary Search': Color(0xFFF2CC8F),
    'Sorting': Color(0xFF81B29A),
  };

  // Fallback palette for topics not in the map.
  static const _extraColors = <Color>[
    Color(0xFF6D597A),
    Color(0xFFB56576),
    Color(0xFFE56B6F),
    Color(0xFF0077B6),
    Color(0xFF90BE6D),
    Color(0xFFCA6702),
    Color(0xFF6A994E),
    Color(0xFF588157),
  ];

  Color _colorForTopic(String topic, int index) {
    if (_topicColors.containsKey(topic)) return _topicColors[topic]!;
    return _extraColors[index % _extraColors.length];
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final topics = widget.topics;
    final isLoading = widget.isLoading;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header ─────────────────────────────────────────────────
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: colorScheme.primary.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(
                    Icons.calendar_view_week_rounded,
                    color: colorScheme.primary,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 14),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Topic Distribution',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    isLoading || topics == null
                        ? const SkeletonLine(width: 100, height: 12)
                        : Text(
                            '${topics.uniqueTopics} topics tracked',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: colorScheme.onSurfaceVariant,
                            ),
                          ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 24),

            // ── Segmented bar ──────────────────────────────────────────
            if (isLoading || topics == null) ...[
              const SkeletonLine(height: 28, borderRadius: 8),
              const SizedBox(height: 20),
              ...List.generate(
                4,
                (i) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    children: [
                      SkeletonLine(width: 10, height: 10, borderRadius: 5),
                      const SizedBox(width: 10),
                      SkeletonLine(width: 70.0 + i * 10.0, height: 12),
                      const Spacer(),
                      const SkeletonLine(width: 32, height: 12),
                    ],
                  ),
                ),
              ),
            ] else if (topics.frequency.isEmpty) ...[
              Container(
                height: 28,
                decoration: BoxDecoration(
                  color: colorScheme.onSurface.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Text(
                    'No topic data yet',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ),
            ] else ...[
              _buildSegmentedBar(topics.frequency),
              const SizedBox(height: 20),
              _buildLegend(theme, colorScheme, topics.frequency),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSegmentedBar(List<TopicFrequency> frequency) {
    final totalCount =
        frequency.fold<int>(0, (sum, f) => sum + f.count);
    if (totalCount == 0) return const SizedBox.shrink();

    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: SizedBox(
        height: 28,
        child: Row(
          children: List.generate(frequency.length, (i) {
            final item = frequency[i];
            final color = _colorForTopic(item.topic, i);
            final flex = (item.count * 1000 ~/ totalCount).clamp(1, 1000);

            return Expanded(
              flex: flex,
              child: Container(color: color),
            );
          }),
        ),
      ),
    );
  }

  Widget _buildLegend(
    ThemeData theme,
    ColorScheme colorScheme,
    List<TopicFrequency> frequency,
  ) {
    final totalCount =
        frequency.fold<int>(0, (sum, f) => sum + f.count);
    if (totalCount == 0) return const SizedBox.shrink();

    const maxVisible = 6;
    final showExpand = frequency.length > maxVisible && !_showAll;
    final visibleItems =
        showExpand ? frequency.take(maxVisible).toList() : frequency;

    // Calculate "Other" count.
    final otherCount = showExpand
        ? frequency
            .skip(maxVisible)
            .fold<int>(0, (sum, f) => sum + f.count)
        : 0;
    final otherTopicCount =
        showExpand ? frequency.length - maxVisible : 0;

    return Column(
      children: [
        ...List.generate(visibleItems.length, (i) {
          final item = visibleItems[i];
          final pct = (item.count / totalCount * 100).toStringAsFixed(1);
          final color = _colorForTopic(item.topic, i);

          return _legendRow(theme, colorScheme, color, item.topic, pct);
        }),
        if (showExpand) ...[
          _legendRow(
            theme,
            colorScheme,
            const Color(0xFF9E9E9E),
            'Other ($otherTopicCount)',
            (otherCount / totalCount * 100).toStringAsFixed(1),
          ),
          const SizedBox(height: 4),
          Align(
            alignment: Alignment.centerLeft,
            child: GestureDetector(
              onTap: () => setState(() => _showAll = true),
              child: Text(
                'Show all',
                style: theme.textTheme.labelSmall?.copyWith(
                  color: colorScheme.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
        if (_showAll && frequency.length > maxVisible)
          Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              padding: const EdgeInsets.only(top: 4),
              child: GestureDetector(
                onTap: () => setState(() => _showAll = false),
                child: Text(
                  'Show less',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: colorScheme.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  static Widget _legendRow(
    ThemeData theme,
    ColorScheme colorScheme,
    Color dotColor,
    String label,
    String pct,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              color: dotColor,
              borderRadius: BorderRadius.circular(5),
            ),
          ),
          const SizedBox(width: 10),
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w500,
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  return CustomPaint(
                    size: Size(constraints.maxWidth, 1),
                    painter: _DottedLinePainter(
                      color: colorScheme.outline,
                    ),
                  );
                },
              ),
            ),
          ),
          Text(
            '$pct%',
            style: theme.textTheme.bodySmall?.copyWith(
              fontWeight: FontWeight.w600,
              color: colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// Dotted line painter for legend rows
// =============================================================================

class _DottedLinePainter extends CustomPainter {
  _DottedLinePainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1
      ..strokeCap = StrokeCap.round;

    const dashWidth = 3.0;
    const dashGap = 4.0;
    var x = 0.0;

    while (x < size.width) {
      canvas.drawLine(
        Offset(x, size.height / 2),
        Offset(x + dashWidth, size.height / 2),
        paint,
      );
      x += dashWidth + dashGap;
    }
  }

  @override
  bool shouldRepaint(covariant _DottedLinePainter old) => color != old.color;
}
