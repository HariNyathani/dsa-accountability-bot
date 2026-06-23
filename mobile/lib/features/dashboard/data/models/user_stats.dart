/// Immutable data models mirroring the FastAPI backend schemas.
///
/// Each model includes a `fromJson` factory that safely unwraps the
/// `APIResponse.data` envelope returned by our VPS backend.
library;

// =============================================================================
// UserStats — GET /users/{id}/stats → APIResponse<UserStats>
// =============================================================================

class UserStats {
  const UserStats({
    required this.userId,
    this.totalMessages = 0,
    this.totalDaysTracked = 0,
    this.daysPosted = 0,
    this.consistencyPct = 0.0,
    this.currentStreak = 0,
    this.longestStreak = 0,
    this.postedToday = false,
    this.today = '',
    this.badges = const [],
  });

  final String userId;
  final int totalMessages;
  final int totalDaysTracked;
  final int daysPosted;
  final double consistencyPct;
  final int currentStreak;
  final int longestStreak;
  final bool postedToday;
  final String today;
  final List<String> badges;

  factory UserStats.fromJson(Map<String, dynamic> json) {
    return UserStats(
      userId: json['user_id']?.toString() ?? '',
      totalMessages: (json['total_messages'] as num?)?.toInt() ?? 0,
      totalDaysTracked: (json['total_days_tracked'] as num?)?.toInt() ?? 0,
      daysPosted: (json['days_posted'] as num?)?.toInt() ?? 0,
      consistencyPct: (json['consistency_pct'] as num?)?.toDouble() ?? 0.0,
      currentStreak: (json['current_streak'] as num?)?.toInt() ?? 0,
      longestStreak: (json['longest_streak'] as num?)?.toInt() ?? 0,
      postedToday: json['posted_today'] as bool? ?? false,
      today: json['today']?.toString() ?? '',
      badges: (json['badges'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
    );
  }
}

// =============================================================================
// HeatmapData — GET /users/{id}/heatmap → APIResponse<HeatmapResponse>
// =============================================================================

class HeatmapData {
  const HeatmapData({
    required this.userId,
    this.dates = const {},
    this.restDates = const [],
    this.activeDays = 0,
    this.currentStreak = 0,
    this.maxStreak = 0,
  });

  /// Map of `"YYYY-MM-DD" → question_count`.
  final String userId;
  final Map<String, int> dates;
  final List<String> restDates;
  final int activeDays;
  final int currentStreak;
  final int maxStreak;

  factory HeatmapData.fromJson(Map<String, dynamic> json) {
    final rawDates = json['dates'];
    final Map<String, int> parsedDates = {};
    if (rawDates is Map) {
      for (final entry in rawDates.entries) {
        parsedDates[entry.key.toString()] =
            (entry.value as num?)?.toInt() ?? 0;
      }
    }

    return HeatmapData(
      userId: json['user_id']?.toString() ?? '',
      dates: parsedDates,
      restDates: (json['rest_dates'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      activeDays: (json['active_days'] as num?)?.toInt() ?? 0,
      currentStreak: (json['current_streak'] as num?)?.toInt() ?? 0,
      maxStreak: (json['max_streak'] as num?)?.toInt() ?? 0,
    );
  }
}

// =============================================================================
// ActivityLog — GET /users/{id}/activity → APIResponse<UserActivityResponse>
// =============================================================================

class ActivityLog {
  const ActivityLog({
    required this.id,
    required this.postedAt,
    required this.messageType,
    this.messageContent,
    this.topics,
    this.parsedFields,
  });

  final int id;
  final String postedAt;
  final String messageType;
  final String? messageContent;
  final String? topics;
  final String? parsedFields;

  factory ActivityLog.fromJson(Map<String, dynamic> json) {
    return ActivityLog(
      id: (json['id'] as num?)?.toInt() ?? 0,
      postedAt: json['posted_at']?.toString() ?? '',
      messageType: json['message_type']?.toString() ?? '',
      messageContent: json['message_content']?.toString(),
      topics: json['topics']?.toString(),
      parsedFields: json['parsed_fields']?.toString(),
    );
  }
}

// =============================================================================
// LogProgressRequest — POST /progress body
// =============================================================================

class LogProgressRequest {
  const LogProgressRequest({
    required this.intentType,
    required this.topics,
    this.note,
    this.targetDate,
    this.confidence,
    this.isReview,
  });

  final String intentType;
  final List<ProgressTopicLog> topics;
  final String? note;
  final String? targetDate;
  /// SRS confidence score 1–5 (LeetCode only). Triggers revision_bank scheduling.
  final int? confidence;
  /// True for spaced-repetition review sessions (does not advance streak).
  final bool? isReview;

  Map<String, dynamic> toJson() => {
        'intent_type': intentType,
        'topics': topics.map((t) => t.toJson()).toList(),
        if (note != null) 'note': note,
        if (targetDate != null) 'target_date': targetDate,
        if (confidence != null) 'confidence': confidence,
        if (isReview != null && isReview!) 'is_review': isReview,
      };
}

class ProgressTopicLog {
  const ProgressTopicLog({
    required this.canonicalTopic,
    required this.questionCount,
    this.difficulty,
  });

  final String canonicalTopic;
  final int questionCount;
  final String? difficulty;

  Map<String, dynamic> toJson() => {
        'canonical_topic': canonicalTopic,
        'question_count': questionCount,
        if (difficulty != null) 'difficulty': difficulty,
      };
}

// =============================================================================
// RevisionDueItem — GET /progress/revision/due list item
// =============================================================================

/// Mirrors the backend `RevisionDueItem` Pydantic schema.
/// Returned by `GET /progress/revision/due` as a JSON array.
class RevisionDueItem {
  const RevisionDueItem({
    required this.problemId,
    required this.title,
    required this.titleSlug,
    required this.difficulty,
    this.topics = const [],
    required this.confidenceLast,
    required this.nextReviewAt,
    required this.firstSolvedAt,
    this.lastReviewedAt,
    this.reviewCount = 0,
  });

  final int problemId;
  final String title;
  final String titleSlug;
  final String difficulty;
  final List<String> topics;
  /// Last self-reported confidence score (1–5).
  final int confidenceLast;
  /// ISO-8601 UTC timestamp when this item became due.
  final String nextReviewAt;
  /// ISO-8601 UTC timestamp of the original solve.
  final String firstSolvedAt;
  /// ISO-8601 UTC timestamp of the last review (null on first-ever review).
  final String? lastReviewedAt;
  final int reviewCount;

  factory RevisionDueItem.fromJson(Map<String, dynamic> json) {
    return RevisionDueItem(
      problemId: (json['problem_id'] as num?)?.toInt() ?? 0,
      title: json['title']?.toString() ?? '',
      titleSlug: json['title_slug']?.toString() ?? '',
      difficulty: json['difficulty']?.toString() ?? '',
      topics: (json['topics'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      confidenceLast: (json['confidence_last'] as num?)?.toInt() ?? 3,
      nextReviewAt: json['next_review_at']?.toString() ?? '',
      firstSolvedAt: json['first_solved_at']?.toString() ?? '',
      lastReviewedAt: json['last_reviewed_at']?.toString(),
      reviewCount: (json['review_count'] as num?)?.toInt() ?? 0,
    );
  }
}


// =============================================================================
// RevisionBankItem — GET /progress/revision/all list item
// =============================================================================

/// Superset of [RevisionDueItem] that covers all problems in the revision bank,
/// not just those that are currently due.
///
/// The extra [daysRemaining] field is computed server-side so the client never
/// needs to do timezone arithmetic:
///   - negative  → overdue (display in red)
///   - ~0        → due today
///   - positive  → upcoming (display normally)
class RevisionBankItem {
  const RevisionBankItem({
    required this.problemId,
    required this.title,
    required this.titleSlug,
    required this.difficulty,
    this.topics = const [],
    required this.confidenceLast,
    required this.nextReviewAt,
    required this.firstSolvedAt,
    this.lastReviewedAt,
    this.reviewCount = 0,
    required this.daysRemaining,
  });

  final int problemId;
  final String title;
  final String titleSlug;
  final String difficulty;
  final List<String> topics;

  /// Last self-reported confidence score (1–5).
  final int confidenceLast;

  /// ISO-8601 UTC timestamp of the next scheduled review.
  final String nextReviewAt;

  /// ISO-8601 UTC timestamp of the original solve.
  final String firstSolvedAt;

  /// ISO-8601 UTC timestamp of the last review (null on first-ever review).
  final String? lastReviewedAt;

  final int reviewCount;

  /// Days until the next review (server-computed).
  /// Negative = overdue, ~0 = today, positive = future.
  final double daysRemaining;

  factory RevisionBankItem.fromJson(Map<String, dynamic> json) {
    return RevisionBankItem(
      problemId: (json['problem_id'] as num?)?.toInt() ?? 0,
      title: json['title']?.toString() ?? '',
      titleSlug: json['title_slug']?.toString() ?? '',
      difficulty: json['difficulty']?.toString() ?? '',
      topics: (json['topics'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      confidenceLast: (json['confidence_last'] as num?)?.toInt() ?? 3,
      nextReviewAt: json['next_review_at']?.toString() ?? '',
      firstSolvedAt: json['first_solved_at']?.toString() ?? '',
      lastReviewedAt: json['last_reviewed_at']?.toString(),
      reviewCount: (json['review_count'] as num?)?.toInt() ?? 0,
      daysRemaining: (json['days_remaining'] as num?)?.toDouble() ?? 0.0,
    );
  }
}


// =============================================================================
// RevisionTopicStat — topic-level SRS confidence aggregate
// =============================================================================

/// Per-topic average SRS confidence derived from the revision bank.
///
/// Computed server-side by unnesting `leetcode_problems.topics` (JSONB) and
/// grouping `revision_bank.confidence_last` values per tag.
/// The backend returns these sorted by [avgConfidence] ascending, so
/// `list[0]` is always the user's weakest DSA pattern.
class RevisionTopicStat {
  const RevisionTopicStat({
    required this.topic,
    required this.avgConfidence,
    required this.problemCount,
  });

  /// Topic name (e.g. "Dynamic Programming", "Graphs").
  final String topic;

  /// Mean confidence score across all revision-bank problems tagged with
  /// this topic. Range: 1.0 (blackout) – 5.0 (confident).
  final double avgConfidence;

  /// Number of revision-bank items contributing to this aggregate.
  final int problemCount;

  factory RevisionTopicStat.fromJson(Map<String, dynamic> json) {
    return RevisionTopicStat(
      topic: json['topic']?.toString() ?? '',
      // Default to 5.0 (confident) so missing data never shows as "weakest".
      avgConfidence: (json['avg_confidence'] as num?)?.toDouble() ?? 5.0,
      problemCount: (json['problem_count'] as num?)?.toInt() ?? 0,
    );
  }
}


// =============================================================================
// RevisionBankPage — GET /progress/revision/all paginated envelope
// =============================================================================

/// Paginated response from `GET /progress/revision/all`.
///
/// Bundles the current page of [RevisionBankItem] items with the full
/// [topicStats] list (already sorted weakest-first by the backend) so the
/// Flutter client can power both the "All Problems" paginated view and the
/// "Weakest Patterns" section from a single round-trip.
class RevisionBankPage {
  const RevisionBankPage({
    required this.items,
    required this.totalCount,
    required this.page,
    required this.limit,
    this.topicStats = const [],
  });

  /// The items on the current page.
  final List<RevisionBankItem> items;

  /// Total number of items in the user's revision bank (pre-pagination).
  final int totalCount;

  final int page;
  final int limit;

  /// Full topic-confidence list, sorted by [RevisionTopicStat.avgConfidence]
  /// ASC. Index 0 is the weakest pattern. Returned on every page.
  final List<RevisionTopicStat> topicStats;

  factory RevisionBankPage.fromJson(Map<String, dynamic> json) {
    return RevisionBankPage(
      items: (json['items'] as List<dynamic>?)
              ?.map((e) => RevisionBankItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      totalCount: (json['total_count'] as num?)?.toInt() ?? 0,
      page: (json['page'] as num?)?.toInt() ?? 1,
      limit: (json['limit'] as num?)?.toInt() ?? 10,
      topicStats: (json['topic_stats'] as List<dynamic>?)
              ?.map((e) => RevisionTopicStat.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );
  }
}


// =============================================================================
// LogProgressResponse — POST /progress response
// =============================================================================

class LogProgressResponse {
  const LogProgressResponse({
    required this.success,
    required this.message,
    this.data,
  });

  final bool success;
  final String message;
  final LogProgressData? data;

  factory LogProgressResponse.fromJson(Map<String, dynamic> json) {
    return LogProgressResponse(
      success: json['success'] as bool? ?? false,
      message: json['message']?.toString() ?? '',
      data: json['data'] != null
          ? LogProgressData.fromJson(json['data'] as Map<String, dynamic>)
          : null,
    );
  }
}

class LogProgressData {
  const LogProgressData({
    required this.msgType,
    this.topicsLogged = const [],
    this.streakCurrent = 0,
    this.streakLongest = 0,
  });

  final String msgType;
  final List<String> topicsLogged;
  final int streakCurrent;
  final int streakLongest;

  factory LogProgressData.fromJson(Map<String, dynamic> json) {
    return LogProgressData(
      msgType: json['msg_type']?.toString() ?? '',
      topicsLogged: (json['topics_logged'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      streakCurrent: (json['streak_current'] as num?)?.toInt() ?? 0,
      streakLongest: (json['streak_longest'] as num?)?.toInt() ?? 0,
    );
  }
}

// =============================================================================
// TopicFrequency — single topic + mention count
// =============================================================================

class TopicFrequency {
  const TopicFrequency({
    required this.topic,
    this.count = 0,
  });

  final String topic;
  final int count;

  factory TopicFrequency.fromJson(Map<String, dynamic> json) {
    return TopicFrequency(
      topic: json['topic']?.toString() ?? '',
      count: (json['count'] as num?)?.toInt() ?? 0,
    );
  }
}

// =============================================================================
// UserTopics — GET /users/{id}/dashboard-aggregate → data.topics
// =============================================================================

class UserTopics {
  const UserTopics({
    required this.userId,
    this.totalMentions = 0,
    this.uniqueTopics = 0,
    this.frequency = const [],
  });

  final String userId;
  final int totalMentions;
  final int uniqueTopics;
  final List<TopicFrequency> frequency;

  factory UserTopics.fromJson(Map<String, dynamic> json) {
    final rawFreq = json['frequency'] as List<dynamic>?;

    return UserTopics(
      userId: json['user_id']?.toString() ?? '',
      totalMentions: (json['total_mentions'] as num?)?.toInt() ?? 0,
      uniqueTopics: (json['unique_topics'] as num?)?.toInt() ?? 0,
      frequency: rawFreq
              ?.map((e) =>
                  TopicFrequency.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );
  }
}

// =============================================================================
// UserDifficulty — GET /users/{id}/dashboard-aggregate → data.difficulty
// =============================================================================

class UserDifficulty {
  const UserDifficulty({
    required this.userId,
    this.easy = 0,
    this.medium = 0,
    this.hard = 0,
    this.expert = 0,
    this.unknown = 0,
  });

  final String userId;
  final int easy;
  final int medium;
  final int hard;
  final int expert;
  final int unknown;

  int get total => easy + medium + hard + expert + unknown;

  factory UserDifficulty.fromJson(Map<String, dynamic> json) {
    return UserDifficulty(
      userId: json['user_id']?.toString() ?? '',
      easy: (json['easy'] as num?)?.toInt() ?? 0,
      medium: (json['medium'] as num?)?.toInt() ?? 0,
      hard: (json['hard'] as num?)?.toInt() ?? 0,
      expert: (json['expert'] as num?)?.toInt() ?? 0,
      unknown: (json['unknown'] as num?)?.toInt() ?? 0,
    );
  }
}

// =============================================================================
// DashboardAggregate — GET /users/{id}/dashboard-aggregate
// =============================================================================

class DashboardAggregate {
  const DashboardAggregate({
    required this.userId,
    required this.stats,
    required this.topics,
    required this.difficulty,
  });

  final String userId;
  final UserStats stats;
  final UserTopics topics;
  final UserDifficulty difficulty;

  factory DashboardAggregate.fromJson(Map<String, dynamic> json) {
    return DashboardAggregate(
      userId: json['user_id']?.toString() ?? '',
      stats: UserStats.fromJson(
        json['stats'] as Map<String, dynamic>? ?? const {},
      ),
      topics: UserTopics.fromJson(
        json['topics'] as Map<String, dynamic>? ?? const {},
      ),
      difficulty: UserDifficulty.fromJson(
        json['difficulty'] as Map<String, dynamic>? ?? const {},
      ),
    );
  }
}
