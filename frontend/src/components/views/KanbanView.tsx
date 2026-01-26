import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll';
import { fetchRecordsCursor } from '@/lib/api';
import { Loader2 } from 'lucide-react';

interface KanbanViewProps {
  tableId: string;
  fields: any[];
}

export const KanbanView: React.FC<KanbanViewProps> = ({ tableId, fields }) => {
  // Find the first select field to group by
  const groupByField = fields.find(f => f.type === 'select' || f.type === 'singleSelect');

  // Set up infinite scroll with cursor-based pagination
  // Wrap fetchRecordsCursor to match the expected signature
  const fetchFn = useMemo(
    () => (cursor: string | null, limit: number) => fetchRecordsCursor(tableId, cursor, limit),
    [tableId]
  );

  const { records, isLoading, hasNext, sentinelRef, error } = useInfiniteScroll({
    tableId,
    fetchFn,
    initialLimit: 50,
    threshold: 0.2,
  });

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
    records.forEach(item => {
      // TableRecord stores values in a 'values' object
      const recordValues = (item as any).values || item;
      const val = recordValues[groupByField.name];
      if (val && groups[val]) {
        groups[val].push(item);
      } else {
        groups['Unassigned'].push(item);
      }
    });

    return groups;
  }, [records, groupByField]);

  // Show error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <p className="text-red-500 mb-2">Error loading records</p>
          <p className="text-sm">{error.message}</p>
        </div>
      </div>
    );
  }

  // Show message if no select field exists
  if (!groupByField) {
    return (
      <div className="p-4 text-muted-foreground">
        Please add a Single Select field to use Kanban view.
      </div>
    );
  }

  return (
    <div className="flex h-full overflow-x-auto gap-4 p-4 bg-muted/10">
      {Object.entries(groupedData).map(([groupName, items]) => (
        <div key={groupName} className="min-w-[280px] w-[280px] flex flex-col gap-3">
          <div className="flex items-center justify-between px-2">
            <span className="font-semibold text-sm uppercase text-muted-foreground">
              {groupName} <span className="ml-1 text-xs opacity-70">({items.length})</span>
            </span>
          </div>
          <div className="flex-1 flex flex-col gap-2 overflow-y-auto pb-4">
            {items.map(item => {
              // Access values from the TableRecord structure
              const recordValues = (item as any).values || item;
              return (
                <Card key={item.id} className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardHeader className="p-3 pb-0">
                    <CardTitle className="text-sm font-medium">
                      {recordValues[fields[0].name] || 'Untitled'}
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
              );
            })}
            <button className="w-full py-2 text-xs text-muted-foreground border border-dashed rounded-md hover:bg-background">
              + New Record
            </button>
          </div>
        </div>
      ))}

      {/* Sentinel element for infinite scroll - positioned at the end of the kanban board */}
      {hasNext && (
        <div ref={sentinelRef} className="min-w-[280px] flex items-center justify-center">
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading more...
            </div>
          )}
        </div>
      )}
    </div>
  );
};
