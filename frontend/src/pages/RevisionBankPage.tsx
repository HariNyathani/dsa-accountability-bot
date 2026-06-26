import { useState, useEffect, useCallback } from "react";
import { useRevisionBank, type RevisionItem } from "../hooks/useRevisionBank";
import GlassCard from "../components/GlassCard";
import LiquidCapsule from "../components/LiquidCapsule";
import Modal from "../components/Modal";
import Button from "../components/Button";
import StatCard from "../components/StatCard";
import { PageHeader } from "../components/Layout";
import sh from "../styles/shared.module.css";
import s from "./RevisionBankPage.module.css";

const TAB_ITEMS = [
  { key: "today", label: "Due Today", icon: "🎯" },
  { key: "progress", label: "Progress", icon: "📊" },
  { key: "all", label: "All Problems", icon: "📚" },
] as const;

type TabKey = (typeof TAB_ITEMS)[number]["key"];

function formatDaysRemaining(days?: number | null) {
  if (days === undefined || days === null) return "No review history";
  const rounded = Math.abs(Math.round(days));
  if (days < 0) return `Overdue by ${rounded} ${rounded === 1 ? "day" : "days"}`;
  if (Math.round(days) === 0) return "Due today";
  return `Due in ${rounded} ${rounded === 1 ? "day" : "days"}`;
}

function diffClass(diff: string): string {
  const l = (diff || "").toLowerCase();
  if (l === "easy") return s.diffEasy;
  if (l === "medium") return s.diffMedium;
  return s.diffHard;
}

