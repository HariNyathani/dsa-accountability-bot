/* ──────────────────────────────────────────────────────────────────────────
   Centralized API client — single point of contact with FastAPI backend.
   In dev, Vite proxies /api → http://localhost:8000.
   In production, set VITE_API_BASE_URL to the deployed API URL.

   Auth: Bearer-only (Module 9 / backend security audit).
   Every request automatically injects Authorization: Bearer <token> from
   localStorage via getAuthHeaders(). No cookies are used or sent.
   ────────────────────────────────────────────────────────────────────────── */

import { getAuthHeaders } from "../contexts/AuthContext";

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
    ...init,
    headers: {
      "Content-Type": "application/json",
      // Inject Bearer token from localStorage (Bearer-only auth, Module 9).
      ...getAuthHeaders(),
      // Caller-supplied headers last so they can override if needed.
      ...init?.headers,
    },
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
    ...init,
    headers: {
      "Content-Type": "application/json",
      // Inject Bearer token when available — public endpoints also benefit
      // from auth context so the API can return personalised data.
      ...getAuthHeaders(),
      ...init?.headers,
    },
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
  health: (init?: RequestInit) => request<APIResponse<HealthCheck>>("/health", init),
  status: (init?: RequestInit) => request<APIResponse<SystemStatus>>("/status", init),

  // Users — public profile endpoints use publicRequest so guests never see auth errors
  users: (page = 1, perPage = 50, init?: RequestInit) =>
    request<PaginatedResponse<UserBase>>(`/users?page=${page}&per_page=${perPage}`, init),
  user: (id: string, init?: RequestInit) => publicRequest<UserDetail>(`/users/${id}`, init),
  userStats: (id: string, init?: RequestInit) => publicRequest<UserStats>(`/users/${id}/stats`, init),
  userStreak: (id: string, init?: RequestInit) => publicRequest<UserStreak>(`/users/${id}/streak`, init),
  userTopics: (id: string, init?: RequestInit) => publicRequest<UserTopics>(`/users/${id}/topics`, init),
  userDifficulty: (id: string, init?: RequestInit) => publicRequest<UserDifficulty>(`/users/${id}/difficulty`, init),
  userActivity: (id: string, init?: RequestInit) => publicRequest<UserActivityResponse>(`/users/${id}/activity`, init),
  heatmap: (id: string, init?: RequestInit) => publicRequest<HeatmapResponse>(`/users/${id}/heatmap`, init),
  dashboardAggregate: (id: string, init?: RequestInit) => publicRequest<DashboardAggregateResponse>(`/users/${id}/dashboard-aggregate`, init),

  // Username (vanity handle)
  checkUsername: (username: string, init?: RequestInit) =>
    request<APIResponse<{ available: boolean; reason?: string }>>(`/users/check-username/${username}`, init),
  updateUsername: (userId: string, username: string, init?: RequestInit) =>
    request<APIResponse<UserDetail>>(`/users/settings/username`, {
      method: "PUT",
      body: JSON.stringify({ user_id: userId, username }),
      ...init,
    }),

  // Leaderboard
  leaderboard: (sortBy = "streak", limit = 25, init?: RequestInit) =>
    request<APIResponse<LeaderboardResponse>>(
      `/leaderboard?sort_by=${sortBy}&limit=${limit}`,
      init
    ),

  // Analytics
  overview: (init?: RequestInit) => request<APIResponse<PlatformOverview>>("/analytics/overview", init),
  topics: (limit = 20, init?: RequestInit) =>
    request<APIResponse<TopicAnalytics>>(`/analytics/topics?limit=${limit}`, init),
  activity: (period = "30d", init?: RequestInit) =>
    request<APIResponse<ActivityAnalytics>>(`/analytics/activity?period=${period}`, init),

  // Summaries
  summaries: (userId: string, init?: RequestInit) =>
    request<APIResponse<SummaryHistory>>(`/summaries/${userId}`, init),
  weeklyReport: (userId: string, week = "last", init?: RequestInit) =>
    request<APIResponse<WeeklyReport>>(`/weekly-report/${userId}?week=${week}`, init),

  // Reminders
  reminders: (userId: string, init?: RequestInit) =>
    request<APIResponse<ReminderSchedule>>(`/reminders/${userId}`, init),

  updateEmail: (userId: string, email: string, init?: RequestInit) =>
    request<APIResponse<UserDetail>>(`/users/${userId}/email`, { method: "PUT", body: JSON.stringify({ email }), ...init }),

  updateTimezone: (userId: string, timezone: string, init?: RequestInit) =>
    request<APIResponse<UserDetail>>(`/users/${userId}/timezone`, { method: "PUT", body: JSON.stringify({ timezone }), ...init }),

  // Progress
  logProgress: (data: { intent_type: string, topics: { canonical_topic: string, question_count: number, difficulty?: string }[], note?: string, target_date?: string }, init?: RequestInit) =>
    request<APIResponse<any>>("/progress", { method: "POST", body: JSON.stringify(data), ...init }),

  logRestDay: (init?: RequestInit) =>
    request<APIResponse<any>>("/progress/rest", { method: "POST", body: JSON.stringify({}), ...init }),

  logPlatformProblem: (data: { platform: string; problem_identifier: string; confidence?: number | null }, init?: RequestInit) =>
    request<APIResponse<any>>("/progress/platform", { method: "POST", body: JSON.stringify(data), ...init }),

  getExportUrl: (userId: string) => `${BASE}/users/${userId}/export`,

  // Revision Bank
  getDueRevisionItems: (init?: RequestInit) => request<any>("/progress/revision/due", init),
  getAllRevisionItems: (page = 1, limit = 10, init?: RequestInit) =>
    request<any>(`/progress/revision/all?page=${page}&limit=${limit}`, init),
  submitRevisionReview: (data: { problem_id: number; confidence: number }, init?: RequestInit) =>
    request<APIResponse<any>>("/progress/revision/review", { method: "POST", body: JSON.stringify(data), ...init }),

  // Admin Panel — protected by require_admin on the backend
  adminUsers: (init?: RequestInit) => request<APIResponse<{ users: any[]; total: number }>>("/admin/users", init),
  adminMissedToday: (init?: RequestInit) => request<APIResponse<{ users: any[]; total: number }>>("/admin/missed-today", init),
  adminSudoLog: (data: { user_id: string; topic: string; count: number; difficulty: string }, init?: RequestInit) =>
    request<APIResponse<{ status: string; message: string; user_id?: string }>>("/admin/sudo-log", {
      method: "POST", body: JSON.stringify(data),
      ...init,
    }),
  adminSudoRestDay: (userId: string, init?: RequestInit) =>
    request<APIResponse<{ status: string; message: string; user_id?: string }>>("/admin/sudo-rest", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
      ...init,
    }),
  adminUndo: (userId: string, init?: RequestInit) =>
    request<APIResponse<{ status: string; message: string; user_id?: string }>>("/admin/undo", {
      method: "POST", body: JSON.stringify({ user_id: userId }),
      ...init,
    }),
  adminForceSummary: (broadcastToDiscord = false, init?: RequestInit) =>
    request<APIResponse<{ status: string; message: string }>>("/admin/force-summary", {
      method: "POST", body: JSON.stringify({ broadcast_to_discord: broadcastToDiscord }),
      ...init,
    }),
};
