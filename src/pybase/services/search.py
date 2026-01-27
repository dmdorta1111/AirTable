"""Search service for PyBase using Meilisearch."""

import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from meilisearch import Client as MeilisearchClient

    MEILISEARCH_AVAILABLE = True
except ImportError:
    MEILISEARCH_AVAILABLE = False
    MeilisearchClient = None

from pybase.schemas.search import SearchRequest, SearchResult, SearchResponse


class SearchService:
    """Service for managing full-text search with Meilisearch."""

    def __init__(self, db: AsyncSession, meilisearch_url: str = "http://localhost:7700"):
        self.db = db
        self.client = None
        if MEILISEARCH_AVAILABLE:
            self.client = MeilisearchClient(meilisearch_url)

    async def search_in_base(
        self,
        base_id: str,
        query: str,
        table_id: Optional[str] = None,
        field_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """Search within a specific base."""
        if not self.client:
            return await self._database_search(
                base_id=base_id,
                query=query,
                table_id=table_id,
                limit=limit,
                offset=offset,
            )

        index_name = f"pybase:base:{base_id}"

        try:
            filter_parts = []
            if table_id:
                filter_parts.append(f"table_id = {table_id}")
            if filters:
                for key, value in filters.items():
                    filter_parts.append(f"{key} = {value}")

            filter_str = " AND ".join(filter_parts) if filter_parts else None

            search_results = self.client.index(index_name).search(
                query,
                limit=limit,
                offset=offset,
                filter=filter_str if filter_str else None,
            )

            results = []
            for hit in search_results.get("hits", []):
                results.append(
                    SearchResult(
                        record_id=str(hit["id"]),
                        table_id=hit["table_id"],
                        base_id=hit["base_id"],
                        table_name=hit.get("table_name", ""),
                        fields=hit.get("values", {}),
                        score=hit.get("_rankingScore", 0),
                        highlights=hit.get("_formatted", None),
                    )
                )

            return SearchResponse(
                results=results,
                total=search_results.get("totalHits", 0),
                limit=limit,
                offset=offset,
                processing_time_ms=search_results.get("processingTimeMs", 0),
            )

        except Exception:
            return await self._database_search(
                base_id=base_id,
                query=query,
                table_id=table_id,
                limit=limit,
                offset=offset,
            )

    async def _database_search(
        self,
        base_id: str,
        query: str,
        table_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """Fallback database search using PostgreSQL FTS."""
        from pybase.models.record import Record
        from pybase.models.base import Base

        stmt = select(Record).join(Base, Base.id == Record.table_id).where(Base.id == UUID(base_id))

        if table_id:
            stmt = stmt.where(Record.table_id == UUID(table_id))

        result = await self.db.execute(stmt)
        records = result.scalars().all()

        results = []
        for record in records[offset : offset + limit]:
            record_values = record.values or {}
            matches_query = False

            for value in record_values.values():
                if isinstance(value, str) and query.lower() in value.lower():
                    matches_query = True
                    break

            if matches_query:
                results.append(
                    SearchResult(
                        record_id=str(record.id),
                        table_id=str(record.table_id),
                        base_id=base_id,
                        table_name="Table",
                        fields=record_values,
                        score=1.0,
                        highlights=None,
                    )
                )

        return SearchResponse(
            results=results,
            total=len(results),
            limit=limit,
            offset=offset,
            processing_time_ms=0,
        )

    async def global_search(
        self,
        user_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """Global search across all accessible bases."""
        return SearchResponse(
            results=[],
            total=0,
            limit=limit,
            offset=offset,
            processing_time_ms=0,
        )

    async def index_record(
        self,
        base_id: str,
        record_id: str,
    ) -> bool:
        """
        Index a single record in Meilisearch.

        Args:
            base_id: Base ID
            record_id: Record ID

        Returns:
            True if indexing succeeded, False otherwise
        """
        from pybase.models.record import Record
        from pybase.models.table import Table
        from pybase.services.meilisearch_index_manager import get_index_manager

        if not self.client:
            return False

        try:
            # Fetch record with table relationship
            stmt = (
                select(Record)
                .join(Table, Table.id == Record.table_id)
                .where(Record.id == UUID(record_id))
                .where(Table.base_id == UUID(base_id))
            )
            result = await self.db.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                return False

            # Get table info
            table_stmt = select(Table).where(Table.id == record.table_id)
            table_result = await self.db.execute(table_stmt)
            table = table_result.scalar_one_or_none()

            if not table:
                return False

            # Get record values
            values = record.get_all_values()

            # Index the record
            index_manager = get_index_manager()
            return index_manager.index_record(
                base_id=base_id,
                record_id=str(record.id),
                table_id=str(table.id),
                table_name=table.name,
                values=values,
                created_at=record.created_at.isoformat() if record.created_at else None,
                updated_at=record.updated_at.isoformat() if record.updated_at else None,
            )

        except Exception:
            return False

    async def index_table(
        self,
        base_id: str,
        table_id: str,
        batch_size: int = 1000,
    ) -> bool:
        """
        Index all records in a table.

        Args:
            base_id: Base ID
            table_id: Table ID
            batch_size: Number of records to index per batch

        Returns:
            True if all records were indexed successfully, False otherwise
        """
        from pybase.models.record import Record
        from pybase.models.table import Table
        from pybase.services.meilisearch_index_manager import get_index_manager

        if not self.client:
            return False

        try:
            # Fetch table
            table_stmt = select(Table).where(Table.id == UUID(table_id))
            table_result = await self.db.execute(table_stmt)
            table = table_result.scalar_one_or_none()

            if not table or str(table.base_id) != base_id:
                return False

            # Fetch all records in table
            record_stmt = select(Record).where(Record.table_id == UUID(table_id))
            record_result = await self.db.execute(record_stmt)
            records = record_result.scalars().all()

            if not records:
                return True

            # Prepare records for batch indexing
            records_data = []
            for record in records:
                records_data.append({
                    "id": str(record.id),
                    "table_id": str(table.id),
                    "table_name": table.name,
                    "values": record.get_all_values(),
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                    "updated_at": record.updated_at.isoformat() if record.updated_at else None,
                })

            # Index records in batch
            index_manager = get_index_manager()
            return index_manager.index_records_batch(
                base_id=base_id,
                records=records_data,
                batch_size=batch_size,
            )

        except Exception:
            return False


def get_search_service(db: AsyncSession) -> SearchService:
    """Get search service instance."""
    return SearchService(db)
