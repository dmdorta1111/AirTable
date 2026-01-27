import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DashboardTemplates, DashboardTemplate } from '@/components/analytics/DashboardTemplates';
import { createFromTemplate } from '@/features/dashboard/api/dashboardApi';
import { useToast } from '@/hooks/use-toast';

export const DashboardTemplatesPage: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  const handleSelectTemplate = async (template: DashboardTemplate) => {
    setIsLoading(true);
    setSelectedTemplateId(template.id);

    try {
      // TODO: Get base_id from context or user selection
      // For now, use a placeholder - this should be replaced with actual base selection
      const baseId = localStorage.getItem('currentBaseId');

      if (!baseId) {
        toast({
          title: "No Base Selected",
          description: "Please select a base before creating a dashboard from a template.",
          variant: "destructive",
        });
        navigate('/bases');
        return;
      }

      const dashboard = await createFromTemplate({
        base_id: baseId,
        template_id: template.id,
        name: template.name,
        is_personal: true,
      });

      toast({
        title: "Dashboard Created",
        description: `"${dashboard.name}" has been created successfully.`,
      });

      // Navigate to the newly created dashboard
      navigate(`/dashboards/${dashboard.id}`);
    } catch (error) {
      console.error('Failed to create dashboard from template:', error);
      toast({
        title: "Creation Failed",
        description: error instanceof Error ? error.message : "Failed to create dashboard from template",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
      setSelectedTemplateId(null);
    }
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
            disabled={isLoading}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className={`h-6 w-6 text-primary ${isLoading ? 'animate-pulse' : ''}`} />
              <h1 className="text-3xl font-bold tracking-tight">Dashboard Templates</h1>
              {isLoading && <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />}
            </div>
            <p className="text-muted-foreground mt-1">
              Choose from pre-built templates for common engineering use cases
            </p>
          </div>
        </div>
      </div>

      {/* Templates */}
      <DashboardTemplates
        onSelectTemplate={handleSelectTemplate}
        disabled={isLoading}
        selectedTemplateId={selectedTemplateId}
      />
    </div>
  );
};

export default DashboardTemplatesPage;
