import { useNavigate } from "react-router-dom";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, PieChart, Pie, Cell,
} from "recharts";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import { SkeletonCards, SkeletonChart } from "../components/Loader";
import { ErrorState } from "../components/EmptyState";

const COLORS = ["#6366f1","#8b5cf6","#10b981","#f59e0b","#0ea5e9","#f43f5e","#14b8a6","#a855f7","#ec4899","#22d3ee"];

export default function DashboardPage() {
  const nav = useNavigate();
  const overview  = useApi(() => api.overview(),      []);
  const activity  = useApi(() => api.activity("30d"), []);
  const topics    = useApi(() => api.topics(10),      []);
  const lb        = useApi(() => api.leaderboard("streak", 5), []);

  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.refetch} />;

  const o = overview.data;

  return (
    <>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Platform overview — real-time data from the DSA Accountability Bot</p>
      </div>

      {/* ── Stat Cards ────────────────────────────────────────────── */}
      {overview.loading ? <SkeletonCards count={6} /> : o && (
        <div className="stats-grid">
          <StatCard icon="👥" value={o.total_users}           label="Total Users"         accent="indigo" />
          <StatCard icon="🔥" value={o.active_users}          label="Active Streaks"      accent="emerald" />
          <StatCard icon="💬" value={o.total_messages}        label="Total Messages"      accent="sky" />
          <StatCard icon="📈" value={`${o.avg_consistency_pct}%`} label="Avg Consistency" accent="amber" />
          <StatCard icon="⚡" value={o.avg_streak.toFixed(1)} label="Avg Streak"          accent="purple" />
          <StatCard icon="🏆" value={o.longest_streak_global} label="Best Streak"         accent="rose" />
        </div>
      )}

      {/* ── Charts Row ────────────────────────────────────────────── */}
      <div className="charts-grid">
        {/* Activity Trend */}
        <div className="chart-container">
          <div className="card">
            <div className="chart-title">📈 Activity Trend (30 Days)</div>
            {activity.loading ? <SkeletonChart /> : activity.data && (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={activity.data.daily_activity}>
                  <defs>
                    <linearGradient id="gMsg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.05)" />
                  <XAxis dataKey="date" tick={{ fill: "#94A3B8", fontSize: 11 }}
                    tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={{ fill: "#94A3B8", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: "#0F0F1A", color: "#F8FAFC", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, fontSize: 13, boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}
                    labelStyle={{ color: "#F8FAFC" }}
                    itemStyle={{ color: "#F8FAFC" }}
                  />
                  <Area type="monotone" dataKey="total_messages" stroke="#6366f1" fill="url(#gMsg)" strokeWidth={2} name="Messages" />
                  <Area type="monotone" dataKey="users_posted" stroke="#10b981" fill="none" strokeWidth={2} strokeDasharray="5 3" name="Active Users" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Topic Distribution */}
        <div className="chart-container">
          <div className="card">
            <div className="chart-title">📚 Topic Distribution</div>
            {topics.loading ? <SkeletonChart /> : topics.data && topics.data.top_topics.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={topics.data.top_topics}
                    dataKey="count"
                    nameKey="topic"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    innerRadius={50}
                    paddingAngle={2}
                    label={({ topic, percent }: { topic: string; percent: number }) =>
                      `${topic} ${(percent * 100).toFixed(0)}%`}
                    labelLine={{ stroke: "#555e77" }}
                  >
                    {topics.data.top_topics.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "#0F0F1A", color: "#F8FAFC", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, fontSize: 13, boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}
                    itemStyle={{ color: "#F8FAFC" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state"><p>No topic data yet</p></div>
            )}
          </div>
        </div>
      </div>

      {/* ── Top Streaks ───────────────────────────────────────────── */}
      <div className="chart-container">
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div className="chart-title" style={{ margin: 0 }}>🔥 Top Streaks</div>
            <button className="sort-tab active" onClick={() => nav("/leaderboard")}>
              View Full Leaderboard →
            </button>
          </div>
          {lb.loading ? <SkeletonChart /> : lb.data && lb.data.entries.length > 0 && (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={lb.data.entries} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.05)" />
                <XAxis type="number" tick={{ fill: "#94A3B8", fontSize: 11 }} />
                <YAxis type="category" dataKey="discord_username" width={130}
                  tick={{ fill: "#F8FAFC", fontSize: 12, fontWeight: 600 }}
                  tickFormatter={(v: string) => v?.length > 15 ? v.slice(0, 13) + "…" : (v || "Unknown")} />
                <Tooltip
                  contentStyle={{ background: "#0F0F1A", color: "#F8FAFC", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, fontSize: 13, boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }}
                  itemStyle={{ color: "#F8FAFC" }}
                />
                <Bar dataKey="current_streak" fill="#6366f1" radius={[0, 6, 6, 0]} name="Streak" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </>
  );
}
