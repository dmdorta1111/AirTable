import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  useSortable,
  rectSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Plus,
  BarChart3,
  PieChart,
  LineChart,
  Table as TableIcon,
  Type,
  Trash2,
  GripVertical,
  Settings,
  Maximize2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { ChartConfigModal, ChartConfig } from './ChartConfigModal';
import { MetricConfigModal, MetricConfig } from './MetricConfigModal';
import { TextConfigModal, TextConfig } from './TextConfigModal';

// Widget types that can be added to the dashboard
export type WidgetType = 'chart' | 'pivot' | 'text' | 'metric';

// Chart sub-types
export type ChartType = 'line' | 'bar' | 'pie' | 'scatter' | 'gauge';

// Widget configuration
interface Widget {
  id: string;
  type: WidgetType;
  title: string;
  config?: {
    chartType?: ChartType;
    chartConfig?: ChartConfig;
    content?: string;
    [key: string]: unknown;
  };
  position: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
}

interface DashboardBuilderProps {
  initialWidgets?: Widget[];
  onSave?: (widgets: Widget[]) => void;
  onCancel?: () => void;
}

// Sortable widget item component
interface SortableWidgetProps {
  widget: Widget;
  onRemove: (id: string) => void;
  onConfigure: (id: string) => void;
  onResize: (id: string, dimensions: { width: number; height: number }) => void;
}

// Resize handle component
const ResizeHandle: React.FC<{ onMouseDown: (e: React.MouseEvent) => void }> = ({ onMouseDown }) => {
  return (
    <div
      className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize opacity-0 group-hover:opacity-100 transition-opacity"
      onMouseDown={onMouseDown}
    >
      <Maximize2 className="h-3 w-3 text-muted-foreground hover:text-primary" />
    </div>
  );
};

