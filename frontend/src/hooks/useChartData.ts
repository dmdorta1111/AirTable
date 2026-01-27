import { useCallback, useEffect, useMemo, useState } from 'react';
import { get } from '@/lib/api';
import type { ChartDataPoint } from '@/components/analytics/ChartWidget';

interface UseChartDataOptions {
  tableId: string;
  chartId?: string;
  enabled?: boolean;
  refreshInterval?: number;
  onError?: (error: Error) => void;
}

interface ChartDataResponse {
  data: ChartDataPoint[];
  chart_id: string;
  table_id: string;
  updated_at: string;
}

/**
 * Custom hook for fetching chart data from the backend.
 * Supports polling refresh and integrates with real-time updates via WebSocket.
 *
 * @param options - Configuration options for chart data fetching
 * @returns Object with chart data, loading state, error, and refresh method
 *
 * @example
 * ```ts
 * const { data, isLoading, error, refresh } = useChartData({
 *   tableId: 'tbl-123',
 *   chartId: 'chart-456',
 *   enabled: true,
 *   refreshInterval: 30000, // 30 seconds
 * });
 * ```
 */
export const useChartData = ({
  tableId,
  chartId,
  enabled = true,
  refreshInterval,
  onError,
}: UseChartDataOptions) => {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchChartData = useCallback(async () => {
    if (!enabled || !tableId) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const url = chartId
        ? `/api/v1/tables/${tableId}/charts/${chartId}/data`
        : `/api/v1/tables/${tableId}/charts/data`;

      const response = await get<ChartDataResponse>(url);
      setData(response.data);
      setLastUpdated(new Date(response.updated_at));
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch chart data');
      setError(error);
      if (onError) {
        onError(error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [tableId, chartId, enabled, onError]);

  const refresh = useCallback(() => {
    fetchChartData();
  }, [fetchChartData]);

  // Initial fetch
  useEffect(() => {
    if (enabled) {
      fetchChartData();
    }
  }, [enabled, fetchChartData]);

  // Polling refresh
  useEffect(() => {
    if (!enabled || !refreshInterval) {
      return;
    }

    const interval = setInterval(() => {
      fetchChartData();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [enabled, refreshInterval, fetchChartData]);

  return useMemo(
    () => ({
      data,
      isLoading,
      error,
      lastUpdated,
      refresh,
    }),
    [data, isLoading, error, lastUpdated, refresh]
  );
};
