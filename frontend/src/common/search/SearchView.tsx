import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Search, Filter, MoreHorizontal, ChevronDown, Check, Loader2 } from 'lucide-react';
import {
  Input,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Popover,
  PopoverContent,
  PopoverTrigger,
  ScrollArea,
  Separator,
  Badge,
} from '@/components/ui';
import { useQuery } from '@tanstack/react-query';

interface RecordFieldValue {
  field_id: string;
  value: unknown;
}

interface Field {
  id: string;
  name: string;
  type: string;
  options?: {
    choices?: string[];
    [key: string]: unknown;
  };
}

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

interface SearchViewProps {
  data: RecordData[];
  fields: Field[];
  onRecordClick: (recordId: string) => void;
  onFilterChange?: (filters: Record<string, unknown>) => void;
  baseId?: string;
}

export const SearchView: React.FC<SearchViewProps> = ({ data, fields, onRecordClick, onFilterChange, baseId }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [fieldFilter, setFieldFilter] = useState<Record<string, unknown>>({});
  const [filters, setFilters] = useState<Record<string, unknown>>({});
  
  const [debouncedSearch, setDebouncedSearch] = useState(searchQuery);
  
  // Debounce search queries
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Update parent when filters change
  useEffect(() => {
    if (onFilterChange) {
      onFilterChange({
        ...filters,
        search: debouncedSearch,
        fields: fieldFilter,
      });
    }
  }, [debouncedSearch, fieldFilter, filters, onFilterChange]);

  // Search in record data
  const { data: searchResults = [], isLoading } = useQuery({
    queryKey: ['search', debouncedSearch, JSON.stringify(fieldFilter), JSON.stringify(filters)],
    queryFn: () => {
      if (!debouncedSearch) return [];
      
      // Local search - will be replaced with API call
      const query = debouncedSearch.toLowerCase();
      
      return data.filter(record => {
        const matchesQuery = query === '' || Object.values(record.data).some(
          val => val && typeof val === 'string' && val.toLowerCase().includes(query)
        );
        
        const matchesFilters = Object.entries(filters).every(([key, value]) => {
          if (!value) return true;
          const recordValue = record.data[key];
          if (!recordValue) return true;
          return recordValue === value;
        });
        
        return matchesQuery && matchesFilters;
      });
    },
    enabled: !!debouncedSearch,
  });

  // Get filterable field types
  const filterableFields = useMemo(() => {
    const defaultFilters = [
      'text', 'long_text', 'email', 'phone', 'url', 'status', 'date', 'datetime', 
      'single_select', 'multi_select'
    ];
    
    return fields.filter(f => defaultFilters.includes(f.type));
  }, [fields]);

  const getAvailableChoices = (fieldId: string) => {
    const field = fields.find(f => f.id === fieldId);
    if (field?.type === 'single_select' || field?.type === 'multi_select') {
      return field.options?.choices || [];
    }
    return [];
  };

  const clearFilters = () => {
    setFilters({});
    setFieldFilter({});
    setSearchQuery('');
    setDebouncedSearch('');
  };

  const hasActiveFilters = Object.keys(filters).length > 0 || debouncedSearch !== '';

  return (
    <div className="space-y-4">
      <Card className="border shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Search className="h-4 w-4 text-muted-foreground" />
              Search
              {hasActiveFilters && (
                <Badge 
                  variant="secondary" 
                  className="h-5"
                >
                  {searchResults.length} results
                </Badge>
              )}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              disabled={!hasActiveFilters}
            >
              Clear
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search all records..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 h-10"
              />
              {searchQuery && (
                <kbd className="absolute right-2.5 top-2.5 h-5 rounded border bg-muted px-2 text-xs text-muted-foreground">
                  ⌘K
                </kbd>
              )}
            </div>

            {/* Filters */}
            <div className="flex gap-4">
              {/* Field Filter Dropdown */}
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm" className="w-[200px]">
                    <Filter className="h-4 w-4 mr-2" />
                    Filter by field
                    <ChevronDown className="h-4 w-4 ml-2" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-56 p-2" align="start">
                  <ScrollArea className="max-h-[200px]">
                    {filterableFields.length > 0 && (
                      <div className="pb-2">
                        <p className="text-sm font-medium mb-1">Fields</p>
                        {filterableFields.map((filterableField) => (
                          <div
                            key={filterableField.id}
                            onClick={() => {
                              const newFilters = { ...fieldFilter };
                              if (newFilters[filterableField.id]) {
                                delete newFilters[filterableField.id];
                              } else {
                                newFilters[filterableField.id] = [];
                              }
                              setFieldFilter(newFilters);
                            }}
                            className={`flex items-center cursor-pointer p-2 rounded hover:bg-accent ${fieldFilter[filterableField.id] ? 'bg-accent' : ''}`}
                          >
                            {fieldFilter[filterableField.id] && (
                              <Check className="mr-2 h-4 w-4" />
                            )}
                            <span className="capitalize">{filterableField.name}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    <Separator />

                    {/* Field filter when a field is selected */}
                    {Object.keys(fieldFilter).map((fieldKey) => {
                      const selectedField = fields.find(f => f.id === fieldKey);
                      if (!selectedField) return null;

                      return (
                        <div key={fieldKey}>
                          <div className="text-sm font-medium mb-2 text-muted-foreground">
                            {selectedField.name}
                          </div>
                          {selectedField.type === 'status' ? (
                            <div
                              className="flex items-center gap-2 cursor-pointer p-2 rounded hover:bg-accent"
                              onClick={() => {
                                const newFilters = { ...fieldFilter };
                                newFilters[fieldKey] = [];
                                setFieldFilter(newFilters);
                              }}
                            >
                              <Check className="mr-2 h-4 w-4" />
                              <span>Clear filter</span>
                            </div>
                          ) : (
                            <div className="text-sm text-muted-foreground">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  const newFilters = { ...fieldFilter };
                                  delete newFilters[fieldKey];
                                  setFieldFilter(newFilters);
                                }}
                              >
                                Clear
                              </Button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </ScrollArea>
                </PopoverContent>
              </Popover>

              {/* Advanced Filters Button */}
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm">
                    <MoreHorizontal className="h-4 w-4 ml-2" />
                    More filters
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-56 p-4" align="start">
                  <div className="text-sm font-medium mb-3">Advanced Filters</div>
                  <Separator />
                  <div className="mb-4">
                    <label className="text-xs text-muted-foreground mb-1">Date Range</label>
                    <Input
                      type="date"
                      placeholder="Start date"
                      onChange={(e) => {
                        const date = e.target.value;
                        setFilters(prev => ({
                          ...prev,
                          dateRangeStart: date || undefined,
                        }));
                      }}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground mb-1">End Date</label>
                    <Input
                      type="date"
                      placeholder="End date"
                      onChange={(e) => {
                        const date = e.target.value;
                        setFilters(prev => ({
                          ...prev,
                          dateRangeEnd: date || undefined,
                        }));
                      }}
                    />
                  </div>
                  <div className="flex justify-end mt-2">
                    <Button variant="outline" size="sm" onClick={clearFilters}>
                      Clear All
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>
            </div>

            {/* Results Count */}
            {debouncedSearch && (
              <p className="text-sm text-muted-foreground">
                Found <span className="font-semibold text-foreground">{searchResults.length}</span> results
              </p>
            )}

            {/* Loading State */}
            {isLoading && <div className="text-center py-8"><Loader2 className="h-6 w-6 animate-spin mx-auto" /></div>}

            {/* Empty State */}
            {!isLoading && searchResults.length === 0 && debouncedSearch && (
              <div className="text-center py-12">
                <p className="text-sm text-muted-foreground italic">No results for "{debouncedSearch}"</p>
                <Button variant="link" onClick={clearFilters} className="mt-2">
                  Clear filters
                </Button>
              </div>
            )}

            {/* Results List */}
            <ScrollArea className="h-[500px]">
              {searchResults.map((record) => {
                const firstFieldValue = Object.values(record.data || {})[0];
                const displayName = firstFieldValue?.value
                  ? String(firstFieldValue.value)
                  : record.id.slice(0, 8);
                const previewValues = Object.values(record.data || {})
                  .slice(0, 3)
                  .map(v => v?.value ? String(v.value) : '')
                  .filter(Boolean)
                  .join(', ');

                return (
                  <div
                    key={record.id}
                    className="mb-2 border rounded-md hover:bg-accent/50 cursor-pointer p-3 transition-colors"
                    onClick={() => onRecordClick(record.id)}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 h-16 w-16 rounded bg-primary/10 flex items-center justify-center text-primary-foreground font-semibold">
                        {displayName.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-medium text-foreground">{displayName}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(record.created_at).toLocaleDateString()} - {new Date(record.updated_at).toLocaleTimeString()}
                        </p>
                      </div>
                      <Button
                        className="ml-auto flex-shrink-0"
                        variant="secondary"
                        size="sm"
                      >
                        View
                      </Button>
                    </div>
                    <div className="flex-1 text-sm text-muted-foreground">
                      <p>{previewValues}</p>
                    </div>
                  </div>
                );
              })}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
  );
};