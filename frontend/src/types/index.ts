/* ──────────────────────────────────────────────────────────────────────────
   TypeScript interfaces — mirrors FastAPI Pydantic schemas exactly.
   ────────────────────────────────────────────────────────────────────────── */

// ── API envelope ────────────────────────────────────────────────────────────

export interface APIResponse<T> {
  success: boolean;
  data: T;
  message: string;
  timestamp: string;
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total_items: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  success: boolean;
  data: T[];
  pagination: PaginationMeta;
  message: string;
  timestamp: string;
}

// ── Health ───────────────────────────────────────────────────────────────────

export interface HealthCheck {
  status: string;
  api_version: string;
  uptime_seconds: number;
  timestamp: string;
}

export interface ServiceStatus {
  name: string;
  status: string;
  latency_ms: number | null;
  detail: string | null;
}

export interface SystemStatus {
  api: string;
  bot: string;
  database: string;
  scheduler: string;
  services: ServiceStatus[];
  registered_users: number;
  uptime_seconds: number;
  timestamp: string;
}

// ── Users ────────────────────────────────────────────────────────────────────

export interface UserBase {
  user_id: string;
  discord_username: string | null;
  email: string | null;
  timezone: string;
  is_active: boolean;
  created_at: string | null;
}

export interface UserSettings {
  tracked_channel_id: number;
  deadline_hour: number;
  deadline_minute: number;
  warn_hour: number;
  warn_minute: number;
  final_hour: number;
  final_minute: number;
  email_hour: number;
  email_minute: number;
}

export interface UserDetail extends UserBase {
  settings: UserSettings | null;
}

export interface UserStreak {
  user_id: string;
  current_streak: number;
  longest_streak: number;
  last_post_date: string | null;
}

export interface UserStats {
  user_id: string;
  total_messages: number;
  total_days_tracked: number;
  days_posted: number;
  consistency_pct: number;
  current_streak: number;
  longest_streak: number;
  posted_today: boolean;
  today: string;
  badges: string[];
}

export interface TopicFrequency {
  topic: string;
  count: number;
}

export interface UserTopics {
  user_id: string;
  total_mentions: number;
  unique_topics: number;
  frequency: TopicFrequency[];
}

export interface ActivityLog {
  id: number;
  posted_at: string;
  message_type: string;
  message_content: string | null;
  topics: string | null;
  parsed_fields: string | null;
}

export interface UserActivityResponse {
  user_id: string;
  recent_logs: ActivityLog[];
}

export interface UserDifficulty {
  user_id: string;
  easy: number;
  medium: number;
  hard: number;
  unknown: number;
}

export interface DashboardAggregateResponse {
  user_id: string;
  stats: UserStats;
  topics: UserTopics;
  difficulty: UserDifficulty;
}


// ── Leaderboard ──────────────────────────────────────────────────────────────

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  discord_username: string | null;
  current_streak: number;
  longest_streak: number;
  consistency_pct: number;
  total_messages: number;
  days_posted: number;
}

export interface LeaderboardResponse {
  sort_by: string;
  total_users: number;
  active_streaks: number;
  entries: LeaderboardEntry[];
}

// ── Analytics ────────────────────────────────────────────────────────────────

export interface PlatformOverview {
  total_users: number;
  active_users: number;
  total_messages: number;
  total_days_tracked: number;
  avg_consistency_pct: number;
  avg_streak: number;
  longest_streak_global: number;
  longest_streak_user: string | null;
}

export interface TopicAnalytics {
  total_mentions: number;
  unique_topics: number;
  top_topics: { topic: string; count: number }[];
}

export interface DailyActivity {
  date: string;
  users_posted: number;
  total_messages: number;
}

export interface ActivityAnalytics {
  period: string;
  total_days: number;
  active_days: number;
  daily_activity: DailyActivity[];
}

// ── Summaries ────────────────────────────────────────────────────────────────

export interface WeeklySummary {
  week_start: string;
  week_end: string;
  days_posted: number;
  days_missed: number;
  consistency_pct: number;
  total_messages: number;
}

export interface WeeklyReport {
  user_id: string;
  week_start: string;
  week_end: string;
  days_posted: number;
  days_missed: number;
  consistency_pct: number;
  total_messages: number;
  current_streak: number;
  longest_streak: number;
  top_topics: { topic: string; count: number }[];
}

export interface SummaryHistory {
  user_id: string;
  summaries: WeeklySummary[];
}

// ── Reminders ────────────────────────────────────────────────────────────────

export interface ReminderSchedule {
  user_id: string;
  timezone: string;
  deadline: string;
  warn_time: string;
  final_time: string;
  email_time: string;
  email_configured: boolean;
}

export interface HeatmapResponse {
  user_id: string;
  dates: Record<string, number>;
  active_days: number;
  current_streak: number;
  max_streak: number;
}
