/// Immutable data models for the platform-based progress logging endpoint.
///
/// Mirrors the `POST /progress/platform` response from the FastAPI backend.
/// Follows the same `fromJson` factory patterns used in `user_stats.dart`.
library;

// =============================================================================
// PlatformLogParsedData — nested `data` object inside the API response
// =============================================================================

class PlatformLogParsedData {
  const PlatformLogParsedData({
    required this.title,
    required this.difficulty,
    this.topics = const [],
    this.questionId = 0,
    required this.platform,
    this.streakCurrent = 0,
    this.streakLongest = 0,
  });

  final String title;
  final String difficulty;
  final List<String> topics;
  final int questionId;
  final String platform;
  final int streakCurrent;
  final int streakLongest;

  factory PlatformLogParsedData.fromJson(Map<String, dynamic> json) {
    return PlatformLogParsedData(
      title: json['title']?.toString() ?? '',
      difficulty: json['difficulty']?.toString() ?? '',
      topics: (json['topics'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      questionId: (json['question_id'] as num?)?.toInt() ?? 0,
      platform: json['platform']?.toString() ?? '',
      streakCurrent: (json['streak_current'] as num?)?.toInt() ?? 0,
      streakLongest: (json['streak_longest'] as num?)?.toInt() ?? 0,
    );
  }
}

// =============================================================================
// PlatformLogResponse — top-level POST /progress/platform response
// =============================================================================

class PlatformLogResponse {
  const PlatformLogResponse({
    required this.success,
    required this.message,
    this.data,
  });

  final bool success;
  final String message;
  final PlatformLogParsedData? data;

  factory PlatformLogResponse.fromJson(Map<String, dynamic> json) {
    return PlatformLogResponse(
      success: json['success'] as bool? ?? false,
      message: json['message']?.toString() ?? '',
      data: json['data'] != null
          ? PlatformLogParsedData.fromJson(
              json['data'] as Map<String, dynamic>)
          : null,
    );
  }
}
