import React, { useMemo, useRef } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  AreaChart,
  Area,
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
  Gauge,
  AlertCircle,
  Sparkles,
  Download,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { get } from '@/lib/api';
import { useAuthStore } from '@/features/auth/stores/authStore';
import { useDashboardRealtime } from '@/hooks/useDashboardRealtime';
import { useChartData } from '@/hooks/useChartData';
import { useRealtime } from '@/hooks/useRealtime';

// Chart types supported
export type ChartType = 'line' | 'bar' | 'pie' | 'donut' | 'scatter' | 'gauge' | 'area' | 'histogram';

// Data point interface
export interface ChartDataPoint {
  name: string | number;
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
  tableId?: string; // Table ID for real-time updates
  histogramBins?: number; // Number of bins for histogram (default: auto-calculated)
}

interface ChartWidgetProps {
  data?: ChartDataPoint[]; // Optional: if not provided, will fetch using widgetId
  config: ChartConfig;
  className?: string;
  isLoading?: boolean;
  error?: string;
  widgetId?: string; // If provided, will auto-fetch data and refresh on WebSocket events
  dashboardId?: string; // Dashboard ID for real-time updates
  showExportButtons?: boolean; // Show export buttons (default: false)
  onExportPNG?: () => void; // Custom PNG export handler
  onExportSVG?: () => void; // Custom SVG export handler
  // Real-time data fetching props
  tableId?: string; // Table ID for auto-fetching chart data
  chartId?: string; // Chart ID for auto-fetching and real-time updates
  enabled?: boolean; // Enable auto-fetch (default: true if tableId provided)
  refreshInterval?: number; // Polling interval in ms (optional)
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
    case 'donut':
      return <PieChartIcon className="h-5 w-5" />;
    case 'scatter':
      return <Sparkles className="h-5 w-5" />;
    case 'gauge':
      return <Gauge className="h-5 w-5" />;
    case 'area':
      return <LineChartIcon className="h-5 w-5" />;
    case 'histogram':
      return <BarChart3 className="h-5 w-5" />;
    default:
      return <BarChart3 className="h-5 w-5" />;
  }
};

