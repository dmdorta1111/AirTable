import React, { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from '@dnd-kit/core';
import { useDraggable, useDroppable } from '@dnd-kit/core';

interface KanbanViewProps {
  data: any[];
  fields: any[];
  onRecordUpdate?: (recordId: string, fieldId: string, value: any) => void;
}

interface DraggableCardProps {
  item: any;
  fields: any[];
}

const DraggableCard: React.FC<DraggableCardProps> = ({ item, fields }) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: item.id,
    data: {
      item,
    },
  });

  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        opacity: isDragging ? 0.5 : 1,
      }
    : undefined;

  // Access values from the TableRecord structure
  const recordValues = (item as any).values || item.data || item;

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes}>
      <Card className="cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow">
        <CardHeader className="p-3 pb-0">
          <CardTitle className="text-sm font-medium">
            {recordValues[fields[0]?.name] || 'Untitled'}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3 text-xs text-muted-foreground">
          {fields.slice(1, 4).map(field => (
            <div key={field.id} className="truncate">
              <span className="opacity-70 mr-1">{field.name}:</span>
              {String(recordValues[field.name] || '-')}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};

interface DroppableColumnProps {
  groupName: string;
  items: any[];
  fields: any[];
  onAddRecord?: () => void;
}

const DroppableColumn: React.FC<DroppableColumnProps> = ({ groupName, items, fields, onAddRecord }) => {
  const { setNodeRef, isOver } = useDroppable({
    id: groupName,
    data: {
      groupName,
    },
  });

  return (
    <div
      ref={setNodeRef}
      className={`min-w-[280px] w-[280px] flex flex-col gap-3 ${
        isOver ? 'bg-accent/20 rounded-lg' : ''
      }`}
    >
      <div className="flex items-center justify-between px-2">
        <span className="font-semibold text-sm uppercase text-muted-foreground">
          {groupName} <span className="ml-1 text-xs opacity-70">({items.length})</span>
        </span>
      </div>
      <div className="flex-1 flex flex-col gap-2 overflow-y-auto pb-4">
        {items.map(item => (
          <DraggableCard key={item.id} item={item} fields={fields} />
        ))}
        <button 
          onClick={onAddRecord}
          className="w-full py-2 text-xs text-muted-foreground border border-dashed rounded-md hover:bg-background"
        >
          + New Record
        </button>
      </div>
    </div>
  );
};

export const KanbanView: React.FC<KanbanViewProps> = ({ data, fields, onRecordUpdate }) => {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  // Simplified Kanban: Groups by the first 'select' field found, or just shows a list if none.
  const groupByField = fields.find(f => f.type === 'select' || f.type === 'singleSelect');

  // Group records by the select field value
  const groupedData = useMemo(() => {
    if (!groupByField) {
      return {};
    }

    const options = groupByField.options?.choices || [];
    const groups: Record<string, any[]> = {};

    // Initialize all option groups
    options.forEach((opt: any) => {
      groups[opt.name || opt] = [];
    });
    // Add unassigned group
    groups['Unassigned'] = [];

    // Group records
    data.forEach(item => {
      // TableRecord stores values in a 'values' or 'data' object
      const recordValues = (item as any).values || item.data || item;
      const val = recordValues[groupByField.name];
      if (val && groups[val]) {
        groups[val].push(item);
      } else {
        groups['Unassigned'].push(item);
      }
    });

    return groups;
  }, [data, groupByField]);

  if (!groupByField) {
    return (
      <div className="p-4 text-muted-foreground">
        Please add a Single Select field to use Kanban view.
      </div>
    );
  }

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over || !onRecordUpdate) return;

    const recordId = active.id as string;
    const newGroupName = over.id as string;
    const activeItem = active.data.current?.item;

    if (!activeItem) return;

    // Get current value from the record
    const recordValues = (activeItem as any).values || activeItem.data || activeItem;
    const currentValue = recordValues[groupByField.name];
    const newValue = newGroupName === 'Unassigned' ? null : newGroupName;

    // Only update if the group changed
    if (currentValue !== newValue) {
      onRecordUpdate(recordId, groupByField.id, newValue);
    }
  };

  const activeItem = activeId ? data.find(item => item.id === activeId) : null;
  const activeRecordValues = activeItem ? ((activeItem as any).values || activeItem.data || activeItem) : null;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-full overflow-x-auto gap-4 p-4 bg-muted/10">
        {Object.entries(groupedData).map(([groupName, items]) => (
          <DroppableColumn
            key={groupName}
            groupName={groupName}
            items={items}
            fields={fields}
          />
        ))}
      </div>
      <DragOverlay>
        {activeItem && activeRecordValues ? (
          <Card className="cursor-grabbing shadow-lg">
            <CardHeader className="p-3 pb-0">
              <CardTitle className="text-sm font-medium">
                {activeRecordValues[fields[0]?.name] || 'Untitled'}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-3 text-xs text-muted-foreground">
              {fields.slice(1, 4).map(field => (
                <div key={field.id} className="truncate">
                  <span className="opacity-70 mr-1">{field.name}:</span>
                  {String(activeRecordValues[field.name] || '-')}
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
};
