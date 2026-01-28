import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Filter, ChevronDown, ChevronUp, X, SlidersHorizontal } from 'lucide-react';
import type { FacetResult, FacetType } from '@/types/search';

interface FacetedFiltersProps {
  /** Facet results from search response */
  facets: FacetResult[];
  /** Currently selected filter values per field */
  selectedFilters?: Record<string, string[]>;
  /** Callback fired when filters are changed */
  onFilterChange?: (fieldId: string, values: string[]) => void;
  /** Callback fired when all filters are cleared */
  onClearAll?: () => void;
  /** Whether filters are currently loading */
  isLoading?: boolean;
  /** Maximum number of facet values to show initially */
  maxValues?: number;
  /** Whether to show facet counts */
  showCounts?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * FacetedFilters component for filtering search results by facet values.
 *
 * Features:
 * - Collapsible facet sections
 * - Checkbox-based multi-select filtering
 * - Display of facet value counts
 * - Support for multiple facet types (string, boolean, numeric)
 * - Clear all filters functionality
 * - Empty and loading states
 *
 * @example
 * ```tsx
 * <FacetedFilters
 *   facets={searchResponse.facets}
 *   selectedFilters={{ status: ['active', 'pending'] }}
 *   onFilterChange={(fieldId, values) => updateFilters(fieldId, values)}
 *   onClearAll={() => clearAllFilters()}
 *   showCounts={true}
 * />
 * ```
 */
export const FacetedFilters: React.FC<FacetedFiltersProps> = ({
  facets,
  selectedFilters = {},
  onFilterChange,
  onClearAll,
  isLoading = false,
  maxValues = 10,
  showCounts = true,
  className,
}) => {
  /** Track collapsed state for each facet section */
  const [collapsedFacets, setCollapsedFacets] = useState<Record<string, boolean>>({});
  /** Track expanded state for showing more values */
  const [expandedFacets, setExpandedFacets] = useState<Record<string, boolean>>({});

  /**
   * Toggle facet section collapse state
   */
  const toggleCollapse = useCallback((fieldId: string) => {
    setCollapsedFacets((prev) => ({
      ...prev,
      [fieldId]: !prev[fieldId],
    }));
  }, []);

  /**
   * Toggle show more values for a facet
   */
  const toggleShowMore = useCallback((fieldId: string) => {
    setExpandedFacets((prev) => ({
      ...prev,
      [fieldId]: !prev[fieldId],
    }));
  }, []);

  /**
   * Handle checkbox change for a facet value
   */
  const handleCheckboxChange = useCallback(
    (fieldId: string, value: string, checked: boolean) => {
      const currentValues = selectedFilters[fieldId] || [];
      let newValues: string[];

      if (checked) {
        newValues = [...currentValues, value];
      } else {
        newValues = currentValues.filter((v) => v !== value);
      }

      onFilterChange?.(fieldId, newValues);
    },
    [selectedFilters, onFilterChange]
  );

  /**
   * Check if a specific value is selected
   */
  const isValueSelected = useCallback(
    (fieldId: string, value: string): boolean => {
      return (selectedFilters[fieldId] || []).includes(value);
    },
    [selectedFilters]
  );

  /**
   * Get total number of active filters
   */
  const getTotalFilterCount = useCallback((): number => {
    return Object.values(selectedFilters).reduce((sum, values) => sum + values.length, 0);
  }, [selectedFilters]);

  /**
   * Get icon for facet type
   */
  const getFacetTypeIcon = useCallback((facetType: FacetType): string => {
    switch (facetType) {
      case 'boolean':
        return '●';
      case 'integer':
      case 'float':
        return '#';
      case 'date':
        return '📅';
      case 'array':
        return '☰';
      default:
        return '●';
    }
  }, []);

  /**
   * Render a single facet value with checkbox
   */
  const renderFacetValue = (
    facet: FacetResult,
    valueObj: { value: string; count: number; is_selected?: boolean }
  ): React.ReactNode => {
    const { value, count } = valueObj;
    const fieldId = facet.field_id;
    const checked = isValueSelected(fieldId, value);

    return (
      <div
        key={value}
        className="flex items-center space-x-2 py-1.5 px-2 hover:bg-muted/50 rounded cursor-pointer transition-colors"
      >
        <Checkbox
          id={`${fieldId}-${value}`}
          checked={checked}
          onCheckedChange={(checked) =>
            handleCheckboxChange(fieldId, value, checked === true)
          }
          className="flex-shrink-0"
        />
        <label
          htmlFor={`${fieldId}-${value}`}
          className="flex-1 text-sm cursor-pointer truncate select-none"
        >
          {value}
        </label>
        {showCounts && (
          <Badge variant="secondary" className="text-xs">
            {count.toLocaleString()}
          </Badge>
        )}
      </div>
    );
  };

  /**
   * Render numeric facet with range stats
   */
  const renderNumericFacet = (facet: FacetResult): React.ReactNode => {
    if (!facet.stats) {
      return null;
    }

    const { stats } = facet;

    return (
      <div className="px-2 py-3 bg-muted/30 rounded text-sm space-y-1">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Min:</span>
          <span className="font-mono">{stats.min.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Max:</span>
          <span className="font-mono">{stats.max.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Average:</span>
          <span className="font-mono">{stats.avg.toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Count:</span>
          <span className="font-mono">{stats.count.toLocaleString()}</span>
        </div>
        <div className="text-xs text-muted-foreground mt-2 pt-2 border-t">
          Range filtering coming soon
        </div>
      </div>
    );
  };

  /**
   * Render a single facet section
   */
  const renderFacetSection = (facet: FacetResult): React.ReactNode => {
    const isCollapsed = collapsedFacets[facet.field_id];
    const isExpanded = expandedFacets[facet.field_id];
    const selectedCount = (selectedFilters[facet.field_id] || []).length;
    const visibleValues = isExpanded
      ? facet.values
      : facet.values.slice(0, maxValues);
    const hasMoreValues = facet.values.length > maxValues;

    return (
      <div key={facet.field_id} className="border-b last:border-b-0">
        {/* Facet header */}
        <button
          onClick={() => toggleCollapse(facet.field_id)}
          className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition-colors text-left"
          aria-expanded={!isCollapsed}
        >
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="text-muted-foreground" aria-hidden="true">
              {getFacetTypeIcon(facet.facet_type)}
            </span>
            <span className="font-medium text-sm truncate">{facet.field_name}</span>
            {selectedCount > 0 && (
              <Badge variant="default" className="text-xs">
                {selectedCount}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <span className="text-xs text-muted-foreground">
              {facet.total_values.toLocaleString()}
            </span>
            {isCollapsed ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
          </div>
        </button>

        {/* Facet content */}
        {!isCollapsed && (
          <div className="px-2 pb-3">
            {facet.facet_type === 'integer' || facet.facet_type === 'float' ? (
              renderNumericFacet(facet)
            ) : (
              <div className="space-y-0.5">
                {visibleValues.map((valueObj) =>
                  renderFacetValue(facet, valueObj)
                )}

                {/* Show more/less button */}
                {hasMoreValues && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleShowMore(facet.field_id)}
                    className="w-full mt-2 text-xs h-7"
                  >
                    {isExpanded ? (
                      <>
                        Show less
                        <ChevronUp className="h-3 w-3 ml-1" />
                      </>
                    ) : (
                      <>
                        Show {facet.values.length - maxValues} more
                        <ChevronDown className="h-3 w-3 ml-1" />
                      </>
                    )}
                  </Button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  /**
   * Render loading state
   */
  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-muted rounded w-3/4 mb-2" />
                <div className="space-y-1.5">
                  {[1, 2, 3].map((j) => (
                    <div key={j} className="h-3 bg-muted/50 rounded w-full" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  /**
   * Render empty state
   */
  if (facets.length === 0) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-sm text-muted-foreground">
            <Filter className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No filters available</p>
            <p className="text-xs mt-1">Perform a search to see filters</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  /**
   * Render faceted filters
   */
  const totalFilterCount = getTotalFilterCount();

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4" />
            Filters
            {totalFilterCount > 0 && (
              <Badge variant="default" className="text-xs">
                {totalFilterCount}
              </Badge>
            )}
          </CardTitle>
          {totalFilterCount > 0 && onClearAll && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearAll}
              className="h-7 text-xs"
            >
              <X className="h-3 w-3 mr-1" />
              Clear all
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="max-h-[600px] overflow-y-auto">
          {facets.map((facet) => renderFacetSection(facet))}
        </div>
      </CardContent>
    </Card>
  );
};

export default FacetedFilters;
