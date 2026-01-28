import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { SearchBar } from '@/components/search/SearchBar';
import { SearchResults } from '@/components/search/SearchResults';
import { FacetedFilters } from '@/components/search/FacetedFilters';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { SearchResponse, SearchResult, FacetResult } from '@/types/search';

/**
 * SearchPage - Full-text search interface with faceted navigation
 *
 * Features:
 * - Global search across all bases/tables
 * - Real-time search with debouncing
 * - Faceted filters for drill-down
 * - Result highlighting
 * - Direct navigation to records
 */
export const SearchPage: React.FC = () => {
  const navigate = useNavigate();

  // State management
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedFilters, setSelectedFilters] = useState<Record<string, string[]>>({});

  /**
   * Handle search results from SearchBar component
   */
  const handleSearchResults = useCallback((results: SearchResponse | null, query: string) => {
    setSearchResponse(results);
    setSearchError(null);

    // Update selected filters based on response facets
    if (results?.facets) {
      const newFilters: Record<string, string[]> = {};
      results.facets.forEach((facet: FacetResult) => {
        const selectedValues = facet.values
          .filter((v) => v.is_selected)
          .map((v) => v.value);
        if (selectedValues.length > 0) {
          newFilters[facet.field_id] = selectedValues;
        }
      });
      setSelectedFilters(newFilters);
    }

    // Unused query parameter - available for future use
    void query;
  }, []);

  /**
   * Handle filter change from FacetedFilters component
   */
  const handleFilterChange = useCallback(
    (fieldId: string, values: string[]) => {
      setSelectedFilters((prev) => ({
        ...prev,
        [fieldId]: values,
      }));

      // Trigger new search with updated filters
      // This would be implemented with the actual search API
      void fieldId;
      void values;
    },
    []
  );

  /**
   * Clear all filters
   */
  const handleClearAllFilters = useCallback(() => {
    setSelectedFilters({});
    // Trigger new search without filters
  }, []);

  /**
   * Handle clicking on a search result
   */
  const handleResultClick = useCallback((result: SearchResult) => {
    // Navigate to the record in the table view
    navigate(`/tables/${result.table_id}?record=${result.record_id}`);
  }, [navigate]);

  /**
   * Calculate total active filters count
   */
  const getTotalFilterCount = useCallback((): number => {
    return Object.values(selectedFilters).reduce((sum, values) => sum + values.length, 0);
  }, [selectedFilters]);

  const totalFilterCount = getTotalFilterCount();

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header Section */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-6 py-6">
          <div className="mb-4">
            <h1 className="text-3xl font-bold tracking-tight">Search</h1>
            <p className="text-muted-foreground mt-1">
              Full-text search across all your bases and tables
            </p>
          </div>

          {/* Search Bar */}
          <SearchBar
            onSearchResults={handleSearchResults}
            placeholder="Search for records, tables, or data..."
            instantSearch={true}
            debounceMs={300}
            minQueryLength={2}
            className="max-w-4xl"
          />

          {/* Active filters display */}
          {totalFilterCount > 0 && (
            <div className="mt-4 flex items-center gap-2 flex-wrap">
              <span className="text-sm text-muted-foreground">Active filters:</span>
              {Object.entries(selectedFilters).map(([fieldId, values]) =>
                values.map((value) => (
                  <Badge
                    key={`${fieldId}-${value}`}
                    variant="secondary"
                    className="gap-1 pr-1"
                  >
                    {fieldId}: {value}
                    <button
                      onClick={() => {
                        const newValues = values.filter((v) => v !== value);
                        handleFilterChange(fieldId, newValues);
                      }}
                      className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
                    >
                      ×
                    </button>
                  </Badge>
                ))
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClearAllFilters}
                className="h-7 text-xs"
              >
                Clear all
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        <div className="container mx-auto px-6 py-6 h-full">
          <div className="flex gap-6 h-full">
            {/* Sidebar - Faceted Filters */}
            <aside className="w-80 flex-shrink-0 overflow-y-auto">
              <FacetedFilters
                facets={searchResponse?.facets || []}
                selectedFilters={selectedFilters}
                onFilterChange={handleFilterChange}
                onClearAll={handleClearAllFilters}
                isLoading={false}
                maxValues={10}
                showCounts={true}
              />
            </aside>

            {/* Main Content - Search Results */}
            <main className="flex-1 overflow-y-auto">
              {searchError ? (
                <SearchResults
                  searchResponse={null}
                  isLoading={false}
                  error={searchError}
                  onResultClick={handleResultClick}
                  showScore={true}
                />
              ) : (
                <SearchResults
                  searchResponse={searchResponse}
                  isLoading={false}
                  error={null}
                  onResultClick={handleResultClick}
                  showScore={true}
                  maxHighlights={3}
                />
              )}

              {/* Initial State */}
              {!searchResponse && !searchError && (
                <div className="flex flex-col items-center justify-center h-full py-16">
                  <div className="max-w-md text-center">
                    <div className="text-6xl mb-4">🔍</div>
                    <h2 className="text-2xl font-semibold mb-2">Start Searching</h2>
                    <p className="text-muted-foreground">
                      Enter a search query above to find records across all your bases and tables.
                      Use the filters on the left to narrow down results.
                    </p>
                    <div className="mt-6 p-4 bg-muted/50 rounded-lg text-sm text-left">
                      <p className="font-medium mb-2">Search Tips:</p>
                      <ul className="space-y-1 text-muted-foreground">
                        <li>• Use quotes for exact phrases: "part number"</li>
                        <li>• Minimum 2 characters to start searching</li>
                        <li>• Filters appear after your first search</li>
                        <li>• Click any result to view the full record</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </main>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SearchPage;
