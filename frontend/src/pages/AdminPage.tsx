/* ──────────────────────────────────────────────────────────────────────────
   AdminPage — Administrative Control Panel.

   Features:
   • User Metrics Table: handles, streaks, totals, posted-today status
   • Sudo-Log Module:    structured form to insert progress for any user
   • Undo Module:        revert latest entry for a targeted user
   • System Hub:         force-summary button, health status indicator
   ────────────────────────────────────────────────────────────────────────── */

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../services/api";

type AdminUser = {
  user_id: string;
  discord_username: string | null;
  is_active: boolean;
  current_streak: number;
  longest_streak: number;
  total_questions: number;
  consistency_pct: number;
  posted_today: boolean;
};

type TabId = "users" | "sudo" | "system";

export default function AdminPage() {
  const { user: authUser } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>("users");

  // ── User table state ────────────────────────────────────────────────
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersError, setUsersError] = useState<string | null>(null);

  // ── Sudo-log state ──────────────────────────────────────────────────
  const [sudoUserId, setSudoUserId] = useState("");
  const [sudoTopic, setSudoTopic] = useState("");
  const [sudoCount, setSudoCount] = useState(1);
  const [sudoDiff, setSudoDiff] = useState("Medium");
  const [sudoLoading, setSudoLoading] = useState(false);
  const [sudoResult, setSudoResult] = useState<{ ok: boolean; msg: string } | null>(null);

  // ── Undo state ──────────────────────────────────────────────────────
  const [undoUserId, setUndoUserId] = useState("");
  const [undoLoading, setUndoLoading] = useState(false);
  const [undoResult, setUndoResult] = useState<{ ok: boolean; msg: string } | null>(null);

  // ── Rest-day override state ─────────────────────────────────────────
  const [restUserId, setRestUserId] = useState("");
  const [restLoading, setRestLoading] = useState(false);
  const [restResult, setRestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  // ── System hub state ────────────────────────────────────────────────
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryResult, setSummaryResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [healthData, setHealthData] = useState<any>(null);

  // ── Fetch users ─────────────────────────────────────────────────────
  const fetchUsers = useCallback(async () => {
    setUsersLoading(true);
    setUsersError(null);
    try {
      const res = await api.adminUsers();
      setUsers(res.data.users || []);
    } catch (e: any) {
      setUsersError(e.message || "Failed to load users");
    } finally {
      setUsersLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
    api.health().then((r) => setHealthData(r.data)).catch(() => {});
  }, [fetchUsers]);

  // ── Handlers ────────────────────────────────────────────────────────
  const handleSudoLog = async () => {
    if (!sudoUserId || !sudoTopic) return;
    setSudoLoading(true);
    setSudoResult(null);
    try {
      const res = await api.adminSudoLog({
        user_id: sudoUserId,
        topic: sudoTopic,
        count: sudoCount,
        difficulty: sudoDiff,
      });
      setSudoResult({ ok: true, msg: res.data.message });
      fetchUsers();
    } catch (e: any) {
      setSudoResult({ ok: false, msg: e.message || "Sudo-log failed" });
    } finally {
      setSudoLoading(false);
    }
  };

  const handleUndo = async () => {
    if (!undoUserId) return;
    setUndoLoading(true);
    setUndoResult(null);
    try {
      const res = await api.adminUndo(undoUserId);
      setUndoResult({ ok: true, msg: res.data.message });
      fetchUsers();
    } catch (e: any) {
      setUndoResult({ ok: false, msg: e.message || "Undo failed" });
    } finally {
      setUndoLoading(false);
    }
  };

  const handleRestDay = async () => {
    if (!restUserId) return;
    setRestLoading(true);
    setRestResult(null);
    try {
      const res = await api.adminSudoRestDay(restUserId);
      setRestResult({ ok: true, msg: `Rest day logged successfully for user ${users.find(u => u.user_id === restUserId)?.discord_username || restUserId}` });
      fetchUsers();
    } catch (e: any) {
      setRestResult({ ok: false, msg: e.message || "Rest day override failed" });
    } finally {
      setRestLoading(false);
    }
  };

  const handleForceSummary = async (broadcast: boolean) => {
    setSummaryLoading(true);
    setSummaryResult(null);
    try {
      const res = await api.adminForceSummary(broadcast);
      setSummaryResult({ ok: true, msg: res.data.message });
    } catch (e: any) {
      setSummaryResult({ ok: false, msg: e.message || "Summary generation failed" });
    } finally {
      setSummaryLoading(false);
    }
  };

  // ── Tabs config ─────────────────────────────────────────────────────
  const tabs: { id: TabId; icon: string; label: string }[] = [
    { id: "users", icon: "👥", label: "User Metrics" },
    { id: "sudo", icon: "⚡", label: "Sudo Operations" },
    { id: "system", icon: "🖥️", label: "System Hub" },
  ];

  return (
    <>
      {/* Admin Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginBottom: "24px",
        flexWrap: "wrap",
        gap: "12px",
      }}>
        <div>
          <h1 style={{
            fontSize: "1.6rem",
            fontWeight: 800,
            background: "linear-gradient(135deg, #f59e0b, #ef4444)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            marginBottom: "4px",
          }}>
            🔐 Admin Control Panel
          </h1>
          <p style={{ color: "#64748b", fontSize: "0.85rem" }}>
            Logged in as <strong style={{ color: "#f59e0b" }}>@{authUser?.username}</strong> · Root Access
          </p>
        </div>
        <span style={{
          padding: "6px 16px",
          background: "rgba(239,68,68,0.1)",
          border: "1px solid rgba(239,68,68,0.25)",
          borderRadius: "100px",
          fontSize: "0.75rem",
          fontWeight: 700,
          color: "#ef4444",
          letterSpacing: "0.05em",
          textTransform: "uppercase",
        }}>
          Admin V3.5
        </span>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "24px", flexWrap: "wrap" }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className="sort-tab"
            style={{
              background: activeTab === t.id
                ? "linear-gradient(135deg, rgba(245,158,11,0.15), rgba(239,68,68,0.15))"
                : undefined,
              borderColor: activeTab === t.id ? "rgba(245,158,11,0.4)" : undefined,
              color: activeTab === t.id ? "#f59e0b" : undefined,
              fontWeight: activeTab === t.id ? 700 : undefined,
            }}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ═══════ USERS TAB ═══════ */}
      {activeTab === "users" && (
        <div className="card">
          <div className="chart-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>👥 Registered Users ({users.length})</span>
            <button
              className="sort-tab"
              onClick={fetchUsers}
              disabled={usersLoading}
              style={{ fontSize: "0.75rem", padding: "4px 12px" }}
            >
              {usersLoading ? "Loading…" : "🔄 Refresh"}
            </button>
          </div>
          {usersError ? (
            <p style={{ color: "#f43f5e", padding: "16px" }}>{usersError}</p>
          ) : (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>ID</th>
                    <th>🔥 Streak</th>
                    <th>🏆 Longest</th>
                    <th>💬 Questions</th>
                    <th>📈 Consistency</th>
                    <th>Today</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.user_id}>
                      <td>
                        <a href={`/users/${u.user_id}`} style={{ color: "#818cf8", fontWeight: 600, textDecoration: "none" }}>
                          {u.discord_username || "Unknown"}
                        </a>
                      </td>
                      <td style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "#64748b" }}>{u.user_id}</td>
                      <td style={{ fontWeight: 700, color: u.current_streak > 0 ? "#10b981" : "#64748b" }}>{u.current_streak}</td>
                      <td style={{ fontWeight: 600 }}>{u.longest_streak}</td>
                      <td>{u.total_questions}</td>
                      <td>
                        <div className="consistency-bar">
                          <span style={{ fontWeight: 600, minWidth: 42 }}>{u.consistency_pct}%</span>
                          <div className="bar-track">
                            <div className="bar-fill" style={{
                              width: `${u.consistency_pct}%`,
                              background: u.consistency_pct >= 80 ? "#10b981" : u.consistency_pct >= 50 ? "#f59e0b" : "#f43f5e",
                            }} />
                          </div>
                        </div>
                      </td>
                      <td>
                        <span style={{
                          display: "inline-block",
                          width: "10px",
                          height: "10px",
                          borderRadius: "50%",
                          background: u.posted_today ? "#10b981" : "#f43f5e",
                          boxShadow: u.posted_today ? "0 0 6px rgba(16,185,129,0.5)" : "0 0 6px rgba(244,63,94,0.3)",
                        }} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ═══════ SUDO OPERATIONS TAB ═══════ */}
      {activeTab === "sudo" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Sudo-Log Card */}
          <div className="card">
            <div className="chart-title">⚡ Sudo-Log — Insert Progress Entry</div>
            <p style={{ fontSize: "0.85rem", color: "#94A3B8", marginBottom: "16px" }}>
              Force-insert a structured qdone entry on behalf of any registered user.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", maxWidth: "500px" }}>
              <div style={{ gridColumn: "1 / -1" }}>
                <label style={labelStyle}>Target User ID</label>
                <select
                  value={sudoUserId}
                  onChange={(e) => setSudoUserId(e.target.value)}
                  style={selectStyle}
                >
                  <option value="" style={optionStyle}>Select a user…</option>
                  {users.map((u) => (
                    <option key={u.user_id} value={u.user_id} style={optionStyle}>
                      {u.discord_username || u.user_id} ({u.user_id})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Topic</label>
                <input
                  type="text"
                  placeholder="arrays, dp, graphs…"
                  value={sudoTopic}
                  onChange={(e) => setSudoTopic(e.target.value)}
                  style={inputStyle}
                />
              </div>
              <div>
                <label style={labelStyle}>Count</label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={sudoCount}
                  onChange={(e) => setSudoCount(Number(e.target.value) || 1)}
                  style={inputStyle}
                />
              </div>
              <div>
                <label style={labelStyle}>Difficulty</label>
                <select value={sudoDiff} onChange={(e) => setSudoDiff(e.target.value)} style={selectStyle}>
                  <option value="Easy" style={optionStyle}>Easy</option>
                  <option value="Medium" style={optionStyle}>Medium</option>
                  <option value="Hard" style={optionStyle}>Hard</option>
                  <option value="Expert" style={optionStyle}>Expert</option>
                </select>
              </div>
            </div>

            <div style={{ marginTop: "16px", display: "flex", alignItems: "center", gap: "12px" }}>
              <button
                className="dsa-btn dsa-btn-primary"
                onClick={handleSudoLog}
                disabled={sudoLoading || !sudoUserId || !sudoTopic}
                style={{ padding: "8px 20px" }}
              >
                {sudoLoading ? "Logging…" : "⚡ Execute Sudo-Log"}
              </button>
              {sudoResult && (
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: sudoResult.ok ? "#10b981" : "#f43f5e" }}>
                  {sudoResult.ok ? "✅" : "❌"} {sudoResult.msg}
                </span>
              )}
            </div>
          </div>

          {/* Emergency Rest Day Card */}
          <div className="card" style={{ position: "relative", overflow: "hidden" }}>
            {/* Accent glow stripe */}
            <div style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: "3px",
              background: "linear-gradient(90deg, #6366f1, #a78bfa, #818cf8)",
              borderRadius: "12px 12px 0 0",
            }} />
            <div className="chart-title" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: "28px",
                height: "28px",
                borderRadius: "8px",
                background: "rgba(99,102,241,0.15)",
                fontSize: "1rem",
              }}>🛌</span>
              Emergency Rest Day Override
            </div>
            <p style={{ fontSize: "0.85rem", color: "#94A3B8", marginBottom: "16px" }}>
              Log a rest day on behalf of a user to preserve their streak without requiring problem completion.
              Subject to the same monthly limit (4/month) enforced by the backend.
            </p>

            <div style={{ display: "flex", gap: "12px", alignItems: "flex-end", flexWrap: "wrap" }}>
              <div>
                <label style={labelStyle}>Target User</label>
                <select
                  value={restUserId}
                  onChange={(e) => { setRestUserId(e.target.value); setRestResult(null); }}
                  style={{ ...selectStyle, minWidth: "220px" }}
                >
                  <option value="" style={optionStyle}>Select a user…</option>
                  {users.map((u) => (
                    <option key={u.user_id} value={u.user_id} style={optionStyle}>
                      {u.discord_username || u.user_id} ({u.user_id})
                    </option>
                  ))}
                </select>
              </div>
              <button
                id="btn-emergency-rest-day"
                onClick={handleRestDay}
                disabled={restLoading || !restUserId}
                style={{
                  padding: "10px 24px",
                  borderRadius: "10px",
                  border: "1px solid rgba(99,102,241,0.35)",
                  background: restLoading
                    ? "rgba(99,102,241,0.15)"
                    : "linear-gradient(135deg, #6366f1, #8b5cf6)",
                  color: "#fff",
                  fontWeight: 700,
                  fontSize: "0.88rem",
                  cursor: restLoading || !restUserId ? "not-allowed" : "pointer",
                  opacity: !restUserId ? 0.5 : 1,
                  transition: "all 0.2s ease",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  boxShadow: restLoading ? "none" : "0 4px 14px rgba(99,102,241,0.3)",
                }}
              >
                {restLoading ? (
                  <>
                    <span style={{
                      display: "inline-block",
                      width: "14px",
                      height: "14px",
                      border: "2px solid rgba(255,255,255,0.3)",
                      borderTopColor: "#fff",
                      borderRadius: "50%",
                      animation: "spin 0.6s linear infinite",
                    }} />
                    Logging…
                  </>
                ) : (
                  <>🛌 Log Emergency Rest Day</>
                )}
              </button>
            </div>

            {/* Toast result */}
            {restResult && (
              <div style={{
                marginTop: "14px",
                padding: "10px 16px",
                borderRadius: "10px",
                background: restResult.ok ? "rgba(16,185,129,0.08)" : "rgba(244,63,94,0.08)",
                border: `1px solid ${restResult.ok ? "rgba(16,185,129,0.25)" : "rgba(244,63,94,0.25)"}`,
                fontSize: "0.85rem",
                fontWeight: 600,
                color: restResult.ok ? "#10b981" : "#f43f5e",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}>
                <span style={{ fontSize: "1.1rem" }}>{restResult.ok ? "✅" : "❌"}</span>
                {restResult.msg}
              </div>
            )}
          </div>

          {/* Undo Card */}
          <div className="card">
            <div className="chart-title">⏪ Undo — Revert Latest Entry</div>
            <p style={{ fontSize: "0.85rem", color: "#94A3B8", marginBottom: "16px" }}>
              Deletes the most recent progress log for the target user and recalculates their streak.
            </p>

            <div style={{ display: "flex", gap: "12px", alignItems: "flex-end", flexWrap: "wrap" }}>
              <div>
                <label style={labelStyle}>Target User ID</label>
                <select
                  value={undoUserId}
                  onChange={(e) => setUndoUserId(e.target.value)}
                  style={{ ...selectStyle, minWidth: "220px" }}
                >
                  <option value="" style={optionStyle}>Select a user…</option>
                  {users.map((u) => (
                    <option key={u.user_id} value={u.user_id} style={optionStyle}>
                      {u.discord_username || u.user_id} ({u.user_id})
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="dsa-btn dsa-btn-primary"
                onClick={handleUndo}
                disabled={undoLoading || !undoUserId}
                style={{
                  padding: "8px 20px",
                  background: "linear-gradient(135deg, #f59e0b, #ef4444)",
                }}
              >
                {undoLoading ? "Reverting…" : "⏪ Undo Last Entry"}
              </button>
              {undoResult && (
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: undoResult.ok ? "#10b981" : "#f43f5e" }}>
                  {undoResult.ok ? "✅" : "❌"} {undoResult.msg}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══════ SYSTEM HUB TAB ═══════ */}
      {activeTab === "system" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* System Health */}
          <div className="card">
            <div className="chart-title">🟢 System Health</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", marginTop: "12px" }}>
              <HealthBox label="API Status" value={healthData ? "Online" : "Checking…"} color="#10b981" />
              <HealthBox label="Database" value={healthData?.database ?? "—"} color={healthData?.database === "connected" ? "#10b981" : "#f59e0b"} />
              <HealthBox label="Uptime" value={healthData?.uptime_formatted ?? "—"} color="#6366f1" />
              <HealthBox label="Users Tracked" value={String(users.length)} color="#8b5cf6" />
            </div>
          </div>

          {/* Force Summary */}
          <div className="card">
            <div className="chart-title">📊 Force Weekly Summary</div>
            <p style={{ fontSize: "0.85rem", color: "#94A3B8", marginBottom: "16px" }}>
              Manually trigger weekly summary computation for all registered users.
            </p>
            <div style={{ display: "flex", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
              <button
                className="dsa-btn dsa-btn-primary"
                onClick={() => handleForceSummary(false)}
                disabled={summaryLoading}
                style={{ padding: "8px 20px" }}
              >
                {summaryLoading ? "Running…" : "📊 Compute Summaries"}
              </button>
              <button
                className="dsa-btn dsa-btn-primary"
                onClick={() => handleForceSummary(true)}
                disabled={summaryLoading}
                style={{
                  padding: "8px 20px",
                  background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                }}
              >
                {summaryLoading ? "Running…" : "📤 Compute + Broadcast to Discord"}
              </button>
              {summaryResult && (
                <span style={{ fontSize: "0.85rem", fontWeight: 600, color: summaryResult.ok ? "#10b981" : "#f43f5e" }}>
                  {summaryResult.ok ? "✅" : "❌"} {summaryResult.msg}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}


// ── Inline helpers ──────────────────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: "0.78rem",
  fontWeight: 600,
  color: "#94A3B8",
  marginBottom: "4px",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(255,255,255,0.1)",
  background: "rgba(0,0,0,0.2)",
  color: "#F8FAFC",
  fontSize: "0.9rem",
};

// Selects need a SOLID dark background — the OS-rendered dropdown panel ignores
// alpha transparency and falls back to white, making options invisible.
const selectStyle: React.CSSProperties = {
  ...inputStyle,
  background: "#0f172a",
  border: "1px solid rgba(99,102,241,0.3)",
  cursor: "pointer",
  appearance: "none" as const,
  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2394A3B8' d='M6 8L1 3h10z'/%3E%3C/svg%3E")`,
  backgroundRepeat: "no-repeat",
  backgroundPosition: "right 12px center",
  paddingRight: "36px",
};

const optionStyle: React.CSSProperties = {
  background: "#0f172a",
  color: "#F8FAFC",
};

function HealthBox({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      padding: "14px 16px",
      borderRadius: "12px",
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.06)",
    }}>
      <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "6px" }}>
        {label}
      </div>
      <div style={{ fontSize: "1rem", fontWeight: 700, color }}>
        {value}
      </div>
    </div>
  );
}
