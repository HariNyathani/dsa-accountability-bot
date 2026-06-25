import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { SkeletonRows } from "../components/Loader";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { PageHeader } from "../components/Layout";
import GlassCard from "../components/GlassCard";
import LiquidCapsule from "../components/LiquidCapsule";
import { consistencyColor } from "../styles/charts";
import s from "../styles/shared.module.css";

const SORT_ITEMS = [
  { key: "streak", label: "Streak", icon: "🔥" },
  { key: "longest", label: "Longest", icon: "🏆" },
  { key: "consistency", label: "Consistency", icon: "📈" },
  { key: "posts", label: "Posts", icon: "💬" },
  { key: "days", label: "Days", icon: "📅" },
] as const;

const MEDALS = ["🥇", "🥈", "🥉"];

export default function LeaderboardPage() {
  const [sortBy, setSortBy] = useState<string>("streak");
  const nav = useNavigate();
  const { data, loading, error, refetch } = useApi(
    () => api.leaderboard(sortBy, 50),
    [sortBy]
  );

  if (error) return <ErrorState message={error} onRetry={refetch} />;

  return (
    <>
      <PageHeader
        title="Leaderboard"
        subtitle={`Rankings across ${data?.total_users ?? "…"} users — ${data?.active_streaks ?? 0} active streaks`}
        actions={
          <LiquidCapsule
            items={SORT_ITEMS}
            value={sortBy}
            onChange={setSortBy}
            variant="filter"
            layout="fit"
            aria-label="Sort by"
          />
        }
      />

      <GlassCard radius={32} glow>
        {loading ? (
          <div style={{ padding: "8px 18px" }}>
            <SkeletonRows count={8} />
          </div>
        ) : !data || data.entries.length === 0 ? (
          <EmptyState icon="🏆" title="No data yet" message="Users need to start posting to appear here." />
        ) : (
          <div className={s.tableWrap}>
            <table className={s.table}>
              <thead>
                <tr>
                  <th style={{ width: 60 }}>Rank</th>
                  <th>User</th>
                  <th>Streak</th>
                  <th>Best</th>
                  <th>Consistency</th>
                  <th>Posts</th>
                  <th>Days</th>
                </tr>
              </thead>
              <tbody>
                {data.entries.map((e) => (
                  <tr key={e.user_id} onClick={() => nav(`/u/${e.username || e.user_id}`)}>
                    <td>
                      {e.rank <= 3 ? (
                        <span className={s.medal}>{MEDALS[e.rank - 1]}</span>
                      ) : (
                        <span className={s.rankNum}>{e.rank}</span>
                      )}
                    </td>
                    <td className={s.username}>{e.discord_username || `User ${e.user_id}`}</td>
                    <td>
                      <span className={`${s.badge} ${e.current_streak > 0 ? s.badgeActive : s.badgeIdle}`}>
                        {e.current_streak > 0 ? "🔥" : "💤"} {e.current_streak}
                      </span>
                    </td>
                    <td className={s.bold}>{e.longest_streak}</td>
                    <td>
                      <div className={s.consBar}>
                        <span className={s.bold} style={{ minWidth: 42 }}>{e.consistency_pct}%</span>
                        <div className={s.track}>
                          <div
                            className={s.fill}
                            style={{
                              width: `${Math.min(e.consistency_pct, 100)}%`,
                              background: consistencyColor(e.consistency_pct),
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>{e.total_messages}</td>
                    <td>{e.days_posted}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </>
  );
}