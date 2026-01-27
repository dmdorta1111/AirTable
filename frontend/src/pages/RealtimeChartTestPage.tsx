import React, { useState, useEffect } from 'react';
import { GridView } from '@/components/views/GridView';
import { ChartPanel, ChartItem } from '@/components/analytics/ChartPanel';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  Wifi,
  WifiOff,
  CheckCircle,
  XCircle,
  Plus,
  Edit,
  Trash2,
} from 'lucide-react';
import { useRealtime } from '@/hooks/useRealtime';
import type { Field, RecordFieldValue } from '@/types';

// Local record data interface matching GridView's RecordData
interface RecordData {
  id: string;
  table_id: string;
  data: Record<string, RecordFieldValue>;
  row_height: number;
  created_at: string;
  updated_at: string;
  created_by_id: string;
  last_modified_by_id: string;
}

// Test table and chart IDs (matching backend test data)
const TEST_TABLE_ID = 'test-table-rt';
const TEST_CHART_ID = 'test-chart-rt';

// Sample record data that will be modified in real-time
const initialRecords: RecordData[] = [
  {
    id: 'rt-1',
    table_id: TEST_TABLE_ID,
    data: {
      product_name: 'Widget A',
      category: 'Electronics',
      quantity: 100,
      price: 25.00,
      status: 'In Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: 'rt-2',
    table_id: TEST_TABLE_ID,
    data: {
      product_name: 'Widget B',
      category: 'Electronics',
      quantity: 150,
      price: 35.00,
      status: 'In Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: 'rt-3',
    table_id: TEST_TABLE_ID,
    data: {
      product_name: 'Gadget X',
      category: 'Mechanical',
      quantity: 75,
      price: 50.00,
      status: 'In Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
  {
    id: 'rt-4',
    table_id: TEST_TABLE_ID,
    data: {
      product_name: 'Gadget Y',
      category: 'Mechanical',
      quantity: 50,
      price: 65.00,
      status: 'Low Stock',
    },
    row_height: 40,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
    created_by_id: 'user-1',
    last_modified_by_id: 'user-1',
  },
];

// Sample fields
const sampleFields: Field[] = [
  {
    id: 'product_name',
    table_id: TEST_TABLE_ID,
    name: 'product_name',
    type: 'text',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'category',
    table_id: TEST_TABLE_ID,
    name: 'category',
    type: 'single_select',
    options: {
      choices: [
        { id: 'electronics', name: 'Electronics', color: '#3b82f6' },
        { id: 'mechanical', name: 'Mechanical', color: '#f59e0b' },
        { id: 'consumables', name: 'Consumables', color: '#10b981' },
      ],
    },
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'quantity',
    table_id: TEST_TABLE_ID,
    name: 'quantity',
    type: 'number',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'price',
    table_id: TEST_TABLE_ID,
    name: 'price',
    type: 'number',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'status',
    table_id: TEST_TABLE_ID,
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

// Real-time event log entry
interface EventLogEntry {
  timestamp: Date;
  type: string;
  message: string;
  success: boolean;
}

export const RealtimeChartTestPage: React.FC = () => {
  const navigate = useNavigate();
  const [records, setRecords] = useState<RecordData[]>(initialRecords);
  const [charts, setCharts] = useState<ChartItem[]>([]);
  const [eventLog, setEventLog] = useState<EventLogEntry[]>([]);
  const [verificationStatus, setVerificationStatus] = useState({
    wsConnected: false,
    chartUpdated: false,
    noStaleData: false,
  });

  // Connect to real-time updates
  const { isConnected, isConnecting } = useRealtime({
    tableId: TEST_TABLE_ID,
    chartId: TEST_CHART_ID,
    enabled: true,
    onChartUpdated: () => {
      addLogEntry('chart.updated', 'Chart data updated via WebSocket', true);
      setVerificationStatus((prev) => ({ ...prev, chartUpdated: true }));
      refreshChartData();
    },
    onRecordUpdated: (msg) => {
      addLogEntry('record.updated', `Record ${msg.data.record_id} updated`, true);
      refreshChartData();
    },
    onRecordCreated: () => {
      addLogEntry('record.created', `New record created`, true);
      refreshChartData();
    },
    onRecordDeleted: (msg) => {
      addLogEntry('record.deleted', `Record ${msg.data.record_id} deleted`, true);
      refreshChartData();
    },
  });

  // Add entry to event log
  const addLogEntry = (type: string, message: string, success: boolean) => {
    setEventLog((prev) => [
      ...prev,
      {
        timestamp: new Date(),
        type,
        message,
        success,
      },
    ].slice(-20)); // Keep last 20 entries
  };

  // Refresh chart data based on current records
  const refreshChartData = () => {
    // Aggregate data by category
    const categoryData = records.reduce((acc, record) => {
      const category = record.data.category as string;
      const quantity = record.data.quantity as number;
      const price = record.data.price as number;

      if (!acc[category]) {
        acc[category] = { quantity: 0, totalValue: 0, count: 0 };
      }

      acc[category].quantity += quantity;
      acc[category].totalValue += quantity * price;
      acc[category].count += 1;

      return acc;
    }, {} as Record<string, { quantity: number; totalValue: number; count: number }>);

    const newCharts: ChartItem[] = [
      {
        id: 'quantity-bar',
        data: Object.entries(categoryData).map(([name, data]) => ({
          name,
          value: data.quantity,
        })),
        config: {
          type: 'bar',
          title: 'Quantity by Category',
          description: 'Real-time quantity chart',
          dataKey: 'value',
          nameKey: 'name',
          showGrid: true,
          showTooltip: true,
          colors: ['#3b82f6', '#f59e0b', '#10b981'],
        },
      },
      {
        id: 'value-area',
        data: Object.entries(categoryData).map(([name, data]) => ({
          name,
          value: data.totalValue,
        })),
        config: {
          type: 'area',
          title: 'Total Value by Category',
          description: 'Real-time value chart',
          dataKey: 'value',
          nameKey: 'name',
          showGrid: true,
          showTooltip: true,
          colors: ['#8b5cf6'],
        },
      },
    ];

    setCharts(newCharts);
    addLogEntry('chart.refresh', 'Chart data refreshed from records', true);
  };

  // Initial chart load
  useEffect(() => {
    refreshChartData();
  }, []);

  // Update verification status
  useEffect(() => {
    setVerificationStatus((prev) => ({
      ...prev,
      wsConnected: isConnected,
    }));
  }, [isConnected]);

  // Test actions
  const handleUpdateQuantity = (recordId: string, delta: number) => {
    setRecords((prev) =>
      prev.map((record) => {
        if (record.id === recordId) {
          const newQuantity = (record.data.quantity as number) + delta;
          addLogEntry(
            'user.action',
            `Updated ${record.data.product_name} quantity: ${(record.data.quantity as number)} → ${newQuantity}`,
            true
          );
          return {
            ...record,
            data: {
              ...record.data,
              quantity: Math.max(0, newQuantity),
            },
            updated_at: new Date().toISOString(),
          };
        }
        return record;
      })
    );

    // Simulate WebSocket event after delay (in real scenario, backend emits this)
    setTimeout(() => {
      addLogEntry('simulate.ws', 'Simulating WebSocket chart.updated event', true);
      refreshChartData();
    }, 500);
  };

  const handleAddRecord = () => {
    const newId = `rt-${records.length + 1}`;
    const newRecord: RecordData = {
      id: newId,
      table_id: TEST_TABLE_ID,
      data: {
        product_name: `New Product ${records.length + 1}`,
        category: 'Consumables',
        quantity: 50,
        price: 15.00,
        status: 'In Stock',
      },
      row_height: 40,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by_id: 'user-1',
      last_modified_by_id: 'user-1',
    };

    setRecords((prev) => [...prev, newRecord]);
    addLogEntry('user.action', `Added new record: ${newRecord.data.product_name}`, true);

    // Simulate WebSocket event
    setTimeout(() => {
      addLogEntry('simulate.ws', 'Simulating WebSocket record.created event', true);
      refreshChartData();
    }, 500);
  };

  const handleDeleteRecord = (recordId: string) => {
    const record = records.find((r) => r.id === recordId);
    setRecords((prev) => prev.filter((r) => r.id !== recordId));
    addLogEntry('user.action', `Deleted record: ${record?.data.product_name}`, true);

    // Simulate WebSocket event
    setTimeout(() => {
      addLogEntry('simulate.ws', 'Simulating WebSocket record.deleted event', true);
      refreshChartData();
    }, 500);
  };

  const handleCellUpdate = (rowId: string, fieldId: string, value: unknown) => {
    setRecords((prev) =>
      prev.map((record) => {
        if (record.id === rowId) {
          addLogEntry(
            'user.action',
            `Edited ${record.data.product_name} ${fieldId}: ${record.data[fieldId]} → ${value}`,
            true
          );
          return {
            ...record,
            data: {
              ...record.data,
              [fieldId]: value as RecordFieldValue,
            },
            updated_at: new Date().toISOString(),
          } as RecordData;
        }
        return record;
      })
    );

    // Simulate WebSocket event
    setTimeout(() => {
      addLogEntry('simulate.ws', 'Simulating WebSocket record.updated event', true);
      refreshChartData();
    }, 500);
  };

  const handleRowAdd = () => {
    handleAddRecord();
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
              <h1 className="text-2xl font-bold tracking-tight">
                Real-Time Chart Updates Test
              </h1>
              <p className="text-sm text-muted-foreground mt-1">
                End-to-end verification of WebSocket-based chart updates
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border">
              {isConnected ? (
                <>
                  <Wifi className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium text-green-600">Connected</span>
                </>
              ) : isConnecting ? (
                <>
                  <RefreshCw className="h-4 w-4 text-yellow-500 animate-spin" />
                  <span className="text-sm font-medium text-yellow-600">Connecting...</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-red-500" />
                  <span className="text-sm font-medium text-red-600">Disconnected</span>
                </>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.reload()}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Reset Test
            </Button>
          </div>
        </div>
      </div>

      <div className="p-6">
        {/* Test Instructions */}
        <div className="mb-6 p-4 border rounded-lg bg-card">
          <h2 className="font-semibold text-lg mb-2">Test Instructions</h2>
          <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
            <li>Verify WebSocket connection status shows "Connected" in green above</li>
            <li>Modify data in the table using the +/- buttons or edit cells directly</li>
            <li>Observe charts update automatically in real-time (within 1 second)</li>
            <li>Check the Event Log to see WebSocket events being received</li>
            <li>Verify that no stale data remains - all charts reflect current data</li>
          </ol>
        </div>

        {/* Action Buttons */}
        <div className="mb-6 p-4 border rounded-lg bg-card">
          <h2 className="font-semibold text-lg mb-3">Test Actions</h2>
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleAddRecord} size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Record
            </Button>
            <Button
              onClick={() => handleUpdateQuantity('rt-1', 50)}
              size="sm"
              variant="outline"
            >
              <Edit className="h-4 w-4 mr-2" />
              Update Widget A Quantity (+50)
            </Button>
            <Button
              onClick={() => handleUpdateQuantity('rt-2', -25)}
              size="sm"
              variant="outline"
            >
              <Edit className="h-4 w-4 mr-2" />
              Update Widget B Quantity (-25)
            </Button>
            <Button
              onClick={() => handleDeleteRecord('rt-4')}
              size="sm"
              variant="destructive"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Gadget Y
            </Button>
          </div>
        </div>

        {/* Charts */}
        {charts.length > 0 && (
          <div className="mb-6">
            <ChartPanel
              charts={charts}
              title="Real-Time Analytics"
              height="300px"
              columns={2}
            />
          </div>
        )}

        {/* Grid View */}
        <GridView
          data={records}
          fields={sampleFields}
          onCellUpdate={handleCellUpdate}
          onRowAdd={handleRowAdd}
        />

        {/* Verification Status */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className={`p-4 border rounded-lg ${verificationStatus.wsConnected ? 'bg-green-50 border-green-200' : 'bg-gray-50'}`}>
            <div className="flex items-center gap-2">
              {verificationStatus.wsConnected ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-400" />
              )}
              <span className="font-medium">WebSocket Connected</span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {verificationStatus.wsConnected
                ? 'Real-time connection is active'
                : 'Waiting for connection...'}
            </p>
          </div>

          <div className={`p-4 border rounded-lg ${verificationStatus.chartUpdated ? 'bg-green-50 border-green-200' : 'bg-gray-50'}`}>
            <div className="flex items-center gap-2">
              {verificationStatus.chartUpdated ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-400" />
              )}
              <span className="font-medium">Chart Updates Received</span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {verificationStatus.chartUpdated
                ? 'Charts updated via WebSocket'
                : 'No updates received yet'}
            </p>
          </div>

          <div className={`p-4 border rounded-lg ${verificationStatus.noStaleData ? 'bg-green-50 border-green-200' : 'bg-gray-50'}`}>
            <div className="flex items-center gap-2">
              {verificationStatus.noStaleData ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-gray-400" />
              )}
              <span className="font-medium">No Stale Data</span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {verificationStatus.noStaleData
                ? 'All charts show current data'
                : 'Verify manually by checking charts'}
            </p>
          </div>
        </div>

        {/* Event Log */}
        <div className="mt-6 p-4 border rounded-lg bg-card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-lg">Event Log</h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setEventLog([])}
            >
              Clear Log
            </Button>
          </div>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {eventLog.length === 0 ? (
              <p className="text-sm text-muted-foreground">No events yet. Perform an action to see real-time updates.</p>
            ) : (
              eventLog.map((entry, index) => (
                <div
                  key={index}
                  className="flex items-start gap-2 text-sm p-2 rounded bg-muted/50"
                >
                  <span className="text-xs text-muted-foreground font-mono min-w-[120px]">
                    {entry.timestamp.toLocaleTimeString()}
                  </span>
                  <span className={`font-mono text-xs min-w-[100px] px-2 py-0.5 rounded ${
                    entry.type === 'user.action' ? 'bg-blue-100 text-blue-700' :
                    entry.type === 'simulate.ws' ? 'bg-purple-100 text-purple-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {entry.type}
                  </span>
                  <span className={entry.success ? 'text-foreground' : 'text-red-600'}>
                    {entry.message}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Verification Checklist */}
        <div className="mt-6 p-4 border rounded-lg bg-card">
          <h2 className="font-semibold text-lg mb-3">Verification Checklist</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-medium text-sm mb-2">WebSocket Connection</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Connection status shows "Connected" in green
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  WebSocket URL includes table and chart IDs
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Connection stays alive during interactions
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-sm mb-2">Real-Time Updates</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Charts update within 1 second of data change
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Event log shows WebSocket events
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  No page refresh required for updates
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-sm mb-2">Data Integrity</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Charts reflect current table data
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  No stale data after multiple updates
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  All chart types update correctly
                </li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium text-sm mb-2">User Actions</h3>
              <ul className="text-sm space-y-1">
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Add record triggers chart update
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Update record triggers chart update
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-4 h-4 border rounded flex items-center justify-center text-xs">□</span>
                  Delete record triggers chart update
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RealtimeChartTestPage;
