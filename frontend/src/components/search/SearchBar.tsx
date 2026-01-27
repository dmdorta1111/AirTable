import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Loader2, Search, X } from 'lucide-react';
import { cn } from '@/components/ui/button';

interface SearchBarProps {
  /** Base/workspace ID to search within */
  baseId?: string;
  /** Callback fired when search results are received */
  onSearchResults?: (results: any, query: string) => void;
  /** Callback fired when search query changes (after debounce) */
  onQueryChange?: (query: string) => void;
  /** Placeholder text for the search input */
  placeholder?: string;
  /** Debounce delay in milliseconds */
  debounceMs?: number;
  /** Minimum query length before triggering search */
  minQueryLength?: number;
  /** Additional CSS classes for the container */
  className?: string;
  /** Whether to show the search button */
  showSearchButton?: boolean;
  /** Initial search query value */
  initialValue?: string;
  /** Whether to enable instant search (search as you type) */
  instantSearch?: boolean;
}

/**
 * SearchBar component with instant search and debouncing.
 *
 * Features:
 * - Debounced input (configurable delay)
 * - Instant search capability
 * - Loading state indicator
 * - Clear button
 * - Keyboard support (Enter to search, Escape to clear)
 *
 * @example
 * ```tsx
 * <SearchBar
 *   baseId="base-123"
 *   onSearchResults={(results, query) => console.log(results)}
 *   placeholder="Search records..."
 *   instantSearch={true}
 * />
 * ```
 */
export const SearchBar: React.FC<SearchBarProps> = ({
  baseId,
  onSearchResults,
  onQueryChange,
  placeholder = 'Search...',
  debounceMs = 300,
  minQueryLength = 2,
  className,
  showSearchButton = true,
  initialValue = '',
  instantSearch = true,
}) => {
  const [query, setQuery] = useState(initialValue);
  const [isSearching, setIsSearching] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState(initialValue);

  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  /**
   * Cleanup debounce timer on unmount
   */
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  /**
   * Debounce query changes
   */
  useEffect(() => {
    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set new timer
    debounceTimerRef.current = setTimeout(() => {
      if (isMountedRef.current) {
        setDebouncedQuery(query);
      }
    }, debounceMs);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [query, debounceMs]);

  /**
   * Execute search when debounced query changes
   */
  useEffect(() => {
    const performSearch = async () => {
      // Don't search if query is too short
      if (debouncedQuery.length < minQueryLength) {
        if (isMountedRef.current) {
          onSearchResults?.([], debouncedQuery);
        }
        return;
      }

      // Notify query change
      onQueryChange?.(debouncedQuery);

      // Only perform actual search if instant search is enabled
      if (!instantSearch) {
        return;
      }

      try {
        if (isMountedRef.current) {
          setIsSearching(true);
        }

        // Import search API dynamically to avoid circular dependencies
        const { searchInBase, globalSearch } = await import('@/lib/api/search');

        const searchRequest = {
          query: debouncedQuery,
          limit: 20,
          highlight_results: true,
        };

        const results = baseId
          ? await searchInBase(baseId, searchRequest)
          : await globalSearch(searchRequest);

        if (isMountedRef.current) {
          onSearchResults?.(results, debouncedQuery);
        }
      } catch (error) {
        console.error('Search failed:', error);
        if (isMountedRef.current) {
          onSearchResults?.({ results: [], facets: [], metadata: { query: debouncedQuery, total_results: 0, total_results_filtered: 0, facets_computed: 0, execution_time_ms: 0 } }, debouncedQuery);
        }
      } finally {
        if (isMountedRef.current) {
          setIsSearching(false);
        }
      }
    };

    performSearch();
  }, [debouncedQuery, baseId, minQueryLength, instantSearch, onSearchResults, onQueryChange]);

  /**
   * Handle input change
   */
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  /**
   * Handle manual search (Enter key or search button)
   */
  const handleSearch = useCallback(async () => {
    if (query.length < minQueryLength) {
      return;
    }

    // Trigger immediate search by updating debounced query
    setDebouncedQuery(query);
  }, [query, minQueryLength]);

  /**
   * Handle clear button click
   */
  const handleClear = useCallback(() => {
    setQuery('');
    setDebouncedQuery('');
    onSearchResults?.([], '');
    onQueryChange?.('');
  }, [onSearchResults, onQueryChange]);

  /**
   * Handle keyboard shortcuts
   */
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !instantSearch) {
      e.preventDefault();
      handleSearch();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleClear();
    }
  }, [instantSearch, handleSearch, handleClear]);

  return (
    <div className={cn('relative flex items-center gap-2', className)}>
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="pl-9 pr-10"
          disabled={isSearching}
        />
        {query && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0 hover:bg-muted"
            onClick={handleClear}
            disabled={isSearching}
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Clear search</span>
          </Button>
        )}
      </div>

      {showSearchButton && !instantSearch && (
        <Button
          onClick={handleSearch}
          disabled={isSearching || query.length < minQueryLength}
          size="default"
        >
          {isSearching ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Searching...
            </>
          ) : (
            <>
              <Search className="mr-2 h-4 w-4" />
              Search
            </>
          )}
        </Button>
      )}

      {instantSearch && isSearching && (
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      )}
    </div>
  );
};

export default SearchBar;
