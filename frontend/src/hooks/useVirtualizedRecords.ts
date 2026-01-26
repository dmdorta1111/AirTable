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

interface UseVirtualizedRecordsOptions {
  tableId: string;
  fetchFn: (cursor: string | null, limit: number) => Promise<CursorPage>;
  initialLimit?: number;
  overscan?: number;
}

const DEFAULT_LIMIT = 50;
const DEFAULT_OVERSCAN = 10;

/**
 * Custom hook for managing virtualized records with cursor-based pagination.
 * Provides efficient data loading and state management for large datasets.
 *
 * @param options - Configuration options for virtualization
 * @returns Object with records, loading state, and control methods
 */
export const useVirtualizedRecords = ({
  tableId,
  fetchFn,
  initialLimit = DEFAULT_LIMIT,
  overscan = DEFAULT_OVERSCAN,
}: UseVirtualizedRecordsOptions) => {
  const [records, setRecords] = useState<Record[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [hasNext, setHasNext] = useState(true);
  const [totalCount, setTotalCount] = useState<number | null>(null);

  const nextCursorRef = useRef<string | null>(null);
  const isLoadingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

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

  const getVisibleRange = useCallback(
    (startIndex: number, endIndex: number) => {
      const start = Math.max(0, startIndex - overscan);
      const end = Math.min(records.length, endIndex + overscan);
      return {
        records: records.slice(start, end),
        startIndex: start,
        endIndex: end,
      };
    },
    [records, overscan]
  );

  useEffect(() => {
    refresh();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [tableId, refresh]);

  return useMemo(
    () => ({
      records,
      isLoading,
      error,
      hasNext,
      totalCount,
      loadMore,
      refresh,
      getVisibleRange,
    }),
    [records, isLoading, error, hasNext, totalCount, loadMore, refresh, getVisibleRange]
  );
};
