import { useEffect, useState, useCallback, useRef } from "react";
import type { DependencyList } from "react";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Generic data-fetching hook with loading / error / refetch.
 * Accepts any async function that returns data.
 * Pass `enabled = false` to skip the fetch (e.g. when params are invalid).
 *
 * `deps` should contain every value the `fetcher` closure captures that can
 * change (e.g. `[uid]`, `[period]`). Typed as React's `DependencyList` so
 * TypeScript rejects accidental `unknown` values at call sites.
 */
export function useApi<T>(
  fetcher: () => Promise<{ data: T }>,
  deps: DependencyList = [],
  enabled = true,
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  // Keep a ref to the latest fetcher so the effect body always calls the
  // freshest closure without needing `fetcher` in the dependency array
  // (which would change on every render and cause infinite loops).
  const fetcherRef = useRef(fetcher);
  useEffect(() => { fetcherRef.current = fetcher; });

  useEffect(() => {
    if (!enabled) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetcherRef.current()
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message ?? "Request failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [tick, enabled, ...deps]); // fetcherRef is a stable ref, no eslint-disable needed

  return { data, loading, error, refetch };
}
