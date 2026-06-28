import { useNavigate } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer,
  CartesianGrid, Cell, PieChart, Pie,
} from "recharts";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../contexts/AuthContext";
import StatCard from "../components/StatCard";
import GlassCard from "../components/GlassCard";
import { SkeletonCards, SkeletonCard, SkeletonRows } from "../components/Loader";
import { EmptyState, ErrorState } from "../components/EmptyState";
import QuickLogCard from "../components/QuickLogCard";
import RecentActivity from "../components/RecentActivity";
import Heatmap from "../components/Heatmap";
import Button from "../components/Button";
import { PageHeader } from "../components/Layout";
import {
  PALETTE, axisTick, axisTickBold, gridProps, tooltipStyle,
  tooltipItemStyle, consistencyColor,
} from "../styles/charts";
import sh from "../styles/shared.module.css";
import s from "./MyDashboardPage.module.css";

const DiscordGlyph = () => (
  <svg width="20" height="15" viewBox="0 0 71 55" fill="none" aria-hidden>
    <path d="M60.1045 4.8978C55.5792 2.8214 50.7265 1.2916 45.6527 0.41542C45.5603 0.39851 45.468 0.440769 45.4204 0.525289C44.7963 1.6353 44.105 3.0834 43.6209 4.2216C38.1637 3.4046 32.7345 3.4046 27.3892 4.2216C26.905 3.0581 26.1886 1.6353 25.5617 0.525289C25.5141 0.443589 25.4218 0.40133 25.3294 0.41542C20.2584 1.2888 15.4057 2.8186 10.8776 4.8978C10.8384 4.9147 10.8048 4.9429 10.7825 4.9795C1.57795 18.7309 -0.943561 32.1443 0.293408 45.3914C0.299005 45.4562 0.335386 45.5182 0.385761 45.5576C6.45866 50.0174 12.3413 52.7249 18.1147 54.5195C18.2071 54.5477 18.305 54.5139 18.3638 54.4378C19.7295 52.5728 20.9469 50.6063 21.9907 48.5383C22.0523 48.4172 21.9935 48.2735 21.8676 48.2256C19.9366 47.4931 18.0979 46.6 16.3292 45.5858C16.1893 45.5041 16.1781 45.304 16.3068 45.2082C16.679 44.9293 17.0513 44.6391 17.4067 44.3461C17.471 44.2926 17.5606 44.2813 17.6362 44.3151C29.2558 49.6202 41.8354 49.6202 53.3179 44.3151C53.3935 44.2785 53.4832 44.2898 53.5502 44.3433C53.9057 44.6363 54.2779 44.9293 54.6529 45.2082C54.7816 45.304 54.7732 45.5041 54.6333 45.5858C52.8646 46.6197 51.0259 47.4931 49.0921 48.2228C48.9662 48.2707 48.9102 48.4172 48.9718 48.5383C50.038 50.6034 51.2554 52.5699 52.5959 54.435C52.6519 54.5139 52.7526 54.5477 52.845 54.5195C58.6464 52.7249 64.529 50.0174 70.6019 45.5576C70.6551 45.5182 70.6887 45.459 70.6943 45.3942C72.1747 30.0791 68.2147 16.7757 60.1968 4.9823C60.1772 4.9429 60.1437 4.9147 60.1045 4.8978ZM23.7259 37.3253C20.2276 37.3253 17.3451 34.1136 17.3451 30.1693C17.3451 26.225 20.1717 23.0133 23.7259 23.0133C27.308 23.0133 30.1626 26.2532 30.1066 30.1693C30.1066 34.1136 27.28 37.3253 23.7259 37.3253ZM47.3178 37.3253C43.8196 37.3253 40.9371 34.1136 40.9371 30.1693C40.9371 26.225 43.7636 23.0133 47.3178 23.0133C50.9 23.0133 53.7545 26.2532 53.6986 30.1693C53.6986 34.1136 50.9 37.3253 47.3178 37.3253Z" fill="currentColor" />
  </svg>
);

