import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { SkeletonRows } from "../components/Loader";
import { EmptyState, ErrorState } from "../components/EmptyState";

const SORT_OPTIONS = [
  { key: "streak",      label: "🔥 Streak" },
  { key: "longest",     label: "🏆 Longest" },
  { key: "consistency", label: "📈 Consistency" },
  { key: "posts",       label: "💬 Posts" },
  { key: "days",        label: "📅 Days" },
];

const MEDALS = ["🥇", "🥈", "🥉"];

function barColor(pct: number) {
  if (pct >= 80) return "#10b981";
  if (pct >= 50) return "#f59e0b";
  return "#f43f5e";
}

export default function LeaderboardPage() {
  const [sortBy, setSortBy] = useState("streak");
  const nav = useNavigate();
  const { data, loading, error, refetch } = useApi(
    () => api.leaderboard(sortBy, 50),
    [sortBy],
  );

  if (error) return <ErrorState message={error} onRetry={refetch} />;

  return (
    <>
      <div className="page-header">
        <h2>Leaderboard</h2>
        <p>Rankings across {data?.total_users ?? "…"} users — {data?.active_streaks ?? 0} active streaks</p>
      </div>

      {/* Sort tabs */}
      <div className="sort-tabs">
        {SORT_OPTIONS.map((o) => (
          <button
            key={o.key}
            className={`sort-tab${sortBy === o.key ? " active" : ""}`}
            onClick={() => setSortBy(o.key)}
          >
            {o.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="card">
        {loading ? <SkeletonRows count={8} /> : !data || data.entries.length === 0 ? (
          <EmptyState icon="🏆" title="No data yet" message="Users need to start posting to appear here." />
        ) : (
          <div className="table-wrapper">
            <table className="data-table">
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
                  <tr key={e.user_id} style={{ cursor: "pointer" }} onClick={() => nav(`/u/${e.username || e.user_id}`)}>
                    <td>
                      {e.rank <= 3
                        ? <span className="rank-medal">{MEDALS[e.rank - 1]}</span>
                        : <span className="rank-num">{e.rank}</span>}
                    </td>
                    <td className="username-cell">{e.discord_username || `User ${e.user_id}`}</td>
                    <td>
                      <span className={`streak-badge ${e.current_streak > 0 ? "active" : "inactive"}`}>
                        {e.current_streak > 0 ? "🔥" : "💤"} {e.current_streak}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{e.longest_streak}</td>
                    <td>
                      <div className="consistency-bar">
                        <span style={{ fontWeight: 600, minWidth: 42 }}>{e.consistency_pct}%</span>
                        <div className="bar-track">
                          <div className="bar-fill" style={{ width: `${Math.min(e.consistency_pct, 100)}%`, background: barColor(e.consistency_pct) }} />
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
      </div>
    </>
  );
}
