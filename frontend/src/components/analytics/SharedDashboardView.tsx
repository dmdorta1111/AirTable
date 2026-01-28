import React, { useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Lock } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { DashboardResponse } from '@/features/dashboard/api/dashboardApi';
import { ChartWidget, type ChartDataPoint } from './ChartWidget';

interface SharedDashboardViewProps {
  shareToken?: string;
}

export const SharedDashboardView: React.FC<SharedDashboardViewProps> = ({
  shareToken: propShareToken,
}) => {
  const { token: paramShareToken } = useParams<{ token: string }>();
  const { toast } = useToast();

  const shareToken = propShareToken || paramShareToken;

  // Fetch dashboard data using share token (no authentication required)
  const { data: dashboard, isLoading, error } = useQuery<DashboardResponse>({
    queryKey: ['shared-dashboard', shareToken],
    queryFn: async () => {
      const response = await fetch(`/api/v1/dashboards/shared/${shareToken}`);
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Shared dashboard not found or link has expired');
        }
        throw new Error('Failed to load shared dashboard');
      }
      return response.json();
    },
    enabled: !!shareToken,
    retry: false,
  });

  // Parse widgets from layout_config
  const widgets = useMemo(() => {
    if (!dashboard?.layout_config) {
      return [];
    }

    const layoutConfig = dashboard.layout_config as {
      widgets?: Array<{
        id: string;
        type: string;
        config?: {
          chartType?: string;
          title?: string;
          dataKey?: string;
          nameKey?: string;
          colors?: string[];
          [key: string]: unknown;
        };
      }>;
    };
    return layoutConfig.widgets || [];
  }, [dashboard]);

  // Fetch widget data for all widgets (no authentication required for shared dashboards)
  const { data: widgetsData } = useQuery<Record<string, ChartDataPoint[]>>({
    queryKey: ['shared-dashboard-widgets', widgets.map(w => w.id)],
    queryFn: async () => {
      const dataMap: Record<string, ChartDataPoint[]> = {};

      // Fetch data for each widget
      await Promise.all(
        widgets.map(async (widget) => {
          try {
            const response = await fetch(`/api/v1/widgets/${widget.id}/data?share_token=${shareToken}`);
            if (response.ok) {
              const data = await response.json();
              dataMap[widget.id] = data;
            }
          } catch (error) {
            // Silently fail for individual widgets
            dataMap[widget.id] = [];
          }
        })
      );

      return dataMap;
    },
    enabled: widgets.length > 0 && !!shareToken,
    retry: false,
  });

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-2">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-muted-foreground">Loading shared dashboard...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !dashboard) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4 max-w-md">
          <div className="mx-auto w-16 h-16 rounded-full bg-muted flex items-center justify-center">
            <Lock className="h-8 w-8 text-muted-foreground" />
          </div>
          <div>
            <h2 className="text-xl font-semibold">Dashboard Not Available</h2>
            <p className="text-muted-foreground mt-2">
              {error instanceof Error
                ? error.message
                : 'This shared dashboard is not available or the link has expired.'}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold tracking-tight">{dashboard.name}</h1>
              <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
                <Lock className="h-3 w-3 mr-1" />
                Shared View
              </span>
            </div>
            {dashboard.description && (
              <p className="text-muted-foreground mt-1">{dashboard.description}</p>
            )}
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-muted/50 rounded-lg p-4 border">
        <p className="text-sm text-muted-foreground">
          You are viewing a shared dashboard in read-only mode. Some features may be limited.
        </p>
      </div>

      {/* Dashboard Content */}
      {widgets.length > 0 ? (
        <div className="grid gap-6">
          {/* Widget count */}
          <div className="text-sm text-muted-foreground">
            {widgets.length} widget{widgets.length !== 1 ? 's' : ''}
          </div>

          {/* Widget Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {widgets.map((widget) => (
              <ChartWidget
                key={widget.id}
                data={widgetsData?.[widget.id]}
                config={{
                  type: (widget.config?.chartType as any) || 'bar',
                  title: widget.config?.title as string || widget.type,
                  dataKey: widget.config?.dataKey as string,
                  nameKey: widget.config?.nameKey as string,
                  colors: widget.config?.colors as string[],
                }}
                className="h-80"
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="border-2 border-dashed rounded-lg p-12 text-center">
          <p className="text-muted-foreground">
            This dashboard has no widgets yet.
          </p>
        </div>
      )}
    </div>
  );
};

export default SharedDashboardView;
