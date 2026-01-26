import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
} from 'recharts';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import {
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  Scatter as ScatterIcon,
  Gauge,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Chart types supported
export type ChartType = 'line' | 'bar' | 'pie' | 'scatter' | 'gauge';

// Data point interface
export interface ChartDataPoint {
  name: string;
  value: number;
  [key: string]: string | number; // Allow additional fields
}

// Chart configuration
export interface ChartConfig {
  type: ChartType;
  dataKey?: string; // Key to use for the data value (default: 'value')
  nameKey?: string; // Key to use for the label (default: 'name')
  colors?: string[]; // Custom colors for the chart
  showGrid?: boolean; // Show grid lines (default: true)
  showLegend?: boolean; // Show legend (default: true)
  showTooltip?: boolean; // Show tooltip (default: true)
  title?: string; // Chart title
  description?: string; // Chart description
  xAxisLabel?: string; // X-axis label
  yAxisLabel?: string; // Y-axis label
  gaugeMin?: number; // Gauge minimum value (default: 0)
  gaugeMax?: number; // Gauge maximum value (default: 100)
  gaugeThresholds?: { // Gauge color thresholds
    low: number;
    medium: number;
    high: number;
  };
}

interface ChartWidgetProps {
  data: ChartDataPoint[];
  config: ChartConfig;
  className?: string;
  isLoading?: boolean;
  error?: string;
}

// Default color palette
const DEFAULT_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#06b6d4', // cyan-500
  '#f97316', // orange-500
];

// Gauge color thresholds (default)
const DEFAULT_GAUGE_THRESHOLDS = {
  low: 33,
  medium: 66,
  high: 100,
};

// Helper to get gauge color based on value
const getGaugeColor = (value: number, thresholds = DEFAULT_GAUGE_THRESHOLDS) => {
  if (value <= thresholds.low) return '#ef4444'; // red-500
  if (value <= thresholds.medium) return '#f59e0b'; // amber-500
  return '#10b981'; // green-500
};

// Render chart icon based on type
const getChartIcon = (type: ChartType) => {
  switch (type) {
    case 'line':
      return <LineChartIcon className="h-5 w-5" />;
    case 'bar':
      return <BarChart3 className="h-5 w-5" />;
    case 'pie':
      return <PieChartIcon className="h-5 w-5" />;
    case 'scatter':
      return <ScatterIcon className="h-5 w-5" />;
    case 'gauge':
      return <Gauge className="h-5 w-5" />;
    default:
      return <BarChart3 className="h-5 w-5" />;
  }
};

