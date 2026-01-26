import React, { useState } from 'react';
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
}

const SortableWidget: React.FC<SortableWidgetProps> = ({ widget, onRemove, onConfigure }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widget.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

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
    <div ref={setNodeRef} style={style} className="h-full">
      <Card className="h-full border-2 hover:border-primary/50 transition-colors">
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

  const configureWidget = (id: string) => {
    // TODO: Open widget configuration modal in later subtask
    void id;
  };

  const handleSave = () => {
    if (onSave) {
      onSave(widgets);
    }
  };

  const activeWidget = activeId ? widgets.find((w) => w.id === activeId) : null;

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="border-b bg-background p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Dashboard Builder</h2>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Widget
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
        <div className="flex items-center gap-2">
          {onCancel && (
            <Button variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button onClick={handleSave}>
            Save Dashboard
          </Button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-auto bg-muted/20 p-6">
        {widgets.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Empty Dashboard</h3>
              <p className="text-muted-foreground mb-4">
                Add widgets to get started building your dashboard
              </p>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Your First Widget
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
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 min-h-full">
                {widgets.map((widget) => (
                  <div key={widget.id} className="h-80">
                    <SortableWidget
                      widget={widget}
                      onRemove={removeWidget}
                      onConfigure={configureWidget}
                    />
                  </div>
                ))}
              </div>
            </SortableContext>
            <DragOverlay>
              {activeWidget ? (
                <div className="h-80 opacity-50">
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
    </div>
  );
};

export default DashboardBuilder;
