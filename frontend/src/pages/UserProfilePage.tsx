import { useParams, useNavigate } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from "recharts";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import { SkeletonCards, SkeletonChart, SkeletonRows } from "../components/Loader";
import { ErrorState, EmptyState } from "../components/EmptyState";

const COLORS = ["#6366f1","#8b5cf6","#10b981","#f59e0b","#0ea5e9","#f43f5e","#14b8a6","#a855f7"];

export default function UserProfilePage() {
  const { userId } = useParams<{ userId: string }>();
  const nav = useNavigate();
  const uid = userId || "";

  // Guard: if the route param isn't a valid string of digits, skip all API calls
  const validId = /^\d+$/.test(uid);

  const user   = useApi(() => api.user(uid),      [uid], validId);
  const stats  = useApi(() => api.userStats(uid),  [uid], validId);
  const topics = useApi(() => api.userTopics(uid), [uid], validId);
  const sums   = useApi(() => api.summaries(uid),  [uid], validId);

  if (!validId) return (
    <EmptyState icon="⚠️" title="Invalid User" message={`The user ID "${userId}" is not valid.`} />
  );

  if (user.error) return <ErrorState message={user.error} onRetry={user.refetch} />;
  if (user.loading) return <SkeletonCards count={4} />;

  const u = user.data;
  const s = stats.data;
  const t = topics.data;

  if (!u) return <EmptyState icon="👤" title="User not found" />;

  const initials = (u.discord_username ?? "?").slice(0, 2).toUpperCase();

  return (
    <>
      {/* Back */}
      <button className="sort-tab" onClick={() => nav(-1)} style={{ marginBottom: 20 }}>← Back</button>

      {/* Profile Header */}
      <div className="profile-header">
        <div className="profile-avatar">{initials}</div>
        <div className="profile-info">
          <h2>{u.discord_username || `User ${u.user_id}`}</h2>
          <p>ID: {u.user_id} · Timezone: {u.timezone} · Joined: {u.created_at?.slice(0, 10) ?? "—"}</p>
        </div>
      </div>

      {/* Stats */}
      {stats.loading ? <SkeletonCards count={6} /> : s && (
        <div className="stats-grid">
          <StatCard icon="🔥" value={s.current_streak}  label="Current Streak" accent="emerald" />
          <StatCard icon="🏆" value={s.longest_streak}   label="Longest Streak" accent="amber" />
          <StatCard icon="📈" value={`${s.consistency_pct}%`} label="Consistency" accent="indigo" />
          <StatCard icon="💬" value={s.total_messages}   label="Total Entries"     accent="sky" />
          <StatCard icon="📅" value={s.days_posted}       label="Days Posted"    accent="purple" />
          <StatCard icon={s.posted_today ? "✅" : "❌"} value={s.posted_today ? "Yes" : "No"} label="Posted Today" accent={s.posted_today ? "emerald" : "rose"} />
        </div>
      )}

      <div className="profile-grid">
        {/* Topic chart */}
        <div className="chart-container">
          <div className="card">
            <div className="chart-title">📚 Topic Breakdown</div>
            {topics.loading ? <SkeletonChart /> : t && t.frequency.length > 0 ? (
              <ResponsiveContainer width="100%" height={Math.max(200, t.frequency.length * 34)}>
                <BarChart data={t.frequency.slice(0, 10)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.05)" />
                  <XAxis type="number" tick={{ fill: "#94A3B8", fontSize: 11 }} />
                  <YAxis type="category" dataKey="topic" width={120} tick={{ fill: "#F8FAFC", fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: "#0F0F1A", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, fontSize: 13, boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }} />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]} name="Questions">
                    {t.frequency.slice(0, 10).map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState icon="📚" title="No topics yet" message="Start posting DSA progress to see topic analysis." />
            )}
          </div>
        </div>

        {/* Summary History */}
        <div className="chart-container">
          <div className="card">
            <div className="chart-title">📊 Weekly Summary History</div>
            {sums.loading ? <SkeletonRows count={5} /> : sums.data && sums.data.summaries.length > 0 ? (
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Week</th>
                      <th>Posted</th>
                      <th>Missed</th>
                      <th>Consistency</th>
                      <th>Messages</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sums.data.summaries.map((w, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 600, fontSize: ".82rem" }}>{w.week_start} → {w.week_end}</td>
                        <td style={{ color: "#10b981", fontWeight: 700 }}>{w.days_posted}</td>
                        <td style={{ color: w.days_missed > 0 ? "#f43f5e" : "#555e77" }}>{w.days_missed}</td>
                        <td>
                          <div className="consistency-bar">
                            <span style={{ fontWeight: 600, minWidth: 42 }}>{w.consistency_pct}%</span>
                            <div className="bar-track">
                              <div className="bar-fill" style={{ width: `${w.consistency_pct}%`, background: w.consistency_pct >= 80 ? "#10b981" : w.consistency_pct >= 50 ? "#f59e0b" : "#f43f5e" }} />
                            </div>
                          </div>
                        </td>
                        <td>{w.total_messages}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon="📊" title="No summaries yet" message="Weekly summaries appear after the first full week." />
            )}
          </div>
        </div>
      </div>

      {/* Settings */}
      {u.settings && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="chart-title">⚙️ Bot Settings</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, fontSize: ".88rem" }}>
            <div><span style={{ color: "#94A3B8" }}>Deadline:</span> <strong>{String(u.settings.deadline_hour).padStart(2,"0")}:{String(u.settings.deadline_minute).padStart(2,"0")}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Warning:</span> <strong>{String(u.settings.warn_hour).padStart(2,"0")}:{String(u.settings.warn_minute).padStart(2,"0")}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Final Alert:</span> <strong>{String(u.settings.final_hour).padStart(2,"0")}:{String(u.settings.final_minute).padStart(2,"0")}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Email Alert:</span> <strong>{String(u.settings.email_hour).padStart(2,"0")}:{String(u.settings.email_minute).padStart(2,"0")}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Channel:</span> <strong>{u.settings.tracked_channel_id || "Not set"}</strong></div>
          </div>
        </div>
      )}
    </>
  );
}
