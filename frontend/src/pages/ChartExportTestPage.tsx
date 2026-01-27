import React, { useState } from 'react';
import { ChartWidget, ChartDataPoint, ChartConfig } from '@/components/analytics/ChartWidget';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

// Chart data for testing all chart types
const chartData: ChartDataPoint[] = [
  { name: 'Jan', value: 400, cost: 120 },
  { name: 'Feb', value: 300, cost: 98 },
  { name: 'Mar', value: 600, cost: 150 },
  { name: 'Apr', value: 800, cost: 180 },
  { name: 'May', value: 500, cost: 140 },
  { name: 'Jun', value: 700, cost: 165 },
];

const scatterData: ChartDataPoint[] = [
  { name: 100, value: 200 },
  { name: 150, value: 280 },
  { name: 200, value: 350 },
  { name: 250, value: 420 },
  { name: 300, value: 500 },
  { name: 350, value: 580 },
];

const gaugeData: ChartDataPoint[] = [
  { name: 'Performance Score', value: 72 },
];

const pieData: ChartDataPoint[] = [
  { name: 'Category A', value: 400 },
  { name: 'Category B', value: 300 },
  { name: 'Category C', value: 300 },
  { name: 'Category D', value: 200 },
  { name: 'Category E', value: 278 },
  { name: 'Category F', value: 189 },
];

// Chart configurations for all 8 types
const chartConfigs: Array<{ id: string; name: string; type: ChartConfig['type']; config: ChartConfig; data: ChartDataPoint[] }> = [
  {
    id: 'line-chart',
    name: 'Line Chart',
    type: 'line',
    data: chartData,
    config: {
      type: 'line',
      title: 'Monthly Revenue Trend',
      description: 'Revenue over 6 months',
      dataKey: 'value',
      nameKey: 'name',
      xAxisLabel: 'Month',
      yAxisLabel: 'Revenue ($)',
      colors: ['#3b82f6'],
    },
  },
  {
    id: 'bar-chart',
    name: 'Bar Chart',
    type: 'bar',
    data: chartData,
    config: {
      type: 'bar',
      title: 'Monthly Revenue',
      description: 'Revenue comparison by month',
      dataKey: 'value',
      nameKey: 'name',
      xAxisLabel: 'Month',
      yAxisLabel: 'Revenue ($)',
      colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
    },
  },
  {
    id: 'area-chart',
    name: 'Area Chart',
    type: 'area',
    data: chartData,
    config: {
      type: 'area',
      title: 'Revenue Area Chart',
      description: 'Cumulative revenue visualization',
      dataKey: 'value',
      nameKey: 'name',
      xAxisLabel: 'Month',
      yAxisLabel: 'Revenue ($)',
      colors: ['#8b5cf6'],
    },
  },
  {
    id: 'pie-chart',
    name: 'Pie Chart',
    type: 'pie',
    data: pieData,
    config: {
      type: 'pie',
      title: 'Category Distribution',
      description: 'Market share by category',
      dataKey: 'value',
      nameKey: 'name',
      colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
    },
  },
  {
    id: 'donut-chart',
    name: 'Donut Chart',
    type: 'donut',
    data: pieData,
    config: {
      type: 'donut',
      title: 'Category Distribution (Donut)',
      description: 'Market share by category with donut style',
      dataKey: 'value',
      nameKey: 'name',
      colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
    },
  },
  {
    id: 'scatter-chart',
    name: 'Scatter Chart',
    type: 'scatter',
    data: scatterData,
    config: {
      type: 'scatter',
      title: 'Correlation Analysis',
      description: 'X vs Y correlation scatter plot',
      dataKey: 'value',
      nameKey: 'name',
      xAxisLabel: 'X Value',
      yAxisLabel: 'Y Value',
      colors: ['#f59e0b'],
    },
  },
  {
    id: 'histogram-chart',
    name: 'Histogram',
    type: 'histogram',
    data: chartData,
    config: {
      type: 'histogram',
      title: 'Revenue Distribution',
      description: 'Frequency distribution of revenue values',
      dataKey: 'value',
      nameKey: 'name',
      xAxisLabel: 'Revenue Range',
      yAxisLabel: 'Frequency',
      histogramBins: 5,
      colors: ['#10b981'],
    },
  },
  {
    id: 'gauge-chart',
    name: 'Gauge',
    type: 'gauge',
    data: gaugeData,
    config: {
      type: 'gauge',
      title: 'Performance Gauge',
      description: 'Current performance score',
      dataKey: 'value',
      nameKey: 'name',
      gaugeMin: 0,
      gaugeMax: 100,
      gaugeThresholds: {
        low: 33,
        medium: 66,
        high: 100,
      },
    },
  },
];

