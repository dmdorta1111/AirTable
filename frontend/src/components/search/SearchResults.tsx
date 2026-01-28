import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, Clock, TrendingUp, ExternalLink } from 'lucide-react';
import { cn } from '@/components/ui/button';
import type { SearchResult, SearchResponse } from '@/types/search';

interface SearchResultsProps {
  /** Search response containing results and metadata */
  searchResponse: SearchResponse | null;
  /** Whether search is in progress */
  isLoading?: boolean;
  /** Error message to display */
  error?: string | null;
  /** Callback when a result is clicked */
  onResultClick?: (result: SearchResult) => void;
  /** Maximum number of highlights to show per field */
  maxHighlights?: number;
  /** Whether to show relevance score */
  showScore?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * SearchResults component displays search results with highlighted matches.
 *
 * Features:
 * - Displays search results in card format
 * - Shows highlighted snippets for matching terms
 * - Displays relevance score and rank
 * - Shows table name and metadata
 * - Handles loading, empty, and error states
 *
 * @example
 * ```tsx
 * <SearchResults
 *   searchResponse={response}
 *   onResultClick={(result) => navigateToRecord(result)}
 *   showScore={true}
 * />
 * ```
 */
export const SearchResults: React.FC<SearchResultsProps> = ({
  searchResponse,
  isLoading = false,
  error = null,
  onResultClick,
  maxHighlights = 3,
  showScore = false,
  className,
}) => {
  /**
   * Render highlighted text with matching terms emphasized
   */
  const renderHighlightedText = (text: string): React.ReactNode => {
    if (!text) return null;

    // Meilisearch uses <em> tags for highlights
    // Parse and convert to React elements
    const parts = text.split(/(<em>.*?<\/em>)/g);

    return parts.map((part, index) => {
      if (part.startsWith('<em>') && part.endsWith('</em>')) {
        const highlightedText = part.slice(4, -5);
        return (
          <mark
            key={index}
            className="bg-yellow-200 dark:bg-yellow-800 rounded px-0.5 font-semibold"
          >
            {highlightedText}
          </mark>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  /**
   * Render field value with appropriate formatting
   */
  const renderFieldValue = (value: unknown): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-muted-foreground italic">Empty</span>;
    }

    if (typeof value === 'boolean') {
      return <Badge variant={value ? 'default' : 'secondary'}>{String(value)}</Badge>;
    }

    if (typeof value === 'number') {
      return <span className="font-mono">{value.toLocaleString()}</span>;
    }

    if (Array.isArray(value)) {
      return (
        <div className="flex flex-wrap gap-1">
          {value.slice(0, 5).map((item, index) => (
            <Badge key={index} variant="outline" className="text-xs">
              {String(item)}
            </Badge>
          ))}
          {value.length > 5 && (
            <Badge variant="outline" className="text-xs">
              +{value.length - 5} more
            </Badge>
          )}
        </div>
      );
    }

    if (typeof value === 'object') {
      return <span className="text-muted-foreground italic">[Object]</span>;
    }

    return <span>{String(value)}</span>;
  };

  /**
   * Render highlights for a single result
   */
  const renderHighlights = (highlights: Record<string, string[]>): React.ReactNode => {
    const entries = Object.entries(highlights).slice(0, maxHighlights);

    if (entries.length === 0) {
      return null;
    }

    return (
      <div className="mt-3 space-y-2">
        {entries.map(([fieldName, snippets]) => (
          <div key={fieldName} className="text-sm">
            <div className="font-medium text-xs text-muted-foreground mb-1">
              {fieldName}
            </div>
            {snippets.slice(0, 2).map((snippet, index) => (
              <div
                key={index}
                className="text-slate-700 dark:text-slate-300 line-clamp-2"
              >
                …{renderHighlightedText(snippet)}…
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  };

  /**
   * Render a single search result card
   */
  const renderResultCard = (result: SearchResult): React.ReactNode => {
    return (
      <Card
        key={result.record_id}
        className={cn(
          'cursor-pointer transition-all hover:shadow-md hover:border-primary/50',
          onResultClick && 'hover:scale-[1.01]'
        )}
        onClick={() => onResultClick?.(result)}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <CardTitle className="text-base truncate flex items-center gap-2">
                <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                <span className="truncate">{result.record_id}</span>
              </CardTitle>
              <CardDescription className="flex items-center gap-2 mt-1">
                <span className="font-medium text-foreground">{result.table_name}</span>
                {showScore && (
                  <>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      {(result.score * 100).toFixed(1)}% match
                    </span>
                  </>
                )}
                <span>•</span>
                <span className="flex items-center gap-1">
                  Rank {result.rank}
                </span>
              </CardDescription>
            </div>
            {onResultClick && (
              <Button
                variant="ghost"
                size="sm"
                className="flex-shrink-0"
                onClick={(e) => {
                  e.stopPropagation();
                  onResultClick(result);
                }}
              >
                <ExternalLink className="h-4 w-4" />
                <span className="sr-only">View record</span>
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="pt-0">
          {/* Display field values */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-3">
            {Object.entries(result.fields)
              .slice(0, 4)
              .map(([fieldName, value]) => (
                <div key={fieldName} className="text-sm">
                  <span className="text-xs text-muted-foreground font-medium">
                    {fieldName}:
                  </span>
                  <span className="ml-2">{renderFieldValue(value)}</span>
                </div>
              ))}
          </div>

          {/* Display highlights if available */}
          {result.highlights && renderHighlights(result.highlights)}

          {/* Display timestamps if available */}
          {(result.created_at || result.updated_at) && (
            <div className="mt-3 pt-3 border-t flex items-center gap-4 text-xs text-muted-foreground">
              {result.created_at && (
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Created {new Date(result.created_at).toLocaleDateString()}
                </div>
              )}
              {result.updated_at && (
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Updated {new Date(result.updated_at).toLocaleDateString()}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  /**
   * Render loading state
   */
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center py-12', className)}>
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-primary border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <p className="mt-4 text-sm text-muted-foreground">Searching records...</p>
        </div>
      </div>
    );
  }

  /**
   * Render error state
   */
  if (error) {
    return (
      <div className={cn('py-8', className)}>
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-destructive font-medium">Search Error</p>
              <p className="text-xs text-muted-foreground mt-1">{error}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  /**
   * Render empty state (no results)
   */
  if (!searchResponse || searchResponse.results.length === 0) {
    return (
      <div className={cn('py-8', className)}>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-sm font-medium">No results found</p>
              <p className="text-xs text-muted-foreground mt-1">
                Try adjusting your search query or filters
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  /**
   * Render search results
   */
  const { results, metadata } = searchResponse;

  return (
    <div className={cn('space-y-4', className)}>
      {/* Results header with metadata */}
      <div className="flex items-center justify-between text-sm">
        <div className="text-muted-foreground">
          <span className="font-medium text-foreground">{metadata.total_results}</span>
          {' '}results found
          {metadata.execution_time_ms && (
            <span className="ml-2">
              in <span className="font-medium">{metadata.execution_time_ms}ms</span>
            </span>
          )}
        </div>
        {metadata.total_results_filtered !== undefined && metadata.filters_applied && (
          <Badge variant="secondary">
            {metadata.total_results_filtered} filtered
          </Badge>
        )}
      </div>

      {/* Results list */}
      <div className="space-y-3">
        {results.map((result) => renderResultCard(result))}
      </div>

      {/* Results footer with pagination info */}
      {metadata.total_results > results.length && (
        <div className="text-center text-sm text-muted-foreground py-2">
          Showing <span className="font-medium">{results.length}</span> of{' '}
          <span className="font-medium">{metadata.total_results}</span> results
        </div>
      )}
    </div>
  );
};

export default SearchResults;
