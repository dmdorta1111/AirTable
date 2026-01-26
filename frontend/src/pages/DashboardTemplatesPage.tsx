import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DashboardTemplates, DashboardTemplate } from '@/components/analytics/DashboardTemplates';

export const DashboardTemplatesPage: React.FC = () => {
  const navigate = useNavigate();

  const handleSelectTemplate = (template: DashboardTemplate) => {
    // TODO: Navigate to dashboard builder with template pre-filled
    // For now, just navigate to the builder
    navigate('/dashboards/new', {
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
            onClick={() => navigate('/dashboards')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-primary" />
              <h1 className="text-3xl font-bold tracking-tight">Dashboard Templates</h1>
            </div>
            <p className="text-muted-foreground mt-1">
              Choose from pre-built templates for common engineering use cases
            </p>
          </div>
        </div>
      </div>

      {/* Templates */}
      <DashboardTemplates onSelectTemplate={handleSelectTemplate} />
    </div>
  );
};

export default DashboardTemplatesPage;
