"""Search API endpoints.

Provides full-text search across records using Meilisearch.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.schemas.search import SearchRequest, SearchResponse, SearchResult

router = APIRouter()


# =============================================================================
# Search Endpoints
# =============================================================================


@router.post("/bases/{base_id}/search", response_model=SearchResponse)
async def search_base(
    base_id: str,
    request: SearchRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> SearchResponse:
    """
    Search within a specific base.

    Supports full-text search with faceted navigation across all tables and records in the base.
    """
    from pybase.services.search import get_search_service

    service = get_search_service(db)

    # Convert filters dict if needed
    filters_dict = None
    if request.filters:
        filters_dict = request.filters.model_dump(exclude_none=True)

    results = await service.search_in_base(
        base_id=base_id,
        query=request.query,
        table_id=request.table_id,
        field_id=request.field_id,
        filters=filters_dict,
        facets=request.facets,
        sort=request.sort,
        limit=request.limit,
        offset=request.offset,
        highlight_results=request.highlight_results,
    )
    return results


@router.post("/search", response_model=SearchResponse)
async def global_search(
    request: SearchRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> SearchResponse:
    """
    Global search across all accessible bases.

    Searches all records the user has access to with faceted navigation support.
    """
    from pybase.services.search import get_search_service

    service = get_search_service(db)

    # Convert filters dict if needed
    filters_dict = None
    if request.filters:
        filters_dict = request.filters.model_dump(exclude_none=True)

    results = await service.global_search(
        user_id=str(current_user.id),
        query=request.query,
        filters=filters_dict,
        facets=request.facets,
        sort=request.sort,
        limit=request.limit,
        offset=request.offset,
        highlight_results=request.highlight_results,
    )
    return results