function ProblemRow({
  item,
  onOpen,
}: {
  item: RevisionItem;
  onOpen: (i: RevisionItem) => void;
}) {
  const overdue = item.days_remaining !== undefined && item.days_remaining < 0;
  return (
    <div
      className={s.row}
      role="button"
      tabIndex={0}
      onClick={() => onOpen(item)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(item);
        }
      }}
      aria-label={`Open review for ${item.title}`}
    >
      <div className={s.rowMain}>
        <div className={s.rowTitle}>
          <span className={s.rowName}>#{item.problem_id} · {item.title}</span>
          <span className={`${s.diff} ${diffClass(item.difficulty || "medium")}`}>
            {item.difficulty || "medium"}
          </span>
          <span className={s.platform}>{item.platform || "LeetCode"}</span>
        </div>
        <div className={s.rowTopics}>{(item.topics || []).join(", ")}</div>
      </div>
      <div className={s.rowSide}>
        {"confidence_last" in item && (
          <div className={s.kv}>
            <span className={s.k}>Confidence</span>
            <span className={s.v}>{item.confidence_last} / 5</span>
          </div>
        )}
        <div className={s.kv}>
          <span className={s.k}>Time Left</span>
          <span className={`${s.v} ${overdue ? s.overdue : s.due}`}>
            {formatDaysRemaining(item.days_remaining)}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function RevisionBankPage() {
  const [currentTab, setCurrentTab] = useState<TabKey>("today");
  const [selectedProblem, setSelectedProblem] = useState<RevisionItem | null>(null);
  const {
    dueItems,
    allRevisionItems,
    topicStats,
    totalCount,
    page,
    setPage,
    limit,
    loading,
    error,
    refetch,
    submitReview,
  } = useRevisionBank();
  const totalPages = Math.max(1, Math.ceil(totalCount / limit));

  // Reset to page 1 when switching to the "progress" tab so the aggregate
  // stats (totalCount, topicStats) are always from page 1.
  useEffect(() => {
    if (currentTab === "progress") setPage(1);
  }, [currentTab, setPage]);

  const handleCloseModal = useCallback(() => setSelectedProblem(null), []);

  const handleReview = async (problemId: number, confidence: number) => {
    await submitReview(problemId, confidence);
    setSelectedProblem(null);
    // Refresh both lists: submitReview already re-fetches due items;
    // refetch() also refreshes the paged history.
    refetch();
  };

  const totalReviews = allRevisionItems.filter((i) => i.last_reviewed_at !== null).length;
  const avgConfidence =
    topicStats.length > 0
      ? (topicStats.reduce((a, c) => a + c.avg_confidence, 0) / topicStats.length).toFixed(1)
      : "0.0";

  return (
    <>
      <PageHeader
        title="Revision Bank"
        subtitle="Spaced Repetition System — Master your weak patterns"
        actions={
          <LiquidCapsule
            items={TAB_ITEMS}
            value={currentTab}
            onChange={(t) => setCurrentTab(t as TabKey)}
            variant="compact"
            layout="fit"
            aria-label="Revision view"
          />
        }
      />

      {error && <div className={s.error}>{error}</div>}

      {currentTab === "today" && (
        <GlassCard padded glow>
          <div className={sh.title}>🎯 Due Today</div>
          <div className={s.panel}>
            {loading && dueItems.length === 0 ? (
              <p className={s.muted}>Loading queue…</p>
            ) : dueItems.length === 0 ? (
              <div className={s.emptyCheer}>
                <div className={s.ic}>✨</div>
                <h3>Queue Cleared!</h3>
                <p>All caught up for today. Enjoy your rest or log new problems.</p>
              </div>
            ) : (
              dueItems.map((item) => (
                <ProblemRow key={item.revision_id} item={item} onOpen={setSelectedProblem} />
              ))
            )}
          </div>
        </GlassCard>
      )}

      {currentTab === "progress" && (
        <>
          <div className={s.metrics} style={{ marginBottom: 20 }}>
            <StatCard icon="📚" value={totalCount} label="Total Problems" accent="espresso" />
            <StatCard icon="🔄" value={totalReviews} label="Total Reviews" accent="slate" />
            <StatCard
              icon="⭐"
              value={`${avgConfidence} / 5`}
              label="Global Avg Confidence"
              accent="amber"
            />
          </div>

          <GlassCard padded glow>
            <div className={sh.title} style={{ marginBottom: 16 }}>Pattern Confidence</div>
            <div className={s.patternGrid}>
              {topicStats.map((stat) => (
                <div key={stat.topic} className={s.pattern}>
                  <span className={s.pl} title={stat.topic}>{stat.topic}</span>
                  <span
                    className={`${s.pc} ${
                      stat.avg_confidence >= 4 ? s.pcGood :
                      stat.avg_confidence >= 2.5 ? s.pcMid : s.pcBad
                    }`}
                  >
                    {stat.avg_confidence.toFixed(1)} <span className={s.pcMax}>/ 5</span>
                  </span>
                </div>
              ))}
              {topicStats.length === 0 && !loading && (
                <div style={{ gridColumn: "span 4" }} className={s.muted}>
                  No topic data available yet.
                </div>
              )}
            </div>
          </GlassCard>
        </>
      )}

      {currentTab === "all" && (
        <GlassCard padded glow>
          <div className={sh.title} style={{ marginBottom: 16 }}>📚 All Problems</div>
          <div className={s.panel}>
            {loading && allRevisionItems.length === 0 ? (
              <p className={s.muted}>Loading history…</p>
            ) : allRevisionItems.length === 0 ? (
              <p className={s.muted}>No problems in your revision bank yet.</p>
            ) : (
              allRevisionItems.map((item) => (
                <ProblemRow key={item.revision_id} item={item} onOpen={setSelectedProblem} />
              ))
            )}
          </div>

          <div className={s.pager}>
            <Button variant="ghost" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
              ← Prev
            </Button>
            <span className={s.pageInfo}>
              Page <b>{page}</b> / {totalPages}
            </span>
            <Button variant="ghost" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages}>
              Next →
            </Button>
          </div>
        </GlassCard>
      )}

      <Modal
        open={!!selectedProblem}
        onClose={handleCloseModal}
        title={selectedProblem ? `#${selectedProblem.problem_id} · ${selectedProblem.title}` : ""}
      >
        {selectedProblem && (
          <div className={s.modalBody}>
            <div className={s.rowTitle} style={{ gap: 10 }}>
              <span style={{ fontSize: 16 }}>{selectedProblem.platform === "LeetCode" ? "🔌" : "📝"}</span>
              <span className={s.platform}>{selectedProblem.platform || "LeetCode"}</span>
              <span className={`${s.diff} ${diffClass(selectedProblem.difficulty || "medium")}`}>
                {selectedProblem.difficulty || "medium"}
              </span>
              <span className={s.rowTopics}>{(selectedProblem.topics || []).join(", ")}</span>
            </div>

            <div className={s.metaPanel}>
              <div className={s.metaRow}>
                <span className={s.mk}>Total Times Revised</span>
                <span className={s.mv}>
                  {(selectedProblem as any).review_count ||
                    (selectedProblem.last_reviewed_at ? 1 : 0)}
                </span>
              </div>
              <div className={s.metaRow}>
                <span className={s.mk}>Last Revised</span>
                <span className={s.mv}>
                  {selectedProblem.last_reviewed_at
                    ? new Date(selectedProblem.last_reviewed_at).toLocaleDateString()
                    : "Never reviewed"}
                </span>
              </div>
              <div className={s.metaRow}>
                <span className={s.mk}>Time Left</span>
                <span
                  className={s.mv}
                  style={{
                    color:
                      selectedProblem.days_remaining !== undefined && selectedProblem.days_remaining < 0
                        ? "var(--diff-hard)"
                        : "var(--diff-easy)",
                  }}
                >
                  {formatDaysRemaining(selectedProblem.days_remaining)}
                </span>
              </div>
            </div>

            <div>
              <div className={s.confLabel}>Rate your confidence</div>
              <div className={s.confGrid}>
                {[1, 2, 3, 4, 5].map((score) => {
                  const labels = ["", "Forgot", "Hard", "Okay", "Good", "Mastered"];
                  return (
                    <button
                      key={score}
                      className={s.confBtn}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleReview(selectedProblem.problem_id, score);
                      }}
                    >
                      <span className={s.confNum}>{score}</span>
                      <span className={s.confTxt}>{labels[score]}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </>
  );
}