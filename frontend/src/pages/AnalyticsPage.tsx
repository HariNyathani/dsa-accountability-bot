import { useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip,
  ResponsiveContainer, CartesianGrid, Cell,
} from "recharts";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import GlassCard from "../components/GlassCard";
import { SkeletonCards, SkeletonChart } from "../components/Loader";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { PageHeader } from "../components/Layout";
import LiquidCapsule from "../components/LiquidCapsule";
import {
  PALETTE, axisTick, axisTickBold, gridProps, tooltipStyle,
  tooltipItemStyle, tooltipLabelStyle,
} from "../styles/charts";
import s from "../styles/shared.module.css";

const PERIOD_ITEMS = [
  { key: "7d", label: "7D" },
  { key: "30d", label: "30D" },
  { key: "all", label: "All" },
] as const;

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<string>("30d");
  const overview = useApi(() => api.overview(), []);
  const topics = useApi(() => api.topics(15), []);
  const activity = useApi(() => api.activity(period), [period]);

  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.refetch} />;
  const o = overview.data;

  return (
    <>
      <PageHeader
        title="Analytics"
        subtitle="Deep-dive into platform-wide DSA study patterns and engagement"
      />

      {overview.loading ? (
        <SkeletonCards count={4} cols={4} />
      ) : (
        o && (
          <div className={s.statsGrid} data-cols="4">
            <StatCard icon="📚" value={topics.data?.unique_topics ?? 0} label="Unique Topics" accent="espresso" />
            <StatCard icon="💬" value={topics.data?.total_mentions ?? 0} label="Questions Logged" accent="slate" />
            <StatCard icon="📅" value={activity.data?.active_days ?? 0} label="Active Days" accent="sage" />
            <StatCard icon="📊" value={`${o.avg_consistency_pct}%`} label="Avg Consistency" accent="amber" />
          </div>
        )
      )}

      {/* Activity chart with liquid capsule period selector */}
      <div className={s.chartContainer}>
        <GlassCard padded glow>
          <div className={s.head}>
            <div className={s.title} style={{ margin: 0 }}>📈 Posting Activity</div>
            <LiquidCapsule
              items={PERIOD_ITEMS}
              value={period}
              onChange={setPeriod}
              variant="compact"
              layout="fit"
              aria-label="Period"
            />
          </div>
          {activity.loading ? (
            <SkeletonChart />
          ) : (
            activity.data && (
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={activity.data.daily_activity}>
                  <defs>
                    <linearGradient id="gMsg2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gUsr2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--diff-easy)" stopOpacity={0.22} />
                      <stop offset="95%" stopColor="var(--diff-easy)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="date" tick={axisTick} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis tick={axisTick} />
                  <RTooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} />
                  <Area type="monotone" dataKey="total_messages" stroke="var(--accent)" fill="url(#gMsg2)" strokeWidth={2} name="Messages" />
                  <Area type="monotone" dataKey="users_posted" stroke="var(--diff-easy)" fill="url(#gUsr2)" strokeWidth={2} name="Users Active" />
                </AreaChart>
              </ResponsiveContainer>
            )
          )}
        </GlassCard>
      </div>

      <div className={s.chartContainer}>
        <GlassCard padded glow>
          <div className={s.title}>📚 DSA Topic Practice Totals</div>
          <div className={s.subtitle}>Weighted top practiced topics across all users</div>
          {topics.loading ? (
            <SkeletonChart />
          ) : topics.data && topics.data.top_topics.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(300, topics.data.top_topics.length * 38)}>
              <BarChart data={topics.data.top_topics} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid {...gridProps} />
                <XAxis type="number" tick={axisTick} />
                <YAxis type="category" dataKey="topic" width={140} tick={axisTickBold} />
                <RTooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} name="Questions">
                  {topics.data.top_topics.map((_, i) => (
                    <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState icon="📚" title="No topic data yet" />
          )}
        </GlassCard>
      </div>
    </>
  );
}