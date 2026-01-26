import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Record } from '@/types';

interface CursorMeta {
  next_cursor: string | null;
  prev_cursor: string | null;
  has_next: boolean;
  has_prev: boolean;
  limit: number;
  total_count: number | null;
}

interface CursorPage {
  items: Record[];
  meta: CursorMeta;
}

interface UseInfiniteScrollOptions {
  tableId: string;
  fetchFn: (cursor: string | null, limit: number) => Promise<CursorPage>;
  initialLimit?: number;
  threshold?: number;
  enabled?: boolean;
}

const DEFAULT_LIMIT = 50;
const DEFAULT_THRESHOLD = 0.1;

/**
 * Custom hook for managing infinite scroll with cursor-based pagination.
 * Automatically loads more data when user scrolls near the bottom using Intersection Observer.
 *
 * @param options - Configuration options for infinite scroll
 * @returns Object with records, loading state, sentinel ref, and control methods
 *
 * @example
 * ```tsx
 * const { records, isLoading, hasNext, sentinelRef, refresh } = useInfiniteScroll({
 *   tableId: 'tbl-123',
 *   fetchFn: fetchRecords,
 *   initialLimit: 50,
 * });
 *
 * return (
 *   <div>
 *     {records.map(record => <RecordCard key={record.id} record={record} />)}
 *     {hasNext && <div ref={sentinelRef} />}
 *   </div>
 * );
 * ```
 */
export const useInfiniteScroll = ({
  tableId,
  fetchFn,
  initialLimit = DEFAULT_LIMIT,
  threshold = DEFAULT_THRESHOLD,
  enabled = true,
}: UseInfiniteScrollOptions) => {
  const [records, setRecords] = useState<Record[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasNext, setHasNext] = useState(true);
  const [totalCount, setTotalCount] = useState<number | null>(null);

  const nextCursorRef = useRef<string | null>(null);
  const isLoadingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  const loadRecords = useCallback(
    async (cursor: string | null = null) => {
      if (isLoadingRef.current) {
        return;
      }

      isLoadingRef.current = true;
      setIsLoading(true);
      setError(null);

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      abortControllerRef.current = new AbortController();

      try {
        const page = await fetchFn(cursor, initialLimit);

        if (cursor === null) {
          setRecords(page.items);
        } else {
          setRecords((prev) => [...prev, ...page.items]);
        }

        nextCursorRef.current = page.meta.next_cursor;
        setHasNext(page.meta.has_next);
        setTotalCount(page.meta.total_count);
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err);
        }
      } finally {
        isLoadingRef.current = false;
        setIsLoading(false);
      }
    },
    [fetchFn, initialLimit]
  );

  const loadMore = useCallback(() => {
    if (hasNext && !isLoadingRef.current && nextCursorRef.current) {
      loadRecords(nextCursorRef.current);
    }
  }, [hasNext, loadRecords]);

  const refresh = useCallback(() => {
    nextCursorRef.current = null;
    loadRecords(null);
  }, [loadRecords]);

  // Set up Intersection Observer for auto-loading
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const target = entries[0];
        if (target.isIntersecting && hasNext && !isLoadingRef.current) {
          loadMore();
        }
      },
      { threshold }
    );

    observerRef.current = observer;

    const currentSentinel = sentinelRef.current;
    if (currentSentinel) {
      observer.observe(currentSentinel);
    }

    return () => {
      observer.disconnect();
    };
  }, [enabled, hasNext, threshold, loadMore]);

  // Initial load on mount and tableId change
  useEffect(() => {
    if (enabled) {
      refresh();
    }

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [tableId, enabled, refresh]);

  return useMemo(
    () => ({
      records,
      isLoading,
      error,
      hasNext,
      totalCount,
      sentinelRef,
      loadMore,
      refresh,
    }),
    [records, isLoading, error, hasNext, totalCount, sentinelRef, loadMore, refresh]
  );
};
