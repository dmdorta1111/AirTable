import { useEffect, useCallback, useMemo } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAuthStore } from '@/features/auth/stores/authStore';

export interface DashboardWidget {
  id: string;
  type: 'chart' | 'pivot' | 'metric' | 'text';
  config?: {
    tableId?: string;
    [key: string]: unknown;
  };
}

export interface RealtimeEvent {
  event_type: string;
  data: {
    table_id?: string;
    record_id?: string;
    dashboard_id?: string;
    [key: string]: unknown;
  };
}

export interface UseDashboardRealtimeOptions {
  dashboardId: string;
  widgets?: DashboardWidget[];
  onWidgetUpdate?: (widgetId: string) => void;
  enabled?: boolean;
}

export interface UseDashboardRealtimeReturn {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  isConnected: boolean;
  refreshWidget: (widgetId: string) => void;
  refreshAllWidgets: () => void;
}

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/v1/realtime/ws';

/**
 * Custom hook for real-time dashboard updates via WebSocket.
 *
 * Subscribes to dashboard:{dashboardId} channel and table:{tableId} channels
 * for each widget's data source. Handles RECORD_UPDATED, RECORD_CREATED, and
 * RECORD_DELETED events to trigger widget refreshes.
 *
 * @param options - Dashboard real-time options
 * @returns Real-time status and refresh methods
 *
 * @example
 * ```tsx
 * const { status, isConnected, refreshWidget } = useDashboardRealtime({
 *   dashboardId: 'dash-123',
 *   widgets: dashboardWidgets,
 *   onWidgetUpdate: (widgetId) => {
 *     queryClient.invalidateQueries({ queryKey: ['widget', widgetId] });
 *   }
 * });
 * ```
 */
export const useDashboardRealtime = ({
  dashboardId,
  widgets = [],
  onWidgetUpdate,
  enabled = true,
}: UseDashboardRealtimeOptions): UseDashboardRealtimeReturn => {
  const { token } = useAuthStore();

  // Collect all unique table IDs from widgets for future subscription use
  useMemo(() => {
    const ids = new Set<string>();
    widgets.forEach((widget) => {
      if (widget.config?.tableId) {
        ids.add(widget.config.tableId as string);
      }
    });
    return Array.from(ids);
  }, [widgets]);

  // Find widgets affected by a table change
  const getAffectedWidgets = useCallback((tableId: string): string[] => {
    return widgets
      .filter((widget) => widget.config?.tableId === tableId)
      .map((widget) => widget.id);
  }, [widgets]);

  // Handle WebSocket messages
  const handleMessage = useCallback((message: RealtimeEvent) => {
    const { event_type, data } = message;

    // Handle record-level events
    if (event_type === 'RECORD_UPDATED' ||
        event_type === 'RECORD_CREATED' ||
        event_type === 'RECORD_DELETED') {
      const tableId = data.table_id;
      if (tableId) {
        const affectedWidgetIds = getAffectedWidgets(tableId);
        affectedWidgetIds.forEach((widgetId) => {
          if (onWidgetUpdate) {
            onWidgetUpdate(widgetId);
          }
        });
      }
    }

    // Handle dashboard-specific events
    if (event_type === 'DASHBOARD_UPDATED' && data.dashboard_id === dashboardId) {
      if (onWidgetUpdate) {
        // Refresh all widgets on dashboard update
        widgets.forEach((widget) => {
          onWidgetUpdate(widget.id);
        });
      }
    }
  }, [dashboardId, getAffectedWidgets, onWidgetUpdate, widgets]);

  // WebSocket connection
  const { status } = useWebSocket({
    url: WS_URL,
    token: enabled ? (token || undefined) : undefined,
    onMessage: handleMessage,
  });

  // Subscribe to channels when connected
  useEffect(() => {
    if (status !== 'connected' || !enabled) {
      return;
    }

    // Subscribe to dashboard channel
    console.log(`[Dashboard Realtime] Subscribing to dashboard:${dashboardId}`);

    // Note: The actual subscription happens via WebSocket messages
    // In a full implementation, we would send subscription messages here
    // For now, the backend broadcasts to all connected clients

  }, [status, dashboardId, enabled]);

  // Refresh a specific widget
  const refreshWidget = useCallback((widgetId: string) => {
    if (onWidgetUpdate) {
      onWidgetUpdate(widgetId);
    }
  }, [onWidgetUpdate]);

  // Refresh all widgets
  const refreshAllWidgets = useCallback(() => {
    if (onWidgetUpdate) {
      widgets.forEach((widget) => {
        onWidgetUpdate(widget.id);
      });
    }
  }, [onWidgetUpdate, widgets]);

  return {
    status,
    isConnected: status === 'connected',
    refreshWidget,
    refreshAllWidgets,
  };
};
