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

export type AggregationType = 'sum' | 'avg' | 'count' | 'min' | 'max' | 'count_unique';

export interface Threshold {
  value: number;
  color: string;
  operator: 'gt' | 'lt' | 'gte' | 'lte' | 'eq';
}

export interface MetricConfig {
  title: string;
  tableId?: string;
  fieldId?: string;
  aggregationType: AggregationType;
  showTrend: boolean;
  showComparison: boolean;
  comparisonFieldId?: string;
  thresholds: Threshold[];
  primaryColor: string;
  decimalPlaces: number;
  prefix?: string;
  suffix?: string;
}

interface MetricConfigModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (config: MetricConfig) => void;
  initialConfig?: Partial<MetricConfig>;
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

const DEFAULT_THRESHOLDS: Threshold[] = [
  { value: 0, color: '#ef4444', operator: 'lt' },
  { value: 50, color: '#f59e0b', operator: 'lt' },
  { value: 100, color: '#10b981', operator: 'gte' },
];

export const MetricConfigModal: React.FC<MetricConfigModalProps> = ({
  open,
  onClose,
  onSave,
  initialConfig,
  tables = [],
  fields = [],
}) => {
  const [config, setConfig] = useState<MetricConfig>({
    title: 'Metric Widget',
    aggregationType: 'sum',
    showTrend: true,
    showComparison: false,
    thresholds: DEFAULT_THRESHOLDS,
    primaryColor: '#3b82f6',
    decimalPlaces: 0,
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

  const handleChange = useCallback((field: keyof MetricConfig, value: unknown) => {
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

  const handleThresholdChange = useCallback((index: number, field: keyof Threshold, value: unknown) => {
    setConfig((prev) => ({
      ...prev,
      thresholds: prev.thresholds.map((threshold, i) =>
        i === index ? { ...threshold, [field]: value } : threshold
      ),
    }));
  }, []);

  const addThreshold = useCallback(() => {
    setConfig((prev) => ({
      ...prev,
      thresholds: [
        ...prev.thresholds,
        { value: 0, color: '#3b82f6', operator: 'eq' }
      ],
    }));
  }, []);

  const removeThreshold = useCallback((index: number) => {
    setConfig((prev) => ({
      ...prev,
      thresholds: prev.thresholds.filter((_, i) => i !== index),
    }));
  }, []);

  const handleSave = useCallback(() => {
    const newErrors: Record<string, string> = {};

    // Validate required fields
    if (!config.tableId) {
      newErrors.tableId = 'Table is required';
    }

    if (!config.fieldId) {
      newErrors.fieldId = 'Field is required';
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

  const getNumericFields = useCallback(() => {
    return getAvailableFields().filter(field =>
      field.type === 'number' || field.type === 'currency' || field.type === 'percent'
    );
  }, [getAvailableFields]);

  const numericFields = getNumericFields();

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configure Metric</DialogTitle>
          <DialogDescription>
            Customize your metric widget by selecting data source, aggregation, and visual settings.
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
              placeholder="Metric title"
              className={cn(errors.title && 'border-destructive')}
            />
            {errors.title && (
              <p className="text-sm text-destructive">{errors.title}</p>
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

          {/* Field Selection */}
          {config.tableId && (
            <div className="space-y-2">
              <Label htmlFor="fieldId">Metric Field</Label>
              <Select
                value={config.fieldId || ''}
                onValueChange={(value) => handleChange('fieldId', value)}
              >
                <SelectTrigger id="fieldId" className={cn(errors.fieldId && 'border-destructive')}>
                  <SelectValue placeholder="Select field to aggregate" />
                </SelectTrigger>
                <SelectContent>
                  {numericFields.map((field) => (
                    <SelectItem key={field.id} value={field.id}>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">[{field.type}]</span>
                        {field.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.fieldId && (
                <p className="text-sm text-destructive">{errors.fieldId}</p>
              )}
            </div>
          )}

          {/* Aggregation Type */}
          {config.fieldId && (
            <div className="space-y-2">
              <Label htmlFor="aggregationType">Aggregation Type</Label>
              <Select
                value={config.aggregationType}
                onValueChange={(value) => handleChange('aggregationType', value as AggregationType)}
              >
                <SelectTrigger id="aggregationType">
                  <SelectValue placeholder="Select aggregation type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sum">Sum</SelectItem>
                  <SelectItem value="avg">Average</SelectItem>
                  <SelectItem value="count">Count</SelectItem>
                  <SelectItem value="count_unique">Count Unique</SelectItem>
                  <SelectItem value="min">Minimum</SelectItem>
                  <SelectItem value="max">Maximum</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Format Options */}
          <div className="space-y-4 pt-4 border-t">
            <h3 className="text-sm font-semibold">Format Options</h3>

            {/* Prefix */}
            <div className="space-y-2">
              <Label htmlFor="prefix">Prefix (Optional)</Label>
              <Input
                id="prefix"
                value={config.prefix || ''}
                onChange={(e) => handleChange('prefix', e.target.value)}
                placeholder="e.g., $, €, £"
              />
            </div>

            {/* Suffix */}
            <div className="space-y-2">
              <Label htmlFor="suffix">Suffix (Optional)</Label>
              <Input
                id="suffix"
                value={config.suffix || ''}
                onChange={(e) => handleChange('suffix', e.target.value)}
                placeholder="e.g., %, units, items"
              />
            </div>

            {/* Decimal Places */}
            <div className="space-y-2">
              <Label htmlFor="decimalPlaces">Decimal Places</Label>
              <Select
                value={config.decimalPlaces.toString()}
                onValueChange={(value) => handleChange('decimalPlaces', parseInt(value, 10))}
              >
                <SelectTrigger id="decimalPlaces">
                  <SelectValue placeholder="Select decimal places" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">0</SelectItem>
                  <SelectItem value="1">1</SelectItem>
                  <SelectItem value="2">2</SelectItem>
                  <SelectItem value="3">3</SelectItem>
                </SelectContent>
              </Select>
            </div>

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
          </div>

          {/* Comparison Options */}
          <div className="space-y-4 pt-4 border-t">
            <h3 className="text-sm font-semibold">Comparison Options</h3>

            {/* Show Trend */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="showTrend"
                checked={config.showTrend}
                onCheckedChange={(checked) => handleChange('showTrend', !!checked)}
              />
              <Label htmlFor="showTrend" className="cursor-pointer">
                Show Trend Indicator
              </Label>
            </div>

            {/* Show Comparison */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="showComparison"
                checked={config.showComparison}
                onCheckedChange={(checked) => handleChange('showComparison', !!checked)}
              />
              <Label htmlFor="showComparison" className="cursor-pointer">
                Show Comparison Value
              </Label>
            </div>

            {/* Comparison Field */}
            {config.showComparison && (
              <div className="space-y-2">
                <Label htmlFor="comparisonFieldId">Comparison Field (Optional)</Label>
                <Select
                  value={config.comparisonFieldId || ''}
                  onValueChange={(value) => handleChange('comparisonFieldId', value)}
                >
                  <SelectTrigger id="comparisonFieldId">
                    <SelectValue placeholder="Select comparison field" />
                  </SelectTrigger>
                  <SelectContent>
                    {numericFields.map((field) => (
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
          </div>

          {/* Thresholds for Color Coding */}
          <div className="space-y-4 pt-4 border-t">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Color Thresholds</h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addThreshold}
              >
                Add Threshold
              </Button>
            </div>

            <p className="text-xs text-muted-foreground">
              Define conditional formatting rules based on metric values. Thresholds are evaluated in order.
            </p>

            <div className="space-y-3">
              {config.thresholds.map((threshold, index) => (
                <div key={index} className="flex items-center gap-2 p-3 border rounded-lg">
                  <div className="flex-1 grid grid-cols-3 gap-2">
                    {/* Operator */}
                    <Select
                      value={threshold.operator}
                      onValueChange={(value) => handleThresholdChange(index, 'operator', value as Threshold['operator'])}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gt">Greater than (&gt;)</SelectItem>
                        <SelectItem value="lt">Less than (&lt;)</SelectItem>
                        <SelectItem value="gte">Greater or equal (≥)</SelectItem>
                        <SelectItem value="lte">Less or equal (≤)</SelectItem>
                        <SelectItem value="eq">Equal (=)</SelectItem>
                      </SelectContent>
                    </Select>

                    {/* Value */}
                    <Input
                      type="number"
                      value={threshold.value}
                      onChange={(e) => handleThresholdChange(index, 'value', parseFloat(e.target.value) || 0)}
                      placeholder="Value"
                    />

                    {/* Color */}
                    <div className="flex items-center gap-1">
                      <Input
                        type="color"
                        value={threshold.color}
                        onChange={(e) => handleThresholdChange(index, 'color', e.target.value)}
                        className="w-12 h-9 p-0.5"
                      />
                      <span className="text-xs text-muted-foreground flex-1 truncate">
                        {threshold.color}
                      </span>
                    </div>
                  </div>

                  {/* Remove Button */}
                  {config.thresholds.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-9 w-9 text-destructive"
                      onClick={() => removeThreshold(index)}
                    >
                      ×
                    </Button>
                  )}
                </div>
              ))}
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

export default MetricConfigModal;
