import React, { useState } from 'react';
import { GridView } from '@/components/views/GridView';
import { ChartItem } from '@/components/analytics/ChartPanel';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import type { Field } from '@/types';

// Sample record data mimicking a parts/inventory table
const sampleRecords = [
  {
    id: '1',
    table_id: 'test-table',
    data: {
      part_name: 'Steel Bolt M8',
      material: 'Steel',
      quantity: 150,
      unit_cost: 2.50,
      category: 'Fasteners',
      supplier: 'ABC Supplies',
      status: 'In Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: '2',
    table_id: 'test-table',
    data: {
      part_name: 'Aluminum Bracket',
      material: 'Aluminum',
      quantity: 75,
      unit_cost: 8.75,
      category: 'Brackets',
      supplier: 'XYZ Manufacturing',
      status: 'In Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: '3',
    table_id: 'test-table',
    data: {
      part_name: 'Plastic Washer',
      material: 'Plastic',
      quantity: 500,
      unit_cost: 0.15,
      category: 'Fasteners',
      supplier: 'ABC Supplies',
      status: 'In Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: '4',
    table_id: 'test-table',
    data: {
      part_name: 'Copper Wire',
      material: 'Copper',
      quantity: 200,
      unit_cost: 12.50,
      category: 'Electrical',
      supplier: 'ElectroParts Inc',
      status: 'Low Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: '5',
    table_id: 'test-table',
    data: {
      part_name: 'Steel Plate',
      material: 'Steel',
      quantity: 25,
      unit_cost: 45.00,
      category: 'Plates',
      supplier: 'MetalWorks Ltd',
      status: 'Low Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: '6',
    table_id: 'test-table',
    data: {
      part_name: 'Brass Fitting',
      material: 'Brass',
      quantity: 120,
      unit_cost: 5.25,
      category: 'Fittings',
      supplier: 'XYZ Manufacturing',
      status: 'In Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: '7',
    table_id: 'test-table',
    data: {
      part_name: 'Stainless Screw',
      material: 'Steel',
      quantity: 300,
      unit_cost: 0.85,
      category: 'Fasteners',
      supplier: 'ABC Supplies',
      status: 'In Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: '8',
    table_id: 'test-table',
    data: {
      part_name: 'Titanium Rod',
      material: 'Titanium',
      quantity: 15,
      unit_cost: 125.00,
      category: 'Rods',
      supplier: 'AeroSpace Parts',
      status: 'Low Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
];

// Sample fields definition
const sampleFields: Field[] = [
  {
    id: 'part_name',
    table_id: 'test-table',
    name: 'part_name',
    type: 'text',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'material',
    table_id: 'test-table',
    name: 'material',
    type: 'single_select',
    options: {
      choices: [
        { id: 'steel', name: 'Steel', color: '#3b82f6' },
        { id: 'aluminum', name: 'Aluminum', color: '#f59e0b' },
        { id: 'plastic', name: 'Plastic', color: '#10b981' },
        { id: 'copper', name: 'Copper', color: '#ef4444' },
        { id: 'brass', name: 'Brass', color: '#8b5cf6' },
        { id: 'titanium', name: 'Titanium', color: '#ec4899' },
      ],
    },
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'quantity',
    table_id: 'test-table',
    name: 'quantity',
    type: 'number',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'unit_cost',
    table_id: 'test-table',
    name: 'unit_cost',
    type: 'number',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'category',
    table_id: 'test-table',
    name: 'category',
    type: 'single_select',
    options: {
      choices: [
        { id: 'fasteners', name: 'Fasteners' },
        { id: 'brackets', name: 'Brackets' },
        { id: 'electrical', name: 'Electrical' },
        { id: 'plates', name: 'Plates' },
        { id: 'fittings', name: 'Fittings' },
        { id: 'rods', name: 'Rods' },
      ],
    },
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'supplier',
    table_id: 'test-table',
    name: 'supplier',
    type: 'text',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'status',
    table_id: 'test-table',
    name: 'status',
    type: 'single_select',
    options: {
      choices: [
        { id: 'in-stock', name: 'In Stock', color: '#10b981' },
        { id: 'low-stock', name: 'Low Stock', color: '#ef4444' },
        { id: 'out-of-stock', name: 'Out of Stock', color: '#6b7280' },
      ],
    },
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
];

// Aggregated chart data
const materialDistributionChart: ChartItem = {
  id: 'material-distribution',
  data: [
    { name: 'Steel', value: 475, cost: 48.70 },
    { name: 'Aluminum', value: 75, cost: 8.75 },
    { name: 'Plastic', value: 500, cost: 0.15 },
    { name: 'Copper', value: 200, cost: 12.50 },
    { name: 'Brass', value: 120, cost: 5.25 },
    { name: 'Titanium', value: 15, cost: 125.00 },
  ],
  config: {
    type: 'donut',
    title: 'Material Distribution (Quantity)',
    description: 'Parts quantity by material type',
    dataKey: 'value',
    nameKey: 'name',
    showLegend: true,
    showTooltip: true,
    colors: ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899'],
  },
};

const categoryBarChart: ChartItem = {
  id: 'category-bar',
  data: [
    { name: 'Fasteners', value: 950, cost: 3.50 },
    { name: 'Brackets', value: 75, cost: 8.75 },
    { name: 'Electrical', value: 200, cost: 12.50 },
    { name: 'Plates', value: 25, cost: 45.00 },
    { name: 'Fittings', value: 120, cost: 5.25 },
    { name: 'Rods', value: 15, cost: 125.00 },
  ],
  config: {
    type: 'bar',
    title: 'Inventory by Category',
    description: 'Total quantity per category',
    dataKey: 'value',
    nameKey: 'name',
    xAxisLabel: 'Category',
    yAxisLabel: 'Quantity',
    showGrid: true,
    showLegend: true,
    showTooltip: true,
    colors: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
  },
};

const costAreaChart: ChartItem = {
  id: 'cost-area',
  data: [
    { name: 'Fasteners', value: 3325.00 },
    { name: 'Brackets', value: 656.25 },
    { name: 'Electrical', value: 2500.00 },
    { name: 'Plates', value: 1125.00 },
    { name: 'Fittings', value: 630.00 },
    { name: 'Rods', value: 1875.00 },
  ],
  config: {
    type: 'area',
    title: 'Total Inventory Value',
    description: 'Total value (quantity × unit cost) by category',
    dataKey: 'value',
    nameKey: 'name',
    xAxisLabel: 'Category',
    yAxisLabel: 'Total Value ($)',
    showGrid: true,
    showLegend: true,
    showTooltip: true,
    colors: ['#8b5cf6'],
  },
};

const quantityHistogram: ChartItem = {
  id: 'quantity-histogram',
  data: [
    { name: 'Steel Bolt M8', value: 150 },
    { name: 'Aluminum Bracket', value: 75 },
    { name: 'Plastic Washer', value: 500 },
    { name: 'Copper Wire', value: 200 },
    { name: 'Steel Plate', value: 25 },
    { name: 'Brass Fitting', value: 120 },
    { name: 'Stainless Screw', value: 300 },
    { name: 'Titanium Rod', value: 15 },
  ],
  config: {
    type: 'histogram',
    title: 'Quantity Distribution',
    description: 'Frequency distribution of part quantities',
    dataKey: 'value',
    nameKey: 'name',
    xAxisLabel: 'Quantity Range',
    yAxisLabel: 'Frequency',
    showGrid: true,
    showTooltip: true,
    histogramBins: 5,
    colors: ['#f59e0b'],
  },
};

const statusPieChart: ChartItem = {
  id: 'status-pie',
  data: [
    { name: 'In Stock', value: 5 },
    { name: 'Low Stock', value: 3 },
  ],
  config: {
    type: 'pie',
    title: 'Stock Status',
    description: 'Parts by stock status',
    dataKey: 'value',
    nameKey: 'name',
    showLegend: true,
    showTooltip: true,
    colors: ['#10b981', '#ef4444'],
  },
};

export const GridViewChartTestPage: React.FC = () => {
  const navigate = useNavigate();
  const [charts] = useState<ChartItem[]>([
    materialDistributionChart,
    categoryBarChart,
    costAreaChart,
    quantityHistogram,
    statusPieChart,
  ]);
  const [chartsLoading] = useState(false);
  const [chartsError] = useState<string | undefined>(undefined);
  const [showCharts, setShowCharts] = useState(true);

  const handleCellUpdate = (rowId: string, fieldId: string, value: unknown) => {
    console.log('Cell updated:', { rowId, fieldId, value });
    // In a real app, this would update the backend
  };

  const handleRowAdd = () => {
    console.log('Add row clicked');
    // In a real app, this would open a dialog to add a new row
  };

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
              <h1 className="text-2xl font-bold tracking-tight">Grid View with Chart Panels Test</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Manual verification of chart panels integrated with Grid View
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCharts(!showCharts)}
            >
              {showCharts ? 'Hide Charts' : 'Show Charts'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.reload()}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Reload
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {/* Info Section */}
        <div className="mb-6 p-4 border rounded-lg bg-card">
          <h2 className="font-semibold text-lg mb-2">Test Information</h2>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            <li>This page demonstrates chart panels integrated with Grid View</li>
            <li>Charts display aggregated data from the table below</li>
            <li>Toggle charts on/off using the "Hide Charts/Show Charts" button</li>
            <li>All new chart types are included: donut, area, histogram, plus bar and pie</li>
            <li>Charts are responsive and display in a 2-column grid layout</li>
          </ul>
        </div>

        {/* Grid View with Chart Panels */}
        <GridView
          data={sampleRecords}
          fields={sampleFields}
          onCellUpdate={handleCellUpdate}
          onRowAdd={handleRowAdd}
          charts={showCharts ? charts : undefined}
          chartsTitle="Inventory Analytics"
          chartsLoading={chartsLoading}
          chartsError={chartsError}
        />

        {/* Verification Checklist */}
        <div className="mt-6 p-4 border rounded-lg bg-card">
          <h2 className="font-semibold text-lg mb-3">Manual Verification Checklist</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-medium text-sm mb-2">Chart Panel</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Chart panel renders above table
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Panel title displays correctly
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Charts display in 2-column grid
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  All 5 charts render without errors
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-sm mb-2">Chart Types</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Donut chart (Material Distribution)
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Bar chart (Category)
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Area chart (Cost)
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Histogram (Quantity Distribution)
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Pie chart (Status)
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-sm mb-2">Interactivity</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Tooltips display on hover
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Legends display correctly
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Charts are responsive
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Hide/Show charts works
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-sm mb-2">Grid View Integration</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Table renders below charts
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Sample data displays correctly
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Sorting works
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Cell editing works
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GridViewChartTestPage;
