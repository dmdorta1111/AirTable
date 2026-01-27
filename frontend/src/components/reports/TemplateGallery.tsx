import React, { useState } from 'react';
import {
  FileText,
  ClipboardList,
  CheckCircle,
  BarChart3,
  AlertTriangle,
  DollarSign,
  Users,
  Clock,
  TrendingUp,
  Package,
  Settings,
  Layers,
  X,
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
import type { SectionType } from './CustomReportBuilder';

// Report template structure
export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  category: 'manufacturing' | 'quality' | 'project' | 'financial' | 'general';
  icon: React.ReactNode;
  sections: TemplateSection[];
  tags: string[];
}

// Section configuration for templates
interface TemplateSection {
  type: SectionType;
  title: string;
  description: string;
  config?: {
    content?: string;
    [key: string]: unknown;
  };
}

// Pre-defined report templates
const REPORT_TEMPLATES: ReportTemplate[] = [
  {
    id: 'bom-report',
    name: 'Bill of Materials (BOM)',
    description: 'Complete BOM with item details, quantities, costs, and supplier information',
    category: 'manufacturing',
    icon: <Package className="h-6 w-6" />,
    tags: ['BOM', 'manufacturing', 'materials', 'inventory'],
    sections: [
      {
        type: 'text',
        title: 'Report Header',
        description: 'Title, date, and project information',
        config: {
          content: 'Bill of Materials Report\nGenerated on: {date}\nProject: {project_name}',
        },
      },
      {
        type: 'table',
        title: 'Materials List',
        description: 'Complete list of all materials with quantities and specifications',
      },
      {
        type: 'table',
        title: 'Cost Breakdown',
        description: 'Item costs, totals, and cost analysis by category',
      },
      {
        type: 'table',
        title: 'Supplier Information',
        description: 'Supplier details, lead times, and contact information',
      },
      {
        type: 'text',
        title: 'Notes',
        description: 'Additional notes and special instructions',
        config: {
          content: 'Notes: Add any special requirements or notes here...',
        },
      },
    ],
  },
  {
    id: 'inspection-report',
    name: 'Quality Inspection Report',
    description: 'Inspection results, defects found, and quality metrics summary',
    category: 'quality',
    icon: <CheckCircle className="h-6 w-6" />,
    tags: ['inspection', 'quality', 'defects', 'testing'],
    sections: [
      {
        type: 'text',
        title: 'Inspection Summary',
        description: 'Overview of inspection scope and results',
        config: {
          content: 'Quality Inspection Report\nDate: {date}\nInspector: {inspector_name}\nOverall Status: {status}',
        },
      },
      {
        type: 'chart',
        title: 'Defect Summary',
        description: 'Visual summary of defects by type and severity',
      },
      {
        type: 'table',
        title: 'Inspection Checklist',
        description: 'Detailed checklist with pass/fail results',
      },
      {
        type: 'table',
        title: 'Defects Found',
        description: 'List of all defects with severity and disposition',
      },
      {
        type: 'text',
        title: 'Recommendations',
        description: 'Quality improvement recommendations',
        config: {
          content: 'Recommendations:\n1. Address critical defects immediately\n2. Schedule follow-up inspection\n',
        },
      },
    ],
  },
  {
    id: 'project-status',
    name: 'Project Status Report',
    description: 'Project progress, milestones, risks, and resource status',
    category: 'project',
    icon: <TrendingUp className="h-6 w-6" />,
    tags: ['project', 'status', 'milestones', 'progress'],
    sections: [
      {
        type: 'text',
        title: 'Executive Summary',
        description: 'High-level project overview',
        config: {
          content: 'Project Status Report\nProject: {project_name}\nPeriod: {reporting_period}\nOverall Status: {status}',
        },
      },
      {
        type: 'chart',
        title: 'Progress Overview',
        description: 'Visual progress indicators and milestone completion',
      },
      {
        type: 'table',
        title: 'Milestone Status',
        description: 'All milestones with status and completion dates',
      },
      {
        type: 'table',
        title: 'Risks and Issues',
        description: 'Current risks, issues, and mitigation plans',
      },
      {
        type: 'table',
        title: 'Resource Allocation',
        description: 'Team assignments and resource utilization',
      },
    ],
  },
  {
    id: 'quality-metrics',
    name: 'Quality Metrics Dashboard',
    description: 'Trend analysis of quality KPIs, defect rates, and compliance metrics',
    category: 'quality',
    icon: <BarChart3 className="h-6 w-6" />,
    tags: ['quality', 'metrics', 'KPIs', 'trends'],
    sections: [
      {
        type: 'text',
        title: 'Quality Overview',
        description: 'Summary of quality performance',
        config: {
          content: 'Quality Metrics Report\nPeriod: {date_range}\nQuality Score: {score}',
        },
      },
      {
        type: 'chart',
        title: 'Defect Trends',
        description: 'Defect rate trends over time',
      },
      {
        type: 'chart',
        title: 'Quality KPIs',
        description: 'Key performance indicators dashboard',
      },
      {
        type: 'table',
        title: 'Metrics Breakdown',
        description: 'Detailed metrics by category and period',
      },
      {
        type: 'chart',
        title: 'Compliance Status',
        description: 'Compliance metrics by standard',
      },
    ],
  },
  {
    id: 'cost-analysis',
    name: 'Cost Analysis Report',
    description: 'Detailed cost breakdown, budget vs actual, and variance analysis',
    category: 'financial',
    icon: <DollarSign className="h-6 w-6" />,
    tags: ['costs', 'budget', 'finance', 'analysis'],
    sections: [
      {
        type: 'text',
        title: 'Financial Summary',
        description: 'Executive summary of financial performance',
        config: {
          content: 'Cost Analysis Report\nPeriod: {period}\nTotal Spend: ${total}\nBudget Variance: {variance}%',
        },
      },
      {
        type: 'chart',
        title: 'Cost Trends',
        description: 'Spending trends over time',
      },
      {
        type: 'table',
        title: 'Budget vs Actual',
        description: 'Comparison of budgeted and actual costs',
      },
      {
        type: 'chart',
        title: 'Cost by Category',
        description: 'Cost breakdown by category',
      },
      {
        type: 'table',
        title: 'Variance Analysis',
        description: 'Detailed variance explanation by category',
      },
    ],
  },
  {
    id: 'production-report',
    name: 'Production Status Report',
    description: 'Production metrics, output, efficiency, and schedule adherence',
    category: 'manufacturing',
    icon: <Settings className="h-6 w-6" />,
    tags: ['production', 'manufacturing', 'output', 'efficiency'],
    sections: [
      {
        type: 'text',
        title: 'Production Summary',
        description: 'Overview of production performance',
        config: {
          content: 'Production Status Report\nDate: {date}\nShift: {shift}\nOutput: {output}',
        },
      },
      {
        type: 'chart',
        title: 'Production Trends',
        description: 'Output trends over time',
      },
      {
        type: 'table',
        title: 'Production Metrics',
        description: 'Key production KPIs and efficiency metrics',
      },
      {
        type: 'table',
        title: 'Schedule Adherence',
        description: 'On-time delivery and schedule performance',
      },
      {
        type: 'chart',
        title: 'Downtime Analysis',
        description: 'Downtime by reason and duration',
      },
    ],
  },
  {
    id: 'risk-assessment',
    name: 'Risk Assessment Report',
    description: 'Risk register, impact analysis, and mitigation status',
    category: 'project',
    icon: <AlertTriangle className="h-6 w-6" />,
    tags: ['risk', 'assessment', 'mitigation', 'management'],
    sections: [
      {
        type: 'text',
        title: 'Risk Summary',
        description: 'High-level risk overview',
        config: {
          content: 'Risk Assessment Report\nProject: {project_name}\nTotal Risks: {count}\nHigh Priority: {high_priority}',
        },
      },
      {
        type: 'chart',
        title: 'Risk Matrix',
        description: 'Visual risk matrix by likelihood and impact',
      },
      {
        type: 'table',
        title: 'Risk Register',
        description: 'Complete list of identified risks',
      },
      {
        type: 'table',
        title: 'Mitigation Status',
        description: 'Mitigation plans and implementation status',
      },
      {
        type: 'text',
        title: 'Recommendations',
        description: 'Risk management recommendations',
        config: {
          content: 'Key Recommendations:\n• Address high-priority risks immediately\n• Update risk register weekly\n',
        },
      },
    ],
  },
  {
    id: 'resource-utilization',
    name: 'Resource Utilization Report',
    description: 'Team capacity, allocation, and utilization metrics',
    category: 'project',
    icon: <Users className="h-6 w-6" />,
    tags: ['resources', 'capacity', 'utilization', 'team'],
    sections: [
      {
        type: 'text',
        title: 'Resource Overview',
        description: 'Summary of resource utilization',
        config: {
          content: 'Resource Utilization Report\nPeriod: {period}\nOverall Utilization: {utilization}%',
        },
      },
      {
        type: 'chart',
        title: 'Utilization by Team',
        description: 'Resource utilization comparison',
      },
      {
        type: 'table',
        title: 'Team Allocation',
        description: 'Detailed allocation by team member',
      },
      {
        type: 'chart',
        title: 'Capacity vs Demand',
        description: 'Capacity planning visualization',
      },
      {
        type: 'table',
        title: 'Utilization Details',
        description: 'Detailed utilization metrics by project',
      },
    ],
  },
  {
    id: 'lead-time-analysis',
    name: 'Lead Time Analysis',
    description: 'Lead times, cycle times, and delivery performance metrics',
    category: 'manufacturing',
    icon: <Clock className="h-6 w-6" />,
    tags: ['lead time', 'cycle time', 'delivery', 'performance'],
    sections: [
      {
        type: 'text',
        title: 'Lead Time Summary',
        description: 'Overview of delivery performance',
        config: {
          content: 'Lead Time Analysis Report\nPeriod: {period}\nAvg Lead Time: {avg_days} days\nOn-Time Delivery: {on_time}%',
        },
      },
      {
        type: 'chart',
        title: 'Lead Time Trends',
        description: 'Lead time trends over time',
      },
      {
        type: 'table',
        title: 'Lead Time by Process',
        description: 'Breakdown by process stage',
      },
      {
        type: 'chart',
        title: 'Delivery Performance',
        description: 'On-time delivery metrics',
      },
      {
        type: 'table',
        title: 'Bottleneck Analysis',
        description: 'Process bottlenecks and improvement opportunities',
      },
    ],
  },
  {
    id: 'general-report',
    name: 'Custom Report',
    description: 'Start with a blank template and build your custom report',
    category: 'general',
    icon: <FileText className="h-6 w-6" />,
    tags: ['custom', 'blank', 'flexible'],
    sections: [
      {
        type: 'text',
        title: 'Report Title',
        description: 'Add your report title',
        config: {
          content: 'Custom Report\nDate: {date}',
        },
      },
    ],
  },
];

