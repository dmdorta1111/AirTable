import React from 'react';
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

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes}>
      <Card className="cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow">
        <CardHeader className="p-3 pb-0">
          <CardTitle className="text-sm font-medium">
            {item[fields[0].name] || 'Untitled'}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3 text-xs text-muted-foreground">
          {fields.slice(1, 4).map(field => (
            <div key={field.id} className="truncate">
              <span className="opacity-70 mr-1">{field.name}:</span>
              {String(item[field.name] || '-')}
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
}

const DroppableColumn: React.FC<DroppableColumnProps> = ({ groupName, items, fields }) => {
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
        <button className="w-full py-2 text-xs text-muted-foreground border border-dashed rounded-md hover:bg-background">
          + New Record
        </button>
      </div>
    </div>
  );
};

export const KanbanView: React.FC<KanbanViewProps> = ({ data, fields, onRecordUpdate }) => {
  const [activeId, setActiveId] = React.useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  // Simplified Kanban: Groups by the first 'select' field found, or just shows a list if none.
  const groupByField = fields.find(f => f.type === 'select' || f.type === 'singleSelect');

  if (!groupByField) {
    return (
        <div className="p-4 text-muted-foreground">
            Please add a Single Select field to use Kanban view.
        </div>
    );
  }

  const options = groupByField.options?.choices || [];
  const groupedData: Record<string, any[]> = {};

  options.forEach((opt: any) => {
    groupedData[opt.name || opt] = [];
  });
  // Also catch unassigned
  groupedData['Unassigned'] = [];

  data.forEach(item => {
    const val = item[groupByField.name];
    if (val && groupedData[val]) {
        groupedData[val].push(item);
    } else {
        groupedData['Unassigned'].push(item);
    }
  });

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

    // Only update if the group changed
    const currentValue = activeItem[groupByField.name];
    const newValue = newGroupName === 'Unassigned' ? null : newGroupName;

    if (currentValue !== newValue) {
      onRecordUpdate(recordId, groupByField.id, newValue);
    }
  };

  const activeItem = activeId ? data.find(item => item.id === activeId) : null;

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
        {activeItem ? (
          <Card className="cursor-grabbing shadow-lg">
            <CardHeader className="p-3 pb-0">
              <CardTitle className="text-sm font-medium">
                {activeItem[fields[0].name] || 'Untitled'}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-3 text-xs text-muted-foreground">
              {fields.slice(1, 4).map(field => (
                <div key={field.id} className="truncate">
                  <span className="opacity-70 mr-1">{field.name}:</span>
                  {String(activeItem[field.name] || '-')}
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
};
