import React, { useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { get } from '@/lib/api';
import { useDashboardRealtime, type DashboardWidget } from '@/hooks/useDashboardRealtime';
import { useAuthStore } from '@/features/auth/stores/authStore';
import type { DashboardResponse } from '@/features/dashboard/api/dashboardApi';

interface DashboardViewProps {
  dashboardId?: string;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ dashboardId: propDashboardId }) => {
  const { id: paramDashboardId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { token } = useAuthStore();

  const dashboardId = propDashboardId || paramDashboardId;

  // Fetch dashboard data
  const { data: dashboard, isLoading, error } = useQuery<DashboardResponse>({
    queryKey: ['dashboard', dashboardId],
    queryFn: () => get<DashboardResponse>(`/api/v1/dashboards/${dashboardId}`),
    enabled: !!dashboardId && !!token,
  });

  // Parse widgets from layout_config
  const widgets: DashboardWidget[] = React.useMemo(() => {
    if (!dashboard?.layout_config) {
      return [];
    }

    // layout_config is expected to have a widgets property
    const layoutConfig = dashboard.layout_config as { widgets?: DashboardWidget[] };
    return layoutConfig.widgets || [];
  }, [dashboard]);

  // Handle widget refresh from real-time updates
  const handleWidgetUpdate = useCallback((widgetId: string) => {
    console.log(`[DashboardView] Widget ${widgetId} updated, refreshing data...`);

    // Invalidate queries for this specific widget
    // In subtask 5-3, this will trigger chart data refetch
    queryClient.invalidateQueries({
      queryKey: ['widget', widgetId],
    });

    // Show toast notification for real-time update
    toast({
      title: 'Dashboard Updated',
      description: 'Widget data has been refreshed',
    });
  }, [queryClient, toast]);

  // Set up real-time WebSocket connection
  const { status, isConnected, refreshAllWidgets } = useDashboardRealtime({
    dashboardId: dashboardId || '',
    widgets,
    onWidgetUpdate: handleWidgetUpdate,
    enabled: !!dashboardId && !!token,
  });

  // Handle manual refresh
  const handleRefresh = useCallback(() => {
    refreshAllWidgets();
    toast({
      title: 'Refreshing',
      description: 'Updating all dashboard widgets...',
    });
  }, [refreshAllWidgets, toast]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-muted-foreground">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-destructive">Error loading dashboard</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/dashboards')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold tracking-tight">{dashboard.name}</h1>
              {dashboard.template_id && (
                <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary">
                  Template
                </span>
              )}
            </div>
            {dashboard.description && (
              <p className="text-muted-foreground mt-1">{dashboard.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Connection status indicator */}
          <div className="flex items-center gap-2 mr-2">
            <div
              className={`h-2 w-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-gray-400'
              }`}
            />
            <span className="text-xs text-muted-foreground">
              {status === 'connected' ? 'Live' : 'Disconnected'}
            </span>
          </div>

          {/* Manual refresh button */}
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={!isConnected}
            title="Refresh all widgets"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>

          <Button
            variant="outline"
            onClick={() => navigate(`/dashboards/${dashboard.id}/edit`)}
          >
            Edit Dashboard
          </Button>
        </div>
      </div>

      {/* Dashboard Content */}
      {widgets.length > 0 ? (
        <div className="grid gap-6">
          {/* Widget count and real-time status */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {widgets.length} widget{widgets.length !== 1 ? 's' : ''}
            </span>
            {isConnected && (
              <span className="flex items-center gap-1">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                </span>
                Real-time updates active
              </span>
            )}
          </div>

          {/* Widget Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {widgets.map((widget) => (
              <div
                key={widget.id}
                className="border rounded-lg p-6 bg-card"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">{widget.type}</h3>
                  <span className="text-xs text-muted-foreground">{widget.id}</span>
                </div>
                <div className="text-sm text-muted-foreground">
                  Widget content will be rendered in subtask-5-3
                </div>
                {widget.config?.tableId && (
                  <div className="text-xs text-muted-foreground mt-2">
                    Data source: {widget.config.tableId}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="border-2 border-dashed rounded-lg p-12 text-center">
          <p className="text-muted-foreground">
            This dashboard has no widgets yet. Click "Edit Dashboard" to add widgets.
          </p>
        </div>
      )}
    </div>
  );
};

export default DashboardView;
