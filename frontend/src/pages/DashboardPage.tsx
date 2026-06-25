import { useNavigate } from "react-router-dom";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip,
  ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell,
} from "recharts";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import GlassCard from "../components/GlassCard";
import { SkeletonCards, SkeletonChart } from "../components/Loader";
import { ErrorState, EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/Layout";
import Button from "../components/Button";
import {
  PALETTE, axisTick, axisTickBold, gridProps, tooltipStyle,
  tooltipItemStyle, tooltipLabelStyle,
} from "../styles/charts";
import s from "../styles/shared.module.css";

export default function DashboardPage() {
  const nav = useNavigate();
  const overview = useApi(() => api.overview(), []);
  const activity = useApi(() => api.activity("30d"), []);
  const topics = useApi(() => api.topics(10), []);
  const lb = useApi(() => api.leaderboard("streak", 5), []);

  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.refetch} />;
  const o = overview.data;

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="Platform overview — real-time data from the DSA Accountability Bot"
      />

      {/* ── Stats ───────────────────────────────────────────────────── */}
      {overview.loading ? (
        <SkeletonCards count={6} />
      ) : (
        o && (
          <div className={s.statsGrid}>
            <StatCard icon="👥" value={o.total_users} label="Total Users" accent="slate" />
            <StatCard icon="🔥" value={o.active_users} label="Active Streaks" accent="sage" />
            <StatCard icon="💬" value={o.total_messages} label="Total Messages" accent="slate" />
            <StatCard icon="📈" value={`${o.avg_consistency_pct}%`} label="Avg Consistency" accent="amber" />
            <StatCard icon="⚡" value={o.avg_streak.toFixed(1)} label="Avg Streak" accent="espresso" />
            <StatCard icon="🏆" value={o.longest_streak_global} label="Best Streak" accent="clay" />
          </div>
        )
      )}

      {/* ── Charts row ─────────────────────────────────────────────── */}
      <div className={s.chartsGrid}>
        <GlassCard padded glow>
          <div className={s.title}>📈 Activity Trend (30 Days)</div>
          {activity.loading ? (
            <SkeletonChart />
          ) : (
            activity.data && (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={activity.data.daily_activity}>
                  <defs>
                    <linearGradient id="gMsg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="date" tick={axisTick} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={axisTick} />
                  <RTooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} />
                  <Area type="monotone" dataKey="total_messages" stroke="var(--accent)" fill="url(#gMsg)" strokeWidth={2} name="Messages" />
                  <Area type="monotone" dataKey="users_posted" stroke="var(--diff-easy)" fill="none" strokeWidth={2} strokeDasharray="5 3" name="Active Users" />
                </AreaChart>
              </ResponsiveContainer>
            )
          )}
        </GlassCard>

        <GlassCard padded glow>
          <div className={s.title}>📚 Topic Distribution</div>
          {topics.loading ? (
            <SkeletonChart />
          ) : topics.data && topics.data.top_topics.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={topics.data.top_topics}
                  dataKey="count"
                  nameKey="topic"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  innerRadius={54}
                  paddingAngle={2}
                  label={({ topic, percent }: { topic: string; percent: number }) =>
                    `${topic} ${(percent * 100).toFixed(0)}%`}
                  labelLine={{ stroke: "var(--border-strong)" }}
                >
                  {topics.data.top_topics.map((_, i) => (
                    <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                  ))}
                </Pie>
                <RTooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState icon="📚" title="No topic data yet" />
          )}
        </GlassCard>
      </div>

      {/* ── Top Streaks ────────────────────────────────────────────── */}
      <div className={s.chartContainer}>
        <GlassCard padded glow>
          <div className={s.head}>
            <div className={s.title} style={{ margin: 0 }}>🔥 Top Streaks</div>
            <Button variant="ghost" size="sm" onClick={() => nav("/leaderboard")}>
              View Full Leaderboard →
            </Button>
          </div>
          {lb.loading ? (
            <SkeletonChart />
          ) : (
            lb.data && lb.data.entries.length > 0 && (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={lb.data.entries} layout="vertical">
                  <CartesianGrid {...gridProps} />
                  <XAxis type="number" tick={axisTick} />
                  <YAxis
                    type="category"
                    dataKey="discord_username"
                    width={130}
                    tick={axisTickBold}
                    tickFormatter={(v: string) => (v?.length > 15 ? v.slice(0, 13) + "…" : v || "Unknown")}
                  />
                  <RTooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} />
                  <Bar dataKey="current_streak" fill="var(--accent)" radius={[0, 6, 6, 0]} name="Streak" />
                </BarChart>
              </ResponsiveContainer>
            )
          )}
        </GlassCard>
      </div>
    </>
  );
}