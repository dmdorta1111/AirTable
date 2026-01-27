import React, { useCallback, useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';

export type ChartType = 'line' | 'bar' | 'pie' | 'scatter' | 'gauge';

export interface ChartConfig {
  chartType: ChartType;
  title: string;
  tableId?: string;
  xAxisField?: string;
  yAxisField?: string;
  groupByField?: string;
  colorField?: string;
  showLegend: boolean;
  showLabels: boolean;
  primaryColor: string;
  aggregationType?: 'sum' | 'avg' | 'count' | 'min' | 'max';
}

interface ChartConfigModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (config: ChartConfig) => void;
  initialConfig?: Partial<ChartConfig>;
  tables?: Array<{ id: string; name: string }>;
  fields?: Array<{ id: string; name: string; type: string }>;
}

const DEFAULT_COLORS = [
  '#3b82f6',
  '#ef4444',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
  '#84cc16',
];

export const ChartConfigModal: React.FC<ChartConfigModalProps> = ({
  open,
  onClose,
  onSave,
  initialConfig,
  tables = [],
  fields = [],
}) => {
  const [config, setConfig] = useState<ChartConfig>({
    chartType: 'bar',
    title: 'Chart Widget',
    showLegend: true,
    showLabels: false,
    primaryColor: '#3b82f6',
    aggregationType: 'sum',
    ...initialConfig,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (initialConfig) {
      setConfig((prev) => ({
        ...prev,
        ...initialConfig,
      }));
    }
  }, [initialConfig]);

  const handleChange = useCallback((field: keyof ChartConfig, value: unknown) => {
    setConfig((prev) => ({
      ...prev,
      [field]: value,
    }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  }, [errors]);

  const handleSave = useCallback(() => {
    const newErrors: Record<string, string> = {};

    // Validate required fields based on chart type
    if (config.chartType !== 'gauge' && !config.tableId) {
      newErrors.tableId = 'Table is required';
    }

    if (config.chartType !== 'gauge') {
      if (!config.xAxisField) {
        newErrors.xAxisField = 'X-axis field is required';
      }
      if (!config.yAxisField) {
        newErrors.yAxisField = 'Y-axis field is required';
      }
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    onSave(config);
  }, [config, onSave]);

  const getAvailableFields = useCallback(() => {
    if (!config.tableId) return [];
    // In a real implementation, this would filter fields by tableId
    // For now, return all fields
    return fields;
  }, [config.tableId, fields]);

  const availableFields = getAvailableFields();

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configure Chart</DialogTitle>
          <DialogDescription>
            Customize your chart widget by selecting data source and appearance settings.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={config.title}
              onChange={(e) => handleChange('title', e.target.value)}
              placeholder="Chart title"
              className={cn(errors.title && 'border-destructive')}
            />
            {errors.title && (
              <p className="text-sm text-destructive">{errors.title}</p>
            )}
          </div>

          {/* Chart Type */}
          <div className="space-y-2">
            <Label htmlFor="chartType">Chart Type</Label>
            <Select
              value={config.chartType}
              onValueChange={(value) => handleChange('chartType', value as ChartType)}
            >
              <SelectTrigger id="chartType" className={cn(errors.chartType && 'border-destructive')}>
                <SelectValue placeholder="Select chart type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="line">Line Chart</SelectItem>
                <SelectItem value="bar">Bar Chart</SelectItem>
                <SelectItem value="pie">Pie Chart</SelectItem>
                <SelectItem value="scatter">Scatter Plot</SelectItem>
                <SelectItem value="gauge">Gauge</SelectItem>
              </SelectContent>
            </Select>
            {errors.chartType && (
              <p className="text-sm text-destructive">{errors.chartType}</p>
            )}
          </div>

          {/* Table Selection */}
          <div className="space-y-2">
            <Label htmlFor="tableId">Data Source</Label>
            <Select
              value={config.tableId || ''}
              onValueChange={(value) => handleChange('tableId', value)}
            >
              <SelectTrigger id="tableId" className={cn(errors.tableId && 'border-destructive')}>
                <SelectValue placeholder="Select a table" />
              </SelectTrigger>
              <SelectContent>
                {tables.map((table) => (
                  <SelectItem key={table.id} value={table.id}>
                    {table.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.tableId && (
              <p className="text-sm text-destructive">{errors.tableId}</p>
            )}
          </div>

          {/* Field Selection - Only show if table is selected */}
          {config.tableId && (
            <>
              {/* X-Axis Field */}
              {config.chartType !== 'gauge' && (
                <div className="space-y-2">
                  <Label htmlFor="xAxisField">X-Axis Field</Label>
                  <Select
                    value={config.xAxisField || ''}
                    onValueChange={(value) => handleChange('xAxisField', value)}
                  >
                    <SelectTrigger id="xAxisField" className={cn(errors.xAxisField && 'border-destructive')}>
                      <SelectValue placeholder="Select field for X-axis" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableFields.map((field) => (
                        <SelectItem key={field.id} value={field.id}>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">[{field.type}]</span>
                            {field.name}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.xAxisField && (
                    <p className="text-sm text-destructive">{errors.xAxisField}</p>
                  )}
                </div>
              )}

              {/* Y-Axis Field */}
              {config.chartType !== 'gauge' && (
                <div className="space-y-2">
                  <Label htmlFor="yAxisField">Y-Axis Field</Label>
                  <Select
                    value={config.yAxisField || ''}
                    onValueChange={(value) => handleChange('yAxisField', value)}
                  >
                    <SelectTrigger id="yAxisField" className={cn(errors.yAxisField && 'border-destructive')}>
                      <SelectValue placeholder="Select field for Y-axis" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableFields.map((field) => (
                        <SelectItem key={field.id} value={field.id}>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">[{field.type}]</span>
                            {field.name}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.yAxisField && (
                    <p className="text-sm text-destructive">{errors.yAxisField}</p>
                  )}
                </div>
              )}

              {/* Aggregation Type */}
              {(config.chartType === 'bar' || config.chartType === 'line') && config.yAxisField && (
                <div className="space-y-2">
                  <Label htmlFor="aggregationType">Aggregation</Label>
                  <Select
                    value={config.aggregationType || 'sum'}
                    onValueChange={(value) => handleChange('aggregationType', value as ChartConfig['aggregationType'])}
                  >
                    <SelectTrigger id="aggregationType">
                      <SelectValue placeholder="Select aggregation type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sum">Sum</SelectItem>
                      <SelectItem value="avg">Average</SelectItem>
                      <SelectItem value="count">Count</SelectItem>
                      <SelectItem value="min">Minimum</SelectItem>
                      <SelectItem value="max">Maximum</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Group By Field */}
              {config.chartType !== 'gauge' && (
                <div className="space-y-2">
                  <Label htmlFor="groupByField">Group By (Optional)</Label>
                  <Select
                    value={config.groupByField || ''}
                    onValueChange={(value) => handleChange('groupByField', value)}
                  >
                    <SelectTrigger id="groupByField">
                      <SelectValue placeholder="Select field to group by" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableFields.map((field) => (
                        <SelectItem key={field.id} value={field.id}>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">[{field.type}]</span>
                            {field.name}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Color Field */}
              {config.chartType !== 'gauge' && (
                <div className="space-y-2">
                  <Label htmlFor="colorField">Color By (Optional)</Label>
                  <Select
                    value={config.colorField || ''}
                    onValueChange={(value) => handleChange('colorField', value)}
                  >
                    <SelectTrigger id="colorField">
                      <SelectValue placeholder="Select field for color coding" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableFields.map((field) => (
                        <SelectItem key={field.id} value={field.id}>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-muted-foreground">[{field.type}]</span>
                            {field.name}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </>
          )}

          {/* Visual Configuration */}
          <div className="space-y-4 pt-4 border-t">
            <h3 className="text-sm font-semibold">Visual Configuration</h3>

            {/* Primary Color */}
            <div className="space-y-2">
              <Label htmlFor="primaryColor">Primary Color</Label>
              <div className="flex items-center gap-2">
                <div className="flex flex-wrap gap-2">
                  {DEFAULT_COLORS.map((color) => (
                    <button
                      key={color}
                      type="button"
                      className={cn(
                        "w-8 h-8 rounded border-2 transition-all hover:scale-110",
                        config.primaryColor === color
                          ? 'border-foreground scale-110'
                          : 'border-transparent'
                      )}
                      style={{ backgroundColor: color }}
                      onClick={() => handleChange('primaryColor', color)}
                    />
                  ))}
                </div>
                <Input
                  id="primaryColor"
                  type="color"
                  value={config.primaryColor}
                  onChange={(e) => handleChange('primaryColor', e.target.value)}
                  className="w-20 h-8"
                />
              </div>
            </div>

            {/* Show Legend */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="showLegend"
                checked={config.showLegend}
                onCheckedChange={(checked) => handleChange('showLegend', !!checked)}
              />
              <Label htmlFor="showLegend" className="cursor-pointer">
                Show Legend
              </Label>
            </div>

            {/* Show Labels */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="showLabels"
                checked={config.showLabels}
                onCheckedChange={(checked) => handleChange('showLabels', !!checked)}
              />
              <Label htmlFor="showLabels" className="cursor-pointer">
                Show Data Labels
              </Label>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>
            Save Configuration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ChartConfigModal;
