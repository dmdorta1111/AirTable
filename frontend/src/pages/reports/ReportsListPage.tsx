import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Plus,
  FileText,
  Share2,
  Calendar,
  Download,
  MoreVertical,
  Edit,
  Trash2,
} from 'lucide-react';
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

// Report type based on backend schema
interface Report {
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

interface ReportListResponse {
  reports: Report[];
  total: number;
}

export const ReportsListPage: React.FC = () => {
  const [selectedBaseId] = useState<string | null>(null);

  // Fetch reports from API
  const { data, isLoading, error } = useQuery<ReportListResponse>({
    queryKey: ['reports', selectedBaseId],
    queryFn: async () => {
      const url = selectedBaseId
        ? `/api/v1/reports?base_id=${selectedBaseId}`
        : '/api/v1/reports';
      return get<ReportListResponse>(url);
    },
  });

  const handleDeleteReport = (reportId: string) => {
    // TODO: Implement delete report in later subtask
    console.log('Delete report:', reportId);
  };

  const handleDuplicateReport = (reportId: string) => {
    // TODO: Implement duplicate report in later subtask
    console.log('Duplicate report:', reportId);
  };

  const handleShareReport = (reportId: string) => {
    // TODO: Implement share report in later subtask
    console.log('Share report:', reportId);
  };

  const handleExportReport = (reportId: string) => {
    // TODO: Implement export report in later subtask
    console.log('Export report:', reportId);
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Custom Reports</h1>
          <p className="text-muted-foreground mt-1">
            Create and manage custom reports for your data
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link to="/reports/templates">
              <FileText className="mr-2 h-4 w-4" />
              Browse Templates
            </Link>
          </Button>
          <Button asChild>
            <Link to="/reports/new">
              <Plus className="mr-2 h-4 w-4" />
              New Report
            </Link>
          </Button>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="text-muted-foreground">Loading reports...</div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="flex items-center justify-center py-16">
          <div className="text-destructive">
            Failed to load reports. Please try again later.
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && data?.reports.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No reports yet</h3>
            <p className="text-muted-foreground text-center max-w-md mb-4">
              Create your first custom report to visualize and analyze your data
            </p>
            <div className="flex items-center gap-2">
              <Button variant="outline" asChild>
                <Link to="/reports/templates">Browse Templates</Link>
              </Button>
              <Button asChild>
                <Link to="/reports/new">Create Report</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Reports Grid */}
      {!isLoading && !error && data?.reports && data.reports.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.reports.map((report) => (
            <Card key={report.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="truncate">{report.name}</CardTitle>
                    {report.description && (
                      <CardDescription className="mt-1 line-clamp-2">
                        {report.description}
                      </CardDescription>
                    )}
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem asChild>
                        <Link to={`/reports/${report.id}/edit`}>
                          <Edit className="mr-2 h-4 w-4" />
                          Edit
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleShareReport(report.id)}
                      >
                        <Share2 className="mr-2 h-4 w-4" />
                        Share
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => handleExportReport(report.id)}
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Export
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => handleDuplicateReport(report.id)}
                      >
                        <FileText className="mr-2 h-4 w-4" />
                        Duplicate
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => handleDeleteReport(report.id)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Metadata */}
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    <span>
                      {new Date(report.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  {report.is_public && (
                    <div className="flex items-center gap-1">
                      <Share2 className="h-4 w-4" />
                      <span>Public</span>
                    </div>
                  )}
                </div>

                {/* Quick Actions */}
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" className="flex-1" asChild>
                    <Link to={`/reports/${report.id}/edit`}>Edit</Link>
                  </Button>
                  <Button size="sm" className="flex-1" asChild>
                    <Link to={`/reports/${report.id}`}>View</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default ReportsListPage;
