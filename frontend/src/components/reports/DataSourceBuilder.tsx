import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  Database,
  Plus,
  Trash2,
  GripVertical,
  ArrowRight,
  AlertCircle,
  Settings,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

// =============================================================================
// Type Definitions matching backend schemas
// =============================================================================

export type JoinType = 'inner' | 'left' | 'right' | 'full';
export type AggregateType = 'none' | 'sum' | 'avg' | 'count' | 'min' | 'max';
export type FilterOperator =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'not_contains'
  | 'greater_than'
  | 'less_than'
  | 'between'
  | 'is_null'
  | 'is_not_null';
export type SortDirection = 'asc' | 'desc';
export type LogicOperator = 'and' | 'or';

// Table metadata
export interface TableField {
  id: string;
  name: string;
  type: string;
}

export interface TableMeta {
  id: string;
  name: string;
  fields: TableField[];
}

// Join definition
export interface JoinDefinition {
  left_table: string;
  left_field: string;
  right_table: string;
  right_field: string;
}

// Table join configuration
export interface TableJoinConfig {
  table_id: string;
  alias?: string;
  join_type: JoinType;
  join_on?: JoinDefinition;
}

// Tables configuration
export interface TablesConfig {
  primary_table: string;
  tables: TableJoinConfig[];
}

// Field configuration
export interface FieldConfig {
  table_id: string;
  field_id: string;
  alias?: string;
  aggregate: AggregateType;
  visible: boolean;
}

// Filter configuration
export interface FilterConfig {
  field_id: string;
  operator: FilterOperator;
  value: unknown;
  logic: LogicOperator;
}

// Sort configuration
export interface SortConfig {
  field_id: string;
  direction: SortDirection;
}

// Sort and group configuration
export interface SortGroupConfig {
  sort_by: SortConfig[];
  group_by: string[];
  limit?: number;
  offset: number;
}

// Data source configuration
export interface DataSourceConfig {
  name: string;
  description?: string;
  tables: TablesConfig;
  fields: FieldConfig[];
  filters: FilterConfig[];
  sort_group: SortGroupConfig;
}

interface DataSourceBuilderProps {
  tables: TableMeta[];
  initialConfig?: Partial<DataSourceConfig>;
  onSave?: (config: DataSourceConfig) => void;
  onCancel?: () => void;
  isLoading?: boolean;
  error?: string;
  className?: string;
}

// =============================================================================
// Sub-components
// =============================================================================

interface JoinConfigRowProps {
  join: TableJoinConfig;
  tables: TableMeta[];
  primaryTable: string;
  onUpdate: (join: TableJoinConfig) => void;
  onRemove: () => void;
  index: number;
}

