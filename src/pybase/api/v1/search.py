"""Search API endpoints.

Provides full-text search across records using Meilisearch.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.schemas.search import (
    IndexCreate,
    IndexResponse,
    IndexStats,
    IndexUpdate,
    ReindexRequest,
    SearchRequest,
    SearchResponse,
)
from pybase.services.meilisearch_index_manager import get_index_manager
from pybase.services.search import get_search_service

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


# =============================================================================
# Index Management Endpoints
# =============================================================================


@router.post(
    "/indexes/base/{base_id}",
    response_model=IndexResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_base_index(
    base_id: str,
    index_data: IndexCreate,
    current_user: CurrentUser,
) -> IndexResponse:
    """
    Create a search index for a base.

    Creates and configures a Meilisearch index for the specified base.
    Index will be configured with faceted search and typo tolerance.
    """
    try:
        base_uuid = UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    # Check if user has access to the base
    from pybase.models.base import Base
    from pybase.services.workspace import WorkspaceService
    from sqlalchemy import select

    index_manager = get_index_manager()

    # Verify base exists and user has access
    # (This check should be done via a database query)
    success = index_manager.create_base_index(
        base_id=str(base_uuid),
        primary_key=index_data.primary_key,
    )

    if success:
        return IndexResponse(
            success=True,
            message=f"Index created for base {base_id}",
            index_name=f"pybase:base:{base_id}",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create search index",
        )


@router.get("/indexes/base/{base_id}", response_model=IndexStats)
async def get_base_index_stats(
    base_id: str,
    current_user: CurrentUser,
) -> IndexStats:
    """
    Get statistics for a base's search index.

    Returns document count, indexing status, and field distribution.
    """
    try:
        base_uuid = UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    index_manager = get_index_manager()
    stats = index_manager.get_index_stats(base_id=str(base_uuid))

    if stats:
        return IndexStats(**stats)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Index not found for base {base_id}",
        )


@router.put("/indexes/base/{base_id}", response_model=IndexResponse)
async def update_base_index(
    base_id: str,
    index_data: IndexUpdate,
    current_user: CurrentUser,
) -> IndexResponse:
    """
    Update settings for a base's search index.

    Updates searchable fields, filterable attributes, ranking rules, and other index settings.
    """
    try:
        base_uuid = UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    index_manager = get_index_manager()

    # Build settings dict from non-None values
    settings = {}
    if index_data.searchable_attributes is not None:
        settings["searchableAttributes"] = index_data.searchable_attributes
    if index_data.filterable_attributes is not None:
        settings["filterableAttributes"] = index_data.filterable_attributes
    if index_data.sortable_attributes is not None:
        settings["sortableAttributes"] = index_data.sortable_attributes
    if index_data.ranking_rules is not None:
        settings["rankingRules"] = index_data.ranking_rules
    if index_data.typo_tolerance is not None:
        settings["typoTolerance"] = index_data.typo_tolerance
    if index_data.faceting is not None:
        settings["faceting"] = index_data.faceting
    if index_data.pagination is not None:
        settings["pagination"] = index_data.pagination

    if not settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No settings provided to update",
        )

    success = index_manager.update_index_settings(
        base_id=str(base_uuid),
        settings=settings,
    )

    if success:
        return IndexResponse(
            success=True,
            message=f"Index settings updated for base {base_id}",
            index_name=f"pybase:base:{base_id}",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update index settings",
        )


@router.delete("/indexes/base/{base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_base_index(
    base_id: str,
    current_user: CurrentUser,
) -> None:
    """
    Delete a base's search index.

    Permanently deletes the Meilisearch index for the specified base.
    All indexed data will be lost.
    """
    try:
        base_uuid = UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    index_manager = get_index_manager()
    success = index_manager.delete_base_index(base_id=str(base_uuid))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete search index",
        )


@router.post(
    "/indexes/base/{base_id}/reindex",
    response_model=IndexResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex_base(
    base_id: str,
    reindex_data: ReindexRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> IndexResponse:
    """
    Reindex all records in a base.

    Triggers reindexing of all tables and records in the specified base.
    This operation runs asynchronously and may take time for large bases.
    """
    try:
        base_uuid = UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    from sqlalchemy import select
    from pybase.models.table import Table

    service = get_search_service(db)

    # Get all tables in the base
    stmt = select(Table).where(Table.base_id == base_uuid)
    result = await db.execute(stmt)
    tables = result.scalars().all()

    if not tables:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tables found in base {base_id}",
        )

    # Reindex each table
    success_count = 0
    for table in tables:
        success = await service.index_table(
            base_id=str(base_uuid),
            table_id=str(table.id),
            batch_size=reindex_data.batch_size,
        )
        if success:
            success_count += 1

    if success_count == len(tables):
        return IndexResponse(
            success=True,
            message=f"Reindexing completed for {success_count} tables in base {base_id}",
            index_name=f"pybase:base:{base_id}",
        )
    elif success_count > 0:
        return IndexResponse(
            success=True,
            message=f"Reindexing partially completed: {success_count}/{len(tables)} tables",
            index_name=f"pybase:base:{base_id}",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reindex base",
        )

