import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer,
  CartesianGrid, Cell, PieChart, Pie,
} from "recharts";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import GlassCard from "../components/GlassCard";
import { SkeletonCards, SkeletonCard, SkeletonRows } from "../components/Loader";
import { ErrorState, EmptyState } from "../components/EmptyState";
import Heatmap from "../components/Heatmap";
import Button from "../components/Button";
import { TextInput, Select } from "../components/Field";
import { PageHeader } from "../components/Layout";
import {
  PALETTE, axisTick, axisTickBold, gridProps, tooltipStyle,
  tooltipItemStyle, consistencyColor,
} from "../styles/charts";
import sh from "../styles/shared.module.css";
import s from "./UserProfilePage.module.css";

export default function UserProfilePage() {
  const { userId, identifier } = useParams<{ userId?: string; identifier?: string }>();
  const nav = useNavigate();
  const uid = identifier || userId || "";
  const { user: authUser, authenticated, loading: authLoading } = useAuth();

  const validId = /^\d{17,19}$/.test(uid) || /^[a-z0-9_]{4,20}$/.test(uid);

  const user = useApi((signal) => api.user(uid, { signal }), [uid], validId);
  const stats = useApi((signal) => api.userStats(uid, { signal }), [uid], validId);
  const aggregate = useApi((signal) => api.dashboardAggregate(uid, { signal }), [uid], validId);
  const heatmap = useApi((signal) => api.heatmap(uid, { signal }), [uid], validId);
  const sums = useApi((signal) => api.summaries(uid, { signal }), [uid], validId);

  const resolvedUserId = user.data?.user_id || "";
  const isOwner = !authLoading && authenticated && !!resolvedUserId && authUser?.id === resolvedUserId;
  const isPublicGuest = !authLoading && !isOwner;

  const [emailInput, setEmailInput] = useState("");
  const [emailSaving, setEmailSaving] = useState(false);
  const [emailSaved, setEmailSaved] = useState(false);
  const [tzInput, setTzInput] = useState("Asia/Kolkata");
  const [tzSaving, setTzSaving] = useState(false);
  const [tzSaved, setTzSaved] = useState(false);
  const [usernameInput, setUsernameInput] = useState("");
  const [usernameSaving, setUsernameSaving] = useState(false);
  const [usernameSaved, setUsernameSaved] = useState(false);
  const [usernameStatus, setUsernameStatus] = useState<"idle" | "checking" | "available" | "taken" | "invalid">("idle");
  const [usernameReason, setUsernameReason] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (isOwner && user.data) {
      setEmailInput(user.data.email || "");
      setTzInput(user.data.timezone || "Asia/Kolkata");
      setUsernameInput(user.data.username || "");
    }
  }, [user.data, isOwner]);

  const handleSaveEmail = async () => {
    if (!isOwner) return;
    setEmailSaving(true);
    setEmailSaved(false);
    try {
      await api.updateEmail(resolvedUserId, emailInput);
      setEmailSaved(true);
      user.refetch();
    } catch (e) {
      console.error(e);
      alert("Failed to save email.");
    }
    setEmailSaving(false);
  };

  const handleSaveTz = async () => {
    if (!isOwner) return;
    setTzSaving(true);
    setTzSaved(false);
    try {
      await api.updateTimezone(resolvedUserId, tzInput);
      setTzSaved(true);
      user.refetch();
    } catch (e) {
      console.error(e);
      alert("Failed to save timezone.");
    }
    setTzSaving(false);
  };

  const checkUsernameAvailability = useCallback(async (name: string) => {
    if (!name || name.length < 4) {
      setUsernameStatus("idle");
      setUsernameReason("");
      return;
    }
    setUsernameStatus("checking");
    try {
      const res = await api.checkUsername(name);
      const d = res.data;
      if (d.available) {
        setUsernameStatus("available");
        setUsernameReason("");
      } else {
        setUsernameStatus("taken");
        setUsernameReason(d.reason || "Unavailable");
      }
    } catch {
      setUsernameStatus("invalid");
      setUsernameReason("Could not check availability.");
    }
  }, []);

  const handleUsernameChange = (val: string) => {
    const cleaned = val.toLowerCase().replace(/[^a-z0-9_]/g, "").slice(0, 20);
    setUsernameInput(cleaned);
    setUsernameSaved(false);
    if (cleaned === (user.data?.username || "")) {
      setUsernameStatus("idle");
      setUsernameReason("");
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => checkUsernameAvailability(cleaned), 300);
  };

  const handleSaveUsername = async () => {
    if (!isOwner || !usernameInput) return;
    setUsernameSaving(true);
    setUsernameSaved(false);
    try {
      await api.updateUsername(resolvedUserId, usernameInput);
      setUsernameSaved(true);
      setUsernameStatus("idle");
      user.refetch();
      nav(`/u/${usernameInput}`, { replace: true });
    } catch (e: any) {
      console.error(e);
      setUsernameStatus("taken");
      setUsernameReason(e.message || "Failed to save username.");
    }
    setUsernameSaving(false);
  };

  if (!validId) return <EmptyState icon="⚠️" title="Invalid User" message={`The identifier "${uid}" is not valid.`} />;
  // Only short-circuit to ErrorState if we have no user data to show.
  // If we have stale data and a mid-refetch error, keep showing the data
  // with a non-blocking inline error indicator further down.
  if (user.error && !user.data) return <ErrorState message={user.error} onRetry={user.refetch} />;
  if (user.loading && !user.data) return <SkeletonCards count={6} />;

  const u = user.data;
  const ss = stats.data;
  const t = aggregate.data?.topics;
  const d = aggregate.data?.difficulty;
  if (!u) return <EmptyState icon="👤" title="User not found" message="This user hasn't registered with the bot yet, or the username is incorrect." />;
  const initials = (u.discord_username ?? "?").slice(0, 2).toUpperCase();

  const borderWidth = usernameStatus === "available"
    ? "color-mix(in srgb, var(--diff-easy) 50%, transparent)"
    : usernameStatus === "taken" || usernameStatus === "invalid"
    ? "color-mix(in srgb, var(--diff-hard) 50%, transparent)"
    : "var(--border)";

  return (
    <>
      <div className={s.back}>
        <Button variant="ghost" size="sm" onClick={() => nav(-1)}>← Back</Button>
      </div>

      {user.error && user.data && (
        <div role="status" style={{ color: "var(--diff-hard)", fontSize: "0.85rem", marginBottom: 16, padding: "10px 14px", background: "color-mix(in srgb, var(--diff-hard) 8%, transparent)", border: "1px solid color-mix(in srgb, var(--diff-hard) 20%, transparent)", borderRadius: 8 }}>
          ⚠ Showing cached data — refresh failed: {user.error}
        </div>
      )}

      <GlassCard radius={32} padded glow className={s.header}>
        <div className={s.avatar}>{initials}</div>
        <div className={s.info}>
          <h2>{u.discord_username || `User ${u.user_id}`}</h2>
          <p className={s.meta}>
            {u.username && <span className={s.handle}>@{u.username} · </span>}
            ID: {u.user_id} · Timezone: {u.timezone} · Joined: {u.created_at?.slice(0, 10) ?? "—"}
          </p>
          {isPublicGuest && (
            <span className={s.publicPill}>👁️ Viewing Public Profile</span>
          )}
        </div>
      </GlassCard>

      {stats.loading ? <SkeletonCards count={6} /> : ss && (
        <div className={sh.statsGrid} style={{ marginBottom: "24px" }}>
          <StatCard icon="🔥" value={ss.current_streak} label="Current Streak" accent="sage" />
          <StatCard icon="🏆" value={ss.longest_streak} label="Longest Streak" accent="amber" />
          <StatCard icon="📈" value={`${ss.consistency_pct}%`} label="Consistency" accent="espresso" />
          <StatCard icon="💬" value={ss.total_messages} label="Total Questions" accent="slate" />
          <StatCard icon="📅" value={ss.days_posted} label="Days Posted" accent="clay" />
          <StatCard icon={ss.posted_today ? "✅" : "❌"} value={ss.posted_today ? "Yes" : "No"} label="Posted Today" accent={ss.posted_today ? "sage" : "rose"} />
        </div>
      )}

      <Heatmap
        data={heatmap.data?.dates || {}}
        restDates={new Set(heatmap.data?.rest_dates || [])}
        activeDays={heatmap.data?.active_days || 0}
        currentStreak={heatmap.data?.current_streak || 0}
        maxStreak={heatmap.data?.max_streak || 0}
        loading={heatmap.loading}
      />

      <div className={sh.chartsGrid} style={{ marginTop: "24px" }}>
        <GlassCard padded glow fill>
          <div className={sh.title}>📚 Topic Distribution</div>
          <div className={sh.bodyCenter}>
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
                    outerRadius={100}
                    innerRadius={52}
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
              <EmptyState icon="📚" title="No topics yet" message="Start posting DSA progress to see topic analysis." />
            )}
          </div>
        </GlassCard>

        <GlassCard padded glow fill>
          <div className={sh.title}>🎯 Difficulty Distribution</div>
          <div className={sh.bodyCenter}>
            {aggregate.loading ? <SkeletonRows count={4} /> : d && (d.easy > 0 || d.medium > 0 || d.hard > 0 || (d.expert || 0) > 0) ? (
              <DifficultyBars d={d} />
            ) : (
              <EmptyState icon="🎯" title="No difficulty data" message="Log questions with difficulty to see distribution." />
            )}
          </div>
        </GlassCard>
      </div>

      <div className={`${sh.chartContainer} ${s.row}`}>
        <GlassCard padded glow>
          <div className={sh.title}>📊 Topic Frequency</div>
          {aggregate.loading ? <SkeletonCard /> : t && t.frequency.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(200, t.frequency.slice(0, 10).length * 34)}>
              <BarChart data={t.frequency.slice(0, 10)} layout="vertical">
                <CartesianGrid {...gridProps} />
                <XAxis type="number" tick={axisTick} />
                <YAxis type="category" dataKey="topic" width={130} tick={axisTickBold} />
                <RTooltip contentStyle={tooltipStyle} itemStyle={tooltipItemStyle} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} name="Questions">
                  {t.frequency.slice(0, 10).map((_, i) => (
                    <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState icon="📊" title="No data yet" message="Topic insights appear once you start logging." />
          )}
        </GlassCard>
      </div>

      <div className={`${sh.chartContainer} ${s.row}`}>
        <GlassCard padded glow>
          <div className={sh.title}>📅 Weekly Summary History</div>
          {sums.loading ? <SkeletonRows count={5} /> : sums.data && sums.data.summaries.length > 0 ? (
            <div className={sh.tableWrap}>
              <table className={sh.table} aria-label="Weekly activity summary">
                <thead>
                  <tr><th>Week</th><th>Posted</th><th>Missed</th><th>Consistency</th><th>Questions</th></tr>
                </thead>
                <tbody>
                  {sums.data.summaries.map((w, i) => (
                    <tr key={i}>
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
            <EmptyState icon="📅" title="No summaries yet" message="Weekly summaries appear after the first full week." />
          )}
        </GlassCard>
      </div>

      {isOwner && (
        <>
          <div className={s.settings}>
            <GlassCard padded glow>
              <div className={sh.title}>🔗 Claim Your Profile Handle</div>
              <p className={s.settingsBody}>
                Choose a unique vanity URL for your profile. Only lowercase letters, numbers, and underscores (4–20 chars).
              </p>
              <div className={s.fieldRow}>
                <div className={s.inputGrow} style={{ borderTopWidth: 0 }}>
                  <TextInput
                    id="username-input"
                    type="text"
                    placeholder="your_handle"
                    value={usernameInput}
                    onChange={(e) => handleUsernameChange(e.target.value)}
                    maxLength={20}
                    style={{ border: `1px solid ${borderWidth}` }}
                  />
                </div>
                <Button
                  id="save-username-btn"
                  variant="primary"
                  size="sm"
                  onClick={handleSaveUsername}
                  disabled={usernameSaving || usernameStatus === "taken" || usernameStatus === "invalid" || usernameStatus === "checking" || !usernameInput || usernameInput.length < 4}
                >
                  {usernameSaving ? "Saving…" : "Save Handle"}
                </Button>
                {usernameSaved && <span className={s.savedTag}>✅ Saved</span>}
              </div>
              {usernameInput.length >= 4 && usernameStatus !== "idle" && (
                <div className={`${s.status} ${
                  usernameStatus === "checking" ? s.statusIdle :
                  usernameStatus === "available" ? s.statusOk : s.statusBad
                }`}>
                  {usernameStatus === "checking" && "⏳ Checking availability…"}
                  {usernameStatus === "available" && "✅ Available!"}
                  {(usernameStatus === "taken" || usernameStatus === "invalid") && `❌ ${usernameReason}`}
                </div>
              )}
              {usernameInput.length >= 4 && (
                <div className={s.urlPreview}>{window.location.origin}/u/{usernameInput}</div>
              )}
            </GlassCard>
          </div>

          <div className={s.settings}>
            <GlassCard padded glow>
              <div className={sh.title}>📬 Email Notifications Setup</div>
              <p className={s.settingsBody}>
                Set up your email to receive a final escalation reminder at 11:00 PM if you forget to log your DSA progress.
              </p>
              <div className={s.fieldRow}>
                <div className={s.inputGrow}>
                  <TextInput
                    type="email"
                    placeholder="your@email.com"
                    value={emailInput}
                    onChange={(e) => { setEmailInput(e.target.value); setEmailSaved(false); }}
                  />
                </div>
                <Button variant="primary" size="sm" onClick={handleSaveEmail} disabled={emailSaving}>
                  {emailSaving ? "Saving…" : "Save Email"}
                </Button>
                {emailSaved && <span className={s.savedTag}>✅ Saved</span>}
              </div>
            </GlassCard>
          </div>

          <div className={s.settings}>
            <GlassCard padded glow>
              <div className={sh.title}>🌍 Timezone Settings</div>
              <p className={s.settingsBody}>
                Set your local timezone so your streaks are calculated perfectly based on your midnight.
              </p>
              <div className={s.fieldRow}>
                <div className={s.inputGrow}>
                  <Select value={tzInput} onChange={(e) => { setTzInput(e.target.value); setTzSaved(false); }}>
                    <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                    <option value="America/New_York">America/New_York (EST)</option>
                    <option value="America/Los_Angeles">America/Los_Angeles (PST)</option>
                    <option value="Europe/London">Europe/London (GMT)</option>
                    <option value="UTC">UTC</option>
                  </Select>
                </div>
                <Button variant="primary" size="sm" onClick={handleSaveTz} disabled={tzSaving}>
                  {tzSaving ? "Saving…" : "Save Timezone"}
                </Button>
                {tzSaved && <span className={s.savedTag}>✅ Saved</span>}
              </div>
            </GlassCard>
          </div>
        </>
      )}
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
    <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "10px" }}>
      {rows.map((r) => {
        const pct = total > 0 ? (r.count / total) * 100 : 0;
        return (
          <div key={r.label}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "6px" }}>
              <span style={{ color: r.color, fontWeight: 600 }}>{r.label}</span>
              <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                {r.count} <span style={{ color: "var(--text-secondary)", fontSize: "0.74rem", fontWeight: 400 }}>({pct.toFixed(0)}%)</span>
              </span>
            </div>
            <div style={{ width: "100%", height: "8px", background: "var(--well-fill)", borderRadius: "999px", overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, height: "100%", background: r.color, borderRadius: "999px", transition: "width 0.5s ease" }} />
            </div>
          </div>
        );
      })}
      {d.unknown && d.unknown > 0 && (
        <div style={{ textAlign: "right", fontSize: "0.74rem", color: "var(--text-secondary)" }}>+ {d.unknown} unknown difficulty</div>
      )}
    </div>
  );
}