export const ChartWidget: React.FC<ChartWidgetProps> = ({
  data,
  config,
  className,
  isLoading = false,
  error,
}) => {
  const {
    type,
    dataKey = 'value',
    nameKey = 'name',
    colors = DEFAULT_COLORS,
    showGrid = true,
    showLegend = true,
    showTooltip = true,
    title,
    description,
    xAxisLabel,
    yAxisLabel,
    gaugeMin = 0,
    gaugeMax = 100,
    gaugeThresholds = DEFAULT_GAUGE_THRESHOLDS,
  } = config;

  // Transform data for gauge chart
  const gaugeData = useMemo(() => {
    if (type !== 'gauge' || data.length === 0) return [];

    const value = Number(data[0][dataKey] || 0);
    const percentage = ((value - gaugeMin) / (gaugeMax - gaugeMin)) * 100;

    return [
      {
        name: data[0][nameKey],
        value: Math.max(0, Math.min(100, percentage)),
        fill: getGaugeColor(percentage, gaugeThresholds),
      },
    ];
  }, [data, type, dataKey, nameKey, gaugeMin, gaugeMax, gaugeThresholds]);

  // Render loading state
  if (isLoading) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              {getChartIcon(type)}
              {title}
            </CardTitle>
          )}
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
        <CardContent className="h-[calc(100%-5rem)]">
          <div className="h-full flex items-center justify-center">
            <div className="space-y-3 w-full">
              <div className="h-4 bg-muted animate-pulse rounded w-3/4 mx-auto" />
              <div className="h-4 bg-muted animate-pulse rounded w-1/2 mx-auto" />
              <div className="h-32 bg-muted animate-pulse rounded" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render error state
  if (error) {
    return (
      <Card className={cn('h-full border-destructive', className)}>
        <CardHeader>
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              {getChartIcon(type)}
              {title}
            </CardTitle>
          )}
        </CardHeader>
        <CardContent className="h-[calc(100%-5rem)]">
          <div className="h-full flex items-center justify-center text-destructive">
            <div className="text-center space-y-2">
              <AlertCircle className="h-8 w-8 mx-auto" />
              <p className="text-sm font-medium">Chart Error</p>
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render empty state
  if (!data || data.length === 0) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              {getChartIcon(type)}
              {title}
            </CardTitle>
          )}
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
        <CardContent className="h-[calc(100%-5rem)]">
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              {getChartIcon(type)}
              <p className="mt-2 text-sm">No data available</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render chart based on type
  const renderChart = () => {
    switch (type) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              {showGrid && <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />}
              <XAxis
                dataKey={nameKey}
                label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined}
                className="text-xs"
              />
              <YAxis
                label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
                className="text-xs"
              />
              {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }} />}
              {showLegend && <Legend />}
              <Line
                type="monotone"
                dataKey={dataKey}
                stroke={colors[0]}
                strokeWidth={2}
                dot={{ fill: colors[0], r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'bar':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              {showGrid && <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />}
              <XAxis
                dataKey={nameKey}
                label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined}
                className="text-xs"
              />
              <YAxis
                label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
                className="text-xs"
              />
              {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }} />}
              {showLegend && <Legend />}
              <Bar dataKey={dataKey} radius={[8, 8, 0, 0]}>
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        );

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }} />}
              {showLegend && <Legend />}
              <Pie
                data={data}
                dataKey={dataKey}
                nameKey={nameKey}
                cx="50%"
                cy="50%"
                outerRadius="80%"
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {data.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        );

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart>
              {showGrid && <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />}
              <XAxis
                type="number"
                dataKey={nameKey}
                label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined}
                className="text-xs"
              />
              <YAxis
                type="number"
                dataKey={dataKey}
                label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
                className="text-xs"
              />
              {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }} />}
              {showLegend && <Legend />}
              <Scatter
                data={data}
                fill={colors[0]}
              />
            </ScatterChart>
          </ResponsiveContainer>
        );

      case 'gauge':
        return (
          <div className="h-full flex flex-col items-center justify-center">
            <ResponsiveContainer width="100%" height="70%">
              <RadialBarChart
                cx="50%"
                cy="50%"
                innerRadius="60%"
                outerRadius="90%"
                barSize={20}
                data={gaugeData}
                startAngle={180}
                endAngle={0}
              >
                <PolarAngleAxis
                  type="number"
                  domain={[0, 100]}
                  angleAxisId={0}
                  tick={false}
                />
                <RadialBar
                  background
                  dataKey="value"
                  cornerRadius={10}
                  fill={gaugeData[0]?.fill}
                />
                {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }} />}
              </RadialBarChart>
            </ResponsiveContainer>
            <div className="text-center mt-2">
              <div className="text-3xl font-bold">
                {data[0] ? Number(data[0][dataKey]).toFixed(1) : 0}
              </div>
              <div className="text-sm text-muted-foreground">
                {data[0] ? data[0][nameKey] : 'Value'}
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                Range: {gaugeMin} - {gaugeMax}
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <p className="text-sm">Unsupported chart type: {type}</p>
          </div>
        );
    }
  };

  return (
    <Card className={cn('h-full', className)}>
      <CardHeader>
        {title && (
          <CardTitle className="text-base font-medium flex items-center gap-2">
            {getChartIcon(type)}
            {title}
          </CardTitle>
        )}
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="h-[calc(100%-5rem)]">
        {renderChart()}
      </CardContent>
    </Card>
  );
};

export default ChartWidget;
