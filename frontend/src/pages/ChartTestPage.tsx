import React from 'react';
import { ChartWidget, ChartDataPoint, ChartConfig } from '@/components/analytics/ChartWidget';
import { PivotTable, PivotTableData, PivotTableConfig } from '@/components/analytics/PivotTable';
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

// Sample data for 1D pivot table (single dimension)
const pivot1DData: PivotTableData = {
  rows: ['Design', 'Development', 'Testing', 'Documentation'],
  cells: [
    { row: 'Design', value: 4500, count: 15, records: [{ id: '1', task: 'UI Mockups', cost: 1500 }, { id: '2', task: 'Wireframes', cost: 1000 }] },
    { row: 'Development', value: 12000, count: 45, records: [{ id: '3', task: 'Backend API', cost: 6000 }, { id: '4', task: 'Frontend', cost: 6000 }] },
    { row: 'Testing', value: 3200, count: 20, records: [{ id: '5', task: 'Unit Tests', cost: 1200 }, { id: '6', task: 'Integration', cost: 2000 }] },
    { row: 'Documentation', value: 1800, count: 10, records: [{ id: '7', task: 'API Docs', cost: 800 }, { id: '8', task: 'User Guide', cost: 1000 }] },
  ],
};

// Sample data for 2D pivot table (two dimensions)
const pivot2DData: PivotTableData = {
  rows: ['Q1', 'Q2', 'Q3', 'Q4'],
  columns: ['Design', 'Development', 'Testing', 'Documentation'],
  cells: [
    { row: 'Q1', column: 'Design', value: 1200, count: 4, records: [{ id: '1', quarter: 'Q1', department: 'Design', cost: 1200 }] },
    { row: 'Q1', column: 'Development', value: 3500, count: 12, records: [{ id: '2', quarter: 'Q1', department: 'Development', cost: 3500 }] },
    { row: 'Q1', column: 'Testing', value: 800, count: 5, records: [{ id: '3', quarter: 'Q1', department: 'Testing', cost: 800 }] },
    { row: 'Q1', column: 'Documentation', value: 400, count: 2, records: [{ id: '4', quarter: 'Q1', department: 'Documentation', cost: 400 }] },
    { row: 'Q2', column: 'Design', value: 1100, count: 3, records: [] },
    { row: 'Q2', column: 'Development', value: 4200, count: 15, records: [] },
    { row: 'Q2', column: 'Testing', value: 950, count: 6, records: [] },
    { row: 'Q2', column: 'Documentation', value: 500, count: 3, records: [] },
    { row: 'Q3', column: 'Design', value: 1000, count: 4, records: [] },
    { row: 'Q3', column: 'Development', value: 3800, count: 13, records: [] },
    { row: 'Q3', column: 'Testing', value: 1050, count: 7, records: [] },
    { row: 'Q3', column: 'Documentation', value: 450, count: 2, records: [] },
    { row: 'Q4', column: 'Design', value: 1200, count: 4, records: [] },
    { row: 'Q4', column: 'Development', value: 4500, count: 16, records: [] },
    { row: 'Q4', column: 'Testing', value: 1400, count: 8, records: [] },
    { row: 'Q4', column: 'Documentation', value: 450, count: 3, records: [] },
  ],
  totals: {
    rows: {
      'Q1': 5900,
      'Q2': 6750,
      'Q3': 6300,
      'Q4': 7550,
    },
    columns: {
      'Design': 4500,
      'Development': 16000,
      'Testing': 4200,
      'Documentation': 1800,
    },
    grand: 26500,
  },
};

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

  // Pivot table configurations
  const pivot1DConfig: PivotTableConfig = {
    title: '1D Pivot Table - Project Costs',
    description: 'Total costs by department',
    rowLabel: 'Department',
    valueLabel: 'Total Cost',
    showTotals: false,
    formatValue: (value) => `$${value.toLocaleString()}`,
  };

  const pivot2DConfig: PivotTableConfig = {
    title: '2D Pivot Table - Quarterly Analysis',
    description: 'Costs by quarter and department with drill-down',
    rowLabel: 'Quarter',
    columnLabel: 'Department',
    valueLabel: 'Cost',
    showTotals: true,
    formatValue: (value) => `$${value.toLocaleString()}`,
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
            <h1 className="text-3xl font-bold tracking-tight">Analytics Test Page</h1>
            <p className="text-muted-foreground mt-1">
              Testing all chart types and pivot tables with drill-down
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

      {/* Pivot Tables Section */}
      <div className="mt-8">
        <h2 className="text-2xl font-bold mb-4">Pivot Tables with Drill-Down</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 1D Pivot Table */}
          <div className="h-96">
            <PivotTable
              data={pivot1DData}
              config={pivot1DConfig}
            />
          </div>

          {/* 2D Pivot Table */}
          <div className="h-96">
            <PivotTable
              data={pivot2DData}
              config={pivot2DConfig}
            />
          </div>
        </div>
      </div>

      {/* Loading State Test */}
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Loading & Error States</h2>
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
            <PivotTable
              data={{ rows: [], cells: [] }}
              config={{ title: 'Empty Pivot Table' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChartTestPage;
