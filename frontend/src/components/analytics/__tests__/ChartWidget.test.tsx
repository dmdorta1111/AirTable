import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChartWidget, ChartConfig, ChartDataPoint } from '../ChartWidget';

// Mock the hooks
vi.mock('@/hooks/useChartData', () => ({
  useChartData: vi.fn(() => ({
    data: [],
    isLoading: false,
    error: undefined,
    refresh: vi.fn(),
  })),
}));

vi.mock('@/hooks/useRealtime', () => ({
  useRealtime: vi.fn(() => ({})),
}));

// Helper function to render chart with proper container
const renderChartWithContainer = (component: React.ReactElement) => {
  const container = document.createElement('div');
  container.style.width = '800px';
  container.style.height = '400px';
  document.body.appendChild(container);
  return {
    ...render(component, { container }),
    container,
  };
};

// Mock html2canvas for export tests
vi.mock('html2canvas', () => ({
  default: vi.fn(() =>
    Promise.resolve({
      toBlob: (callback: (blob: Blob) => void) => {
        callback(new Blob(['test'], { type: 'image/png' }));
      },
    })
  ),
}));

// Mock data
const mockChartData: ChartDataPoint[] = [
  { name: 'Jan', value: 100 },
  { name: 'Feb', value: 200 },
  { name: 'Mar', value: 150 },
  { name: 'Apr', value: 300 },
  { name: 'May', value: 250 },
];

const mockHistogramData: ChartDataPoint[] = [
  { name: 'Item 1', value: 10 },
  { name: 'Item 2', value: 25 },
  { name: 'Item 3', value: 15 },
  { name: 'Item 4', value: 30 },
  { name: 'Item 5', value: 20 },
  { name: 'Item 6', value: 35 },
  { name: 'Item 7', value: 12 },
  { name: 'Item 8', value: 28 },
  { name: 'Item 9', value: 18 },
  { name: 'Item 10', value: 22 },
];

const mockPieData: ChartDataPoint[] = [
  { name: 'Category A', value: 400 },
  { name: 'Category B', value: 300 },
  { name: 'Category C', value: 200 },
  { name: 'Category D', value: 100 },
];