const SortableWidget: React.FC<SortableWidgetProps> = ({ widget, onRemove, onConfigure, onResize }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widget.id });

  const widgetRef = useRef<HTMLDivElement | null>(null);
  const [isResizing, setIsResizing] = useState(false);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  // Calculate grid column and row spans based on widget position
  const gridColumn = widget.position.w ? `span ${widget.position.w}` : 'span 1';
  const gridRow = widget.position.h ? `span ${widget.position.h}` : 'span 1';

  // Handle resize start
  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
  };

  // Handle resize using mouse events
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!widgetRef.current) return;

      const rect = widgetRef.current.getBoundingClientRect();
      const newWidth = e.clientX - rect.left;
      const newHeight = e.clientY - rect.top;

      // Calculate grid units (assuming minimum grid cell size)
      const gridCellWidth = rect.width / widget.position.w;
      const gridCellHeight = rect.height / widget.position.h;

      const newWidthUnits = Math.max(1, Math.round(newWidth / gridCellWidth));
      const newHeightUnits = Math.max(1, Math.round(newHeight / gridCellHeight));

      // Update widget dimensions
      onResize(widget.id, { width: newWidthUnits, height: newHeightUnits });
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, widget.id, widget.position.w, widget.position.h, onResize]);

  const getWidgetIcon = () => {
    switch (widget.type) {
      case 'chart':
        switch (widget.config?.chartType) {
          case 'line':
            return <LineChart className="h-5 w-5" />;
          case 'bar':
            return <BarChart3 className="h-5 w-5" />;
          case 'pie':
            return <PieChart className="h-5 w-5" />;
          default:
            return <BarChart3 className="h-5 w-5" />;
        }
      case 'pivot':
        return <TableIcon className="h-5 w-5" />;
      case 'text':
        return <Type className="h-5 w-5" />;
      case 'metric':
        return <BarChart3 className="h-5 w-5" />;
      default:
        return <BarChart3 className="h-5 w-5" />;
    }
  };

  const getWidgetContent = () => {
    switch (widget.type) {
      case 'chart':
        return (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              {getWidgetIcon()}
              <p className="mt-2 text-sm">
                {widget.config?.chartType ? `${widget.config.chartType} Chart` : 'Chart Widget'}
              </p>
              <p className="text-xs mt-1">Click settings to configure</p>
            </div>
          </div>
        );
      case 'pivot':
        return (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              {getWidgetIcon()}
              <p className="mt-2 text-sm">Pivot Table</p>
              <p className="text-xs mt-1">Click settings to configure</p>
            </div>
          </div>
        );
      case 'text':
        return (
          <div className="h-full p-4">
            <p className="text-sm text-muted-foreground">
              {widget.config?.content || 'Text widget - click settings to edit content'}
            </p>
          </div>
        );
      case 'metric':
        return (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl font-bold">0</div>
              <p className="text-sm text-muted-foreground mt-2">Metric Value</p>
              <p className="text-xs text-muted-foreground mt-1">Click settings to configure</p>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div
      ref={(node) => {
        setNodeRef(node);
        widgetRef.current = node;
      }}
      style={{
        ...style,
        gridColumn,
        gridRow,
      }}
      className="h-full group relative"
    >
      <Card className="h-full border-2 hover:border-primary/50 transition-colors relative">
        <CardHeader className="pb-3 flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2 flex-1">
            <div
              {...attributes}
              {...listeners}
              className="cursor-move hover:text-primary transition-colors"
            >
              <GripVertical className="h-4 w-4" />
            </div>
            <CardTitle className="text-sm font-medium">{widget.title}</CardTitle>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onConfigure(widget.id)}
            >
              <Settings className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive hover:text-destructive"
              onClick={() => onRemove(widget.id)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="h-[calc(100%-4rem)]">
          {getWidgetContent()}
        </CardContent>
        <ResizeHandle onMouseDown={handleResizeStart} />
      </Card>
    </div>
  );
};

// Main DashboardBuilder component
export const DashboardBuilder: React.FC<DashboardBuilderProps> = ({
  initialWidgets = [],
  onSave,
  onCancel,
}) => {
  const [widgets, setWidgets] = useState<Widget[]>(initialWidgets);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [configuringWidgetId, setConfiguringWidgetId] = useState<string | null>(null);
  const [configModalType, setConfigModalType] = useState<'chart' | 'metric' | 'text' | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      setWidgets((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id);
        const newIndex = items.findIndex((item) => item.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }

    setActiveId(null);
  };

  const addWidget = (type: WidgetType, chartType?: ChartType) => {
    const newWidget: Widget = {
      id: `widget-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      title: type === 'chart'
        ? `${chartType ? chartType.charAt(0).toUpperCase() + chartType.slice(1) : 'Chart'} Widget`
        : `${type.charAt(0).toUpperCase() + type.slice(1)} Widget`,
      config: chartType ? { chartType } : {},
      position: { x: 0, y: 0, w: 6, h: 4 },
    };
    setWidgets([...widgets, newWidget]);
  };

  const removeWidget = (id: string) => {
    setWidgets(widgets.filter((w) => w.id !== id));
  };

  const handleResize = useCallback((id: string, dimensions: { width: number; height: number }) => {
    setWidgets((prev) =>
      prev.map((widget) =>
        widget.id === id
          ? {
              ...widget,
              position: {
                ...widget.position,
                w: dimensions.width,
                h: dimensions.height,
              },
            }
          : widget
      )
    );
  }, []);

  const configureWidget = useCallback((id: string) => {
    const widget = widgets.find((w) => w.id === id);
    if (widget) {
      setConfiguringWidgetId(id);
      if (widget.type === 'metric') {
        setConfigModalType('metric');
      } else if (widget.type === 'text') {
        setConfigModalType('text');
      } else {
        setConfigModalType('chart');
      }
      setConfigModalOpen(true);
    }
  }, [widgets]);

  const handleChartConfigSave = useCallback((chartConfig: ChartConfig) => {
    if (configuringWidgetId) {
      setWidgets((prev) =>
        prev.map((widget) =>
          widget.id === configuringWidgetId
            ? {
                ...widget,
                title: chartConfig.title,
                config: {
                  ...widget.config,
                  chartType: chartConfig.chartType,
                  chartConfig,
                },
              }
            : widget
        )
      );
    }
    setConfigModalOpen(false);
    setConfiguringWidgetId(null);
    setConfigModalType(null);
  }, [configuringWidgetId]);

  const handleMetricConfigSave = useCallback((metricConfig: MetricConfig) => {
    if (configuringWidgetId) {
      setWidgets((prev) =>
        prev.map((widget) =>
          widget.id === configuringWidgetId
            ? {
                ...widget,
                title: metricConfig.title,
                config: {
                  ...widget.config,
                  metricConfig,
                },
              }
            : widget
        )
      );
    }
    setConfigModalOpen(false);
    setConfiguringWidgetId(null);
    setConfigModalType(null);
  }, [configuringWidgetId]);

  const handleTextConfigSave = useCallback((textConfig: TextConfig) => {
    if (configuringWidgetId) {
      setWidgets((prev) =>
        prev.map((widget) =>
          widget.id === configuringWidgetId
            ? {
                ...widget,
                title: textConfig.title,
                config: {
                  ...widget.config,
                  content: textConfig.content,
                  textConfig,
                },
              }
            : widget
        )
      );
    }
    setConfigModalOpen(false);
    setConfiguringWidgetId(null);
    setConfigModalType(null);
  }, [configuringWidgetId]);

  const handleConfigModalClose = useCallback(() => {
    setConfigModalOpen(false);
    setConfiguringWidgetId(null);
    setConfigModalType(null);
  }, []);

  const handleSave = () => {
    if (onSave) {
      onSave(widgets);
    }
  };

  const activeWidget = activeId ? widgets.find((w) => w.id === activeId) : null;

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="border-b bg-background p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <h2 className="text-lg font-semibold truncate">Dashboard Builder</h2>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="flex-shrink-0">
                <Plus className="mr-2 h-4 w-4" />
                <span className="hidden sm:inline">Add Widget</span>
                <span className="sm:hidden">Add</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuItem onClick={() => addWidget('chart', 'line')}>
                <LineChart className="mr-2 h-4 w-4" />
                Line Chart
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => addWidget('chart', 'bar')}>
                <BarChart3 className="mr-2 h-4 w-4" />
                Bar Chart
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => addWidget('chart', 'pie')}>
                <PieChart className="mr-2 h-4 w-4" />
                Pie Chart
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => addWidget('pivot')}>
                <TableIcon className="mr-2 h-4 w-4" />
                Pivot Table
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => addWidget('text')}>
                <Type className="mr-2 h-4 w-4" />
                Text Widget
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => addWidget('metric')}>
                <BarChart3 className="mr-2 h-4 w-4" />
                Metric Widget
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          {onCancel && (
            <Button variant="outline" onClick={onCancel} className="flex-1 sm:flex-initial">
              Cancel
            </Button>
          )}
          <Button onClick={handleSave} className="flex-1 sm:flex-initial">
            Save Dashboard
          </Button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-auto bg-muted/20 p-4 md:p-6">
        {widgets.length === 0 ? (
          <div className="h-full flex items-center justify-center p-4">
            <div className="text-center max-w-md">
              <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Empty Dashboard</h3>
              <p className="text-muted-foreground mb-4 text-sm md:text-base">
                Add widgets to get started building your dashboard
              </p>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button className="w-full sm:w-auto">
                    <Plus className="mr-2 h-4 w-4" />
                    <span>Add Your First Widget</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="center" className="w-56">
                  <DropdownMenuItem onClick={() => addWidget('chart', 'line')}>
                    <LineChart className="mr-2 h-4 w-4" />
                    Line Chart
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => addWidget('chart', 'bar')}>
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Bar Chart
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => addWidget('chart', 'pie')}>
                    <PieChart className="mr-2 h-4 w-4" />
                    Pie Chart
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => addWidget('pivot')}>
                    <TableIcon className="mr-2 h-4 w-4" />
                    Pivot Table
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => addWidget('text')}>
                    <Type className="mr-2 h-4 w-4" />
                    Text Widget
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => addWidget('metric')}>
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Metric Widget
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={widgets.map((w) => w.id)}
              strategy={rectSortingStrategy}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 min-h-full auto-rows-min">
                {widgets.map((widget) => (
                  <div key={widget.id} className="min-h-[16rem]">
                    <SortableWidget
                      widget={widget}
                      onRemove={removeWidget}
                      onConfigure={configureWidget}
                      onResize={handleResize}
                    />
                  </div>
                ))}
              </div>
            </SortableContext>
            <DragOverlay>
              {activeWidget ? (
                <div
                  className="opacity-50"
                  style={{
                    gridColumn: activeWidget.position.w ? `span ${activeWidget.position.w}` : 'span 1',
                    gridRow: activeWidget.position.h ? `span ${activeWidget.position.h}` : 'span 1',
                  }}
                >
                  <Card className={cn("h-full border-2 border-primary")}>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <GripVertical className="h-4 w-4" />
                        {activeWidget.title}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="h-[calc(100%-4rem)]">
                      <div className="h-full flex items-center justify-center text-muted-foreground">
                        Moving...
                      </div>
                    </CardContent>
                  </Card>
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        )}
      </div>

      {/* Chart Configuration Modal */}
      {configuringWidgetId && configModalType === 'chart' && (
        <ChartConfigModal
          open={configModalOpen}
          onClose={handleConfigModalClose}
          onSave={handleChartConfigSave}
          initialConfig={widgets.find((w) => w.id === configuringWidgetId)?.config?.chartConfig}
          tables={[
            // Mock data - in real implementation, this would come from API
            { id: 'table-1', name: 'Sales Data' },
            { id: 'table-2', name: 'Customer Info' },
            { id: 'table-3', name: 'Products' },
          ]}
          fields={[
            // Mock data - in real implementation, this would come from API
            { id: 'field-1', name: 'Revenue', type: 'number' },
            { id: 'field-2', name: 'Date', type: 'date' },
            { id: 'field-3', name: 'Category', type: 'text' },
            { id: 'field-4', name: 'Quantity', type: 'number' },
            { id: 'field-5', name: 'Region', type: 'text' },
          ]}
        />
      )}

      {/* Metric Configuration Modal */}
      {configuringWidgetId && configModalType === 'metric' && (
        <MetricConfigModal
          open={configModalOpen}
          onClose={handleConfigModalClose}
          onSave={handleMetricConfigSave}
          initialConfig={widgets.find((w) => w.id === configuringWidgetId)?.config?.metricConfig as Partial<MetricConfig> | undefined}
          tables={[
            // Mock data - in real implementation, this would come from API
            { id: 'table-1', name: 'Sales Data' },
            { id: 'table-2', name: 'Customer Info' },
            { id: 'table-3', name: 'Products' },
          ]}
          fields={[
            // Mock data - in real implementation, this would come from API
            { id: 'field-1', name: 'Revenue', type: 'number' },
            { id: 'field-2', name: 'Date', type: 'date' },
            { id: 'field-3', name: 'Category', type: 'text' },
            { id: 'field-4', name: 'Quantity', type: 'number' },
            { id: 'field-5', name: 'Region', type: 'text' },
            { id: 'field-6', name: 'Profit', type: 'currency' },
            { id: 'field-7', name: 'Completion', type: 'percent' },
          ]}
        />
      )}

      {/* Text Configuration Modal */}
      {configuringWidgetId && configModalType === 'text' && (
        <TextConfigModal
          open={configModalOpen}
          onClose={handleConfigModalClose}
          onSave={handleTextConfigSave}
          initialConfig={widgets.find((w) => w.id === configuringWidgetId)?.config?.textConfig as Partial<TextConfig> | undefined}
        />
      )}
    </div>
  );
};

export default DashboardBuilder;
