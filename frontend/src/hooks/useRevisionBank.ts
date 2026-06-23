import { useState, useCallback } from 'react';
import { api } from '../services/api';

export interface TopicStat {
  topic: string;
  avg_confidence: number;
  problem_count: number;
}

export interface RevisionItem {
  revision_id: number;
  problem_id: number;
  confidence_last: number;
  next_review_at: string;
  last_reviewed_at: string | null;
  days_remaining?: number;
  title: string;
  difficulty: string;
  topics: string[];
  platform: string;
}

export function useRevisionBank() {
  const [dueItems, setDueItems] = useState<RevisionItem[]>([]);
  const [allRevisionItems, setAllRevisionItems] = useState<RevisionItem[]>([]);
  const [topicStats, setTopicStats] = useState<TopicStat[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDueItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getDueRevisionItems();
      if (res) {
        setDueItems(res || []);
      }
    } catch (err: any) {
      setError(err.message || "Failed to fetch due items.");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchPagedHistory = useCallback(async (page: number, limit: number = 10) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getAllRevisionItems(page, limit);
      if (res) {
        setAllRevisionItems(res.items || []);
        setTotalCount(res.total_count || 0);
        if (res.topic_stats) {
          setTopicStats(res.topic_stats);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to fetch revision history.");
    } finally {
      setLoading(false);
    }
  }, []);

  const submitReview = useCallback(async (problemId: number, confidence: number) => {
    setLoading(true);
    setError(null);
    try {
      await api.submitRevisionReview({ problem_id: problemId, confidence });
      // After submission, re-fetch due items to refresh the list
      await fetchDueItems();
    } catch (err: any) {
      setError(err.message || "Failed to submit review.");
    } finally {
      setLoading(false);
    }
  }, [fetchDueItems]);

  return {
    dueItems,
    allRevisionItems,
    topicStats,
    totalCount,
    loading,
    error,
    fetchDueItems,
    fetchPagedHistory,
    submitReview
  };
}
