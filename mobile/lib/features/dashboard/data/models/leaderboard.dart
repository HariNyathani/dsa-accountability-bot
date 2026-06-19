/// Immutable data models for the leaderboard API endpoint.
///
/// Endpoint: `GET /leaderboard?sort_by=streak&limit=25`
/// Response envelope: `APIResponse<LeaderboardData>`
library;

// =============================================================================
// LeaderboardEntry — a single ranked user row
// =============================================================================

class LeaderboardEntry {
  const LeaderboardEntry({
    required this.rank,
    required this.userId,
    this.discordUsername,
    this.username,
    this.currentStreak = 0,
    this.longestStreak = 0,
    this.consistencyPct = 0.0,
    this.totalMessages = 0,
    this.daysPosted = 0,
  });

  final int rank;
  final String userId;
  final String? discordUsername;
  final String? username;
  final int currentStreak;
  final int longestStreak;
  final double consistencyPct;
  final int totalMessages;
  final int daysPosted;

  factory LeaderboardEntry.fromJson(Map<String, dynamic> json) {
    return LeaderboardEntry(
      rank: (json['rank'] as num?)?.toInt() ?? 0,
      userId: json['user_id']?.toString() ?? '',
      discordUsername: json['discord_username']?.toString(),
      username: json['username']?.toString(),
      currentStreak: (json['current_streak'] as num?)?.toInt() ?? 0,
      longestStreak: (json['longest_streak'] as num?)?.toInt() ?? 0,
      consistencyPct: (json['consistency_pct'] as num?)?.toDouble() ?? 0.0,
      totalMessages: (json['total_messages'] as num?)?.toInt() ?? 0,
      daysPosted: (json['days_posted'] as num?)?.toInt() ?? 0,
    );
  }
}

// =============================================================================
// LeaderboardData — full response payload
// =============================================================================

class LeaderboardData {
  const LeaderboardData({
    this.sortBy = 'streak',
    this.totalUsers = 0,
    this.activeStreaks = 0,
    this.entries = const [],
  });

  final String sortBy;
  final int totalUsers;
  final int activeStreaks;
  final List<LeaderboardEntry> entries;

  factory LeaderboardData.fromJson(Map<String, dynamic> json) {
    final rawEntries = json['entries'] as List<dynamic>?;

    return LeaderboardData(
      sortBy: json['sort_by']?.toString() ?? 'streak',
      totalUsers: (json['total_users'] as num?)?.toInt() ?? 0,
      activeStreaks: (json['active_streaks'] as num?)?.toInt() ?? 0,
      entries: rawEntries
              ?.map((e) =>
                  LeaderboardEntry.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
    );
  }
}