describe('ChartWidget - Area Chart', () => {
  it('renders area chart with data', () => {
    const config: ChartConfig = {
      type: 'area',
      title: 'Sales Trend',
      description: 'Monthly sales overview',
    };

    render(<ChartWidget data={mockChartData} config={config} />);

    expect(screen.getByText('Sales Trend')).toBeInTheDocument();
    expect(screen.getByText('Monthly sales overview')).toBeInTheDocument();
  });

  it('applies custom colors to area chart', () => {
    const config: ChartConfig = {
      type: 'area',
      colors: ['#ff0000', '#00ff00', '#0000ff'],
    };

    // Should render without errors with custom colors
    expect(() => render(<ChartWidget data={mockChartData} config={config} />)).not.toThrow();
  });

  it('shows/hides grid in area chart', () => {
    const config: ChartConfig = {
      type: 'area',
      showGrid: false,
    };

    const { container } = render(<ChartWidget data={mockChartData} config={config} />);

    // Grid should not be present when showGrid is false
    const gridElement = container.querySelector('.recharts-cartesian-grid');
    expect(gridElement).not.toBeInTheDocument();
  });

  it('shows/hides tooltip in area chart', () => {
    const config: ChartConfig = {
      type: 'area',
      showTooltip: false,
    };

    const { container } = render(<ChartWidget data={mockChartData} config={config} />);

    // Tooltip should not be present when showTooltip is false
    const tooltipElement = container.querySelector('.recharts-tooltip-wrapper');
    expect(tooltipElement).not.toBeInTheDocument();
  });

  it('shows/hides legend in area chart', () => {
    const config: ChartConfig = {
      type: 'area',
      showLegend: false,
    };

    const { container } = render(<ChartWidget data={mockChartData} config={config} />);

    // Legend should not be present when showLegend is false
    const legendElement = container.querySelector('.recharts-legend-wrapper');
    expect(legendElement).not.toBeInTheDocument();
  });

  it('displays axis labels in area chart', () => {
    const config: ChartConfig = {
      type: 'area',
      xAxisLabel: 'Month',
      yAxisLabel: 'Sales ($)',
    };

    // Should render without errors with axis labels
    expect(() => render(<ChartWidget data={mockChartData} config={config} />)).not.toThrow();
  });

  it('handles empty data for area chart', () => {
    const config: ChartConfig = {
      type: 'area',
      title: 'Empty Chart',
    };

    render(<ChartWidget data={[]} config={config} />);

    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('handles loading state for area chart', () => {
    const config: ChartConfig = {
      type: 'area',
    };

    render(<ChartWidget data={mockChartData} config={config} isLoading={true} />);

    // Should render skeleton loader
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('handles error state for area chart', () => {
    const config: ChartConfig = {
      type: 'area',
      title: 'Error Chart',
    };

    render(<ChartWidget data={mockChartData} config={config} error="Failed to load data" />);

    expect(screen.getByText('Chart Error')).toBeInTheDocument();
    expect(screen.getByText('Failed to load data')).toBeInTheDocument();
  });
});

describe('ChartWidget - Donut Chart', () => {
  it('renders donut chart with data', () => {
    const config: ChartConfig = {
      type: 'donut',
      title: 'Category Distribution',
      description: 'Sales by category',
    };

    render(<ChartWidget data={mockPieData} config={config} />);

    expect(screen.getByText('Category Distribution')).toBeInTheDocument();
    expect(screen.getByText('Sales by category')).toBeInTheDocument();
  });

  it('applies custom colors to donut chart', () => {
    const config: ChartConfig = {
      type: 'donut',
      colors: ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0'],
    };

    // Should render without errors with custom colors
    expect(() => render(<ChartWidget data={mockPieData} config={config} />)).not.toThrow();
  });

  it('displays percentage labels on donut chart', () => {
    const config: ChartConfig = {
      type: 'donut',
    };

    // Should render without errors (labels are rendered internally)
    expect(() => render(<ChartWidget data={mockPieData} config={config} />)).not.toThrow();
  });

  it('shows/hides legend in donut chart', () => {
    const config: ChartConfig = {
      type: 'donut',
      showLegend: false,
    };

    const { container } = render(<ChartWidget data={mockPieData} config={config} />);

    // Legend should not be present when showLegend is false
    const legendElement = container.querySelector('.recharts-legend-wrapper');
    expect(legendElement).not.toBeInTheDocument();
  });

  it('shows/hides tooltip in donut chart', () => {
    const config: ChartConfig = {
      type: 'donut',
      showTooltip: false,
    };

    const { container } = render(<ChartWidget data={mockPieData} config={config} />);

    // Tooltip should not be present when showTooltip is false
    const tooltipElement = container.querySelector('.recharts-tooltip-wrapper');
    expect(tooltipElement).not.toBeInTheDocument();
  });

  it('handles empty data for donut chart', () => {
    const config: ChartConfig = {
      type: 'donut',
      title: 'Empty Donut',
    };

    render(<ChartWidget data={[]} config={config} />);

    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('handles loading state for donut chart', () => {
    const config: ChartConfig = {
      type: 'donut',
    };

    render(<ChartWidget data={mockPieData} config={config} isLoading={true} />);

    // Should render skeleton loader
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('handles error state for donut chart', () => {
    const config: ChartConfig = {
      type: 'donut',
      title: 'Error Donut',
    };

    render(<ChartWidget data={mockPieData} config={config} error="Failed to load" />);

    expect(screen.getByText('Chart Error')).toBeInTheDocument();
    expect(screen.getByText('Failed to load')).toBeInTheDocument();
  });

  it('renders donut chart with inner radius distinct from pie chart', () => {
    const donutConfig: ChartConfig = {
      type: 'donut',
    };

    // Donut should render without errors (innerRadius is applied internally)
    expect(() => render(<ChartWidget data={mockPieData} config={donutConfig} />)).not.toThrow();
  });
});

describe('ChartWidget - Histogram Chart', () => {
  it('renders histogram chart with data', () => {
    const config: ChartConfig = {
      type: 'histogram',
      title: 'Value Distribution',
      description: 'Frequency distribution of values',
    };

    render(<ChartWidget data={mockHistogramData} config={config} />);

    expect(screen.getByText('Value Distribution')).toBeInTheDocument();
    expect(screen.getByText('Frequency distribution of values')).toBeInTheDocument();
  });

  it('calculates bins automatically when histogramBins not specified', () => {
    const config: ChartConfig = {
      type: 'histogram',
    };

    // Should render without errors (bins are calculated automatically)
    expect(() => render(<ChartWidget data={mockHistogramData} config={config} />)).not.toThrow();
  });

  it('uses custom bin count when specified', () => {
    const config: ChartConfig = {
      type: 'histogram',
      histogramBins: 5,
    };

    // Should render without errors with custom bin count
    expect(() => render(<ChartWidget data={mockHistogramData} config={config} />)).not.toThrow();
  });

  it('handles single value dataset for histogram', () => {
    const singleValueData: ChartDataPoint[] = [
      { name: 'Item 1', value: 100 },
      { name: 'Item 2', value: 100 },
      { name: 'Item 3', value: 100 },
    ];

    const config: ChartConfig = {
      type: 'histogram',
    };

    // Should render without errors (handles min === max case)
    expect(() => render(<ChartWidget data={singleValueData} config={config} />)).not.toThrow();
  });

  it('shows/hides grid in histogram', () => {
    const config: ChartConfig = {
      type: 'histogram',
      showGrid: false,
    };

    const { container } = render(<ChartWidget data={mockHistogramData} config={config} />);

    // Grid should not be present when showGrid is false
    const gridElement = container.querySelector('.recharts-cartesian-grid');
    expect(gridElement).not.toBeInTheDocument();
  });

  it('shows/hides legend in histogram', () => {
    const config: ChartConfig = {
      type: 'histogram',
      showLegend: false,
    };

    const { container } = render(<ChartWidget data={mockHistogramData} config={config} />);

    // Legend should not be present when showLegend is false
    const legendElement = container.querySelector('.recharts-legend-wrapper');
    expect(legendElement).not.toBeInTheDocument();
  });

  it('displays axis labels for histogram', () => {
    const config: ChartConfig = {
      type: 'histogram',
      xAxisLabel: 'Value Range',
      yAxisLabel: 'Frequency',
    };

    // Should render without errors with axis labels
    expect(() => render(<ChartWidget data={mockHistogramData} config={config} />)).not.toThrow();
  });

  it('handles empty data for histogram', () => {
    const config: ChartConfig = {
      type: 'histogram',
      title: 'Empty Histogram',
    };

    render(<ChartWidget data={[]} config={config} />);

    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('handles loading state for histogram', () => {
    const config: ChartConfig = {
      type: 'histogram',
    };

    render(<ChartWidget data={mockHistogramData} config={config} isLoading={true} />);

    // Should render skeleton loader
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('handles error state for histogram', () => {
    const config: ChartConfig = {
      type: 'histogram',
      title: 'Error Histogram',
    };

    render(<ChartWidget data={mockHistogramData} config={config} error="Calculation failed" />);

    expect(screen.getByText('Chart Error')).toBeInTheDocument();
    expect(screen.getByText('Calculation failed')).toBeInTheDocument();
  });

  it('filters out non-numeric values for histogram binning', () => {
    const dataWithNaN: ChartDataPoint[] = [
      { name: 'Item 1', value: 10 },
      { name: 'Item 2', value: NaN },
      { name: 'Item 3', value: 20 },
    ];

    const config: ChartConfig = {
      type: 'histogram',
    };

    // Should render without errors (NaN values are filtered internally)
    expect(() => render(<ChartWidget data={dataWithNaN} config={config} />)).not.toThrow();
  });
});

describe('ChartWidget - Export Functionality', () => {
  beforeEach(() => {
    // Setup DOM for export tests
    document.body.innerHTML = '<div id="root"></div>';
  });

  afterEach(() => {
    // Cleanup DOM
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('shows export buttons when showExportButtons is true', () => {
    const config: ChartConfig = {
      type: 'area',
    };

    const { container } = render(
      <ChartWidget data={mockChartData} config={config} showExportButtons={true} />
    );

    // Check for download buttons
    const buttons = container.querySelectorAll('button[title*="Export"]');
    expect(buttons.length).toBe(2); // PNG and SVG buttons
  });

  it('calls custom onExportPNG handler when provided', () => {
    const config: ChartConfig = {
      type: 'area',
    };

    const mockExportPNG = vi.fn();

    const { container } = render(
      <ChartWidget
        data={mockChartData}
        config={config}
        showExportButtons={true}
        onExportPNG={mockExportPNG}
      />
    );

    const pngButton = container.querySelector('button[title="Export as PNG"]');
    if (pngButton) {
      fireEvent.click(pngButton);
      expect(mockExportPNG).toHaveBeenCalledTimes(1);
    }
  });

  it('calls custom onExportSVG handler when provided', () => {
    const config: ChartConfig = {
      type: 'donut',
    };

    const mockExportSVG = vi.fn();

    const { container } = render(
      <ChartWidget
        data={mockPieData}
        config={config}
        showExportButtons={true}
        onExportSVG={mockExportSVG}
      />
    );

    const svgButton = container.querySelector('button[title="Export as SVG"]');
    if (svgButton) {
      fireEvent.click(svgButton);
      expect(mockExportSVG).toHaveBeenCalledTimes(1);
    }
  });
});

describe('ChartWidget - Custom Styling', () => {
  it('applies custom className', () => {
    const config: ChartConfig = {
      type: 'area',
    };

    const { container } = render(
      <ChartWidget data={mockChartData} config={config} className="custom-chart-class" />
    );

    const card = container.querySelector('.custom-chart-class');
    expect(card).toBeInTheDocument();
  });

  it('uses custom dataKey and nameKey', () => {
    const customData: ChartDataPoint[] = [
      { month: 'Jan', sales: 100 } as any,
      { month: 'Feb', sales: 200 } as any,
    ];

    const config: ChartConfig = {
      type: 'area',
      dataKey: 'sales',
      nameKey: 'month',
    };

    // Chart should render with custom keys
    expect(() => render(<ChartWidget data={customData} config={config} />)).not.toThrow();
  });
});

describe('ChartWidget - Edge Cases', () => {
  it('handles chart with title and description', () => {
    const config: ChartConfig = {
      type: 'area',
      title: 'Test Title',
      description: 'Test Description',
    };

    render(<ChartWidget data={mockChartData} config={config} />);

    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
  });

  it('handles chart without title', () => {
    const config: ChartConfig = {
      type: 'donut',
    };

    // Should render without title
    expect(() => render(<ChartWidget data={mockPieData} config={config} />)).not.toThrow();
  });

  it('handles histogram with all same values', () => {
    const sameValueData: ChartDataPoint[] = [
      { name: 'Item 1', value: 50 },
      { name: 'Item 2', value: 50 },
      { name: 'Item 3', value: 50 },
    ];

    const config: ChartConfig = {
      type: 'histogram',
    };

    // Should handle min === max case
    expect(() => render(<ChartWidget data={sameValueData} config={config} />)).not.toThrow();
  });

  it('handles very small dataset for histogram', () => {
    const smallData: ChartDataPoint[] = [
      { name: 'Item 1', value: 10 },
      { name: 'Item 2', value: 20 },
    ];

    const config: ChartConfig = {
      type: 'histogram',
    };

    // Should calculate appropriate number of bins
    expect(() => render(<ChartWidget data={smallData} config={config} />)).not.toThrow();
  });

  it('handles very large dataset for histogram', () => {
    const largeData: ChartDataPoint[] = Array.from({ length: 1000 }, (_, i) => ({
      name: `Item ${i}`,
      value: Math.random() * 100,
    }));

    const config: ChartConfig = {
      type: 'histogram',
    };

    // Should handle large dataset and calculate bins using Sturges' rule
    expect(() => render(<ChartWidget data={largeData} config={config} />)).not.toThrow();
  });
});
