import { useState } from "react";
import { api } from "../services/api";
import GlassCard from "./GlassCard";
import LiquidCapsule from "./LiquidCapsule";
import Button from "./Button";
import { TextInput, Select } from "./Field";
import { motion, AnimatePresence } from "motion/react";
import { quickSpring } from "../styles/springs";
import s from "./QuickLogCard.module.css";

const COMMON_TOPICS = [
  "arrays", "sliding window", "strings", "linked lists", "stacks", "queues",
  "hashing", "recursion", "sorting", "binary search", "trees", "heaps",
  "graphs", "dynamic programming", "greedy", "bit manipulation",
];

type LogMode = "manual" | "platform";
type Platform = "leetcode" | "codeforces" | "codechef";

const PLATFORMS: { id: Platform; label: string; icon: string; enabled: boolean }[] = [
  { id: "leetcode", label: "LeetCode", icon: "🟠", enabled: true },
  { id: "codeforces", label: "Codeforces", icon: "🔵", enabled: true },
  { id: "codechef", label: "CodeChef", icon: "⭐", enabled: false },
];

const MODE_ITEMS = [
  { key: "manual", label: "✏️ Manual", icon: "" },
  { key: "platform", label: "🌐 Platform", icon: "" },
] as const;

const CONF_LABELS: Record<number, string> = {
  1: "1 — Completely Forgot",
  2: "2 — Hard / Barely Remember",
  3: "3 — Okay / Needs Revision",
  4: "4 — Good / Highly Confident",
  5: "5 — Mastered / Perfect",
};

export default function QuickLogCard({ onLogSuccess }: { onLogSuccess: () => void }) {
  const [mode, setMode] = useState<LogMode>("manual");
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // ── Manual log state ──
  const [intent, setIntent] = useState<"done" | "rest">("done");
  const [topic, setTopic] = useState("");
  const [countText, setCountText] = useState("1");
  const [difficulty, setDifficulty] = useState("None");
  const [note, setNote] = useState("");

  // ── Platform log state ──
  const [platform, setPlatform] = useState<Platform>("leetcode");
  const [problemId, setProblemId] = useState("");
  const [confidence, setConfidence] = useState<number | null>(3);

  // ── Manual submit (preserved logic) ──
  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (intent === "rest") {
      await handleLogRest();
      return;
    }
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
          difficulty: difficulty !== "None" ? difficulty : undefined,
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

  // ── Platform submit (preserved logic) ──
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
        confidence: platform.toLowerCase() === "leetcode" ? confidence : null,
      });
      const data = (res as any).data || res;
      const title = data.title || "Unknown";
      const diff = data.difficulty || "";
      const topics = data.topics || [];
      const diffBadge = diff ? ` [${diff}]` : "";
      const topicsStr = topics.length > 0 ? ` (${topics.join(", ")})` : "";
      setFeedback({ type: "success", message: `✅ Logged: ${title}${diffBadge}${topicsStr}` });
      setProblemId("");
      onLogSuccess();
      setTimeout(() => setFeedback(null), 6000);
    } catch (err: any) {
      setFeedback({ type: "error", message: err.message || "Failed to log platform problem" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <GlassCard padded glow className={s.wrap}>
      <div className={s.title}>⚡ Quick Log</div>

      <div className={s.tabsWrap}>
        <LiquidCapsule
          items={MODE_ITEMS}
          value={mode}
          onChange={(m) => { setMode(m as LogMode); setFeedback(null); setConfidence(3); }}
          variant="compact"
          layout="stretch"
          aria-label="Log mode"
        />
      </div>

      <AnimatePresence>
        {feedback && (
          <motion.div
            key={feedback.message + feedback.type}
            className={`${s.feedback} ${feedback.type === "success" ? s.feedbackOk : s.feedbackBad}`}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={quickSpring}
          >
            {feedback.message}
          </motion.div>
        )}
      </AnimatePresence>

      {mode === "manual" && (
        <form onSubmit={handleManualSubmit}>
          <div className={s.intent}>
            <button
              type="button"
              className={s.intentChip}
              data-active={intent === "done"}
              onClick={() => setIntent("done")}
            >
              ✅ Done Today
            </button>
            <button
              type="button"
              className={s.intentChip}
              data-active={intent === "rest"}
              onClick={() => setIntent("rest")}
              disabled={loading}
            >
              🛌 Rest Day
            </button>
          </div>

          {intent === "done" && (
            <>
              <div className={s.row}>
                <div className={s.colTopic}>
                  <TextInput
                    label="Topic"
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. Arrays"
                    list="topic-options"
                    required
                  />
                  <datalist id="topic-options">
                    {COMMON_TOPICS.map((t) => <option key={t} value={t} />)}
                  </datalist>
                </div>
                <div className={s.colDiff}>
                  <Select label="Difficulty" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                    <option value="None">None</option>
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </Select>
                </div>
                <div className={s.colCount}>
                  <TextInput
                    label="Questions"
                    type="number"
                    min="1"
                    value={countText}
                    onChange={(e) => setCountText(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className={s.field}>
                <TextInput
                  label="Note (Optional)"
                  type="text"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Any extra context?"
                />
              </div>
            </>
          )}

          <Button
            type="submit"
            variant="primary"
            block
            disabled={loading}
          >
            {loading ? "Logging…" : intent === "rest" ? "🛌 Log Rest Day" : "Log Progress"}
          </Button>
        </form>
      )}

      {mode === "platform" && (
        <form onSubmit={handlePlatformSubmit}>
          <div className={s.platforms}>
            {PLATFORMS.map((p) => (
              <button
                key={p.id}
                type="button"
                className={s.platformBtn}
                data-active={platform === p.id && p.enabled ? "true" : "false"}
                data-disabled={p.enabled ? "false" : "true"}
                disabled={!p.enabled}
                onClick={() => p.enabled && setPlatform(p.id)}
              >
                <span className={s.platformIcon}>{p.icon}</span>
                <span>{p.label}</span>
                {!p.enabled && <span className={s.soon}>Soon</span>}
              </button>
            ))}
          </div>

          <div className={s.field}>
            <TextInput
              label="Problem ID or URL"
              type="text"
              value={problemId}
              onChange={(e) => setProblemId(e.target.value)}
              placeholder={
                platform === "codeforces"
                  ? "e.g., 1189A or codeforces.com/contest/1189/problem/A"
                  : "e.g. 1, two-sum, or leetcode.com/problems/two-sum"
              }
              required
            />
            <div className={s.hint}>Accepts: Problem number • Title slug • Full URL</div>
          </div>

          {platform === "leetcode" && (
            <div className={s.confSection}>
              <span className={s.title} style={{ fontSize: "0.95rem", marginBottom: 0 }}>
                Confidence Rating (SRS Selection)
              </span>
              <div className={s.confGrid}>
                {[1, 2, 3, 4, 5].map((score) => (
                  <button
                    key={score}
                    type="button"
                    className={s.confBtn}
                    data-active={confidence === score ? "true" : "false"}
                    onClick={() => setConfidence(score)}
                  >
                    {score}
                  </button>
                ))}
              </div>
              <span className={s.confHint}>{confidence ? CONF_LABELS[confidence] : ""}</span>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            block
            disabled={loading || !problemId.trim()}
          >
            {loading ? "Resolving…" : "🚀 Log Problem"}
          </Button>
        </form>
      )}
    </GlassCard>
  );
}