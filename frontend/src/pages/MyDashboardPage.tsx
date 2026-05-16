/* ──────────────────────────────────────────────────────────────────────────
   MyDashboardPage — personalized dashboard for authenticated users.

   Shows the logged-in user's:
   • Stats (streak, consistency, posts, etc.)
   • Topic distribution chart
   • Weekly summary history
   • Reminder settings
   ────────────────────────────────────────────────────────────────────────── */

import { useNavigate } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell, PieChart, Pie,
} from "recharts";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../contexts/AuthContext";
import StatCard from "../components/StatCard";
import { SkeletonCards, SkeletonChart, SkeletonRows } from "../components/Loader";
import { EmptyState, ErrorState } from "../components/EmptyState";
import QuickLogCard from "../components/QuickLogCard";
import RecentActivity from "../components/RecentActivity";
import Heatmap from "../components/Heatmap";

const COLORS = ["#6366f1", "#8b5cf6", "#10b981", "#f59e0b", "#0ea5e9", "#f43f5e", "#14b8a6", "#a855f7", "#ec4899", "#22d3ee"];

export default function MyDashboardPage() {
  const { user, authenticated, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const uid = user?.id ?? "";
  const enabled = authenticated && !!uid;

  const userInfo = useApi(() => api.user(uid), [uid], enabled);
  const aggregate = useApi(() => api.dashboardAggregate(uid), [uid], enabled);
  const sums = useApi(() => api.summaries(uid), [uid], enabled);
  const remind = useApi(() => api.reminders(uid), [uid], enabled);
  const activity = useApi(() => api.userActivity(uid), [uid], enabled);
  const heatmap = useApi(() => api.heatmap(uid), [uid], enabled);

  // Not authenticated — show a friendly prompt
  if (!authLoading && !authenticated) {
    return (
      <>
        <div className="page-header">
          <h2>My Dashboard</h2>
          <p>Login with Discord to see your personalized analytics</p>
        </div>
        <div className="auth-prompt-card card">
          <div className="auth-prompt-icon">🔒</div>
          <h3>Authentication Required</h3>
          <p>Connect your Discord account to unlock your personal dashboard with detailed analytics, streak tracking, topic insights, and more.</p>
          <button
            className="discord-login-btn discord-login-btn-lg"
            onClick={() => { window.location.href = "/auth/login"; }}
          >
            <svg width="20" height="15" viewBox="0 0 71 55" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M60.1045 4.8978C55.5792 2.8214 50.7265 1.2916 45.6527 0.41542C45.5603 0.39851 45.468 0.440769 45.4204 0.525289C44.7963 1.6353 44.105 3.0834 43.6209 4.2216C38.1637 3.4046 32.7345 3.4046 27.3892 4.2216C26.905 3.0581 26.1886 1.6353 25.5617 0.525289C25.5141 0.443589 25.4218 0.40133 25.3294 0.41542C20.2584 1.2888 15.4057 2.8186 10.8776 4.8978C10.8384 4.9147 10.8048 4.9429 10.7825 4.9795C1.57795 18.7309 -0.943561 32.1443 0.293408 45.3914C0.299005 45.4562 0.335386 45.5182 0.385761 45.5576C6.45866 50.0174 12.3413 52.7249 18.1147 54.5195C18.2071 54.5477 18.305 54.5139 18.3638 54.4378C19.7295 52.5728 20.9469 50.6063 21.9907 48.5383C22.0523 48.4172 21.9935 48.2735 21.8676 48.2256C19.9366 47.4931 18.0979 46.6 16.3292 45.5858C16.1893 45.5041 16.1781 45.304 16.3068 45.2082C16.679 44.9293 17.0513 44.6391 17.4067 44.3461C17.471 44.2926 17.5606 44.2813 17.6362 44.3151C29.2558 49.6202 41.8354 49.6202 53.3179 44.3151C53.3935 44.2785 53.4832 44.2898 53.5502 44.3433C53.9057 44.6363 54.2779 44.9293 54.6529 45.2082C54.7816 45.304 54.7732 45.5041 54.6333 45.5858C52.8646 46.6197 51.0259 47.4931 49.0921 48.2228C48.9662 48.2707 48.9102 48.4172 48.9718 48.5383C50.038 50.6034 51.2554 52.5699 52.5959 54.435C52.6519 54.5139 52.7526 54.5477 52.845 54.5195C58.6464 52.7249 64.529 50.0174 70.6019 45.5576C70.6551 45.5182 70.6887 45.459 70.6943 45.3942C72.1747 30.0791 68.2147 16.7757 60.1968 4.9823C60.1772 4.9429 60.1437 4.9147 60.1045 4.8978ZM23.7259 37.3253C20.2276 37.3253 17.3451 34.1136 17.3451 30.1693C17.3451 26.225 20.1717 23.0133 23.7259 23.0133C27.308 23.0133 30.1626 26.2532 30.1066 30.1693C30.1066 34.1136 27.28 37.3253 23.7259 37.3253ZM47.3178 37.3253C43.8196 37.3253 40.9371 34.1136 40.9371 30.1693C40.9371 26.225 43.7636 23.0133 47.3178 23.0133C50.9 23.0133 53.7545 26.2532 53.6986 30.1693C53.6986 34.1136 50.9 37.3253 47.3178 37.3253Z" fill="currentColor" />
            </svg>
            Login with Discord
          </button>
        </div>
      </>
    );
  }

  if (authLoading) return <SkeletonCards count={6} />;

  // Authenticated — data error guard
  if (userInfo.error) {
    // User may not be registered in the bot yet
    if (userInfo.error.includes("not found") || userInfo.error.includes("404")) {
      return (
        <>
          <div className="page-header">
            <h2>Welcome, {user?.username}!</h2>
            <p>Your personalized dashboard</p>
          </div>
          <div className="auth-prompt-card card">
            <div className="auth-prompt-icon">📋</div>
            <h3>Not Yet Registered</h3>
            <p>
              Your Discord account is linked, but you haven't registered with the DSA
              Accountability Bot yet. Use the <code>!register</code> command in Discord
              to start tracking your DSA progress.
            </p>
            <p style={{ marginTop: 12, color: "var(--text-secondary)", fontSize: ".9rem" }}>
              Once registered, your personal stats, streaks, and topic analytics will appear here.
            </p>
          </div>
        </>
      );
    }
    return <ErrorState message={userInfo.error} onRetry={userInfo.refetch} />;
  }

  const s = aggregate.data?.stats;
  const t = aggregate.data?.topics;
  const d = aggregate.data?.difficulty;
  const u = userInfo.data;

  return (
    <>
      {/* Header */}
      <div className="page-header">
        <div className="my-dashboard-header">
          <div className="my-dashboard-greeting">
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="" className="my-dashboard-avatar" />
            ) : (
              <div className="profile-avatar" style={{ width: 56, height: 56, fontSize: "1.4rem" }}>
                {user?.username?.slice(0, 2).toUpperCase()}
              </div>
            )}
            <div style={{ flexGrow: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
                <div>
                  <h2>Welcome back, {user?.username}!</h2>
                  <p>Your personal DSA accountability dashboard</p>
                  {s?.badges && s.badges.length > 0 && (
                    <div style={{ display: "flex", gap: "8px", marginTop: "12px", flexWrap: "wrap" }}>
                      {s.badges.map((b, i) => (
                        <span key={i} style={{ padding: "4px 10px", background: "rgba(99, 102, 241, 0.1)", color: "#818cf8", borderRadius: "100px", fontSize: "0.8rem", fontWeight: 600, border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                          {b}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => window.open(api.getExportUrl(uid), "_blank")}
                  className="dsa-btn"
                  style={{
                    marginTop: "6px",
                    background: "rgba(99, 102, 241, 0.1)",
                    color: "#818cf8",
                    border: "1px solid rgba(99, 102, 241, 0.3)",
                    fontSize: "0.85rem",
                    padding: "8px 16px",
                    borderRadius: "8px",
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    transition: "all 0.2s ease",
                    cursor: "pointer"
                  }}
                  onMouseOver={(e) => e.currentTarget.style.background = "rgba(99, 102, 241, 0.2)"}
                  onMouseOut={(e) => e.currentTarget.style.background = "rgba(99, 102, 241, 0.1)"}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                  Export Data
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      {aggregate.loading ? <SkeletonCards count={6} /> : s && (
        <div className="stats-grid">
          <StatCard icon="🔥" value={s.current_streak} label="Current Streak" accent="emerald" />
          <StatCard icon="🏆" value={s.longest_streak} label="Longest Streak" accent="amber" />
          <StatCard icon="📈" value={`${s.consistency_pct}%`} label="Consistency" accent="indigo" />
          <StatCard icon="💬" value={s.total_messages} label="Total Questions" accent="sky" />
          <StatCard icon="📅" value={s.days_posted} label="Days Posted" accent="purple" />
          <StatCard icon={s.posted_today ? "✅" : "❌"} value={s.posted_today ? "Yes" : "No"} label="Posted Today" accent={s.posted_today ? "emerald" : "rose"} />
        </div>
      )}

      {/* Heatmap (Full Width Row) */}
      <Heatmap
        data={heatmap.data?.dates || {}}
        activeDays={heatmap.data?.active_days || 0}
        currentStreak={heatmap.data?.current_streak || 0}
        maxStreak={heatmap.data?.max_streak || 0}
        loading={heatmap.loading}
      />

      {/* Quick Log and Main Charts (Two-Column Layout) */}
      <div className="charts-grid">

        {/* LEFT COLUMN: Actions & Feed */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px", height: "100%" }}>
          <QuickLogCard onLogSuccess={() => { aggregate.refetch(); sums.refetch(); activity.refetch(); heatmap.refetch(); }} />
          <RecentActivity logs={activity.data?.recent_logs} loading={activity.loading} />
        </div>

        {/* RIGHT COLUMN: Summaries & Charts */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Topic Distribution Pie */}
          <div className="chart-container" style={{ marginBottom: 0 }}>
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="chart-title">📚 Your Topic Distribution</div>
              {aggregate.loading ? <SkeletonChart /> : t && t.frequency.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={t.frequency.slice(0, 8)}
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
                      {t.frequency.slice(0, 8).map((_, i) => (
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
                <EmptyState icon="📚" title="No topics yet" message="Start posting DSA progress to see your topic analysis." />
              )}
            </div>
          </div>

          {/* Difficulty Distribution */}
          <div className="chart-container" style={{ marginBottom: 0 }}>
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="chart-title">🎯 Difficulty Distribution</div>
              {aggregate.loading ? <SkeletonRows count={4} /> : d && (d.easy > 0 || d.medium > 0 || d.hard > 0 || (d.expert || 0) > 0) ? (
                (() => {
                  const expertCount = d.expert || 0;
                  const total = d.easy + d.medium + d.hard + expertCount;
                  return (
                    <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "16px" }}>
                      {[
                        { label: "Easy", count: d.easy, color: "#10b981", bg: "rgba(16, 185, 129, 0.1)" },
                        { label: "Medium", count: d.medium, color: "#f59e0b", bg: "rgba(245, 158, 11, 0.1)" },
                        { label: "Hard", count: d.hard, color: "#f43f5e", bg: "rgba(244, 63, 94, 0.1)" },
                        { label: "Expert (CF 2000+)", count: expertCount, color: "#9f1239", bg: "rgba(159, 18, 57, 0.1)" },
                      ].map(item => {
                        const pct = total > 0 ? (item.count / total) * 100 : 0;
                        return (
                          <div key={item.label}>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "6px" }}>
                              <span style={{ color: item.color, fontWeight: 500 }}>{item.label}</span>
                              <span style={{ fontWeight: 600 }}>{item.count} <span style={{ color: "#64748b", fontSize: "0.75rem", fontWeight: 400 }}>({pct.toFixed(0)}%)</span></span>
                            </div>
                            <div style={{ width: "100%", height: "8px", background: "rgba(255, 255, 255, 0.05)", borderRadius: "4px", overflow: "hidden" }}>
                              <div style={{ width: `${pct}%`, height: "100%", background: item.color, borderRadius: "4px", transition: "width 0.5s ease" }} />
                            </div>
                          </div>
                        );
                      })}
                      {d.unknown > 0 && (
                        <div style={{ textAlign: "right", marginTop: "4px" }}>
                          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>+ {d.unknown} unknown</span>
                        </div>
                      )}
                    </div>
                  );
                })()
              ) : (
                <EmptyState icon="🎯" title="No difficulty data" message="Log questions with difficulty to see your distribution." />
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="chart-container" style={{ marginBottom: "32px" }}>
        <div className="card">
          <div className="chart-title">📊 Topic Frequency</div>
          {aggregate.loading ? <SkeletonChart /> : t && t.frequency.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(200, t.frequency.slice(0, 8).length * 34)}>
              <BarChart data={t.frequency.slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.05)" />
                <XAxis type="number" tick={{ fill: "#94A3B8", fontSize: 11 }} />
                <YAxis type="category" dataKey="topic" width={120} tick={{ fill: "#F8FAFC", fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#0F0F1A", color: "#F8FAFC", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, fontSize: 13, boxShadow: "0 8px 32px rgba(0,0,0,0.4)" }} itemStyle={{ color: "#F8FAFC" }} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} name="Questions">
                  {t.frequency.slice(0, 8).map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState icon="📊" title="No data yet" message="Topic insights appear once you start logging." />
          )}
        </div>
      </div>

      {/* Weekly Summary History */}
      <div className="chart-container">
        <div className="card">
          <div className="chart-title">📊 Your Weekly Summary History</div>
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

      {/* Reminder Settings */}
      {remind.data && (
        <div className="card" style={{ marginTop: 0 }}>
          <div className="chart-title">⏰ Your Reminder Settings</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, fontSize: ".88rem" }}>
            <div><span style={{ color: "#94A3B8" }}>Timezone:</span> <strong>{remind.data.timezone}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Deadline:</span> <strong>{remind.data.deadline}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Warning:</span> <strong>{remind.data.warn_time}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Final Alert:</span> <strong>{remind.data.final_time}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Email Alert:</span> <strong>{remind.data.email_time}</strong></div>
            <div><span style={{ color: "#94A3B8" }}>Email Setup:</span> <strong>{remind.data.email_configured ? "✅ Configured" : "❌ Not set"}</strong></div>
          </div>
        </div>
      )}

      {/* Bot Settings */}
      {u?.settings && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="chart-title">⚙️ Bot Settings</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, fontSize: ".88rem" }}>
            <div><span style={{ color: "#94A3B8" }}>Channel:</span> <strong>{u.settings.tracked_channel_id || "Not set"}</strong></div>
          </div>
        </div>
      )}
    </>
  );
}
