import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { CustomReportBuilder, ReportSection } from '@/components/reports/CustomReportBuilder';
import { post, get, patch } from '@/lib/api';
import { ArrowLeft, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface CreateReportRequest {
  name: string;
  description?: string;
  base_id?: string;
  layout_config: {
    sections: ReportSection[];
  };
  settings?: Record<string, unknown>;
}

interface Report {
  id: string;
  base_id: string;
  name: string;
  description?: string;
  layout_config?: {
    sections: ReportSection[];
  };
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

export const ReportBuilderPage: React.FC = () => {
  const navigate = useNavigate();
  const { reportId } = useParams<{ reportId?: string }>();

  // Fetch existing report if editing
  const { data: fetchedReport, isLoading: isLoadingReport } = useQuery<Report>({
    queryKey: ['report', reportId],
    queryFn: async () => {
      if (!reportId) throw new Error('Report ID is required');
      return get<Report>(`/api/v1/reports/${reportId}`);
    },
    enabled: !!reportId,
  });

  const createReportMutation = useMutation({
    mutationFn: async (data: CreateReportRequest) => {
      return post<Report>('/api/v1/reports', data);
    },
    onSuccess: (data) => {
      navigate(`/reports/${data.id}`);
    },
  });

  const updateReportMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<CreateReportRequest> }) => {
      return patch<Report>(`/api/v1/reports/${id}`, data);
    },
    onSuccess: () => {
      navigate('/reports');
    },
  });

  const handleSave = (sections: ReportSection[]) => {
    const reportData = {
      name: fetchedReport?.name || 'New Report',
      description: fetchedReport?.description,
      layout_config: {
        sections,
      },
      settings: fetchedReport?.settings,
    };

    if (reportId) {
      updateReportMutation.mutate({
        id: reportId,
        data: reportData,
      });
    } else {
      createReportMutation.mutate(reportData);
    }
  };

  const handleCancel = () => {
    if (reportId) {
      navigate(`/reports/${reportId}`);
    } else {
      navigate('/reports');
    }
  };

  if (reportId && isLoadingReport) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-muted-foreground">Loading report...</div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="border-b px-6 py-4 flex items-center gap-4 bg-background">
        <Button
          variant="ghost"
          size="icon"
          onClick={handleCancel}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex items-center gap-2 flex-1">
          <FileText className="h-5 w-5 text-primary" />
          <h1 className="text-xl font-semibold">
            {reportId ? 'Edit Report' : 'Create New Report'}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>
          <Button
            onClick={() => handleSave(fetchedReport?.layout_config?.sections || [])}
            disabled={createReportMutation.isPending || updateReportMutation.isPending}
          >
            {createReportMutation.isPending || updateReportMutation.isPending
              ? 'Saving...'
              : 'Save Report'}
          </Button>
        </div>
      </div>

      {/* Builder */}
      <div className="flex-1 overflow-hidden">
        <CustomReportBuilder
          onSave={handleSave}
          onCancel={handleCancel}
          initialSections={fetchedReport?.layout_config?.sections}
        />
      </div>
    </div>
  );
};

export default ReportBuilderPage;
