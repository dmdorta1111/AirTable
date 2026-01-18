import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface KanbanViewProps {
  data: any[];
  fields: any[];
}

export const KanbanView: React.FC<KanbanViewProps> = ({ data, fields }) => {
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
                    {items.map(item => (
                        <Card key={item.id} className="cursor-pointer hover:shadow-md transition-shadow">
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
                    ))}
                    <button className="w-full py-2 text-xs text-muted-foreground border border-dashed rounded-md hover:bg-background">
                        + New Record
                    </button>
                </div>
            </div>
        ))}
    </div>
  );
};
