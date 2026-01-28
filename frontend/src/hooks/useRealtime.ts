import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import type { RecordFieldValue } from '@/types';

interface RealtimeMessageData {
  [key: string]: RecordFieldValue | string | undefined;
  table_id?: string;
  record_id?: string;
  view_id?: string;
  chart_id?: string;
}

interface RealtimeMessage {
  event_type: string;
  data: RealtimeMessageData;
}

type RealtimeEventHandler = (message: RealtimeMessage) => void;

interface UseRealtimeOptions {
  tableId?: string;
  viewId?: string;
  chartId?: string;
  enabled?: boolean;
  onRecordCreated?: RealtimeEventHandler;
  onRecordUpdated?: RealtimeEventHandler;
  onRecordDeleted?: RealtimeEventHandler;
  onChartUpdated?: RealtimeEventHandler;
  onMessage?: RealtimeEventHandler;
}

const WS_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

/**
 * Custom hook for real-time updates via WebSocket.
 * Subscribes to table/view/chart updates and provides event handlers.
 *
 * @param options - Configuration options for real-time subscriptions
 * @returns Object with connection status and subscription info
 *
 * @example
 * ```ts
 * const { status, isConnected } = useRealtime({
 *   tableId: 'tbl-123',
 *   chartId: 'chart-456',
 *   onChartUpdated: (msg) => console.log('Chart updated:', msg),
 * });
 * ```
 */
export const useRealtime = ({
  tableId,
  viewId,
  chartId,
  enabled = true,
  onRecordCreated,
  onRecordUpdated,
  onRecordDeleted,
  onChartUpdated,
  onMessage,
}: UseRealtimeOptions) => {
  const activeSubscriptionsRef = useRef<Set<string>>(new Set());
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : undefined;

  // Build WebSocket URL with subscriptions
  const wsUrl = useMemo(() => {
    if (!enabled) {
      return '';
    }

    const subscriptions = new URLSearchParams();

    if (tableId) {
      subscriptions.append('table', tableId);
      activeSubscriptionsRef.current.add(`table:${tableId}`);
    }

    if (viewId) {
      subscriptions.append('view', viewId);
      activeSubscriptionsRef.current.add(`view:${viewId}`);
    }

    if (chartId) {
      subscriptions.append('chart', chartId);
      activeSubscriptionsRef.current.add(`chart:${chartId}`);
    }

    const queryString = subscriptions.toString();
    return `${WS_URL}/api/v1/realtime${queryString ? `?${queryString}` : ''}`;
  }, [tableId, viewId, chartId, enabled]);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback(
    (message: RealtimeMessage) => {
      const { event_type, data } = message;

      // Filter messages by subscriptions
      if (tableId && data.table_id !== tableId) {
        return;
      }

      if (chartId && data.chart_id !== chartId) {
        return;
      }

      if (viewId && data.view_id !== viewId) {
        return;
      }

      // Call specific event handlers
      switch (event_type) {
        case 'record.created':
          if (onRecordCreated) {
            onRecordCreated(message);
          }
          break;

        case 'record.updated':
          if (onRecordUpdated) {
            onRecordUpdated(message);
          }
          break;

        case 'record.deleted':
          if (onRecordDeleted) {
            onRecordDeleted(message);
          }
          break;

        case 'chart.updated':
          if (onChartUpdated) {
            onChartUpdated(message);
          }
          break;

        default:
          break;
      }

      // Call general message handler
      if (onMessage) {
        onMessage(message);
      }
    },
    [tableId, viewId, chartId, onRecordCreated, onRecordUpdated, onRecordDeleted, onChartUpdated, onMessage]
  );

  // WebSocket connection
  const { status, send, disconnect } = useWebSocket({
    url: wsUrl,
    token: token || undefined,
    onMessage: handleMessage,
    reconnectInterval: 3000,
  });

  // Cleanup subscriptions on unmount
  useEffect(() => {
    return () => {
      activeSubscriptionsRef.current.clear();
    };
  }, []);

  // Manual reconnect method
  const reconnect = useCallback(() => {
    disconnect();
    // Connection will auto-reconnect via useWebSocket hook
  }, [disconnect]);

  return useMemo(
    () => ({
      status,
      isConnected: status === 'connected',
      isConnecting: status === 'connecting',
      isDisconnected: status === 'disconnected',
      hasError: status === 'error',
      send,
      disconnect,
      reconnect,
      subscriptions: Array.from(activeSubscriptionsRef.current),
    }),
    [status, send, disconnect, reconnect]
  );
};
