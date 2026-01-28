import React, { useState } from 'react';
import {
  BarChart3,
  LineChart,
  PieChart,
  TrendingUp,
  DollarSign,
  Clock,
  Users,
  AlertTriangle,
  CheckCircle,
  Calendar,
  Target,
  Activity,
  Layers,
  X,
  Loader2,
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { cn } from '@/lib/utils';

// Dashboard template structure
export interface DashboardTemplate {
  id: string;
  name: string;
  description: string;
  category: 'engineering' | 'project' | 'quality' | 'operations' | 'general';
  icon: React.ReactNode;
  widgets: TemplateWidget[];
  tags: string[];
}

// Widget configuration for templates
interface TemplateWidget {
  type: 'chart' | 'pivot' | 'metric' | 'text';
  title: string;
  chartType?: 'line' | 'bar' | 'pie' | 'scatter' | 'gauge';
  description: string;
}

// Pre-defined dashboard templates
const DASHBOARD_TEMPLATES: DashboardTemplate[] = [
  {
    id: 'engineering-cost-tracking',
    name: 'Engineering Cost Tracking',
    description: 'Track and analyze engineering costs, spending trends, and budget utilization',
    category: 'engineering',
    icon: <DollarSign className="h-6 w-6" />,
    tags: ['costs', 'budget', 'spending', 'finance'],
    widgets: [
      {
        type: 'metric',
        title: 'Total Monthly Spend',
        description: 'Current month total engineering costs',
      },
      {
        type: 'chart',
        chartType: 'line',
        title: 'Cost Trend Over Time',
        description: 'Monthly spending trends for the past year',
      },
      {
        type: 'chart',
        chartType: 'pie',
        title: 'Cost by Category',
        description: 'Breakdown of costs by engineering department',
      },
      {
        type: 'chart',
        chartType: 'bar',
        title: 'Top Projects by Cost',
        description: 'Highest spending projects this quarter',
      },
      {
        type: 'pivot',
        title: 'Cost Analysis Table',
        description: 'Detailed pivot table of costs by project and category',
      },
    ],
  },
  {
    id: 'quality-metrics',
    name: 'Quality Metrics Dashboard',
    description: 'Monitor defects, quality trends, and compliance metrics for engineering quality',
    category: 'quality',
    icon: <CheckCircle className="h-6 w-6" />,
    tags: ['quality', 'defects', 'compliance', 'testing'],
    widgets: [
      {
        type: 'metric',
        title: 'Open Defects',
        description: 'Total number of open quality issues',
      },
      {
        type: 'chart',
        chartType: 'line',
        title: 'Defect Trend',
        description: 'Defect count trends over the past 6 months',
      },
      {
        type: 'chart',
        chartType: 'bar',
        title: 'Defects by Severity',
        description: 'Distribution of defects by severity level',
      },
      {
        type: 'chart',
        chartType: 'pie',
        title: 'Defects by Component',
        description: 'Which components have the most issues',
      },
      {
        type: 'chart',
        chartType: 'gauge',
        title: 'Quality Score',
        description: 'Overall quality score based on defect metrics',
      },
    ],
  },
  {
    id: 'project-status',
    name: 'Project Status Overview',
    description: 'Track project progress, milestones, and deliverables across engineering teams',
    category: 'project',
    icon: <Target className="h-6 w-6" />,
    tags: ['projects', 'milestones', 'progress', 'status'],
    widgets: [
      {
        type: 'metric',
        title: 'Active Projects',
        description: 'Number of projects currently in progress',
      },
      {
        type: 'chart',
        chartType: 'bar',
        title: 'Projects by Status',
        description: 'Project count by status (on track, at risk, delayed)',
      },
      {
        type: 'chart',
        chartType: 'line',
        title: 'Milestone Completion',
        description: 'Milestone completion trend over time',
      },
      {
        type: 'chart',
        chartType: 'pie',
        title: 'Project Distribution',
        description: 'Projects by engineering team or department',
      },
      {
        type: 'pivot',
        title: 'Project Details Table',
        description: 'Detailed view of all projects with key metrics',
      },
    ],
  },
  {
    id: 'lead-time-analysis',
    name: 'Lead Time Analysis',
    description: 'Analyze lead times, cycle times, and delivery performance for engineering workflows',
    category: 'operations',
    icon: <Clock className="h-6 w-6" />,
    tags: ['lead time', 'cycle time', 'performance', 'delivery'],
    widgets: [
      {
        type: 'metric',
        title: 'Average Lead Time',
        description: 'Average time from start to completion (days)',
      },
      {
        type: 'chart',
        chartType: 'line',
        title: 'Lead Time Trend',
        description: 'Lead time trends over the past quarter',
      },
      {
        type: 'chart',
        chartType: 'bar',
        title: 'Lead Time by Process',
        description: 'Comparison of lead times across different processes',
      },
      {
        type: 'chart',
        chartType: 'scatter',
        title: 'Lead Time vs Complexity',
        description: 'Correlation between project complexity and lead time',
      },
      {
        type: 'pivot',
        title: 'Lead Time Breakdown',
        description: 'Detailed breakdown of lead times by stage',
      },
    ],
  },
  {
    id: 'resource-utilization',
    name: 'Resource Utilization',
    description: 'Track engineering resource allocation, capacity, and utilization rates',
    category: 'operations',
    icon: <Users className="h-6 w-6" />,
    tags: ['resources', 'capacity', 'utilization', 'team'],
    widgets: [
      {
        type: 'metric',
        title: 'Team Utilization',
        description: 'Overall team utilization percentage',
      },
      {
        type: 'chart',
        chartType: 'bar',
        title: 'Utilization by Team',
        description: 'Resource utilization comparison across teams',
      },
      {
        type: 'chart',
        chartType: 'line',
        title: 'Capacity Trend',
        description: 'Team capacity and utilization over time',
      },
      {
        type: 'chart',
        chartType: 'pie',
        title: 'Time Allocation',
        description: 'How team time is allocated across activities',
      },
      {
        type: 'pivot',
        title: 'Resource Details',
        description: 'Detailed resource allocation by person and project',
      },
    ],
  },
  {
    id: 'risk-management',
    name: 'Risk Management Dashboard',
    description: 'Monitor engineering risks, issues, and mitigation actions across projects',
    category: 'project',
    icon: <AlertTriangle className="h-6 w-6" />,
    tags: ['risk', 'issues', 'mitigation', 'safety'],
    widgets: [
      {
        type: 'metric',
        title: 'Open Risks',
        description: 'Total number of active risks',
      },
      {
        type: 'chart',
        chartType: 'bar',
        title: 'Risks by Severity',
        description: 'Risk count by severity level (high, medium, low)',
      },
      {
        type: 'chart',
        chartType: 'pie',
        title: 'Risks by Category',
        description: 'Distribution of risks by type',
      },
      {
        type: 'chart',
        chartType: 'line',
        title: 'Risk Trend',
        description: 'Open risk count trend over the past 3 months',
      },
      {
        type: 'pivot',
        title: 'Risk Register',
        description: 'Comprehensive risk register with mitigation status',
      },
    ],
  },
  {
    id: 'performance-kpis',
    name: 'Performance KPIs',
    description: 'Track key performance indicators and operational metrics for engineering',
    category: 'general',
    icon: <Activity className="h-6 w-6" />,
    tags: ['KPIs', 'performance', 'metrics', 'operations'],
    widgets: [
      {
        type: 'metric',
        title: 'Overall KPI Score',
        description: 'Composite performance score',
      },
      {
        type: 'chart',
        chartType: 'gauge',
        title: 'Quality KPI',
        description: 'Quality performance indicator',
      },
      {
        type: 'chart',
        chartType: 'gauge',
        title: 'Delivery KPI',
        description: 'On-time delivery performance',
      },
      {
        type: 'chart',
        chartType: 'line',
        title: 'KPI Trends',
        description: 'All KPIs tracked over time',
      },
      {
        type: 'pivot',
        title: 'KPI Details',
        description: 'Detailed KPI breakdown by metric',
      },
    ],
  },
  {
    id: 'sprint-velocity',
    name: 'Sprint Velocity Tracker',
    description: 'Monitor agile sprint velocity, burn-down, and team productivity metrics',
    category: 'project',
    icon: <TrendingUp className="h-6 w-6" />,
    tags: ['agile', 'sprint', 'velocity', 'productivity'],
    widgets: [
      {
        type: 'metric',
        title: 'Current Sprint Velocity',
        description: 'Story points completed in current sprint',
      },
      {
        type: 'chart',
        chartType: 'bar',
        title: 'Velocity by Sprint',
        description: 'Sprint velocity over the past 6 sprints',
      },
      {
        type: 'chart',
        chartType: 'line',
        title: 'Sprint Burn-down',
        description: 'Daily burn-down for current sprint',
      },
      {
        type: 'chart',
        chartType: 'pie',
        title: 'Story Point Distribution',
        description: 'Story points by team member',
      },
      {
        type: 'pivot',
        title: 'Sprint Summary',
        description: 'Detailed sprint metrics and completion rates',
      },
    ],
  },
];

// Category configuration
const CATEGORIES = [
  { value: 'all', label: 'All Templates', icon: <Layers className="h-4 w-4" /> },
  { value: 'engineering', label: 'Engineering', icon: <BarChart3 className="h-4 w-4" /> },
  { value: 'project', label: 'Project Management', icon: <Target className="h-4 w-4" /> },
  { value: 'quality', label: 'Quality', icon: <CheckCircle className="h-4 w-4" /> },
  { value: 'operations', label: 'Operations', icon: <Activity className="h-4 w-4" /> },
  { value: 'general', label: 'General', icon: <Calendar className="h-4 w-4" /> },
];

interface DashboardTemplatesProps {
  onSelectTemplate?: (template: DashboardTemplate) => void;
  className?: string;
  disabled?: boolean;
  selectedTemplateId?: string | null;
}

export const DashboardTemplates: React.FC<DashboardTemplatesProps> = ({
  onSelectTemplate,
  className,
  disabled = false,
  selectedTemplateId = null,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [previewTemplate, setPreviewTemplate] = useState<DashboardTemplate | null>(null);

  // Filter templates by category
  const filteredTemplates =
    selectedCategory === 'all'
      ? DASHBOARD_TEMPLATES
      : DASHBOARD_TEMPLATES.filter((t) => t.category === selectedCategory);

  // Handle template selection
  const handleUseTemplate = (template: DashboardTemplate) => {
    if (!disabled && onSelectTemplate) {
      onSelectTemplate(template);
    }
  };

  // Check if a specific template is currently being processed
  const isTemplateProcessing = (templateId: string) => {
    return disabled && selectedTemplateId === templateId;
  };

  // Handle template preview
  const handlePreview = (template: DashboardTemplate) => {
    setPreviewTemplate(template);
  };

  // Get widget icon based on type
  const getWidgetIcon = (widget: TemplateWidget) => {
    if (widget.type === 'chart') {
      switch (widget.chartType) {
        case 'line':
          return <LineChart className="h-4 w-4" />;
        case 'bar':
          return <BarChart3 className="h-4 w-4" />;
        case 'pie':
          return <PieChart className="h-4 w-4" />;
        default:
          return <BarChart3 className="h-4 w-4" />;
      }
    }
    return <BarChart3 className="h-4 w-4" />;
  };

  return (
    <div className={cn('space-y-6', className)}>
      {/* Category Filter */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {CATEGORIES.map((category) => (
          <Button
            key={category.value}
            variant={selectedCategory === category.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory(category.value)}
            className="flex items-center gap-2 whitespace-nowrap"
          >
            {category.icon}
            {category.label}
          </Button>
        ))}
      </div>

      {/* Template Grid */}
      {filteredTemplates.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Layers className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No templates found</h3>
            <p className="text-muted-foreground text-center max-w-md">
              Try selecting a different category to see available templates.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTemplates.map((template) => (
            <Card
              key={template.id}
              className="hover:shadow-lg transition-shadow group"
            >
              <CardHeader>
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary">
                    {template.icon}
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                    <CardDescription className="mt-1.5">
                      {template.description}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Widget Count */}
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Layers className="h-4 w-4" />
                  <span>{template.widgets.length} widgets</span>
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-1">
                  {template.tags.slice(0, 3).map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium"
                    >
                      {tag}
                    </span>
                  ))}
                  {template.tags.length > 3 && (
                    <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium">
                      +{template.tags.length - 3} more
                    </span>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => handlePreview(template)}
                    disabled={disabled}
                  >
                    Preview
                  </Button>
                  <Button
                    size="sm"
                    className="flex-1"
                    onClick={() => handleUseTemplate(template)}
                    disabled={disabled || isTemplateProcessing(template.id)}
                  >
                    {isTemplateProcessing(template.id) ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      'Use Template'
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Preview Dialog */}
      <Dialog open={!!previewTemplate} onOpenChange={() => setPreviewTemplate(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          {previewTemplate && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  <div className="p-3 rounded-lg bg-primary/10 text-primary">
                    {previewTemplate.icon}
                  </div>
                  <div className="flex-1">
                    <DialogTitle className="text-xl">{previewTemplate.name}</DialogTitle>
                    <DialogDescription className="mt-1">
                      {previewTemplate.description}
                    </DialogDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setPreviewTemplate(null)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </DialogHeader>

              {/* Template Details */}
              <div className="space-y-6 mt-4">
                {/* Tags */}
                <div>
                  <h4 className="text-sm font-semibold mb-2">Tags</h4>
                  <div className="flex flex-wrap gap-1">
                    {previewTemplate.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Widgets */}
                <div>
                  <h4 className="text-sm font-semibold mb-3">
                    Included Widgets ({previewTemplate.widgets.length})
                  </h4>
                  <div className="space-y-2">
                    {previewTemplate.widgets.map((widget, index) => (
                      <div
                        key={index}
                        className="flex items-start gap-3 p-3 rounded-lg border bg-card"
                      >
                        <div className="p-2 rounded-md bg-muted">
                          {getWidgetIcon(widget)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm">{widget.title}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {widget.description}
                          </div>
                          <div className="flex items-center gap-2 mt-2">
                            <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                              {widget.type}
                            </span>
                            {widget.chartType && (
                              <span className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs font-medium">
                                {widget.chartType}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <DialogFooter className="mt-6">
                <Button
                  variant="outline"
                  onClick={() => setPreviewTemplate(null)}
                  disabled={disabled}
                >
                  Close
                </Button>
                <Button
                  onClick={() => {
                    handleUseTemplate(previewTemplate);
                    setPreviewTemplate(null);
                  }}
                  disabled={disabled || isTemplateProcessing(previewTemplate.id)}
                >
                  {isTemplateProcessing(previewTemplate.id) ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    'Use This Template'
                  )}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DashboardTemplates;
