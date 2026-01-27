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
  Table as TableIcon,
  BarChart3,
  Type,
  Image as ImageIcon,
  Trash2,
  GripVertical,
  Settings,
  FileText,
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

// Section types that can be added to the report
export type SectionType = 'table' | 'chart' | 'text' | 'image';

// Report section configuration
export interface ReportSection {
  id: string;
  type: SectionType;
  title: string;
  config?: {
    content?: string;
    imageUrl?: string;
    dataSourceId?: string;
    [key: string]: unknown;
  };
  position: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
}

interface CustomReportBuilderProps {
  initialSections?: ReportSection[];
  onSave?: (sections: ReportSection[]) => void;
  onCancel?: () => void;
}

// Sortable section item component
interface SortableSectionProps {
  section: ReportSection;
  onRemove: (id: string) => void;
  onConfigure: (id: string) => void;
}

const SortableSection: React.FC<SortableSectionProps> = ({ section, onRemove, onConfigure }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: section.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const getSectionIcon = () => {
    switch (section.type) {
      case 'table':
        return <TableIcon className="h-5 w-5" />;
      case 'chart':
        return <BarChart3 className="h-5 w-5" />;
      case 'text':
        return <Type className="h-5 w-5" />;
      case 'image':
        return <ImageIcon className="h-5 w-5" />;
      default:
        return <FileText className="h-5 w-5" />;
    }
  };

  const getSectionContent = () => {
    switch (section.type) {
      case 'table':
        return (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              {getSectionIcon()}
              <p className="mt-2 text-sm">Table Section</p>
              <p className="text-xs mt-1">Click settings to configure data source</p>
            </div>
          </div>
        );
      case 'chart':
        return (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              {getSectionIcon()}
              <p className="mt-2 text-sm">Chart Section</p>
              <p className="text-xs mt-1">Click settings to configure chart</p>
            </div>
          </div>
        );
      case 'text':
        return (
          <div className="h-full p-4">
            <p className="text-sm text-muted-foreground">
              {section.config?.content || 'Text section - click settings to edit content'}
            </p>
          </div>
        );
      case 'image':
        return (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              {getSectionIcon()}
              <p className="mt-2 text-sm">Image Section</p>
              <p className="text-xs mt-1">Click settings to add image</p>
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
            <CardTitle className="text-sm font-medium">{section.title}</CardTitle>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => onConfigure(section.id)}
            >
              <Settings className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive hover:text-destructive"
              onClick={() => onRemove(section.id)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="h-[calc(100%-4rem)]">
          {getSectionContent()}
        </CardContent>
      </Card>
    </div>
  );
};

// Main CustomReportBuilder component
export const CustomReportBuilder: React.FC<CustomReportBuilderProps> = ({
  initialSections = [],
  onSave,
  onCancel,
}) => {
  const [sections, setSections] = useState<ReportSection[]>(initialSections);
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
      setSections((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id);
        const newIndex = items.findIndex((item) => item.id === over.id);
        return arrayMove(items, oldIndex, newIndex);
      });
    }

    setActiveId(null);
  };

  const addSection = (type: SectionType) => {
    const newSection: ReportSection = {
      id: `section-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      title: `${type.charAt(0).toUpperCase() + type.slice(1)} Section`,
      config: {},
      position: { x: 0, y: 0, w: 6, h: 4 },
    };
    setSections([...sections, newSection]);
  };

  const removeSection = (id: string) => {
    setSections(sections.filter((s) => s.id !== id));
  };

  const configureSection = (id: string) => {
    // TODO: Open section configuration modal in later subtask
    void id;
  };

  const handleSave = () => {
    if (onSave) {
      onSave(sections);
    }
  };

  const activeSection = activeId ? sections.find((s) => s.id === activeId) : null;

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="border-b bg-background p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">Report Builder</h2>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Plus className="mr-2 h-4 w-4" />
                Add Section
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuItem onClick={() => addSection('table')}>
                <TableIcon className="mr-2 h-4 w-4" />
                Table Section
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => addSection('chart')}>
                <BarChart3 className="mr-2 h-4 w-4" />
                Chart Section
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => addSection('text')}>
                <Type className="mr-2 h-4 w-4" />
                Text Section
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => addSection('image')}>
                <ImageIcon className="mr-2 h-4 w-4" />
                Image Section
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
            Save Report
          </Button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1 overflow-auto bg-muted/20 p-6">
        {sections.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Empty Report</h3>
              <p className="text-muted-foreground mb-4">
                Add sections to get started building your custom report
              </p>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Your First Section
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="center" className="w-56">
                  <DropdownMenuItem onClick={() => addSection('table')}>
                    <TableIcon className="mr-2 h-4 w-4" />
                    Table Section
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => addSection('chart')}>
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Chart Section
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => addSection('text')}>
                    <Type className="mr-2 h-4 w-4" />
                    Text Section
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => addSection('image')}>
                    <ImageIcon className="mr-2 h-4 w-4" />
                    Image Section
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
              items={sections.map((s) => s.id)}
              strategy={rectSortingStrategy}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 min-h-full">
                {sections.map((section) => (
                  <div key={section.id} className="h-80">
                    <SortableSection
                      section={section}
                      onRemove={removeSection}
                      onConfigure={configureSection}
                    />
                  </div>
                ))}
              </div>
            </SortableContext>
            <DragOverlay>
              {activeSection ? (
                <div className="h-80 opacity-50">
                  <Card className={cn("h-full border-2 border-primary")}>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <GripVertical className="h-4 w-4" />
                        {activeSection.title}
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

export default CustomReportBuilder;
