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
  });

  final String intentType;
  final List<ProgressTopicLog> topics;
  final String? note;
  final String? targetDate;

  Map<String, dynamic> toJson() => {
        'intent_type': intentType,
        'topics': topics.map((t) => t.toJson()).toList(),
        if (note != null) 'note': note,
        if (targetDate != null) 'target_date': targetDate,
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
