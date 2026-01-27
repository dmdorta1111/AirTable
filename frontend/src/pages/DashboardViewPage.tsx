import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQuery } from '@tanstack/react-query';
import { get } from '@/lib/api';
import type { DashboardResponse } from '@/features/dashboard/api/dashboardApi';

export const DashboardViewPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: dashboard, isLoading, error } = useQuery<DashboardResponse>({
    queryKey: ['dashboard', id],
    queryFn: () => get<DashboardResponse>(`/api/v1/dashboards/${id}`),
    enabled: !!id,
  });

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
          <Button
            variant="outline"
            onClick={() => navigate(`/dashboards/${dashboard.id}/edit`)}
          >
            Edit Dashboard
          </Button>
        </div>
      </div>

      {/* Dashboard Content */}
      {dashboard.layout_config && Object.keys(dashboard.layout_config).length > 0 ? (
        <div className="grid gap-6">
          <div className="text-sm text-muted-foreground">
            Dashboard loaded with {Object.keys(dashboard.layout_config).length} widgets
          </div>
          {/* Widgets will be rendered here in future subtasks */}
          <div className="border-2 border-dashed rounded-lg p-12 text-center">
            <p className="text-muted-foreground">
              Dashboard widgets will be rendered here in the next phase (subtask-5-3: Real-time Dashboard Updates)
            </p>
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

export default DashboardViewPage;