// Category configuration
const CATEGORIES = [
  { value: 'all', label: 'All Templates', icon: <Layers className="h-4 w-4" /> },
  { value: 'manufacturing', label: 'Manufacturing', icon: <Package className="h-4 w-4" /> },
  { value: 'quality', label: 'Quality', icon: <CheckCircle className="h-4 w-4" /> },
  { value: 'project', label: 'Project', icon: <TrendingUp className="h-4 w-4" /> },
  { value: 'financial', label: 'Financial', icon: <DollarSign className="h-4 w-4" /> },
  { value: 'general', label: 'General', icon: <FileText className="h-4 w-4" /> },
];

interface TemplateGalleryProps {
  onSelectTemplate?: (template: ReportTemplate) => void;
  className?: string;
}

export const TemplateGallery: React.FC<TemplateGalleryProps> = ({
  onSelectTemplate,
  className,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [previewTemplate, setPreviewTemplate] = useState<ReportTemplate | null>(null);

  // Filter templates by category
  const filteredTemplates =
    selectedCategory === 'all'
      ? REPORT_TEMPLATES
      : REPORT_TEMPLATES.filter((t) => t.category === selectedCategory);

  // Handle template selection
  const handleUseTemplate = (template: ReportTemplate) => {
    if (onSelectTemplate) {
      onSelectTemplate(template);
    }
  };

  // Handle template preview
  const handlePreview = (template: ReportTemplate) => {
    setPreviewTemplate(template);
  };

  // Get section icon based on type
  const getSectionIcon = (section: TemplateSection) => {
    switch (section.type) {
      case 'table':
        return <ClipboardList className="h-4 w-4" />;
      case 'chart':
        return <BarChart3 className="h-4 w-4" />;
      case 'text':
        return <FileText className="h-4 w-4" />;
      case 'image':
        return <Layers className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
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
                {/* Section Count */}
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Layers className="h-4 w-4" />
                  <span>{template.sections.length} sections</span>
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
                  >
                    Preview
                  </Button>
                  <Button
                    size="sm"
                    className="flex-1"
                    onClick={() => handleUseTemplate(template)}
                  >
                    Use Template
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

                {/* Sections */}
                <div>
                  <h4 className="text-sm font-semibold mb-3">
                    Included Sections ({previewTemplate.sections.length})
                  </h4>
                  <div className="space-y-2">
                    {previewTemplate.sections.map((section, index) => (
                      <div
                        key={index}
                        className="flex items-start gap-3 p-3 rounded-lg border bg-card"
                      >
                        <div className="p-2 rounded-md bg-muted">
                          {getSectionIcon(section)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm">{section.title}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {section.description}
                          </div>
                          <div className="flex items-center gap-2 mt-2">
                            <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                              {section.type}
                            </span>
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
                >
                  Close
                </Button>
                <Button
                  onClick={() => {
                    handleUseTemplate(previewTemplate);
                    setPreviewTemplate(null);
                  }}
                >
                  Use This Template
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TemplateGallery;
