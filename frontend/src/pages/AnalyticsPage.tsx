import { useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell,
} from "recharts";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import { SkeletonCards, SkeletonChart } from "../components/Loader";
import { ErrorState } from "../components/EmptyState";

const COLORS = ["#6366f1","#8b5cf6","#10b981","#f59e0b","#0ea5e9","#f43f5e","#14b8a6","#a855f7","#ec4899","#22d3ee","#84cc16","#f97316"];

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("30d");
  const overview = useApi(() => api.overview(), []);
  const topics   = useApi(() => api.topics(15), []);
  const activity = useApi(() => api.activity(period), [period]);

  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.refetch} />;

  const o = overview.data;

  return (
    <>
      <div className="page-header">
        <h2>Analytics</h2>
        <p>Deep-dive into platform-wide DSA study patterns and engagement</p>
      </div>

      {/* Stats */}
      {overview.loading ? <SkeletonCards count={4} /> : o && (
        <div className="stats-grid">
          <StatCard icon="📚" value={topics.data?.unique_topics ?? 0} label="Unique Topics" accent="purple" />
          <StatCard icon="💬" value={topics.data?.total_mentions ?? 0} label="Questions Logged" accent="sky" />
          <StatCard icon="📅" value={activity.data?.active_days ?? 0}  label="Active Days"   accent="emerald" />
          <StatCard icon="📊" value={`${o.avg_consistency_pct}%`}      label="Avg Consistency" accent="amber" />
        </div>
      )}

      {/* Activity Chart */}
      <div className="chart-container">
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div className="chart-title" style={{ margin: 0 }}>📈 Posting Activity</div>
            <div className="period-selector">
              {["7d", "30d", "all"].map((p) => (
                <button key={p} className={`period-btn${period === p ? " active" : ""}`} onClick={() => setPeriod(p)}>
                  {p === "all" ? "All" : p}
                </button>
              ))}
            </div>
          </div>
          {activity.loading ? <SkeletonChart /> : activity.data && (
            <ResponsiveContainer width="100%" height={320}>
              <AreaChart data={activity.data.daily_activity}>
                <defs>
                  <linearGradient id="gMsg2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gUsr2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.05)" />
                <XAxis dataKey="date" tick={{ fill: "#94A3B8", fontSize: 11 }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis tick={{ fill: "#94A3B8", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#0F0F1A", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, fontSize: 13, boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }} labelStyle={{ color: "#F8FAFC" }} />
                <Area type="monotone" dataKey="total_messages" stroke="#6366f1" fill="url(#gMsg2)" strokeWidth={2} name="Messages" />
                <Area type="monotone" dataKey="users_posted"   stroke="#10b981" fill="url(#gUsr2)" strokeWidth={2} name="Users Active" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Topic Bar Chart */}
      <div className="chart-container">
        <div className="card">
          <div className="chart-title">📚 DSA Topic Practice Totals</div>
          <div className="chart-subtitle">Weighted top practiced topics across all users</div>
          {topics.loading ? <SkeletonChart /> : topics.data && topics.data.top_topics.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(300, topics.data.top_topics.length * 38)}>
              <BarChart data={topics.data.top_topics} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.05)" />
                <XAxis type="number" tick={{ fill: "#94A3B8", fontSize: 11 }} />
                <YAxis type="category" dataKey="topic" width={140} tick={{ fill: "#F8FAFC", fontSize: 12, fontWeight: 500 }} />
                <Tooltip contentStyle={{ background: "#0F0F1A", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, fontSize: 13, boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} name="Questions">
                  {topics.data.top_topics.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state"><p>No topic data available</p></div>
          )}
        </div>
      </div>
    </>
  );
}
