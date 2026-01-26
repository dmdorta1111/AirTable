import React from 'react';
import { ChartWidget, ChartDataPoint, ChartConfig } from '@/components/analytics/ChartWidget';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

// Sample data for line and bar charts
const timeSeriesData: ChartDataPoint[] = [
  { name: 'Jan', value: 65, cost: 4000, revenue: 5500 },
  { name: 'Feb', value: 78, cost: 3000, revenue: 4200 },
  { name: 'Mar', value: 90, cost: 5000, revenue: 6800 },
  { name: 'Apr', value: 81, cost: 4500, revenue: 6200 },
  { name: 'May', value: 95, cost: 6000, revenue: 8100 },
  { name: 'Jun', value: 88, cost: 5500, revenue: 7500 },
];

// Sample data for pie chart
const categoryData: ChartDataPoint[] = [
  { name: 'Design', value: 30 },
  { name: 'Development', value: 45 },
  { name: 'Testing', value: 15 },
  { name: 'Documentation', value: 10 },
];

// Sample data for scatter chart
const scatterData: ChartDataPoint[] = [
  { name: 1, value: 10 },
  { name: 2, value: 15 },
  { name: 3, value: 13 },
  { name: 4, value: 20 },
  { name: 5, value: 18 },
  { name: 6, value: 25 },
  { name: 7, value: 22 },
  { name: 8, value: 30 },
  { name: 9, value: 28 },
  { name: 10, value: 35 },
];

// Sample data for gauge chart
const gaugeData: ChartDataPoint[] = [
  { name: 'Progress', value: 72 },
];

export const ChartTestPage: React.FC = () => {
  const navigate = useNavigate();

  // Chart configurations
  const lineChartConfig: ChartConfig = {
    type: 'line',
    title: 'Line Chart - Monthly Performance',
    description: 'Performance metrics over time',
    dataKey: 'value',
    nameKey: 'name',
    xAxisLabel: 'Month',
    yAxisLabel: 'Performance Score',
    showGrid: true,
    showLegend: true,
    showTooltip: true,
    colors: ['#3b82f6'],
  };

  const barChartConfig: ChartConfig = {
    type: 'bar',
    title: 'Bar Chart - Monthly Performance',
    description: 'Performance metrics comparison',
    dataKey: 'value',
    nameKey: 'name',
    xAxisLabel: 'Month',
    yAxisLabel: 'Performance Score',
    showGrid: true,
    showLegend: true,
    showTooltip: true,
    colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
  };

  const pieChartConfig: ChartConfig = {
    type: 'pie',
    title: 'Pie Chart - Team Distribution',
    description: 'Distribution of effort across categories',
    dataKey: 'value',
    nameKey: 'name',
    showLegend: true,
    showTooltip: true,
    colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'],
  };

  const scatterChartConfig: ChartConfig = {
    type: 'scatter',
    title: 'Scatter Chart - Data Correlation',
    description: 'Correlation between two variables',
    dataKey: 'value',
    nameKey: 'name',
    xAxisLabel: 'X Variable',
    yAxisLabel: 'Y Variable',
    showGrid: true,
    showLegend: true,
    showTooltip: true,
    colors: ['#8b5cf6'],
  };

  const gaugeChartConfig: ChartConfig = {
    type: 'gauge',
    title: 'Gauge Chart - Project Progress',
    description: 'Current project completion status',
    dataKey: 'value',
    nameKey: 'name',
    gaugeMin: 0,
    gaugeMax: 100,
    gaugeThresholds: {
      low: 33,
      medium: 66,
      high: 100,
    },
    showTooltip: true,
  };

  return (
    <div className="min-h-screen bg-background p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/dashboards')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Chart Widget Test</h1>
            <p className="text-muted-foreground mt-1">
              Testing all chart types: line, bar, pie, scatter, and gauge
            </p>
          </div>
        </div>
      </div>

      {/* Chart Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Line Chart */}
        <div className="h-96">
          <ChartWidget
            data={timeSeriesData}
            config={lineChartConfig}
          />
        </div>

        {/* Bar Chart */}
        <div className="h-96">
          <ChartWidget
            data={timeSeriesData}
            config={barChartConfig}
          />
        </div>

        {/* Pie Chart */}
        <div className="h-96">
          <ChartWidget
            data={categoryData}
            config={pieChartConfig}
          />
        </div>

        {/* Scatter Chart */}
        <div className="h-96">
          <ChartWidget
            data={scatterData}
            config={scatterChartConfig}
          />
        </div>

        {/* Gauge Chart - Full Width */}
        <div className="h-96 md:col-span-2">
          <ChartWidget
            data={gaugeData}
            config={gaugeChartConfig}
          />
        </div>
      </div>

      {/* Loading State Test */}
      <div className="mt-6">
        <h2 className="text-xl font-semibold mb-4">Loading State</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="h-64">
            <ChartWidget
              data={[]}
              config={{ type: 'line', title: 'Loading Chart' }}
              isLoading={true}
            />
          </div>
          <div className="h-64">
            <ChartWidget
              data={[]}
              config={{ type: 'bar', title: 'Error Chart' }}
              error="Failed to load chart data"
            />
          </div>
          <div className="h-64">
            <ChartWidget
              data={[]}
              config={{ type: 'pie', title: 'Empty Chart' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChartTestPage;
