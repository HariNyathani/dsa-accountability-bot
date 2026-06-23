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

/**
 * Like `request`, but treats 401/403 as a graceful no-data response (returns null)
 * instead of throwing. Used for publicly-accessible profile endpoints so that
 * unauthenticated visitors never see an auth error in the UI.
 */
async function publicRequest<T>(path: string, init?: RequestInit): Promise<{ data: T }> {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    credentials: "include",
    ...init,
  });

  if (!res.ok) {
    if (res.status === 401 || res.status === 403) {
      // Return an empty shell so the UI degrades gracefully rather than erroring
      return { data: null as unknown as T };
    }
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

  // Users — public profile endpoints use publicRequest so guests never see auth errors
  users: (page = 1, perPage = 50) =>
    request<PaginatedResponse<UserBase>>(`/users?page=${page}&per_page=${perPage}`),
  user: (id: string) => publicRequest<UserDetail>(`/users/${id}`),
  userStats: (id: string) => publicRequest<UserStats>(`/users/${id}/stats`),
  userStreak: (id: string) => publicRequest<UserStreak>(`/users/${id}/streak`),
  userTopics: (id: string) => publicRequest<UserTopics>(`/users/${id}/topics`),
  userDifficulty: (id: string) => publicRequest<UserDifficulty>(`/users/${id}/difficulty`),
  userActivity: (id: string) => publicRequest<UserActivityResponse>(`/users/${id}/activity`),
  heatmap: (id: string) => publicRequest<HeatmapResponse>(`/users/${id}/heatmap`),
  dashboardAggregate: (id: string) => publicRequest<DashboardAggregateResponse>(`/users/${id}/dashboard-aggregate`),

  // Username (vanity handle)
  checkUsername: (username: string) =>
    request<APIResponse<{ available: boolean; reason?: string }>>(`/users/check-username/${username}`),
  updateUsername: (userId: string, username: string) =>
    request<APIResponse<UserDetail>>(`/users/settings/username`, {
      method: "PUT",
      body: JSON.stringify({ user_id: userId, username }),
    }),

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

  logPlatformProblem: (data: { platform: string; problem_identifier: string; confidence?: number | null }) =>
    request<APIResponse<any>>("/progress/platform", { method: "POST", body: JSON.stringify(data) }),

  getExportUrl: (userId: string) => `${BASE}/users/${userId}/export`,

  // Revision Bank
  getDueRevisionItems: () => request<any>("/progress/revision/due"),
  getAllRevisionItems: (page = 1, limit = 10) =>
    request<any>(`/progress/revision/all?page=${page}&limit=${limit}`),
  submitRevisionReview: (data: { problem_id: number; confidence: number }) =>
    request<APIResponse<any>>("/progress/revision/review", { method: "POST", body: JSON.stringify(data) }),

  // Admin Panel — protected by require_admin on the backend
  adminUsers: () => request<APIResponse<{ users: any[]; total: number }>>("/admin/users"),
  adminMissedToday: () => request<APIResponse<{ users: any[]; total: number }>>("/admin/missed-today"),
  adminSudoLog: (data: { user_id: string; topic: string; count: number; difficulty: string }) =>
    request<APIResponse<{ status: string; message: string; user_id?: string }>>("/admin/sudo-log", {
      method: "POST", body: JSON.stringify(data),
    }),
  adminSudoRestDay: (userId: string) =>
    request<APIResponse<{ status: string; message: string; user_id?: string }>>("/admin/sudo-rest", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
  adminUndo: (userId: string) =>
    request<APIResponse<{ status: string; message: string; user_id?: string }>>("/admin/undo", {
      method: "POST", body: JSON.stringify({ user_id: userId }),
    }),
  adminForceSummary: (broadcastToDiscord = false) =>
    request<APIResponse<{ status: string; message: string }>>("/admin/force-summary", {
      method: "POST", body: JSON.stringify({ broadcast_to_discord: broadcastToDiscord }),
    }),
};
