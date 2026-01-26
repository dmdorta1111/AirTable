import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, LayoutDashboard, Share2, Calendar, Download, MoreVertical, Edit, Trash2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { get } from '@/lib/api';

// Dashboard type based on backend schema
interface Dashboard {
  id: string;
  base_id: string;
  name: string;
  description?: string;
  layout_config?: Record<string, unknown>;
  settings?: Record<string, unknown>;
  is_default: boolean;
  is_personal: boolean;
  is_public: boolean;
  is_locked: boolean;
  share_token?: string;
  created_at: string;
  updated_at: string;
  created_by_id: string;
}

interface DashboardListResponse {
  dashboards: Dashboard[];
  total: number;
}

export const DashboardPage: React.FC = () => {
  const [selectedBaseId] = useState<string | null>(null);

  // Fetch dashboards from API
  const { data, isLoading, error } = useQuery<DashboardListResponse>({
    queryKey: ['dashboards', selectedBaseId],
    queryFn: async () => {
      const url = selectedBaseId
        ? `/api/v1/dashboards?base_id=${selectedBaseId}`
        : '/api/v1/dashboards';
      return get<DashboardListResponse>(url);
    },
  });

  const handleDeleteDashboard = (dashboardId: string) => {
    // TODO: Implement delete dashboard in later subtask
    void dashboardId;
  };

  const handleShareDashboard = (dashboardId: string) => {
    // TODO: Implement share dashboard in later subtask
    void dashboardId;
  };

  const handleExportDashboard = (dashboardId: string) => {
    // TODO: Implement export dashboard in later subtask
    void dashboardId;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading dashboards...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-destructive">Error loading dashboards</div>
      </div>
    );
  }

  const dashboards = data?.dashboards || [];

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Analytics Dashboards</h1>
          <p className="text-muted-foreground mt-1">
            Create and manage custom dashboards with charts, pivot tables, and reports
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/dashboards/templates">
            <Button variant="outline" size="lg">
              <Sparkles className="mr-2 h-4 w-4" />
              Browse Templates
            </Button>
          </Link>
          <Link to="/dashboards/new">
            <Button size="lg">
              <Plus className="mr-2 h-4 w-4" />
              New Dashboard
            </Button>
          </Link>
        </div>
      </div>

      {/* Dashboard Grid */}
      {dashboards.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <LayoutDashboard className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No dashboards yet</h3>
            <p className="text-muted-foreground text-center mb-4 max-w-md">
              Get started by creating your first analytics dashboard with custom charts,
              pivot tables, and scheduled reports.
            </p>
            <Link to="/dashboards/new">
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Dashboard
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {dashboards.map((dashboard) => (
            <Card
              key={dashboard.id}
              className="hover:shadow-lg transition-shadow cursor-pointer group"
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <Link to={`/dashboards/${dashboard.id}`}>
                      <CardTitle className="text-lg hover:text-primary transition-colors">
                        {dashboard.name}
                      </CardTitle>
                    </Link>
                    {dashboard.description && (
                      <CardDescription className="mt-1.5 line-clamp-2">
                        {dashboard.description}
                      </CardDescription>
                    )}
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleShareDashboard(dashboard.id)}>
                        <Share2 className="mr-2 h-4 w-4" />
                        Share
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleExportDashboard(dashboard.id)}>
                        <Download className="mr-2 h-4 w-4" />
                        Export as PDF
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem>
                        <Edit className="mr-2 h-4 w-4" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleDeleteDashboard(dashboard.id)}
                        className="text-destructive"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  {dashboard.is_default && (
                    <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
                      Default
                    </span>
                  )}
                  {dashboard.is_public && (
                    <span className="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
                      Public
                    </span>
                  )}
                  {dashboard.is_personal && (
                    <span className="inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
                      Personal
                    </span>
                  )}
                  {dashboard.is_locked && (
                    <span className="inline-flex items-center rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/10">
                      Locked
                    </span>
                  )}
                </div>
                <div className="mt-3 flex items-center text-xs text-muted-foreground">
                  <Calendar className="mr-1 h-3 w-3" />
                  Updated {new Date(dashboard.updated_at).toLocaleDateString()}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