export default function MyDashboardPage() {
  const { user, authenticated, loading: authLoading } = useAuth();
  const nav = useNavigate();
  const uid = user?.id ?? "";
  const enabled = authenticated && !!uid;

  const userInfo = useApi((signal) => api.user(uid, { signal }), [uid], enabled);
  const aggregate = useApi((signal) => api.dashboardAggregate(uid, { signal }), [uid], enabled);
  const sums = useApi((signal) => api.summaries(uid, { signal }), [uid], enabled);
  const remind = useApi((signal) => api.reminders(uid, { signal }), [uid], enabled);
  const activity = useApi((signal) => api.userActivity(uid, { signal }), [uid], enabled);
  const heatmap = useApi((signal) => api.heatmap(uid, { signal }), [uid], enabled);

  // Not authenticated — friendly prompt
  if (!authLoading && !authenticated) {
    return (
      <>
        <PageHeader title="My Dashboard" subtitle="Login with Discord to see your personalized analytics" />
        <div className={s.prompt}>
          <div className={s.pIcon}>🔒</div>
          <h3>Authentication Required</h3>
          <p>Connect your Discord account to unlock your personal dashboard with detailed analytics, streak tracking, topic insights, and more.</p>
          <Button variant="primary" onClick={() => { window.location.href = "/auth/login"; }}>
            {<DiscordGlyph />}
            Login with Discord
          </Button>
        </div>
      </>
    );
  }

  if (authLoading) return <SkeletonCards count={6} />;

  // "Not Yet Registered" is a special case — the user authenticated via Discord
  // but hasn't run !register in the bot. Show the friendly prompt regardless
  // of whether we have stale data.
  if (userInfo.error && (userInfo.error.includes("not found") || userInfo.error.includes("404"))) {
    return (
      <>
        <PageHeader title={`Welcome, ${user?.username}!`} subtitle="Your personalized dashboard" />
        <div className={s.prompt}>
          <div className={s.pIcon}>📋</div>
          <h3>Not Yet Registered</h3>
          <p>Your Discord account is linked, but you haven't registered with the DSA Accountability Bot yet. Use the <code>!register</code> command in Discord to start tracking your DSA progress.</p>
          <p>Once registered, your personal stats, streaks, and topic analytics will appear here.</p>
        </div>
      </>
    );
  }

  // Only short-circuit to ErrorState if we have no user data to show.
  // If we have stale data and a mid-refetch error, keep showing the data
  // with a non-blocking inline error indicator further down.
  if (userInfo.error && !userInfo.data) {
    return <ErrorState message={userInfo.error} onRetry={userInfo.refetch} />;
  }

  const st = aggregate.data?.stats;
  const t = aggregate.data?.topics;
  const d = aggregate.data?.difficulty;
  const u = userInfo.data;

  return (
    <>
      {/* Hero */}
      <div className={s.hero}>
        <div className={s.greeting}>
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className={s.avatar} />
          ) : (
            <div className={s.avatarFallback}>{user?.username?.slice(0, 2).toUpperCase()}</div>
          )}
          <div>
            <div className={s.name}>Welcome back, {user?.username}!</div>
            <div className={s.sub}>Your personal DSA accountability dashboard</div>
            {st?.badges && st.badges.length > 0 && (
              <div className={s.badges}>
                {st.badges.map((b, i) => (
                  <span key={i} className={s.badge}>{b}</span>
                ))}
              </div>
            )}
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={() => window.open(api.getExportUrl(uid), "_blank")}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>
          Export Data
        </Button>
      </div>

      {userInfo.error && userInfo.data && (
        <div role="status" style={{ color: "var(--diff-hard)", fontSize: "0.85rem", marginBottom: 16, padding: "10px 14px", background: "color-mix(in srgb, var(--diff-hard) 8%, transparent)", border: "1px solid color-mix(in srgb, var(--diff-hard) 20%, transparent)", borderRadius: 8 }}>
          ⚠ Showing cached data — refresh failed: {userInfo.error}
        </div>
      )}

      {/* Stats */}
      {aggregate.loading ? <SkeletonCards count={6} /> : st && (
        <div className={sh.statsGrid}>
          <StatCard icon="🔥" value={st.current_streak} label="Current Streak" accent="sage" />
          <StatCard icon="🏆" value={st.longest_streak} label="Longest Streak" accent="amber" />
          <StatCard icon="📈" value={`${st.consistency_pct}%`} label="Consistency" accent="espresso" />
          <StatCard icon="💬" value={st.total_messages} label="Total Questions" accent="slate" />
          <StatCard icon="📅" value={st.days_posted} label="Days Posted" accent="clay" />
          <StatCard icon={st.posted_today ? "✅" : "❌"} value={st.posted_today ? "Yes" : "No"} label="Posted Today" accent={st.posted_today ? "sage" : "rose"} />
        </div>
      )}

      {/* Heatmap full width */}
      <Heatmap
        data={heatmap.data?.dates || {}}
        restDates={new Set(heatmap.data?.rest_dates || [])}
        activeDays={heatmap.data?.active_days || 0}
        currentStreak={heatmap.data?.current_streak || 0}
        maxStreak={heatmap.data?.max_streak || 0}
        loading={heatmap.loading}
      />

      {/* Bento: QuickLog | Topic | Difficulty */}
      <div className={s.bento}>
        <div className={s.colQuickLog}>
          <QuickLogCard onLogSuccess={() => { aggregate.refetch(); sums.refetch(); activity.refetch(); heatmap.refetch(); }} />
        </div>

        <div className={s.colTopic}>
          <GlassCard padded glow fill>
            <div className={sh.title}>📚 Your Topic Distribution</div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", paddingRight: "16px" }}>
              {aggregate.loading ? <SkeletonCard /> : t && t.frequency.length > 0 ? (() => {
                  const top8 = t.frequency.slice(0, 8);
                  const top8Sum = top8.reduce((s, f) => s + f.count, 0);
                  const otherCount = (t.total_mentions ?? 0) - top8Sum;
                  const pieData = otherCount > 0
                    ? [...top8, { topic: `Other (${t.frequency.length - 8})`, count: otherCount }]
                    : top8;
                  return (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="count"
                      nameKey="topic"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      innerRadius={46}
                      paddingAngle={2}
                      label={({ topic, percent }: { topic: string; percent: number }) => `${topic} ${(percent * 100).toFixed(0)}%`}
                      labelLine={{ stroke: "var(--border-strong)" }}
                    >
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={i < 8 ? PALETTE[i % PALETTE.length] : "#9E9E9E"} />
                      ))}
                    </Pie>
                    <RTooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} />
                  </PieChart>
                </ResponsiveContainer>
                  );
                })()
              ) : (
                <EmptyState icon="📚" title="No topics yet" message="Start posting DSA progress to see your topic analysis." />
              )}
            </div>
          </GlassCard>
        </div>

        <div className={s.colDifficulty}>
          <GlassCard padded glow fill>
            <div className={sh.title}>🎯 Difficulty</div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
              {aggregate.loading ? <SkeletonRows count={4} /> : d && (d.easy > 0 || d.medium > 0 || d.hard > 0 || (d.expert || 0) > 0) ? (
                <DifficultyBars d={d} />
              ) : (
                <EmptyState icon="🎯" title="No difficulty data" message="Log questions with difficulty to see your distribution." />
              )}
            </div>
          </GlassCard>
        </div>
      </div>

      {/* Bento Lower: Topic Frequency | Recent Activity */}
      <div className={s.bentoLower}>
        <div className={s.colFreq}>
          <GlassCard padded glow fill>
            <div className={sh.title}>📊 Topic Frequency</div>
            <div style={{ marginTop: "24px" }}>
              {aggregate.loading ? <SkeletonCard /> : t && t.frequency.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(200, t.frequency.slice(0, 8).length * 34)}>
                  <BarChart data={t.frequency.slice(0, 8)} layout="vertical">
                    <CartesianGrid {...gridProps} />
                    <XAxis type="number" tick={axisTick} />
                    <YAxis type="category" dataKey="topic" width={120} tick={axisTickBold} />
                    <RTooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} />
                    <Bar dataKey="count" radius={[0, 6, 6, 0]} name="Questions">
                      {t.frequency.slice(0, 8).map((_, i) => (
                        <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState icon="📊" title="No data yet" message="Topic insights appear once you start logging." />
              )}
            </div>
          </GlassCard>
        </div>
        <div className={s.colActivity}>
          <RecentActivity logs={activity.data?.recent_logs} loading={activity.loading} />
        </div>
      </div>

      {/* Weekly Summary History */}
      <div className={sh.chartContainer}>
        <GlassCard padded glow>
          <div className={sh.title}>📊 Your Weekly Summary History</div>
          {sums.loading ? <SkeletonRows count={5} /> : sums.data && sums.data.summaries.length > 0 ? (
            <div className={sh.tableWrap}>
              <table className={sh.table} aria-label="Weekly activity summary">
                <thead>
                  <tr><th>Week</th><th>Posted</th><th>Missed</th><th>Consistency</th><th>Messages</th></tr>
                </thead>
                <tbody>
                  {sums.data.summaries.map((w, i) => (
                    <tr key={i} className={sh.row}>
                      <td className={sh.bold} style={{ fontSize: ".82rem" }}>{w.week_start} → {w.week_end}</td>
                      <td style={{ color: "var(--diff-easy)", fontWeight: 700 }}>{w.days_posted}</td>
                      <td style={{ color: w.days_missed > 0 ? "var(--diff-hard)" : "var(--text-secondary)" }}>{w.days_missed}</td>
                      <td>
                        <div className={sh.consBar}>
                          <span className={sh.bold} style={{ minWidth: 42 }}>{w.consistency_pct}%</span>
                          <div className={sh.track}>
                            <div className={sh.fill} style={{ width: `${w.consistency_pct}%`, background: consistencyColor(w.consistency_pct) }} />
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
        </GlassCard>
      </div>

      {/* Settings Row */}
      <div className={s.bentoLower}>
        {remind.data && (
          <div className={s.colFreq}>
            <GlassCard padded glow fill>
              <div className={sh.title}>⏰ Your Reminder Settings</div>
              <div className={s.kvGrid} style={{ marginTop: "24px" }}>
                <div className={s.kv}>Timezone: <strong>{remind.data.timezone}</strong></div>
                <div className={s.kv}>Deadline: <strong>{remind.data.deadline}</strong></div>
                <div className={s.kv}>Warning: <strong>{remind.data.warn_time}</strong></div>
                <div className={s.kv}>Final Alert: <strong>{remind.data.final_time}</strong></div>
                <div className={s.kv}>Email Alert: <strong>{remind.data.email_time}</strong></div>
                <div className={s.kv}>Email Setup: <strong>{remind.data.email_configured ? "✅ Configured" : "❌ Not set"}</strong></div>
              </div>
            </GlassCard>
          </div>
        )}

        {u?.settings && (
          <div className={s.colActivity}>
            <GlassCard padded glow fill>
              <div className={sh.title}>⚙️ Bot Settings</div>
              <div className={s.kvGrid} style={{ marginTop: "24px" }}>
                <div className={s.kv}>Channel: <strong>{u.settings.tracked_channel_id || "Not set"}</strong></div>
              </div>
            </GlassCard>
          </div>
        )}
      </div>
    </>
  );
}

function DifficultyBars({ d }: { d: { easy: number; medium: number; hard: number; expert?: number; unknown?: number } }) {
  const rows = [
    { label: "Easy", count: d.easy, color: "var(--diff-easy)" },
    { label: "Medium", count: d.medium, color: "var(--diff-medium)" },
    { label: "Hard", count: d.hard, color: "var(--diff-hard)" },
    { label: "Expert (CF 2000+)", count: d.expert || 0, color: "var(--diff-expert)" },
  ];
  const total = rows.reduce((a, r) => a + r.count, 0);
  return (
    <div className={s.diffList}>
      {rows.map((r) => {
        const pct = total > 0 ? (r.count / total) * 100 : 0;
        return (
          <div key={r.label} className={s.diffRow}>
            <div className={s.rowHead}>
              <span className={s.lbl} style={{ color: r.color }}>{r.label}</span>
              <span className={s.count}>{r.count} <span className={s.pct}>({pct.toFixed(0)}%)</span></span>
            </div>
            <div className={s.diffTrack}>
              <div className={s.diffFill} style={{ width: `${pct}%`, background: r.color }} />
            </div>
          </div>
        );
      })}
      {d.unknown && d.unknown > 0 && <div className={s.unknown}>+ {d.unknown} unknown</div>}
    </div>
  );
}