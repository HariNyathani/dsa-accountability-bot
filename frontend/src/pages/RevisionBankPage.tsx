import React, { useState, useEffect } from 'react';
import { useRevisionBank, RevisionItem } from '../hooks/useRevisionBank';

const formatDaysRemaining = (days?: number | null) => {
  if (days === undefined || days === null) return "No review history";
  const rounded = Math.abs(Math.round(days));
  if (days < 0) {
    return `Overdue by ${rounded} ${rounded === 1 ? 'day' : 'days'}`;
  } else if (Math.round(days) === 0) {
    return "Due today";
  } else {
    return `Due in ${rounded} ${rounded === 1 ? 'day' : 'days'}`;
  }
};

export default function RevisionBankPage() {
  const [currentTab, setCurrentTab] = useState<'today' | 'progress' | 'all'>('today');
  const [selectedProblem, setSelectedProblem] = useState<RevisionItem | null>(null);
  
  const {
    dueItems,
    allRevisionItems,
    topicStats,
    totalCount,
    loading,
    error,
    fetchDueItems,
    fetchPagedHistory,
    submitReview
  } = useRevisionBank();

  const [page, setPage] = useState(1);
  const limit = 10;
  const totalPages = Math.max(1, Math.ceil(totalCount / limit));

  useEffect(() => {
    if (currentTab === 'today') {
      fetchDueItems();
    } else if (currentTab === 'progress') {
      fetchPagedHistory(1, limit);
    } else if (currentTab === 'all') {
      fetchPagedHistory(page, limit);
    }
  }, [currentTab, page, fetchDueItems, fetchPagedHistory]);

  const handleReview = async (problemId: number, confidence: number) => {
    await submitReview(problemId, confidence);
    setSelectedProblem(null);
    // Trigger global data cache invalidation to recalculate stats
    fetchPagedHistory(1, limit);
    fetchDueItems();
  };

  const renderDifficultyBadge = (diff: string) => {
    const l = diff.toLowerCase();
    const bg = l === 'easy' ? 'rgba(16, 185, 129, 0.15)' : 
               l === 'medium' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)';
    const color = l === 'easy' ? '#10b981' : 
                  l === 'medium' ? '#f59e0b' : '#ef4444';
    return (
      <span style={{ 
        background: bg, color: color, padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', textTransform: 'uppercase'
      }}>
        {diff}
      </span>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <h2>Revision Bank</h2>
        <p>Spaced Repetition System — Master your weak patterns</p>
      </div>

      {error && (
        <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.4)', color: '#ef4444', padding: '12px 16px', borderRadius: '8px' }}>
          {error}
        </div>
      )}

      {/* Segmented Control */}
      <div style={{ display: 'flex', gap: '8px', background: 'var(--bg-card)', padding: '6px', borderRadius: '12px', border: '1px solid var(--border)', width: 'fit-content' }}>
        {(['today', 'progress', 'all'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setCurrentTab(tab)}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '14px',
              textTransform: 'capitalize',
              transition: 'all 0.2s',
              background: currentTab === tab ? 'var(--accent)' : 'transparent',
              color: currentTab === tab ? '#fff' : 'var(--text-secondary)'
            }}
          >
            {tab === 'today' ? '🎯 Due Today' : tab === 'progress' ? '📊 Progress' : '📚 All Problems'}
          </button>
        ))}
      </div>

      {/* Today Sub-panel */}
      {currentTab === 'today' && (
        <div className="card">
          <div className="chart-title">🎯 Due Today</div>
          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {loading && dueItems.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>Loading queue...</p>
            ) : dueItems.length === 0 ? (
              <div style={{ padding: '40px', textAlign: 'center' }}>
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>✨</div>
                <h3 style={{ color: '#fff', marginBottom: '8px' }}>Queue Cleared!</h3>
                <p style={{ color: 'var(--text-secondary)' }}>All caught up for today. Enjoy your rest or log new problems.</p>
              </div>
            ) : (
              dueItems.map(item => (
                <div 
                  key={item.revision_id} 
                  className="card"
                  onClick={() => setSelectedProblem(item)}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', cursor: 'pointer', transition: 'transform 0.2s', border: '1px solid rgba(255,255,255,0.05)', margin: 0 }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '15px' }}>#{item.problem_id} - {item.title}</span>
                      {renderDifficultyBadge(item.difficulty || 'medium')}
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                        {item.platform || 'LeetCode'}
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--accent-light)' }}>
                      {(item.topics || []).join(', ')}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'center', textAlign: 'right' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', minWidth: '100px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Time Left</span>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: item.days_remaining !== undefined && item.days_remaining < 0 ? '#ef4444' : '#10b981' }}>
                        {formatDaysRemaining(item.days_remaining)}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Progress Sub-panel */}
      {currentTab === 'progress' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Top Metrics Row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <div className="card stat-card" data-accent="indigo" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '24px' }}>📚</div>
              <div style={{ fontSize: '28px', fontWeight: 800, color: '#fff' }}>{totalCount}</div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Total Problems</div>
            </div>
            <div className="card stat-card" data-accent="emerald" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '24px' }}>🔄</div>
              <div style={{ fontSize: '28px', fontWeight: 800, color: '#fff' }}>
                {allRevisionItems.filter(i => i.last_reviewed_at !== null).length}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Total Reviews</div>
            </div>
            <div className="card stat-card" data-accent="amber" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '24px' }}>⭐</div>
              <div style={{ fontSize: '28px', fontWeight: 800, color: '#fff' }}>
                {topicStats.length > 0 
                  ? (topicStats.reduce((acc, curr) => acc + curr.avg_confidence, 0) / topicStats.length).toFixed(1)
                  : '0.0'} <span style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>/ 5</span>
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Global Avg Confidence</div>
            </div>
          </div>

          {/* The 16-Pattern Grid Canvas */}
          <div className="card">
            <div className="chart-title" style={{ marginBottom: '16px' }}>Pattern Confidence</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
              {topicStats.map(stat => (
                <div key={stat.topic} style={{ 
                  background: 'rgba(255,255,255,0.03)', 
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span style={{ fontSize: '13px', color: '#e2e8f0', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '120px' }}>
                    {stat.topic}
                  </span>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: stat.avg_confidence >= 4 ? '#10b981' : stat.avg_confidence >= 2.5 ? '#f59e0b' : '#ef4444' }}>
                    {stat.avg_confidence.toFixed(1)} <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500 }}>/ 5</span>
                  </span>
                </div>
              ))}
              {topicStats.length === 0 && !loading && (
                <div style={{ gridColumn: 'span 4', color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>
                  No topic data available yet.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* All Problems Ledger */}
      {currentTab === 'all' && (
        <div className="card" style={{ paddingBottom: '0' }}>
          <div className="chart-title" style={{ marginBottom: '16px' }}>📚 All Problems</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {loading && allRevisionItems.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>Loading history...</p>
            ) : allRevisionItems.length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>No problems in your revision bank yet.</p>
            ) : (
              allRevisionItems.map(item => (
                <div 
                  key={item.revision_id} 
                  className="card"
                  onClick={() => setSelectedProblem(item)}
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', cursor: 'pointer', border: '1px solid rgba(255,255,255,0.05)', margin: 0 }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 600, color: '#f8fafc', fontSize: '15px' }}>#{item.problem_id} - {item.title}</span>
                      {renderDifficultyBadge(item.difficulty || 'medium')}
                      <span style={{ fontSize: '12px', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                        {item.platform || 'LeetCode'}
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--accent-light)' }}>
                      {(item.topics || []).join(', ')}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '16px', alignItems: 'center', textAlign: 'right' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Confidence</span>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{item.confidence_last} / 5</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', minWidth: '100px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Time Left</span>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: item.days_remaining !== undefined && item.days_remaining < 0 ? '#ef4444' : '#10b981' }}>
                        {formatDaysRemaining(item.days_remaining)}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Pagination Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', marginTop: '16px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
            <button 
              disabled={page === 1} 
              onClick={() => setPage(p => Math.max(1, p - 1))}
              style={{
                background: page === 1 ? 'transparent' : 'rgba(255,255,255,0.05)',
                color: page === 1 ? 'var(--text-secondary)' : '#fff',
                border: '1px solid rgba(255,255,255,0.1)',
                padding: '6px 16px',
                borderRadius: '6px',
                cursor: page === 1 ? 'not-allowed' : 'pointer',
                fontSize: '13px',
                fontWeight: 600
              }}
            >
              Prev
            </button>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Page <span style={{ color: '#fff', fontWeight: 600 }}>{page}</span> / {totalPages}
            </span>
            <button 
              disabled={page >= totalPages} 
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              style={{
                background: page >= totalPages ? 'transparent' : 'rgba(255,255,255,0.05)',
                color: page >= totalPages ? 'var(--text-secondary)' : '#fff',
                border: '1px solid rgba(255,255,255,0.1)',
                padding: '6px 16px',
                borderRadius: '6px',
                cursor: page >= totalPages ? 'not-allowed' : 'pointer',
                fontSize: '13px',
                fontWeight: 600
              }}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Detail Inspector Modal Overlay */}
      {selectedProblem && (
        <div style={{ 
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 
        }}>
          <div className="card" style={{ width: '400px', maxWidth: '90%', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '16px' }}>{selectedProblem.platform === 'LeetCode' ? '🔌' : '📝'}</span>
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
                    {selectedProblem.platform || 'LeetCode'}
                  </span>
                </div>
                <h3 style={{ fontSize: '18px', color: '#fff', margin: 0 }}>#{selectedProblem.problem_id} - {selectedProblem.title}</h3>
              </div>
              <button 
                onClick={() => setSelectedProblem(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px' }}
              >
                ×
              </button>
            </div>

            {/* Analytics Panel */}
            <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Total Times Revised:</span>
                <span style={{ color: '#fff', fontWeight: 600, fontSize: '13px' }}>{(selectedProblem as any).review_count || (selectedProblem.last_reviewed_at ? 1 : 0)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Last Revised:</span>
                <span style={{ color: '#fff', fontWeight: 600, fontSize: '13px' }}>{selectedProblem.last_reviewed_at ? new Date(selectedProblem.last_reviewed_at).toLocaleDateString() : 'Never reviewed'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Time Left:</span>
                <span style={{ color: selectedProblem.days_remaining !== undefined && selectedProblem.days_remaining < 0 ? '#ef4444' : '#10b981', fontWeight: 600, fontSize: '13px' }}>
                  {formatDaysRemaining(selectedProblem.days_remaining)}
                </span>
              </div>
            </div>

            {/* Confidence Selector Grid */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff', textAlign: 'center' }}>Rate your confidence</span>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                {[1, 2, 3, 4, 5].map(score => {
                  let label = "";
                  if (score === 1) label = "Forgot";
                  if (score === 2) label = "Hard";
                  if (score === 3) label = "Okay";
                  if (score === 4) label = "Good";
                  if (score === 5) label = "Mastered";

                  return (
                    <button
                      key={score}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleReview(selectedProblem.problem_id, score);
                      }}
                      style={{
                        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px',
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '8px',
                        padding: '12px 4px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.background = 'var(--accent)';
                        e.currentTarget.style.borderColor = 'var(--accent)';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
                      }}
                    >
                      <span style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>{score}</span>
                      <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>{label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
