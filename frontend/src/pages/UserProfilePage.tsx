import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell, PieChart, Pie,
} from "recharts";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import { SkeletonCards, SkeletonChart, SkeletonRows } from "../components/Loader";
import { ErrorState, EmptyState } from "../components/EmptyState";
import Heatmap from "../components/Heatmap";

const COLORS = ["#6366f1", "#8b5cf6", "#10b981", "#f59e0b", "#0ea5e9", "#f43f5e", "#14b8a6", "#a855f7", "#ec4899", "#22d3ee"];

export default function UserProfilePage() {
  // Support both /users/:userId (legacy numeric) and /u/:identifier (vanity)
  const { userId, identifier } = useParams<{ userId?: string; identifier?: string }>();
  const nav = useNavigate();
  const uid = identifier || userId || "";
  const { user: authUser, authenticated, loading: authLoading } = useAuth();

  // A valid identifier is either a numeric Discord ID (17-21 digits) or a valid username string (2-20 chars, a-z0-9_)
  const validId = /^\d{17,21}$/.test(uid) || /^[a-z0-9_]{4,20}$/.test(uid);

  const user = useApi(() => api.user(uid), [uid], validId);
  const stats = useApi(() => api.userStats(uid), [uid], validId);
  const aggregate = useApi(() => api.dashboardAggregate(uid), [uid], validId);
  const heatmap = useApi(() => api.heatmap(uid), [uid], validId);
  const sums = useApi(() => api.summaries(uid), [uid], validId);

  // Once we have the actual user_id from the API response, use it for ownership checks
  const resolvedUserId = user.data?.user_id || "";

  // Wait for auth to resolve before computing ownership to avoid a flash
  const isOwner = !authLoading && authenticated && !!resolvedUserId && authUser?.id === resolvedUserId;
  // True when we know the viewer is definitely not the owner (auth settled)
  const isPublicGuest = !authLoading && !isOwner;

  // ── Email settings ──
  const [emailInput, setEmailInput] = useState("");
  const [emailSaving, setEmailSaving] = useState(false);
  const [emailSaved, setEmailSaved] = useState(false);

  // ── Timezone settings ──
  const [tzInput, setTzInput] = useState("Asia/Kolkata");
  const [tzSaving, setTzSaving] = useState(false);
  const [tzSaved, setTzSaved] = useState(false);

  // ── Username settings ──
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

  // ── Username availability check (debounced) ──
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
    // Force lowercase, strip invalid chars
    const cleaned = val.toLowerCase().replace(/[^a-z0-9_]/g, "").slice(0, 20);
    setUsernameInput(cleaned);
    setUsernameSaved(false);

    // If it matches the current username, show idle
    if (cleaned === (user.data?.username || "")) {
      setUsernameStatus("idle");
      setUsernameReason("");
      return;
    }

    // Debounce the availability check
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
      // Navigate to the new vanity URL
      nav(`/u/${usernameInput}`, { replace: true });
    } catch (e: any) {
      console.error(e);
      setUsernameStatus("taken");
      setUsernameReason(e.message || "Failed to save username.");
    }
    setUsernameSaving(false);
  };

  if (!validId) return (
    <EmptyState icon="⚠️" title="Invalid User" message={`The identifier "${uid}" is not valid.`} />
  );

  if (user.error) return <ErrorState message={user.error} onRetry={user.refetch} />;
  if (user.loading) return <SkeletonCards count={6} />;

  const u = user.data;
  const s = stats.data;
  const t = aggregate.data?.topics;
  const d = aggregate.data?.difficulty;

  if (!u) return <EmptyState icon="👤" title="User not found" />;

  const initials = (u.discord_username ?? "?").slice(0, 2).toUpperCase();

  return (
    <>
      {/* Back */}
      <button className="sort-tab" onClick={() => nav(-1)} style={{ marginBottom: 20 }}>← Back</button>

      <div className="profile-header" style={{ marginBottom: "24px" }}>
        <div className="profile-avatar">{initials}</div>
        <div className="profile-info">
          <h2 style={{ marginBottom: "4px" }}>{u.discord_username || `User ${u.user_id}`}</h2>
          <p style={{ color: "#94A3B8", fontSize: "0.9rem" }}>
            {u.username && (
              <span style={{ color: "#a78bfa", fontWeight: 600 }}>@{u.username} · </span>
            )}
            ID: {u.user_id} · Timezone: {u.timezone} · Joined: {u.created_at?.slice(0, 10) ?? "—"}
          </p>
          {isPublicGuest && (
            <span
              style={{
                marginTop: "10px",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "5px 14px",
                background: "linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15))",
                color: "#a5b4fc",
                borderRadius: "100px",
                fontSize: "0.78rem",
                fontWeight: 600,
                border: "1px solid rgba(99,102,241,0.3)",
                letterSpacing: "0.02em",
              }}
            >
              👁️ Viewing Public Profile
            </span>
          )}
        </div>
      </div>

      {/* ROW 1 — Stats Cards */}
      {stats.loading ? <SkeletonCards count={6} /> : s && (
        <div className="stats-grid" style={{ marginBottom: "24px" }}>
          <StatCard icon="🔥" value={s.current_streak} label="Current Streak" accent="emerald" />
          <StatCard icon="🏆" value={s.longest_streak} label="Longest Streak" accent="amber" />
          <StatCard icon="📈" value={`${s.consistency_pct}%`} label="Consistency" accent="indigo" />
          <StatCard icon="💬" value={s.total_messages} label="Total Questions" accent="sky" />
          <StatCard icon="📅" value={s.days_posted} label="Days Posted" accent="purple" />
          <StatCard icon={s.posted_today ? "✅" : "❌"} value={s.posted_today ? "Yes" : "No"} label="Posted Today" accent={s.posted_today ? "emerald" : "rose"} />
        </div>
      )}

      {/* ROW 2 — Annual Heatmap */}
      <Heatmap
        data={heatmap.data?.dates || {}}
        restDates={new Set(heatmap.data?.rest_dates || [])}
        activeDays={heatmap.data?.active_days || 0}
        currentStreak={heatmap.data?.current_streak || 0}
        maxStreak={heatmap.data?.max_streak || 0}
        loading={heatmap.loading}
      />

      {/* ROW 3 — Topic Distribution (Left) + Difficulty Distribution (Right) */}
      <div className="charts-grid" style={{ marginTop: "24px" }}>
        {/* Topic Pie Chart */}
        <div className="card">
          <div className="chart-title">📚 Topic Distribution</div>
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
                  contentStyle={{ background: "#0F0F1A", color: "#F8FAFC", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, fontSize: 13 }}
                  itemStyle={{ color: "#F8FAFC" }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState icon="📚" title="No topics yet" message="Start posting DSA progress to see topic analysis." />
          )}
        </div>

        {/* Difficulty Distribution */}
        <div className="card">
          <div className="chart-title">🎯 Difficulty Distribution</div>
          {aggregate.loading ? <SkeletonRows count={4} /> : d && (d.easy > 0 || d.medium > 0 || d.hard > 0 || (d.expert || 0) > 0) ? (
            (() => {
              const expertCount = d.expert || 0;
              const total = d.easy + d.medium + d.hard + expertCount;
              return (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "16px" }}>
                  {[
                    { label: "Easy", count: d.easy, color: "#10b981" },
                    { label: "Medium", count: d.medium, color: "#f59e0b" },
                    { label: "Hard", count: d.hard, color: "#f43f5e" },
                    { label: "Expert (CF 2000+)", count: expertCount, color: "#9f1239" },
                  ].map(item => {
                    const pct = total > 0 ? (item.count / total) * 100 : 0;
                    return (
                      <div key={item.label}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "6px" }}>
                          <span style={{ color: item.color, fontWeight: 500 }}>{item.label}</span>
                          <span style={{ fontWeight: 600 }}>{item.count} <span style={{ color: "#64748b", fontSize: "0.75rem", fontWeight: 400 }}>({pct.toFixed(0)}%)</span></span>
                        </div>
                        <div style={{ width: "100%", height: "8px", background: "rgba(255,255,255,0.05)", borderRadius: "4px", overflow: "hidden" }}>
                          <div style={{ width: `${pct}%`, height: "100%", background: item.color, borderRadius: "4px", transition: "width 0.5s ease" }} />
                        </div>
                      </div>
                    );
                  })}
                  {d.unknown > 0 && (
                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontSize: "0.75rem", color: "#64748b" }}>+ {d.unknown} unknown difficulty</span>
                    </div>
                  )}
                </div>
              );
            })()
          ) : (
            <EmptyState icon="🎯" title="No difficulty data" message="Log questions with difficulty to see distribution." />
          )}
        </div>
      </div>

      {/* ROW 4 — Topic Frequency Bar Chart (Full Width) */}
      <div className="card" style={{ marginTop: "24px" }}>
        <div className="chart-title">📊 Topic Frequency</div>
        {aggregate.loading ? <SkeletonChart /> : t && t.frequency.length > 0 ? (
          <ResponsiveContainer width="100%" height={Math.max(200, t.frequency.slice(0, 10).length * 34)}>
            <BarChart data={t.frequency.slice(0, 10)} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,.05)" />
              <XAxis type="number" tick={{ fill: "#94A3B8", fontSize: 11 }} />
              <YAxis type="category" dataKey="topic" width={130} tick={{ fill: "#F8FAFC", fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#0F0F1A", color: "#F8FAFC", border: "1px solid rgba(99,102,241,.2)", borderRadius: 12, fontSize: 13 }} itemStyle={{ color: "#F8FAFC" }} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]} name="Questions">
                {t.frequency.slice(0, 10).map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyState icon="📊" title="No data yet" message="Topic insights appear once you start logging." />
        )}
      </div>

      {/* ROW 5 — Weekly Summary History */}
      <div className="card" style={{ marginTop: "24px" }}>
        <div className="chart-title">📅 Weekly Summary History</div>
        {sums.loading ? <SkeletonRows count={5} /> : sums.data && sums.data.summaries.length > 0 ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Week</th>
                  <th>Posted</th>
                  <th>Missed</th>
                  <th>Consistency</th>
                  <th>Questions</th>
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
          <EmptyState icon="📅" title="No summaries yet" message="Weekly summaries appear after the first full week." />
        )}
      </div>

      {/* OWNER ONLY — Settings */}
      {isOwner && (
        <>
          {/* ── Claim Profile Handle ── */}
          <div className="card chart-container" style={{ marginTop: "24px" }}>
            <div className="chart-title">🔗 Claim Your Profile Handle</div>
            <div style={{ fontSize: ".88rem", color: "#94A3B8", marginBottom: "16px" }}>
              Choose a unique vanity URL for your profile. Only lowercase letters, numbers, and underscores (4–20 chars).
            </div>

            <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
              <div style={{ position: "relative", flexGrow: 1, maxWidth: "300px" }}>
                <input
                  id="username-input"
                  type="text"
                  placeholder="your_handle"
                  value={usernameInput}
                  onChange={(e) => handleUsernameChange(e.target.value)}
                  maxLength={20}
                  className="dsa-input"
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: `1px solid ${
                      usernameStatus === "available" ? "rgba(16,185,129,0.5)" :
                      usernameStatus === "taken" || usernameStatus === "invalid" ? "rgba(244,63,94,0.5)" :
                      "rgba(255,255,255,0.1)"
                    }`,
                    background: "rgba(0,0,0,0.2)",
                    color: "#fff",
                    transition: "border-color 0.2s ease",
                  }}
                />
              </div>
              <button
                id="save-username-btn"
                onClick={handleSaveUsername}
                disabled={usernameSaving || usernameStatus === "taken" || usernameStatus === "invalid" || usernameStatus === "checking" || !usernameInput || usernameInput.length < 4}
                className="dsa-btn dsa-btn-primary"
                style={{ padding: "8px 16px" }}
              >
                {usernameSaving ? "Saving..." : "Save Handle"}
              </button>
              {usernameSaved && <span style={{ color: "#10b981", fontSize: ".85rem", fontWeight: 600 }}>✅ Saved</span>}
            </div>

            {/* Status indicator */}
            {usernameInput.length >= 4 && usernameStatus !== "idle" && (
              <div style={{ marginTop: "8px", fontSize: ".82rem", fontWeight: 500 }}>
                {usernameStatus === "checking" && (
                  <span style={{ color: "#94A3B8" }}>⏳ Checking availability...</span>
                )}
                {usernameStatus === "available" && (
                  <span style={{ color: "#10b981" }}>✅ Available!</span>
                )}
                {(usernameStatus === "taken" || usernameStatus === "invalid") && (
                  <span style={{ color: "#f43f5e" }}>❌ {usernameReason}</span>
                )}
              </div>
            )}

            {/* Live URL preview */}
            {usernameInput.length >= 4 && (
              <div style={{
                marginTop: "12px",
                padding: "10px 14px",
                background: "rgba(99,102,241,0.08)",
                border: "1px solid rgba(99,102,241,0.2)",
                borderRadius: "8px",
                fontSize: ".84rem",
                color: "#a5b4fc",
                fontFamily: "monospace",
                letterSpacing: "0.02em",
              }}>
                {window.location.origin}/u/{usernameInput}
              </div>
            )}
          </div>

          {/* ── Email Notifications ── */}
          <div className="card chart-container" style={{ marginTop: "24px" }}>
            <div className="chart-title">📬 Email Notifications Setup</div>
            <div style={{ fontSize: ".88rem", color: "#94A3B8", marginBottom: "16px" }}>
              Set up your email to receive a final escalation reminder at 11:00 PM if you forget to log your DSA progress.
            </div>
            <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
              <input
                type="email"
                placeholder="your@email.com"
                value={emailInput}
                onChange={(e) => { setEmailInput(e.target.value); setEmailSaved(false); }}
                className="dsa-input"
                style={{ flexGrow: 1, maxWidth: "300px", padding: "8px 12px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.2)", color: "#fff" }}
              />
              <button
                onClick={handleSaveEmail}
                disabled={emailSaving}
                className="dsa-btn dsa-btn-primary"
                style={{ padding: "8px 16px" }}
              >
                {emailSaving ? "Saving..." : "Save Email"}
              </button>
              {emailSaved && <span style={{ color: "#10b981", fontSize: ".85rem", fontWeight: 600 }}>✅ Saved</span>}
            </div>
          </div>

          {/* ── Timezone ── */}
          <div className="card chart-container" style={{ marginTop: "20px" }}>
            <div className="chart-title">🌍 Timezone Settings</div>
            <div style={{ fontSize: ".88rem", color: "#94A3B8", marginBottom: "16px" }}>
              Set your local timezone so your streaks are calculated perfectly based on your midnight.
            </div>
            <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
              <select
                value={tzInput}
                onChange={(e) => { setTzInput(e.target.value); setTzSaved(false); }}
                className="dsa-input"
                style={{ flexGrow: 1, maxWidth: "300px", padding: "8px 12px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.1)", background: "rgba(0,0,0,0.2)", color: "#fff" }}
              >
                <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                <option value="America/New_York">America/New_York (EST)</option>
                <option value="America/Los_Angeles">America/Los_Angeles (PST)</option>
                <option value="Europe/London">Europe/London (GMT)</option>
                <option value="UTC">UTC</option>
              </select>
              <button
                onClick={handleSaveTz}
                disabled={tzSaving}
                className="dsa-btn dsa-btn-primary"
                style={{ padding: "8px 16px" }}
              >
                {tzSaving ? "Saving..." : "Save Timezone"}
              </button>
              {tzSaved && <span style={{ color: "#10b981", fontSize: ".85rem", fontWeight: 600 }}>✅ Saved</span>}
            </div>
          </div>
        </>
      )}
    </>
  );
}