const JoinConfigRow: React.FC<JoinConfigRowProps> = ({
  join,
  tables,
  primaryTable,
  onUpdate,
  onRemove,
  index,
}) => {
  const [expanded, setExpanded] = useState(false);

  const getAvailableTables = () => {
    return tables.filter((t) => t.id !== primaryTable);
  };

  const getLeftTableFields = () => {
    if (join.join_on?.left_table) {
      const table = tables.find((t) => t.id === join.join_on?.left_table);
      return table?.fields || [];
    }
    return [];
  };

  const getRightTableFields = () => {
    if (join.join_on?.right_table) {
      const table = tables.find((t) => t.id === join.join_on?.right_table);
      return table?.fields || [];
    }
    return [];
  };

  const getJoinTypeLabel = (type: JoinType) => {
    const labels: Record<JoinType, string> = {
      inner: 'INNER JOIN',
      left: 'LEFT JOIN',
      right: 'RIGHT JOIN',
      full: 'FULL JOIN',
    };
    return labels[type];
  };

  return (
    <div className="border rounded-lg p-3 space-y-3 bg-muted/20">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-1">
          <GripVertical className="h-4 w-4 text-muted-foreground" />
          <Badge variant="outline">{getJoinTypeLabel(join.join_type)}</Badge>
          <span className="text-sm font-medium">
            {tables.find((t) => t.id === join.table_id)?.name || join.table_id}
          </span>
          {join.alias && (
            <Badge variant="secondary" className="text-xs">
              {join.alias}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive"
            onClick={onRemove}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {expanded && (
        <div className="space-y-3 pt-2 border-t">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Join Type</Label>
              <Select
                value={join.join_type}
                onValueChange={(value) =>
                  onUpdate({ ...join, join_type: value as JoinType })
                }
              >
                <SelectTrigger className="h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="inner">INNER JOIN</SelectItem>
                  <SelectItem value="left">LEFT JOIN</SelectItem>
                  <SelectItem value="right">RIGHT JOIN</SelectItem>
                  <SelectItem value="full">FULL JOIN</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label className="text-xs">Alias (optional)</Label>
              <Input
                value={join.alias || ''}
                onChange={(e) =>
                  onUpdate({ ...join, alias: e.target.value || undefined })
                }
                placeholder="Table alias"
                className="h-8"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-xs">Join Condition</Label>
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <Select
                  value={join.join_on?.left_table}
                  onValueChange={(value) =>
                    onUpdate({
                      ...join,
                      join_on: {
                        ...join.join_on!,
                        left_table: value,
                        left_field: '',
                      },
                    })
                  }
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="Left table" />
                  </SelectTrigger>
                  <SelectContent>
                    {[primaryTable, ...getAvailableTables().map((t) => t.id)].map(
                      (id) => (
                        <SelectItem key={id} value={id}>
                          {tables.find((t) => t.id === id)?.name || id}
                        </SelectItem>
                      )
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex-1">
                <Select
                  value={join.join_on?.left_field}
                  onValueChange={(value) =>
                    onUpdate({
                      ...join,
                      join_on: { ...join.join_on!, left_field: value },
                    })
                  }
                  disabled={!join.join_on?.left_table}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="Field" />
                  </SelectTrigger>
                  <SelectContent>
                    {getLeftTableFields().map((field) => (
                      <SelectItem key={field.id} value={field.id}>
                        {field.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <ArrowRight className="h-4 w-4 text-muted-foreground" />

              <div className="flex-1">
                <Select
                  value={join.join_on?.right_table}
                  onValueChange={(value) =>
                    onUpdate({
                      ...join,
                      join_on: {
                        ...join.join_on!,
                        right_table: value,
                        right_field: '',
                      },
                    })
                  }
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="Right table" />
                  </SelectTrigger>
                  <SelectContent>
                    {getAvailableTables().map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex-1">
                <Select
                  value={join.join_on?.right_field}
                  onValueChange={(value) =>
                    onUpdate({
                      ...join,
                      join_on: { ...join.join_on!, right_field: value },
                    })
                  }
                  disabled={!join.join_on?.right_table}
                >
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="Field" />
                  </SelectTrigger>
                  <SelectContent>
                    {getRightTableFields().map((field) => (
                      <SelectItem key={field.id} value={field.id}>
                        {field.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// =============================================================================
// Main DataSourceBuilder Component
// =============================================================================

export const DataSourceBuilder: React.FC<DataSourceBuilderProps> = ({
  tables,
  initialConfig,
  onSave,
  onCancel,
  isLoading = false,
  error,
  className,
}) => {
  const [config, setConfig] = useState<DataSourceConfig>(() => ({
    name: initialConfig?.name || '',
    description: initialConfig?.description || '',
    tables: initialConfig?.tables || { primary_table: '', tables: [] },
    fields: initialConfig?.fields || [],
    filters: initialConfig?.filters || [],
    sort_group: initialConfig?.sort_group || { sort_by: [], group_by: [], offset: 0 },
  }));

  const [activeTab, setActiveTab] = useState<
    'tables' | 'fields' | 'filters' | 'sort'
  >('tables');

  const handleAddJoin = () => {
    const availableTables = tables.filter(
      (t) =>
        t.id !== config.tables.primary_table &&
        !config.tables.tables.some((j) => j.table_id === t.id)
    );

    if (availableTables.length > 0) {
      const newJoin: TableJoinConfig = {
        table_id: availableTables[0].id,
        join_type: 'inner',
      };
      setConfig({
        ...config,
        tables: { ...config.tables, tables: [...config.tables.tables, newJoin] },
      });
    }
  };

  const handleUpdateJoin = (index: number, join: TableJoinConfig) => {
    const updatedTables = [...config.tables.tables];
    updatedTables[index] = join;
    setConfig({
      ...config,
      tables: { ...config.tables, tables: updatedTables },
    });
  };

  const handleRemoveJoin = (index: number) => {
    setConfig({
      ...config,
      tables: {
        ...config.tables,
        tables: config.tables.tables.filter((_, i) => i !== index),
      },
    });
  };

  const handleAddField = (tableId: string, fieldId: string) => {
    const existingField = config.fields.find(
      (f) => f.table_id === tableId && f.field_id === fieldId
    );

    if (!existingField) {
      setConfig({
        ...config,
        fields: [...config.fields, { table_id: tableId, field_id, field_id: fieldId, aggregate: 'none', visible: true }],
      });
    }
  };

  const handleUpdateField = (index: number, field: FieldConfig) => {
    const updatedFields = [...config.fields];
    updatedFields[index] = field;
    setConfig({ ...config, fields: updatedFields });
  };

  const handleRemoveField = (index: number) => {
    setConfig({
      ...config,
      fields: config.fields.filter((_, i) => i !== index),
    });
  };

  const handleAddFilter = () => {
    if (config.fields.length > 0) {
      const newFilter: FilterConfig = {
        field_id: config.fields[0].field_id,
        operator: 'equals',
        value: '',
        logic: 'and',
      };
      setConfig({ ...config, filters: [...config.filters, newFilter] });
    }
  };

  const handleUpdateFilter = (index: number, filter: FilterConfig) => {
    const updatedFilters = [...config.filters];
    updatedFilters[index] = filter;
    setConfig({ ...config, filters: updatedFilters });
  };

  const handleRemoveFilter = (index: number) => {
    setConfig({
      ...config,
      filters: config.filters.filter((_, i) => i !== index),
    });
  };

  const handleAddSort = () => {
    if (config.fields.length > 0) {
      const newSort: SortConfig = {
        field_id: config.fields[0].field_id,
        direction: 'asc',
      };
      setConfig({
        ...config,
        sort_group: {
          ...config.sort_group,
          sort_by: [...config.sort_group.sort_by, newSort],
        },
      });
    }
  };

  const handleUpdateSort = (index: number, sort: SortConfig) => {
    const updatedSorts = [...config.sort_group.sort_by];
    updatedSorts[index] = sort;
    setConfig({
      ...config,
      sort_group: { ...config.sort_group, sort_by: updatedSorts },
    });
  };

  const handleRemoveSort = (index: number) => {
    setConfig({
      ...config,
      sort_group: {
        ...config.sort_group,
        sort_by: config.sort_group.sort_by.filter((_, i) => i !== index),
      },
    });
  };

  const handleSave = () => {
    if (onSave) {
      onSave(config);
    }
  };

  const isFormValid = () => {
    return (
      config.name.trim() !== '' &&
      config.tables.primary_table !== '' &&
      config.fields.some((f) => f.visible)
    );
  };

  // Render loading state
  if (isLoading) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Data Source Builder
          </CardTitle>
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
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Data Source Builder
          </CardTitle>
        </CardHeader>
        <CardContent className="h-[calc(100%-5rem)]">
          <div className="h-full flex items-center justify-center text-destructive">
            <div className="text-center space-y-2">
              <AlertCircle className="h-8 w-8 mx-auto" />
              <p className="text-sm font-medium">Configuration Error</p>
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const availableTablesForJoin = tables.filter(
    (t) =>
      t.id !== config.tables.primary_table &&
      !config.tables.tables.some((j) => j.table_id === t.id)
  );

  return (
    <Card className={cn('h-full flex flex-col', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Data Source Builder
        </CardTitle>
        <CardDescription>
          Configure data sources with multi-table joins, filters, and sorting
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 overflow-auto space-y-4">
        {/* Basic Info */}
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="datasource-name">Data Source Name *</Label>
            <Input
              id="datasource-name"
              value={config.name}
              onChange={(e) => setConfig({ ...config, name: e.target.value })}
              placeholder="My Data Source"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="datasource-description">Description</Label>
            <Input
              id="datasource-description"
              value={config.description || ''}
              onChange={(e) =>
                setConfig({ ...config, description: e.target.value })
              }
              placeholder="Optional description"
            />
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b">
          <div className="flex gap-4">
            <button
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'tables'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              onClick={() => setActiveTab('tables')}
            >
              Tables
            </button>
            <button
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'fields'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              onClick={() => setActiveTab('fields')}
            >
              Fields ({config.fields.filter((f) => f.visible).length})
            </button>
            <button
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'filters'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              onClick={() => setActiveTab('filters')}
            >
              Filters ({config.filters.length})
            </button>
            <button
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 transition-colors',
                activeTab === 'sort'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              onClick={() => setActiveTab('sort')}
            >
              Sort & Group
            </button>
          </div>
        </div>

        {/* Tables Tab */}
        {activeTab === 'tables' && (
          <div className="space-y-4">
            {/* Primary Table */}
            <div className="space-y-2">
              <Label>Primary Table *</Label>
              <Select
                value={config.tables.primary_table}
                onValueChange={(value) =>
                  setConfig({
                    ...config,
                    tables: { ...config.tables, primary_table: value },
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select primary table" />
                </SelectTrigger>
                <SelectContent>
                  {tables.map((table) => (
                    <SelectItem key={table.id} value={table.id}>
                      {table.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Joins */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Joined Tables</Label>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleAddJoin}
                  disabled={
                    !config.tables.primary_table ||
                    availableTablesForJoin.length === 0
                  }
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Add Join
                </Button>
              </div>

              {config.tables.tables.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground border rounded-lg border-dashed">
                  <Database className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No joins configured</p>
                  <p className="text-xs mt-1">
                    Add joins to combine data from multiple tables
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {config.tables.tables.map((join, index) => (
                    <JoinConfigRow
                      key={`${join.table_id}-${index}`}
                      join={join}
                      tables={tables}
                      primaryTable={config.tables.primary_table}
                      onUpdate={(j) => handleUpdateJoin(index, j)}
                      onRemove={() => handleRemoveJoin(index)}
                      index={index}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Fields Tab */}
        {activeTab === 'fields' && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Selected Fields</Label>
              {config.fields.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground border rounded-lg border-dashed">
                  <p className="text-sm">No fields selected</p>
                  <p className="text-xs mt-1">
                    Add fields from the primary and joined tables
                  </p>
                </div>
              ) : (
                <div className="border rounded-md">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-12">Visible</TableHead>
                        <TableHead>Field</TableHead>
                        <TableHead>Alias</TableHead>
                        <TableHead>Aggregate</TableHead>
                        <TableHead className="w-12"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {config.fields.map((field, index) => {
                        const table = tables.find((t) => t.id === field.table_id);
                        const fieldMeta = table?.fields.find(
                          (f) => f.id === field.field_id
                        );
                        return (
                          <TableRow key={index}>
                            <TableCell>
                              <Checkbox
                                checked={field.visible}
                                onCheckedChange={(checked) =>
                                  handleUpdateField(index, {
                                    ...field,
                                    visible: checked as boolean,
                                  })
                                }
                              />
                            </TableCell>
                            <TableCell>
                              <div>
                                <div className="font-medium">
                                  {fieldMeta?.name || field.field_id}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {table?.name || field.table_id}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Input
                                value={field.alias || ''}
                                onChange={(e) =>
                                  handleUpdateField(index, {
                                    ...field,
                                    alias: e.target.value || undefined,
                                  })
                                }
                                placeholder="Optional alias"
                                className="h-8"
                              />
                            </TableCell>
                            <TableCell>
                              <Select
                                value={field.aggregate}
                                onValueChange={(value) =>
                                  handleUpdateField(index, {
                                    ...field,
                                    aggregate: value as AggregateType,
                                  })
                                }
                              >
                                <SelectTrigger className="h-8">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="none">None</SelectItem>
                                  <SelectItem value="sum">Sum</SelectItem>
                                  <SelectItem value="avg">Average</SelectItem>
                                  <SelectItem value="count">Count</SelectItem>
                                  <SelectItem value="min">Min</SelectItem>
                                  <SelectItem value="max">Max</SelectItem>
                                </SelectContent>
                              </Select>
                            </TableCell>
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={() => handleRemoveField(index)}
                              >
                                <Trash2 className="h-3.5 w-3.5 text-destructive" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Filters Tab */}
        {activeTab === 'filters' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Filters</Label>
              <Button
                size="sm"
                variant="outline"
                onClick={handleAddFilter}
                disabled={config.fields.length === 0}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Filter
              </Button>
            </div>

            {config.filters.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground border rounded-lg border-dashed">
                <p className="text-sm">No filters configured</p>
                <p className="text-xs mt-1">
                  Add filters to narrow down your data
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {config.filters.map((filter, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 p-3 border rounded-lg bg-muted/20"
                  >
                    <Select
                      value={filter.logic}
                      onValueChange={(value) =>
                        handleUpdateFilter(index, {
                          ...filter,
                          logic: value as LogicOperator,
                        })
                      }
                    >
                      <SelectTrigger className="w-20 h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="and">AND</SelectItem>
                        <SelectItem value="or">OR</SelectItem>
                      </SelectContent>
                    </Select>

                    <Select
                      value={filter.field_id}
                      onValueChange={(value) =>
                        handleUpdateFilter(index, { ...filter, field_id: value })
                      }
                    >
                      <SelectTrigger className="flex-1 h-8">
                        <SelectValue placeholder="Field" />
                      </SelectTrigger>
                      <SelectContent>
                        {config.fields.map((field) => {
                          const table = tables.find((t) => t.id === field.table_id);
                          const fieldMeta = table?.fields.find(
                            (f) => f.id === field.field_id
                          );
                          return (
                            <SelectItem key={field.field_id} value={field.field_id}>
                              {fieldMeta?.name || field.field_id}
                            </SelectItem>
                          );
                        })}
                      </SelectContent>
                    </Select>

                    <Select
                      value={filter.operator}
                      onValueChange={(value) =>
                        handleUpdateFilter(index, {
                          ...filter,
                          operator: value as FilterOperator,
                        })
                      }
                    >
                      <SelectTrigger className="w-32 h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="equals">Equals</SelectItem>
                        <SelectItem value="not_equals">Not Equals</SelectItem>
                        <SelectItem value="contains">Contains</SelectItem>
                        <SelectItem value="not_contains">Not Contains</SelectItem>
                        <SelectItem value="greater_than">
                          Greater Than
                        </SelectItem>
                        <SelectItem value="less_than">Less Than</SelectItem>
                        <SelectItem value="between">Between</SelectItem>
                        <SelectItem value="is_null">Is Null</SelectItem>
                        <SelectItem value="is_not_null">Is Not Null</SelectItem>
                      </SelectContent>
                    </Select>

                    <Input
                      value={String(filter.value || '')}
                      onChange={(e) =>
                        handleUpdateFilter(index, {
                          ...filter,
                          value: e.target.value,
                        })
                      }
                      placeholder="Value"
                      className="flex-1 h-8"
                      disabled={filter.operator === 'is_null' || filter.operator === 'is_not_null'}
                    />

                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => handleRemoveFilter(index)}
                    >
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Sort Tab */}
        {activeTab === 'sort' && (
          <div className="space-y-4">
            {/* Sort By */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Sort By</Label>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleAddSort}
                  disabled={config.fields.length === 0}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Add Sort
                </Button>
              </div>

              {config.sort_group.sort_by.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground border rounded-lg border-dashed">
                  <p className="text-sm">No sorting configured</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {config.sort_group.sort_by.map((sort, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 p-2 border rounded-lg"
                    >
                      <GripVertical className="h-4 w-4 text-muted-foreground" />
                      <Select
                        value={sort.field_id}
                        onValueChange={(value) =>
                          handleUpdateSort(index, { ...sort, field_id: value })
                        }
                      >
                        <SelectTrigger className="flex-1 h-8">
                          <SelectValue placeholder="Field" />
                        </SelectTrigger>
                        <SelectContent>
                          {config.fields.map((field) => {
                            const table = tables.find((t) => t.id === field.table_id);
                            const fieldMeta = table?.fields.find(
                              (f) => f.id === field.field_id
                            );
                            return (
                              <SelectItem key={field.field_id} value={field.field_id}>
                                {fieldMeta?.name || field.field_id}
                              </SelectItem>
                            );
                          })}
                        </SelectContent>
                      </Select>

                      <Select
                        value={sort.direction}
                        onValueChange={(value) =>
                          handleUpdateSort(index, {
                            ...sort,
                            direction: value as SortDirection,
                          })
                        }
                      >
                        <SelectTrigger className="w-24 h-8">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="asc">Ascending</SelectItem>
                          <SelectItem value="desc">Descending</SelectItem>
                        </SelectContent>
                      </Select>

                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => handleRemoveSort(index)}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Limit and Offset */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Limit Records</Label>
                <Input
                  type="number"
                  value={config.sort_group.limit || ''}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      sort_group: {
                        ...config.sort_group,
                        limit: e.target.value ? parseInt(e.target.value) : undefined,
                      },
                    })
                  }
                  placeholder="No limit"
                  className="h-8"
                  min={1}
                  max={10000}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Offset Records</Label>
                <Input
                  type="number"
                  value={config.sort_group.offset}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      sort_group: {
                        ...config.sort_group,
                        offset: parseInt(e.target.value) || 0,
                      },
                    })
                  }
                  placeholder="0"
                  className="h-8"
                  min={0}
                />
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="text-sm text-muted-foreground">
            {config.fields.filter((f) => f.visible).length} visible fields
          </div>
          <div className="flex items-center gap-2">
            {onCancel && (
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
            <Button onClick={handleSave} disabled={!isFormValid()}>
              Save Data Source
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default DataSourceBuilder;
