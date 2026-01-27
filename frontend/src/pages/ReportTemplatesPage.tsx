import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TemplateGallery, ReportTemplate } from '@/components/reports/TemplateGallery';

export const ReportTemplatesPage: React.FC = () => {
  const navigate = useNavigate();

  const handleSelectTemplate = (template: ReportTemplate) => {
    // TODO: Navigate to report builder with template pre-filled
    // For now, just navigate to the builder
    navigate('/reports/new', {
      state: { template },
    });
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/reports')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <FileText className="h-6 w-6 text-primary" />
              <h1 className="text-3xl font-bold tracking-tight">Report Templates</h1>
            </div>
            <p className="text-muted-foreground mt-1">
              Choose from pre-built templates for common engineering reports
            </p>
          </div>
        </div>
      </div>

      {/* Templates */}
      <TemplateGallery onSelectTemplate={handleSelectTemplate} />
    </div>
  );
};

export default ReportTemplatesPage;
