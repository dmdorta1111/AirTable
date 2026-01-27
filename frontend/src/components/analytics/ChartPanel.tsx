import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChartWidget, ChartDataPoint, ChartConfig } from './ChartWidget';
import { BarChart3, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

// Chart item configuration
export interface ChartItem {
  id: string;
  data: ChartDataPoint[];
  config: ChartConfig;
}

interface ChartPanelProps {
  charts: ChartItem[];
  className?: string;
  isLoading?: boolean;
  error?: string;
  title?: string;
  columns?: 1 | 2 | 3 | 4; // Number of columns in the grid
  height?: string; // Height for each chart widget
}

// Grid column mappings
const getColumnClasses = (columns: 1 | 2 | 3 | 4) => {
  switch (columns) {
    case 1:
      return 'grid-cols-1';
    case 2:
      return 'grid-cols-1 md:grid-cols-2';
    case 3:
      return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
    case 4:
      return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';
    default:
      return 'grid-cols-1 md:grid-cols-2';
  }
};

export const ChartPanel: React.FC<ChartPanelProps> = ({
  charts,
  className,
  isLoading = false,
  error,
  title,
  columns = 2,
  height = '300px',
}) => {
  const gridClasses = getColumnClasses(columns);

  // Render loading state
  if (isLoading) {
    return (
      <Card className={cn('w-full', className)}>
        <CardHeader>
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              {title}
            </CardTitle>
          )}
        </CardHeader>
        <CardContent>
          <div className={cn('grid gap-4', gridClasses)}>
            {Array.from({ length: columns }).map((_, index) => (
              <div
                key={`skeleton-${index}`}
                className="space-y-3 p-4 border rounded-lg"
                style={{ height }}
              >
                <div className="h-4 bg-muted animate-pulse rounded w-3/4" />
                <div className="h-4 bg-muted animate-pulse rounded w-1/2" />
                <div className="flex-1 bg-muted animate-pulse rounded mt-4" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render error state
  if (error) {
    return (
      <Card className={cn('w-full border-destructive', className)}>
        <CardHeader>
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              {title}
            </CardTitle>
          )}
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center text-destructive py-8">
            <div className="text-center space-y-2">
              <AlertCircle className="h-8 w-8 mx-auto" />
              <p className="text-sm font-medium">Chart Panel Error</p>
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render empty state
  if (!charts || charts.length === 0) {
    return (
      <Card className={cn('w-full', className)}>
        <CardHeader>
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              {title}
            </CardTitle>
          )}
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center text-muted-foreground py-8">
            <div className="text-center">
              <BarChart3 className="h-8 w-8 mx-auto mb-2" />
              <p className="text-sm">No charts to display</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render chart panel
  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        {title && (
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            {title}
          </CardTitle>
        )}
      </CardHeader>
      <CardContent>
        <div className={cn('grid gap-4', gridClasses)}>
          {charts.map((chartItem) => (
            <div key={chartItem.id} style={{ height }}>
              <ChartWidget
                data={chartItem.data}
                config={chartItem.config}
                className="h-full"
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default ChartPanel;
