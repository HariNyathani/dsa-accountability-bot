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
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.error ?? res.statusText, res.status);
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
  LeaderboardResponse,
  PlatformOverview,
  TopicAnalytics,
  ActivityAnalytics,
  SummaryHistory,
  WeeklyReport,
  ReminderSchedule,
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
};
