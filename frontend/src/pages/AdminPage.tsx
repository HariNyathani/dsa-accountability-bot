import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";
import { api } from "../services/api";
import GlassCard from "../components/GlassCard";
import LiquidCapsule from "../components/LiquidCapsule";
import Button from "../components/Button";
import { Select, TextInput } from "../components/Field";
import { SkeletonRows } from "../components/Loader";
import sh from "../styles/shared.module.css";
import s from "./AdminPage.module.css";

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

const TAB_ITEMS = [
  { key: "users", label: "User Metrics", icon: "👥" },
  { key: "sudo", label: "Sudo Operations", icon: "⚡" },
  { key: "system", label: "System Hub", icon: "🖥️" },
] as const;

export default function AdminPage() {
  const { user: authUser } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>("users");

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersError, setUsersError] = useState<string | null>(null);

  const [sudoUserId, setSudoUserId] = useState("");
  const [sudoTopic, setSudoTopic] = useState("");
  const [sudoCount, setSudoCount] = useState(1);
  const [sudoDiff, setSudoDiff] = useState("Medium");
  const [sudoLoading, setSudoLoading] = useState(false);
  const [sudoResult, setSudoResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const [undoUserId, setUndoUserId] = useState("");
  const [undoLoading, setUndoLoading] = useState(false);
  const [undoResult, setUndoResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const [restUserId, setRestUserId] = useState("");
  const [restLoading, setRestLoading] = useState(false);
  const [restResult, setRestResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryResult, setSummaryResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [healthData, setHealthData] = useState<any>(null);

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
      await api.adminSudoRestDay(restUserId);
      setRestResult({
        ok: true,
        msg: `Rest day logged for ${users.find((u) => u.user_id === restUserId)?.discord_username || restUserId}`,
      });
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

  return (
    <>
      <div className={s.adminHead}>
        <div>
          <h1 className={s.adminTitle}>🔐 Admin Control Panel</h1>
          <p className={s.adminSub}>
            Logged in as <strong>@{authUser?.username}</strong> · Root Access
          </p>
        </div>
        <span className={s.adminPill}>Admin V3.5</span>
      </div>

      <div style={{ marginBottom: 24 }}>
        <LiquidCapsule
          items={TAB_ITEMS}
          value={activeTab}
          onChange={(t) => setActiveTab(t as TabId)}
          variant="compact"
          layout="fit"
          aria-label="Admin section"
        />
      </div>

      {activeTab === "users" && (
        <GlassCard padded glow>
          <div className={`${sh.title} ${s.titleRow}`}>
            <span>👥 Registered Users ({users.length})</span>
            <Button variant="ghost" size="sm" onClick={fetchUsers} disabled={usersLoading}>
              {usersLoading ? "Loading…" : "🔄 Refresh"}
            </Button>
          </div>
          {usersError ? (
            <p style={{ color: "var(--diff-hard)", padding: "16px 0" }}>{usersError}</p>
          ) : usersLoading ? (
            <SkeletonRows count={6} />
          ) : (
            <div className={sh.tableWrap}>
              <table className={sh.table}>
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
                        <a href={`/users/${u.user_id}`} className={sh.username} style={{ color: "var(--link)" }}>
                          {u.discord_username || "Unknown"}
                        </a>
                      </td>
                      <td style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "var(--text-secondary)" }}>{u.user_id}</td>
                      <td style={{ fontWeight: 800, color: u.current_streak > 0 ? "var(--diff-easy)" : "var(--text-secondary)" }}>{u.current_streak}</td>
                      <td className={sh.bold}>{u.longest_streak}</td>
                      <td>{u.total_questions}</td>
                      <td>
                        <div className={sh.consBar}>
                          <span className={sh.bold} style={{ minWidth: 42 }}>{u.consistency_pct}%</span>
                          <div className={sh.track}>
                            <div
                              className={sh.fill}
                              style={{
                                width: `${u.consistency_pct}%`,
                                background: u.consistency_pct >= 80 ? "var(--diff-easy)" : u.consistency_pct >= 50 ? "var(--diff-medium)" : "var(--diff-hard)",
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`${s.dot} ${u.posted_today ? s.dotOn : ""}`} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassCard>
      )}

      {activeTab === "sudo" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <GlassCard padded glow>
            <div className={sh.title}>⚡ Sudo-Log — Insert Progress Entry</div>
            <p className={s.helpText}>
              Force-insert a structured qdone entry on behalf of any registered user.
            </p>
            <div className={s.formGrid}>
              <div className={s.span}>
                <Select value={sudoUserId} onChange={(e) => setSudoUserId(e.target.value)}>
                  <option value="">Select a user…</option>
                  {users.map((u) => (
                    <option key={u.user_id} value={u.user_id}>
                      {u.discord_username || u.user_id} ({u.user_id})
                    </option>
                  ))}
                </Select>
              </div>
              <TextInput
                type="text"
                placeholder="Topic"
                label="Topic"
                value={sudoTopic}
                onChange={(e) => setSudoTopic(e.target.value)}
              />
              <TextInput
                type="number"
                min={1}
                max={50}
                label="Count"
                value={sudoCount}
                onChange={(e) => setSudoCount(Number(e.target.value) || 1)}
              />
              <Select label="Difficulty" value={sudoDiff} onChange={(e) => setSudoDiff(e.target.value)}>
                <option value="Easy">Easy</option>
                <option value="Medium">Medium</option>
                <option value="Hard">Hard</option>
                <option value="Expert">Expert</option>
              </Select>
            </div>
            <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <Button variant="primary" onClick={handleSudoLog} disabled={sudoLoading || !sudoUserId || !sudoTopic}>
                {sudoLoading ? "Logging…" : "⚡ Execute Sudo-Log"}
              </Button>
              {sudoResult && (
                <AdminResult ok={sudoResult.ok} msg={sudoResult.msg} />
              )}
            </div>
          </GlassCard>

          <GlassCard padded glow className={s.stripe}>
            <div className={`${sh.title} ${s.stripeTitle}`}>
              <span className={s.stripeBadge}>🛌</span>
              Emergency Rest Day Override
            </div>
            <p className={s.helpText}>
              Log a rest day on behalf of a user to preserve their streak without requiring problem completion.
              Subject to the same monthly limit (4/month) enforced by the backend.
            </p>
            <div className={s.formRow}>
              <div style={{ flex: 1, maxWidth: 280 }}>
                <Select
                  value={restUserId}
                  onChange={(e) => { setRestUserId(e.target.value); setRestResult(null); }}
                >
                  <option value="">Select a user…</option>
                  {users.map((u) => (
                    <option key={u.user_id} value={u.user_id}>
                      {u.discord_username || u.user_id} ({u.user_id})
                    </option>
                  ))}
                </Select>
              </div>
              <Button
                id="btn-emergency-rest-day"
                onClick={handleRestDay}
                disabled={restLoading || !restUserId}
              >
                {restLoading ? "Logging…" : "🛌 Log Emergency Rest Day"}
              </Button>
            </div>
            {restResult && (
              <div className={`${s.toast} ${restResult.ok ? s.toastOk : s.toastBad}`}>
                <span>{restResult.ok ? "✅" : "❌"}</span>
                {restResult.msg}
              </div>
            )}
          </GlassCard>

          <GlassCard padded glow>
            <div className={sh.title}>⏪ Undo — Revert Latest Entry</div>
            <p className={s.helpText}>
              Deletes the most recent progress log for the target user and recalculates their streak.
            </p>
            <div className={s.formRow}>
              <div style={{ flex: 1, maxWidth: 280 }}>
                <Select value={undoUserId} onChange={(e) => setUndoUserId(e.target.value)}>
                  <option value="">Select a user…</option>
                  {users.map((u) => (
                    <option key={u.user_id} value={u.user_id}>
                      {u.discord_username || u.user_id} ({u.user_id})
                    </option>
                  ))}
                </Select>
              </div>
              <Button variant="danger" onClick={handleUndo} disabled={undoLoading || !undoUserId}>
                {undoLoading ? "Reverting…" : "⏪ Undo Last Entry"}
              </Button>
              {undoResult && <AdminResult ok={undoResult.ok} msg={undoResult.msg} />}
            </div>
          </GlassCard>
        </div>
      )}

      {activeTab === "system" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
          <GlassCard padded glow>
            <div className={sh.title}>🟢 System Health</div>
            <div className={s.healthGrid}>
              <div className={s.healthBox}>
                <div className={s.hl}>API Status</div>
                <div className={s.hv} style={{ color: "var(--diff-easy)" }}>{healthData ? "Online" : "Checking…"}</div>
              </div>
              <div className={s.healthBox}>
                <div className={s.hl}>Database</div>
                <div className={s.hv} style={{ color: healthData?.database === "connected" ? "var(--diff-easy)" : "var(--diff-medium)" }}>
                  {healthData?.database ?? "—"}
                </div>
              </div>
              <div className={s.healthBox}>
                <div className={s.hl}>Uptime</div>
                <div className={s.hv}>{healthData?.uptime_formatted ?? "—"}</div>
              </div>
              <div className={s.healthBox}>
                <div className={s.hl}>Users Tracked</div>
                <div className={s.hv}>{String(users.length)}</div>
              </div>
            </div>
          </GlassCard>

          <GlassCard padded glow>
            <div className={sh.title}>📊 Force Weekly Summary</div>
            <p className={s.helpText}>
              Manually trigger weekly summary computation for all registered users.
            </p>
            <div className={s.formRow}>
              <Button variant="primary" onClick={() => handleForceSummary(false)} disabled={summaryLoading}>
                {summaryLoading ? "Running…" : "📊 Compute Summaries"}
              </Button>
              <Button variant="ghost" onClick={() => handleForceSummary(true)} disabled={summaryLoading}>
                {summaryLoading ? "Running…" : "📤 Compute + Broadcast to Discord"}
              </Button>
              {summaryResult && <AdminResult ok={summaryResult.ok} msg={summaryResult.msg} />}
            </div>
          </GlassCard>
        </div>
      )}
    </>
  );
}

function AdminResult({ ok, msg }: { ok: boolean; msg: string }) {
  return (
    <span className={`${s.result} ${ok ? s.resultOk : s.resultBad}`}>
      {ok ? "✅" : "❌"} {msg}
    </span>
  );
}