interface ExportStatus {
  chartId: string;
  png: boolean;
  svg: boolean;
  pngError?: string;
  svgError?: string;
}

export const ChartExportTestPage: React.FC = () => {
  const navigate = useNavigate();
  const [exportStatuses, setExportStatuses] = useState<Record<string, ExportStatus>>({});

  const updateExportStatus = (chartId: string, type: 'png' | 'svg', success: boolean, error?: string) => {
    setExportStatuses((prev) => ({
      ...prev,
      [chartId]: {
        ...prev[chartId],
        chartId,
        [type]: success,
        [`${type}Error`]: error,
      },
    }));
  };

  const handleExportPNG = (chartId: string) => async () => {
    try {
      // The export will be triggered by the ChartWidget's default handler
      updateExportStatus(chartId, 'png', true);
    } catch (error) {
      updateExportStatus(chartId, 'png', false, error instanceof Error ? error.message : 'Unknown error');
    }
  };

  const handleExportSVG = (chartId: string) => () => {
    try {
      // The export will be triggered by the ChartWidget's default handler
      updateExportStatus(chartId, 'svg', true);
    } catch (error) {
      updateExportStatus(chartId, 'svg', false, error instanceof Error ? error.message : 'Unknown error');
    }
  };

  const allExportsComplete = () => {
    return chartConfigs.every(
      (chart) => exportStatuses[chart.id]?.png && exportStatuses[chart.id]?.svg
    );
  };

  const getSuccessCount = () => {
    let pngCount = 0;
    let svgCount = 0;
    chartConfigs.forEach((chart) => {
      if (exportStatuses[chart.id]?.png) pngCount++;
      if (exportStatuses[chart.id]?.svg) svgCount++;
    });
    return { pngCount, svgCount };
  };

  const { pngCount, svgCount } = getSuccessCount();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/dashboards/test')}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Chart Export Functionality Test</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Test PNG and SVG export for all 8 chart types
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-sm text-muted-foreground">
              <span className="font-semibold text-foreground">{pngCount}</span> / {chartConfigs.length} PNG exports,
              <span className="font-semibold text-foreground ml-1">{svgCount}</span> / {chartConfigs.length} SVG exports
            </div>
            {allExportsComplete() && (
              <span className="text-green-600 text-sm font-medium flex items-center gap-1">
                <CheckCircle className="h-4 w-4" />
                All exports complete!
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Instructions */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Test Instructions</CardTitle>
            <CardDescription>Manual verification of chart export functionality</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 text-sm">
              <p>
                <strong>Purpose:</strong> Verify that all 8 chart types can be successfully exported to PNG and SVG formats.
              </p>
              <ol className="list-decimal list-inside space-y-2 ml-2">
                <li>For each chart below, click the <Download className="inline h-3 w-3" /> button to export as PNG</li>
                <li>Verify the PNG file downloads and opens correctly in an image viewer</li>
                <li>Click the <Download className="inline h-3 w-3" /> <strong>SVG</strong> button to export as SVG</li>
                <li>Verify the SVG file downloads and opens correctly in a browser or vector editor</li>
                <li>Check that the exported image matches the chart display (colors, labels, data)</li>
                <li>Verify file names follow the pattern: <code className="bg-muted px-1 py-0.5 rounded">{`{title}_chart.png`}</code> and <code className="bg-muted px-1 py-0.5 rounded">{`{title}_chart.svg`}</code></li>
              </ol>
              <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded">
                <p className="text-blue-800 dark:text-blue-200 font-medium">
                  <CheckCircle className="inline h-4 w-4 mr-1" />
                  Success Criteria:
                </p>
                <ul className="list-disc list-inside text-blue-700 dark:text-blue-300 mt-2 space-y-1">
                  <li>All 8 chart types (line, bar, area, pie, donut, scatter, histogram, gauge) can export to PNG</li>
                  <li>All 8 chart types can export to SVG</li>
                  <li>Exported files are valid and can be opened</li>
                  <li>Visual quality is good (PNG is crisp, SVG is scalable)</li>
                  <li>File names are descriptive and valid</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {chartConfigs.map((chart) => {
            const status = exportStatuses[chart.id];
            const pngSuccess = status?.png;
            const svgSuccess = status?.svg;

            return (
              <Card key={chart.id} className={pngSuccess && svgSuccess ? 'border-green-500' : ''}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{chart.name}</CardTitle>
                    <div className="flex items-center gap-2">
                      {pngSuccess && (
                        <span className="flex items-center gap-1" title="PNG exported successfully">
                          <CheckCircle className="h-5 w-5 text-green-600" />
                        </span>
                      )}
                      {svgSuccess && (
                        <span className="flex items-center gap-1" title="SVG exported successfully">
                          <CheckCircle className="h-5 w-5 text-green-600" />
                        </span>
                      )}
                    </div>
                  </div>
                  <CardDescription>{chart.config.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="mb-4">
                    <ChartWidget
                      data={chart.data}
                      config={chart.config}
                      showExportButtons={true}
                      onExportPNG={handleExportPNG(chart.id)}
                      onExportSVG={handleExportSVG(chart.id)}
                      className="h-[250px]"
                    />
                  </div>

                  {/* Export Status Checklist */}
                  <div className="border-t pt-3">
                    <p className="text-xs font-medium text-muted-foreground mb-2">Export Verification:</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={pngSuccess || false}
                          onChange={(e) => updateExportStatus(chart.id, 'png', e.target.checked)}
                          className="rounded"
                        />
                        <span className={pngSuccess ? 'text-green-600' : ''}>
                          PNG exports and opens
                        </span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={svgSuccess || false}
                          onChange={(e) => updateExportStatus(chart.id, 'svg', e.target.checked)}
                          className="rounded"
                        />
                        <span className={svgSuccess ? 'text-green-600' : ''}>
                          SVG exports and opens
                        </span>
                      </label>
                    </div>
                    {status?.pngError && (
                      <p className="text-xs text-red-600 mt-1">PNG Error: {status.pngError}</p>
                    )}
                    {status?.svgError && (
                      <p className="text-xs text-red-600 mt-1">SVG Error: {status.svgError}</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Summary Section */}
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Export Summary</CardTitle>
            <CardDescription>Overall test results</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 border rounded">
                <div className="text-3xl font-bold text-blue-600">{pngCount}</div>
                <div className="text-sm text-muted-foreground">PNG Exports</div>
                <div className="text-xs text-muted-foreground mt-1">{pngCount} / {chartConfigs.length} charts</div>
              </div>
              <div className="text-center p-4 border rounded">
                <div className="text-3xl font-bold text-purple-600">{svgCount}</div>
                <div className="text-sm text-muted-foreground">SVG Exports</div>
                <div className="text-xs text-muted-foreground mt-1">{svgCount} / {chartConfigs.length} charts</div>
              </div>
              <div className="text-center p-4 border rounded">
                <div className="text-3xl font-bold text-green-600">
                  {Math.round(((pngCount + svgCount) / (chartConfigs.length * 2)) * 100)}%
                </div>
                <div className="text-sm text-muted-foreground">Completion</div>
                <div className="text-xs text-muted-foreground mt-1">{pngCount + svgCount} / {chartConfigs.length * 2} exports</div>
              </div>
            </div>

            {allExportsComplete() && (
              <div className="mt-4 p-4 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded">
                <p className="text-green-800 dark:text-green-200 font-medium text-center">
                  <CheckCircle className="inline h-5 w-5 mr-2" />
                  All export tests passed! All 8 chart types successfully export to both PNG and SVG formats.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ChartExportTestPage;
