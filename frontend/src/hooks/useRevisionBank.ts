import { useState, useCallback } from "react";
import { api } from "../services/api";
import { useApi } from "./useApi";

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

interface PagedHistory {
  items: RevisionItem[];
  total_count: number;
  topic_stats?: TopicStat[];
}

export function useRevisionBank() {
  const [page, setPage] = useState(1);
  const limit = 10;

  const due = useApi(
    (signal) => api.getDueRevisionItems({ signal }),
    []
  );
  const history = useApi(
    (signal) => api.getAllRevisionItems(page, limit, { signal }),
    [page]
  );
  const [submitting, setSubmitting] = useState(false);

  const refetch = useCallback(() => {
    due.refetch();
    history.refetch();
  }, [due, history]);

  const submitReview = useCallback(
    async (problemId: number, confidence: number) => {
      setSubmitting(true);
      try {
        await api.submitRevisionReview({ problem_id: problemId, confidence });
        due.refetch();
      } finally {
        setSubmitting(false);
      }
    },
    [due]
  );

  const dueData = (due.data as RevisionItem[] | null) ?? null;
  const historyData = (history.data as PagedHistory | null) ?? null;

  return {
    dueItems: dueData ?? [],
    allRevisionItems: historyData?.items ?? [],
    topicStats: historyData?.topic_stats ?? [],
    totalCount: historyData?.total_count ?? 0,
    page,
    setPage,
    limit,
    loading: due.loading || history.loading || submitting,
    error: due.error ?? history.error,
    refetch,
    submitReview,
  };
}
