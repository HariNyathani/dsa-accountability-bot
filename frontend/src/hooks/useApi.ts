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
 *
 * The fetcher receives an optional `AbortSignal`. On dep change or unmount,
 * the in-flight request is aborted via `AbortController` so the browser stops
 * the network round-trip instead of just discarding the response.
 */
export function useApi<T>(
  fetcher: (signal?: AbortSignal) => Promise<{ data: T }>,
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

    const ctl = new AbortController();
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetcherRef.current(ctl.signal)
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err?.name === "AbortError") return;
        // Friendly message for network failures (offline, CORS, server down).
        if (err instanceof TypeError && /fetch|network|load/i.test(err.message)) {
          setError("Couldn't reach the server. Check your connection and retry.");
        } else {
          setError(err?.message ?? "Request failed");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; ctl.abort(); };
  }, [tick, enabled, ...deps]); // fetcherRef is a stable ref, no eslint-disable needed

  return { data, loading, error, refetch };
}
