import { useState } from "react";
import { api } from "../services/api";

const COMMON_TOPICS = [
  "arrays", "sliding window", "strings", "linked lists", "stacks", "queues",
  "hashing", "recursion", "sorting", "binary search", "trees", "heaps",
  "graphs", "dynamic programming", "greedy", "bit manipulation"
];

type LogMode = "manual" | "platform";
type Platform = "leetcode" | "codeforces" | "codechef";

const PLATFORMS: { id: Platform; label: string; icon: string; enabled: boolean }[] = [
  { id: "leetcode", label: "LeetCode", icon: "🟠", enabled: true },
  { id: "codeforces", label: "Codeforces", icon: "🔵", enabled: true },
  { id: "codechef", label: "CodeChef", icon: "⭐", enabled: false },
];

export default function QuickLogCard({ onLogSuccess }: { onLogSuccess: () => void }) {
  // ── Shared state ──────────────────────────────────────────
  const [mode, setMode] = useState<LogMode>("manual");
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // ── Manual log state ──────────────────────────────────────

  const [topic, setTopic] = useState("");
  const [countText, setCountText] = useState("1");
  const [difficulty, setDifficulty] = useState("None");
  const [note, setNote] = useState("");

  // ── Platform log state ────────────────────────────────────
  const [platform, setPlatform] = useState<Platform>("leetcode");
  const [problemId, setProblemId] = useState("");
  const [confidence, setConfidence] = useState<number | null>(3);

  // ── Manual submit (unchanged logic) ───────────────────────
  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      setFeedback({ type: "error", message: "Please enter or select a topic." });
      return;
    }

    setLoading(true);
    setFeedback(null);

    try {
      const res = await api.logProgress({
        intent_type: "done",
        topics: [{
          canonical_topic: topic.toLowerCase().trim(),
          question_count: parseInt(countText) || 1,
          difficulty: difficulty !== "None" ? difficulty : undefined
        }],
        note: note.trim() || undefined,
      });

      if ((res as any).error) {
        setFeedback({ type: "error", message: (res as any).error });
      } else {
        const d = res as any;
        if (d.msg_type === "skipped") {
          setFeedback({ type: "error", message: "This exact progress was already logged today." });
        } else {
          setFeedback({ type: "success", message: `✅ Successfully logged ${parseInt(countText) || 1} ${topic} questions!` });
          setTopic("");
          setCountText("1");
          setDifficulty("None");
          setNote("");
          onLogSuccess();
          setTimeout(() => setFeedback(null), 4000);
        }
      }
    } catch (err: any) {
      setFeedback({ type: "error", message: err.message || "Failed to log progress" });
    } finally {
      setLoading(false);
    }
  };

  const handleLogRest = async () => {
    setLoading(true);
    setFeedback(null);
    try {
      const res = await api.logRestDay();
      if ((res as any).error) {
        setFeedback({ type: "error", message: (res as any).error });
      } else {
        setFeedback({ type: "success", message: "Rest Day Logged. See you tomorrow, legend!" });
        onLogSuccess();
        setTimeout(() => setFeedback(null), 4000);
      }
    } catch (err: any) {
      setFeedback({ type: "error", message: err.message || "Failed to log rest day" });
    } finally {
      setLoading(false);
    }
  };

  // ── Platform submit ───────────────────────────────────────
  const handlePlatformSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!problemId.trim()) {
      setFeedback({ type: "error", message: "Please enter a problem ID or URL." });
      return;
    }

    setLoading(true);
    setFeedback(null);

    try {
      const res = await api.logPlatformProblem({
        platform,
        problem_identifier: problemId.trim(),
        confidence: platform.toLowerCase() === 'leetcode' ? confidence : null,
      });

      const data = (res as any).data || res;

      const title = data.title || "Unknown";
      const diff = data.difficulty || "";
      const topics = data.topics || [];

      const diffBadge = diff ? ` [${diff}]` : "";
      const topicsStr = topics.length > 0 ? ` (${topics.join(", ")})` : "";

      setFeedback({
        type: "success",
        message: `✅ Logged: ${title}${diffBadge}${topicsStr}`,
      });
      setProblemId("");
      onLogSuccess();
      setTimeout(() => setFeedback(null), 6000);
    } catch (err: any) {
      setFeedback({ type: "error", message: err.message || "Failed to log platform problem" });
    } finally {
      setLoading(false);
    }
  };

  // ── Shared styles ─────────────────────────────────────────
  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "10px", borderRadius: "8px",
    background: "rgba(0, 0, 0, 0.2)", border: "1px solid rgba(255, 255, 255, 0.1)",
    color: "#fff", fontSize: "0.95rem",
  };

  const labelStyle: React.CSSProperties = {
    display: "block", fontSize: "0.8rem", color: "#94A3B8", marginBottom: "6px",
  };

  return (
    <div className="card quick-log-card">
      <div className="chart-title" style={{ marginBottom: "1rem" }}>⚡ Quick Log</div>

      {/* ── Mode Tabs ── */}
      <div className="ql-mode-tabs" style={{ display: "flex", gap: "4px", marginBottom: "16px", background: "rgba(0,0,0,0.2)", borderRadius: "10px", padding: "4px", border: "1px solid rgba(255,255,255,0.05)" }}>
        <button
          type="button"
          className={`ql-mode-tab ${mode === "manual" ? "active" : ""}`}
          onClick={() => { setMode("manual"); setFeedback(null); setConfidence(3); }}
          style={{
            flex: 1, padding: "9px 4px", borderRadius: "8px", fontSize: "0.85rem", fontWeight: 600,
            background: mode === "manual" ? "rgba(99, 102, 241, 0.15)" : "transparent",
            color: mode === "manual" ? "#818cf8" : "#64748b",
            border: mode === "manual" ? "1px solid rgba(99, 102, 241, 0.25)" : "1px solid transparent",
            cursor: "pointer", transition: "all 0.25s ease",
          }}
        >
          ✏️ Manual Log
        </button>
        <button
          type="button"
          className={`ql-mode-tab ${mode === "platform" ? "active" : ""}`}
          onClick={() => { setMode("platform"); setFeedback(null); setConfidence(3); }}
          style={{
            flex: 1, padding: "9px 4px", borderRadius: "8px", fontSize: "0.85rem", fontWeight: 600,
            background: mode === "platform" ? "rgba(245, 158, 11, 0.15)" : "transparent",
            color: mode === "platform" ? "#fcd34d" : "#64748b",
            border: mode === "platform" ? "1px solid rgba(245, 158, 11, 0.25)" : "1px solid transparent",
            cursor: "pointer", transition: "all 0.25s ease",
          }}
        >
          🌐 Platform Log
        </button>
      </div>

      {/* ── Feedback Banner ── */}
      {feedback && (
        <div className="ql-feedback" style={{
          padding: "10px 14px",
          borderRadius: 8,
          marginBottom: 16,
          fontSize: "0.9rem",
          background: feedback.type === "success" ? "rgba(16, 185, 129, 0.1)" : "rgba(244, 63, 94, 0.1)",
          color: feedback.type === "success" ? "#10b981" : "#f43f5e",
          border: `1px solid ${feedback.type === "success" ? "rgba(16, 185, 129, 0.2)" : "rgba(244, 63, 94, 0.2)"}`,
          animation: "fadeInDown 0.3s ease",
        }}>
          {feedback.message}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          MANUAL LOG MODE (existing functionality, preserved exactly)
          ═══════════════════════════════════════════════════════════ */}
      {mode === "manual" && (
        <form onSubmit={handleManualSubmit}>
          <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
            <button
              type="button"
              style={{
                flex: 1, padding: "10px 4px", borderRadius: "6px", fontSize: "0.85rem",
                fontWeight: 600,
                background: "rgba(99, 102, 241, 0.15)",
                color: "#818cf8",
                border: "1px solid rgba(99, 102, 241, 0.3)",
                cursor: "default",
              }}
            >
              ✅ Done Today
            </button>
            <button
              type="button"
              style={{
                flex: 1, padding: "10px 4px", borderRadius: "6px", fontSize: "0.85rem",
                fontWeight: 600,
                background: "transparent",
                color: "#94A3B8",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                cursor: loading ? "not-allowed" : "pointer", transition: "all 0.2s",
                opacity: loading ? 0.5 : 1
              }}
              onClick={handleLogRest}
              disabled={loading}
            >
              🛌 Rest Day
            </button>
          </div>

          <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
            <div style={{ flex: 2 }}>
              <label style={labelStyle}>Topic</label>
              <input
                type="text"
                value={topic}
                onChange={e => setTopic(e.target.value)}
                placeholder="e.g. Arrays"
                list="topic-options"
                required
                style={inputStyle}
              />
              <datalist id="topic-options">
                {COMMON_TOPICS.map(t => <option key={t} value={t} />)}
              </datalist>
            </div>

            <div style={{ flex: 1.2 }}>
              <label style={labelStyle}>Difficulty</label>
              <select
                value={difficulty}
                onChange={e => setDifficulty(e.target.value)}
                style={{
                  width: "100%", padding: "10px", borderRadius: "8px",
                  background: "rgba(0, 0, 0, 0.2)", border: "1px solid rgba(255, 255, 255, 0.1)",
                  color: "#fff", fontSize: "0.95rem"
                }}
              >
                <option value="None">None</option>
                <option value="Easy">Easy</option>
                <option value="Medium">Medium</option>
                <option value="Hard">Hard</option>
              </select>
            </div>

            <div style={{ flex: 1 }}>
              <label style={labelStyle}>Questions</label>
              <input
                type="number"
                min="1"
                value={countText}
                onChange={e => setCountText(e.target.value)}
                required
                style={inputStyle}
              />
            </div>
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label style={labelStyle}>Note (Optional)</label>
            <input
              type="text"
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="Any extra context?"
              style={inputStyle}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%", padding: "12px", borderRadius: "8px",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#fff", border: "none", fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1, transition: "opacity 0.2s"
            }}
          >
            {loading ? "Logging..." : "Log Progress"}
          </button>
        </form>
      )}

      {/* ═══════════════════════════════════════════════════════════
          PLATFORM LOG MODE (new feature)
          ═══════════════════════════════════════════════════════════ */}
      {mode === "platform" && (
        <form onSubmit={handlePlatformSubmit}>
          {/* Platform Selector */}
          <div style={{ marginBottom: "16px" }}>
            <label style={labelStyle}>Platform</label>
            <div style={{ display: "flex", gap: "8px" }}>
              {PLATFORMS.map(p => (
                <button
                  key={p.id}
                  type="button"
                  disabled={!p.enabled}
                  onClick={() => p.enabled && setPlatform(p.id)}
                  style={{
                    flex: 1,
                    padding: "10px 6px",
                    borderRadius: "8px",
                    fontSize: "0.83rem",
                    fontWeight: 600,
                    background: platform === p.id && p.enabled
                      ? "rgba(245, 158, 11, 0.12)"
                      : !p.enabled
                        ? "rgba(255,255,255,0.02)"
                        : "rgba(0, 0, 0, 0.15)",
                    color: platform === p.id && p.enabled
                      ? "#fcd34d"
                      : !p.enabled
                        ? "#3e4255"
                        : "#94A3B8",
                    border: platform === p.id && p.enabled
                      ? "1px solid rgba(245, 158, 11, 0.3)"
                      : "1px solid rgba(255, 255, 255, 0.08)",
                    cursor: p.enabled ? "pointer" : "not-allowed",
                    transition: "all 0.2s",
                    opacity: p.enabled ? 1 : 0.55,
                    position: "relative",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "4px",
                  }}
                >
                  <span style={{ fontSize: "1.1rem" }}>{p.icon}</span>
                  <span>{p.label}</span>
                  {!p.enabled && (
                    <span style={{
                      fontSize: "0.6rem",
                      fontWeight: 700,
                      color: "#64748b",
                      background: "rgba(255,255,255,0.05)",
                      padding: "1px 6px",
                      borderRadius: "4px",
                      letterSpacing: "0.04em",
                      textTransform: "uppercase",
                    }}>
                      Soon
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Problem Input */}
          <div style={{ marginBottom: "20px" }}>
            <label style={labelStyle}>Problem ID or URL</label>
            <input
              type="text"
              value={problemId}
              onChange={e => setProblemId(e.target.value)}
              placeholder={
                platform === "codeforces"
                  ? "e.g., 1189A or codeforces.com/contest/1189/problem/A"
                  : "e.g. 1, two-sum, or leetcode.com/problems/two-sum"
              }
              required
              style={{
                ...inputStyle,
                borderColor: problemId.trim() ? "rgba(245, 158, 11, 0.25)" : "rgba(255,255,255,0.1)",
              }}
            />
            <div style={{
              marginTop: "6px",
              fontSize: "0.73rem",
              color: "#555e77",
              lineHeight: 1.5,
            }}>
              Accepts: Problem number • Title slug • Full URL
            </div>
          </div>

          {platform === 'leetcode' && (
            <div style={{ marginTop: '1rem', marginBottom: '1rem' }}>
              <label className="chart-title" style={{ display: 'block', marginBottom: '0.5rem' }}>
                Confidence Rating (SRS Selection)
              </label>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {[1, 2, 3, 4, 5].map((score) => (
                  <button
                    key={score}
                    type="button"
                    onClick={() => setConfidence(score)}
                    className={`card ${confidence === score ? 'active' : ''}`}
                    style={{
                      flex: 1,
                      padding: '0.5rem',
                      textAlign: 'center',
                      backgroundColor: confidence === score ? 'var(--accent, #6366f1)' : 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      cursor: 'pointer',
                      color: '#fff',
                      borderRadius: '6px',
                      margin: 0
                    }}
                  >
                    {score}
                  </button>
                ))}
              </div>
              <span style={{ fontSize: '0.8rem', color: '#aaa', display: 'block', marginTop: '0.25rem' }}>
                {confidence === 1 && '1 - Completely Forgot'}
                {confidence === 2 && '2 - Hard / Barely Remember'}
                {confidence === 3 && '3 - Okay / Needs Revision'}
                {confidence === 4 && '4 - Good / Highly Confident'}
                {confidence === 5 && '5 - Mastered / Perfect'}
              </span>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !problemId.trim()}
            style={{
              width: "100%",
              padding: "12px",
              borderRadius: "8px",
              background: loading || !problemId.trim()
                ? "rgba(245, 158, 11, 0.15)"
                : "linear-gradient(135deg, #f59e0b, #d97706)",
              color: loading || !problemId.trim() ? "#a8852e" : "#fff",
              border: "none",
              fontWeight: 600,
              fontSize: "0.95rem",
              cursor: loading || !problemId.trim() ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
              transition: "all 0.25s ease",
              boxShadow: !loading && problemId.trim() ? "0 4px 16px rgba(245, 158, 11, 0.2)" : "none",
            }}
          >
            {loading ? (
              <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                <span className="ql-spinner" />
                Resolving...
              </span>
            ) : (
              "🚀 Log Problem"
            )}
          </button>
        </form>
      )}
    </div>
  );
}
