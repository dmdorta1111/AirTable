"""Search schemas for PyBase."""

from typing import Generic, TypeVar, Optional, List, Dict, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class SearchRequest(BaseModel):
    """Search request parameters."""

    query: str = Field(..., min_length=1, description="Search query string")
    table_id: Optional[str] = Field(None, description="Limit search to specific table")
    field_id: Optional[str] = Field(None, description="Limit search to specific field")
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional search filters"
    )
    limit: int = Field(20, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")


class SearchResult(BaseModel):
    """Individual search result."""

    record_id: str
    table_id: str
    base_id: str
    table_name: str
    fields: Dict[str, Any]
    score: float = Field(..., ge=0, le=1, description="Relevance score")
    highlights: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Matched text segments with highlighting"
    )


class SearchResponse(BaseModel, Generic[T]):
    """Search response with results and metadata."""

    results: List[SearchResult]
    total: int
    limit: int
    offset: int
    processing_time_ms: float = Field(..., description="Query processing time")