export const ChartWidget: React.FC<ChartWidgetProps> = ({
  data: propData,
  config,
  className,
  isLoading: propIsLoading = false,
  error: propError,
  widgetId,
  dashboardId,
  showExportButtons = false,
  onExportPNG,
  onExportSVG,
  tableId,
  chartId,
  enabled = true,
  refreshInterval,
}) => {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  const chartContainerRef = useRef<HTMLDivElement>(null);

  // Auto-fetch chart data if tableId is provided
  const shouldAutoFetch = Boolean(tableId && enabled);
  const {
    data: fetchedData,
    isLoading: fetchedIsLoading,
    error: fetchedError,
    refresh,
  } = useChartData({
    tableId: tableId || '',
    chartId,
    enabled: shouldAutoFetch,
    refreshInterval,
  });

  // Real-time updates for chart data
  useRealtime({
    tableId,
    chartId,
    enabled: shouldAutoFetch,
    onChartUpdated: () => {
      // Refresh chart data when update is received
      if (shouldAutoFetch) {
        refresh();
      }
    },
    onRecordUpdated: () => {
      // Refresh chart data when record is updated
      if (shouldAutoFetch) {
        refresh();
      }
    },
    onRecordCreated: () => {
      // Refresh chart data when record is created
      if (shouldAutoFetch) {
        refresh();
      }
    },
    onRecordDeleted: () => {
      // Refresh chart data when record is deleted
      if (shouldAutoFetch) {
        refresh();
      }
    },
  });

  // Use prop data if provided, otherwise use fetched data
  const data = propData ?? fetchedData;
  const isLoading = propIsLoading || (shouldAutoFetch && fetchedIsLoading);
  const error = propError ?? (shouldAutoFetch ? fetchedError?.message : undefined);
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
    tableId,
    histogramBins,
  } = config;

  // Enable real-time updates for this widget when dashboardId and widgetId are provided
  useDashboardRealtime({
    dashboardId: dashboardId || '',
    widgets: dashboardId && widgetId && tableId ? [{
      id: widgetId,
      type: 'chart',
      config: { tableId },
    }] : [],
    onWidgetUpdate: (updatedWidgetId) => {
      if (updatedWidgetId === widgetId) {
        // Invalidate the query to trigger a refetch
        queryClient.invalidateQueries({ queryKey: ['widget', widgetId] });
      }
    },
    enabled: !!(dashboardId && widgetId && tableId),
  });

  // Fetch widget data if widgetId is provided (enables auto-refresh via WebSocket)
  const { data: fetchedData, isLoading: fetchIsLoading, error: fetchError } = useQuery<ChartDataPoint[]>({
    queryKey: ['widget', widgetId],
    queryFn: () => get<ChartDataPoint[]>(`/api/v1/widgets/${widgetId}/data`),
    enabled: !!widgetId && !!token,
    refetchOnWindowFocus: false,
  });

  // Use fetched data if available, otherwise use prop data
  const data = widgetId ? fetchedData : propData;
  const isLoading = widgetId ? fetchIsLoading : propIsLoading;
  const error = widgetId ? (fetchError?.message || 'Failed to load widget data') : propError;

  // Transform data for gauge chart
  const gaugeData = useMemo(() => {
    if (type !== 'gauge' || !data || data.length === 0) return [];

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

  // Transform data for histogram chart
  const histogramData = useMemo(() => {
    if (type !== 'histogram' || data.length === 0) return [];

    // Extract all numeric values
    const values = data.map((d) => Number(d[dataKey] || 0)).filter((v) => !isNaN(v));

    if (values.length === 0) return [];

    // Calculate bin count using Sturges' rule if not specified
    const binCount = histogramBins || Math.max(5, Math.ceil(Math.log2(values.length)) + 1);

    // Find min and max values
    const min = Math.min(...values);
    const max = Math.max(...values);

    // Avoid division by zero
    if (min === max) {
      return [{ name: `${min}`, value: values.length, count: values.length }];
    }

    // Calculate bin width
    const binWidth = (max - min) / binCount;

    // Initialize bins
    const bins: Array<{ name: string; value: number; count: number; range: string }> = [];

    for (let i = 0; i < binCount; i++) {
      const binStart = min + i * binWidth;
      const binEnd = min + (i + 1) * binWidth;

      bins.push({
        name: `${binStart.toFixed(2)}-${binEnd.toFixed(2)}`,
        value: 0,
        count: 0,
        range: `${binStart.toFixed(2)} - ${binEnd.toFixed(2)}`,
      });
    }

    // Distribute values into bins
    values.forEach((value) => {
      let binIndex = Math.floor((value - min) / binWidth);
      // Handle the edge case where value equals max
      if (binIndex >= binCount) binIndex = binCount - 1;
      bins[binIndex].value++;
      bins[binIndex].count++;
    });

    return bins;
  }, [data, type, dataKey, histogramBins]);

  // Handle PNG export
  const handleExportPNG = async () => {
    if (onExportPNG) {
      onExportPNG();
      return;
    }

    if (chartContainerRef.current) {
      const filename = title ? `${title.replace(/[^a-z0-9]/gi, '_')}_chart.png` : 'chart.png';
      await exportChartAsPNG(chartContainerRef.current, filename);
    }
  };

  // Handle SVG export
  const handleExportSVG = () => {
    if (onExportSVG) {
      onExportSVG();
      return;
    }

    if (chartContainerRef.current) {
      const filename = title ? `${title.replace(/[^a-z0-9]/gi, '_')}_chart.svg` : 'chart.svg';
      exportChartAsSVG(chartContainerRef.current, filename);
    }
  };

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

      case 'area':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
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
              <Area
                type="monotone"
                dataKey={dataKey}
                stroke={colors[0]}
                fill={colors[0]}
                fillOpacity={0.6}
              />
            </AreaChart>
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

      case 'histogram':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histogramData}>
              {showGrid && <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />}
              <XAxis
                dataKey="name"
                label={xAxisLabel ? { value: xAxisLabel, position: 'insideBottom', offset: -5 } : undefined}
                className="text-xs"
                tick={{ fontSize: 10 }}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis
                label={yAxisLabel ? { value: yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
                className="text-xs"
              />
              {showTooltip && <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' }} />}
              {showLegend && <Legend />}
              <Bar dataKey="value" fill={colors[0]} radius={[4, 4, 0, 0]} />
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

      case 'donut':
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
                innerRadius="60%"
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
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {title && (
              <CardTitle className="text-base font-medium flex items-center gap-2">
                {getChartIcon(type)}
                {title}
              </CardTitle>
            )}
          </div>
          {showExportButtons && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleExportPNG}
                className="p-2 hover:bg-accent rounded-md transition-colors"
                title="Export as PNG"
                aria-label="Export chart as PNG"
              >
                <Download className="h-4 w-4" />
              </button>
              <button
                onClick={handleExportSVG}
                className="p-2 hover:bg-accent rounded-md transition-colors"
                title="Export as SVG"
                aria-label="Export chart as SVG"
              >
                <Download className="h-4 w-4" />
                <span className="text-xs ml-1">SVG</span>
              </button>
            </div>
          )}
        </div>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="h-[calc(100%-5rem)]" ref={chartContainerRef}>
        {renderChart()}
      </CardContent>
    </Card>
  );
};

// Export utility functions
export const exportChartAsPNG = async (element: HTMLElement, filename: string = 'chart.png'): Promise<void> => {
  try {
    // Dynamic import to avoid loading html2canvas until needed
    const html2canvas = (await import('html2canvas')).default;

    const canvas = await html2canvas(element, {
      background: '#ffffff',
      scale: 2, // Higher resolution
      logging: false,
    } as any); // Use type assertion to handle html2canvas type definition limitations

    canvas.toBlob((blob) => {
      if (blob) {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }
    });
  } catch (error) {
    console.error('Failed to export chart as PNG:', error);
    throw new Error('Failed to export chart as PNG');
  }
};

export const exportChartAsSVG = (element: HTMLElement, filename: string = 'chart.svg'): void => {
  try {
    // Find SVG element within the container
    const svgElement = element.querySelector('svg');

    if (!svgElement) {
      throw new Error('No SVG element found in the chart');
    }

    // Clone the SVG element to avoid modifying the original
    const svgClone = svgElement.cloneNode(true) as SVGElement;

    // Get SVG dimensions
    const width = svgElement.getAttribute('width') || '800';
    const height = svgElement.getAttribute('height') || '400';

    // Set explicit dimensions on the clone
    svgClone.setAttribute('width', width);
    svgClone.setAttribute('height', height);
    svgClone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');

    // Serialize SVG to string
    const svgData = new XMLSerializer().serializeToString(svgClone);

    // Create blob and download
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Failed to export chart as SVG:', error);
    throw new Error('Failed to export chart as SVG');
  }
};

export default ChartWidget;
