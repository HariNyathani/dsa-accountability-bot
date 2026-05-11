/* ──────────────────────────────────────────────────────────────────────────
   Centralized API client — single point of contact with FastAPI backend.
   In dev, Vite proxies /api → http://localhost:8000.
   In production, set VITE_API_BASE_URL to the deployed API URL.
   ────────────────────────────────────────────────────────────────────────── */

const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    credentials: "include",
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? body.error ?? res.statusText, res.status);
  }

  return res.json();
}

// ── Typed endpoint helpers ──────────────────────────────────────────────────

import type {
  APIResponse,
  PaginatedResponse,
  HealthCheck,
  SystemStatus,
  UserBase,
  UserDetail,
  UserStats,
  UserStreak,
  UserTopics,
  UserActivityResponse,
  UserDifficulty,
  DashboardAggregateResponse,
  LeaderboardResponse,
  PlatformOverview,
  TopicAnalytics,
  ActivityAnalytics,
  SummaryHistory,
  WeeklyReport,
  ReminderSchedule,
  HeatmapResponse,
} from "../types";

export const api = {
  // Health
  health: () => request<APIResponse<HealthCheck>>("/health"),
  status: () => request<APIResponse<SystemStatus>>("/status"),

  // Users
  users: (page = 1, perPage = 50) =>
    request<PaginatedResponse<UserBase>>(`/users?page=${page}&per_page=${perPage}`),
  user: (id: string) => request<APIResponse<UserDetail>>(`/users/${id}`),
  userStats: (id: string) => request<APIResponse<UserStats>>(`/users/${id}/stats`),
  userStreak: (id: string) => request<APIResponse<UserStreak>>(`/users/${id}/streak`),
  userTopics: (id: string) => request<APIResponse<UserTopics>>(`/users/${id}/topics`),
  userDifficulty: (id: string) => request<APIResponse<UserDifficulty>>(`/users/${id}/difficulty`),
  userActivity: (id: string) => request<APIResponse<UserActivityResponse>>(`/users/${id}/activity`),
  heatmap: (id: string) => request<APIResponse<HeatmapResponse>>(`/users/${id}/heatmap`),
  dashboardAggregate: (id: string) => request<APIResponse<DashboardAggregateResponse>>(`/users/${id}/dashboard-aggregate`),

  // Leaderboard
  leaderboard: (sortBy = "streak", limit = 25) =>
    request<APIResponse<LeaderboardResponse>>(
      `/leaderboard?sort_by=${sortBy}&limit=${limit}`
    ),

  // Analytics
  overview: () => request<APIResponse<PlatformOverview>>("/analytics/overview"),
  topics: (limit = 20) =>
    request<APIResponse<TopicAnalytics>>(`/analytics/topics?limit=${limit}`),
  activity: (period = "30d") =>
    request<APIResponse<ActivityAnalytics>>(`/analytics/activity?period=${period}`),

  // Summaries
  summaries: (userId: string) =>
    request<APIResponse<SummaryHistory>>(`/summaries/${userId}`),
  weeklyReport: (userId: string, week = "last") =>
    request<APIResponse<WeeklyReport>>(`/weekly-report/${userId}?week=${week}`),

  // Reminders
  reminders: (userId: string) =>
    request<APIResponse<ReminderSchedule>>(`/reminders/${userId}`),

  updateEmail: (userId: string, email: string) =>
    request<APIResponse<UserDetail>>(`/users/${userId}/email`, { method: "PUT", body: JSON.stringify({ email }) }),

  updateTimezone: (userId: string, timezone: string) =>
    request<APIResponse<UserDetail>>(`/users/${userId}/timezone`, { method: "PUT", body: JSON.stringify({ timezone }) }),

  // Progress
  logProgress: (data: { intent_type: string, topics: { canonical_topic: string, question_count: number, difficulty?: string }[], note?: string, target_date?: string }) =>
    request<APIResponse<any>>("/progress", { method: "POST", body: JSON.stringify(data) }),

  logRestDay: () =>
    request<APIResponse<any>>("/progress/rest", { method: "POST", body: JSON.stringify({}) }),

  getExportUrl: (userId: string) => `${BASE}/users/${userId}/export`,
};
