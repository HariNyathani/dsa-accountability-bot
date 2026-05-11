import { useState } from "react";
import { api } from "../services/api";

const COMMON_TOPICS = [
  "arrays", "sliding window", "strings", "linked lists", "stacks", "queues",
  "hashing", "recursion", "sorting", "binary search", "trees", "heaps",
  "graphs", "dynamic programming", "greedy", "bit manipulation"
];

export default function QuickLogCard({ onLogSuccess }: { onLogSuccess: () => void }) {
  const [intent, setIntent] = useState<"done" | "plan">("done");
  const [topic, setTopic] = useState("");
  const [countText, setCountText] = useState("1");
  const [difficulty, setDifficulty] = useState("None");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) {
      setFeedback({ type: "error", message: "Please enter or select a topic." });
      return;
    }

    setLoading(true);
    setFeedback(null);

    try {
      const res = await api.logProgress({
        intent_type: intent,
        topics: [{ 
          canonical_topic: topic.toLowerCase().trim(), 
          question_count: parseInt(countText) || 1,
          difficulty: intent === "done" && difficulty !== "None" ? difficulty : undefined
        }],
        note: note.trim() || undefined,
      });

      if ((res as any).error) {
        setFeedback({ type: "error", message: (res as any).error });
      } else {
        const d = res as any; // Cast since the type might not fully cover skipped
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

  return (
    <div className="card quick-log-card">
      <div className="chart-title" style={{ marginBottom: "1rem" }}>⚡ Quick Log</div>
      
      {feedback && (
        <div style={{
          padding: "10px 14px",
          borderRadius: 8,
          marginBottom: 16,
          fontSize: "0.9rem",
          background: feedback.type === "success" ? "rgba(16, 185, 129, 0.1)" : "rgba(244, 63, 94, 0.1)",
          color: feedback.type === "success" ? "#10b981" : "#f43f5e",
          border: `1px solid ${feedback.type === "success" ? "rgba(16, 185, 129, 0.2)" : "rgba(244, 63, 94, 0.2)"}`
        }}>
          {feedback.message}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ display: "flex", gap: "10px", marginBottom: "16px" }}>
          <button
            type="button"
            style={{
              flex: 1, padding: "8px", borderRadius: "6px",
              background: intent === "done" ? "rgba(99, 102, 241, 0.15)" : "transparent",
              color: intent === "done" ? "#818cf8" : "#94A3B8",
              border: `1px solid ${intent === "done" ? "rgba(99, 102, 241, 0.3)" : "rgba(255, 255, 255, 0.1)"}`,
              cursor: "pointer", transition: "all 0.2s"
            }}
            onClick={() => setIntent("done")}
          >
            ✅ Done Today
          </button>
          <button
            type="button"
            style={{
              flex: 1, padding: "8px", borderRadius: "6px",
              background: intent === "plan" ? "rgba(245, 158, 11, 0.15)" : "transparent",
              color: intent === "plan" ? "#fcd34d" : "#94A3B8",
              border: `1px solid ${intent === "plan" ? "rgba(245, 158, 11, 0.3)" : "rgba(255, 255, 255, 0.1)"}`,
              cursor: "pointer", transition: "all 0.2s"
            }}
            onClick={() => setIntent("plan")}
          >
            📋 Plan Tomorrow
          </button>
        </div>

        <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
          <div style={{ flex: 2 }}>
            <label style={{ display: "block", fontSize: "0.8rem", color: "#94A3B8", marginBottom: "6px" }}>Topic</label>
            <input
              type="text"
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="e.g. Arrays"
              list="topic-options"
              required
              style={{
                width: "100%", padding: "10px", borderRadius: "8px",
                background: "rgba(0, 0, 0, 0.2)", border: "1px solid rgba(255, 255, 255, 0.1)",
                color: "#fff", fontSize: "0.95rem"
              }}
            />
            <datalist id="topic-options">
              {COMMON_TOPICS.map(t => <option key={t} value={t} />)}
            </datalist>
          </div>
          
          <div style={{ flex: 1.2 }}>
            <label style={{ display: "block", fontSize: "0.8rem", color: "#94A3B8", marginBottom: "6px" }}>Difficulty</label>
            <select
              value={difficulty}
              onChange={e => setDifficulty(e.target.value)}
              disabled={intent !== "done"}
              style={{
                width: "100%", padding: "10px", borderRadius: "8px",
                background: "rgba(0, 0, 0, 0.2)", border: "1px solid rgba(255, 255, 255, 0.1)",
                color: intent === "done" ? "#fff" : "#64748b", fontSize: "0.95rem"
              }}
            >
              <option value="None">None</option>
              <option value="Easy">Easy</option>
              <option value="Medium">Medium</option>
              <option value="Hard">Hard</option>
            </select>
          </div>

          <div style={{ flex: 1 }}>
            <label style={{ display: "block", fontSize: "0.8rem", color: "#94A3B8", marginBottom: "6px" }}>Questions</label>
            <input
              type="number"
              min="1"
              value={countText}
              onChange={e => setCountText(e.target.value)}
              required
              style={{
                width: "100%", padding: "10px", borderRadius: "8px",
                background: "rgba(0, 0, 0, 0.2)", border: "1px solid rgba(255, 255, 255, 0.1)",
                color: "#fff", fontSize: "0.95rem"
              }}
            />
          </div>
        </div>

        <div style={{ marginBottom: "20px" }}>
          <label style={{ display: "block", fontSize: "0.8rem", color: "#94A3B8", marginBottom: "6px" }}>Note (Optional)</label>
          <input
            type="text"
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="Any extra context?"
            style={{
              width: "100%", padding: "10px", borderRadius: "8px",
              background: "rgba(0, 0, 0, 0.2)", border: "1px solid rgba(255, 255, 255, 0.1)",
              color: "#fff", fontSize: "0.95rem"
            }}
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
          {loading ? "Logging..." : (intent === "done" ? "Log Progress" : "Save Plan")}
        </button>
      </form>
    </div>
  );
}
