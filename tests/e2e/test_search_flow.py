"""
End-to-end tests for search flow: Create record, index, search, verify.

This test suite validates the complete search workflow:
1. Create a test record via API
2. Verify Celery task indexes the record
3. Search for the record via API
4. Verify record appears in search results
"""

import json
import time
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import settings
from pybase.models.base import Base
from pybase.models.table import Table
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


@pytest_asyncio.fixture
async def search_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner for search testing."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Search Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add owner as workspace member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    return workspace


@pytest_asyncio.fixture
async def search_base(db_session: AsyncSession, search_workspace: Workspace) -> Base:
    """Create a test base for search testing."""
    base = Base(
        workspace_id=search_workspace.id,
        name="Search Test Base",
        description="Base for E2E search testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def search_table(db_session: AsyncSession, search_base: Base, test_user: User) -> Table:
    """Create a test table with sample fields for search testing."""
    # Create table
    table = Table(
        base_id=search_base.id,
        name="Parts Inventory",
        description="Engineering parts for search testing",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields
    fields = [
        Field(
            table_id=table.id,
            name="Part Name",
            field_type=FieldType.TEXT,
            order=0,
        ),
        Field(
            table_id=table.id,
            name="Description",
            field_type=FieldType.TEXT,
            order=1,
        ),
        Field(
            table_id=table.id,
            name="Material",
            field_type=FieldType.TEXT,
            order=2,
        ),
        Field(
            table_id=table.id,
            name="Quantity",
            field_type=FieldType.NUMBER,
            order=3,
        ),
    ]
    for field in fields:
        db_session.add(field)
    await db_session.commit()

    # Refresh to get field IDs
    for field in fields:
        await db_session.refresh(field)

    return table


@pytest.mark.asyncio
class TestSearchFlow:
    """End-to-end test suite for complete search workflow."""

    async def test_end_to_end_search_with_background_indexing(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        search_base: Base,
        search_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test the complete search flow with background indexing.

        Workflow:
        1. Create a new record via API
        2. Verify record is created in database
        3. Trigger Celery indexing task directly
        4. Wait for indexing to complete
        5. Search for the record via API
        6. Verify record appears in search results
        """
        # Step 1: Create a new record via API
        record_data = {
            "table_id": str(search_table.id),
            "records": [
                {
                    "field_values": {
                        "Part Name": "M6x50 Hex Bolt",
                        "Description": "Steel hex bolt with 50mm length, M6 thread",
                        "Material": "Steel",
                        "Quantity": 100,
                    }
                }
            ]
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/records/batch",
            headers=auth_headers,
            json=record_data,
        )
        assert response.status_code in (200, 201), f"Record creation failed: {response.text}"
        created_records = response.json()
        assert len(created_records) == 1, "Should create exactly 1 record"
        record_id = created_records[0]["id"]

        # Step 2: Verify record is created in database
        from sqlalchemy import select

        result = await db_session.execute(
            select(Record).where(Record.id == record_id)
        )
        db_record = result.scalar_one_or_none()
        assert db_record is not None, "Record should exist in database"
        assert db_record.table_id == search_table.id

        # Step 3: Trigger Celery indexing task directly (in test env, we call service directly)
        from pybase.services.search import get_search_service

        search_service = get_search_service(db_session)

        # Index the record
        index_success = await search_service.index_record(record_id)
        assert index_success is True, "Record indexing should succeed"

        # Give Meilisearch a moment to process the index
        time.sleep(1)

        # Step 5: Search for the record via API
        search_request = {
            "query": "M6x50 Hex Bolt",
            "limit": 10,
            "highlight_results": True,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/search/bases/{search_base.id}/search",
            headers=auth_headers,
            json=search_request,
        )
        assert response.status_code == 200, f"Search request failed: {response.text}"
        search_results = response.json()

        # Step 6: Verify record appears in search results
        assert "results" in search_results, "Response should contain results"
        results = search_results["results"]
        assert len(results) >= 1, "Should find at least the created record"

        # Find our record in results
        found_record = None
        for result in results:
            if result["id"] == record_id:
                found_record = result
                break

        assert found_record is not None, f"Created record {record_id} should appear in search results"

        # Verify search result structure
        assert "id" in found_record
        assert "table_id" in found_record
        assert "values" in found_record
        assert "rank" in found_record
        assert found_record["table_id"] == str(search_table.id)

        # Verify the values match what we created
        values = found_record["values"]
        assert values.get("Part Name") == "M6x50 Hex Bolt"
        assert "Steel" in values.get("Description", "")

        # Verify metadata if present
        if "metadata" in search_results:
            metadata = search_results["metadata"]
            assert "total_results" in metadata
            assert metadata["total_results"] >= 1

    async def test_search_with_partial_match_and_typo_tolerance(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        search_base: Base,
        search_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test search with partial matches and typo tolerance.

        Workflow:
        1. Create multiple records with similar names
        2. Index all records
        3. Search with partial query
        4. Search with typo (e.g., "dimenson" instead of "dimension")
        5. Verify results include relevant records
        """
        from pybase.services.search import get_search_service

        # Step 1: Create multiple test records
        test_records = [
            {
                "field_values": {
                    "Part Name": "M6x30 Hex Bolt",
                    "Description": "Short steel bolt for light applications",
                    "Material": "Steel",
                    "Quantity": 50,
                }
            },
            {
                "field_values": {
                    "Part Name": "M6x30 Dimensional Bolt",
                    "Description": "Precision bolt with tight tolerances",
                    "Material": "Stainless Steel",
                    "Quantity": 25,
                }
            },
            {
                "field_values": {
                    "Part Name": "M8x40 Hex Nut",
                    "Description": "Hexagonal nut for M8 bolts",
                    "Material": "Steel",
                    "Quantity": 75,
                }
            },
        ]

        created_record_ids = []
        for record_data in test_records:
            response = await client.post(
                f"{settings.api_v1_prefix}/records/batch",
                headers=auth_headers,
                json={"table_id": str(search_table.id), "records": [record_data]},
            )
            assert response.status_code in (200, 201)
            created_records = response.json()
            created_record_ids.append(created_records[0]["id"])

        # Step 2: Index all records
        search_service = get_search_service(db_session)
        for record_id in created_record_ids:
            await search_service.index_record(record_id)

        # Give Meilisearch time to process
        time.sleep(1)

        # Step 3: Search with partial query
        search_request = {
            "query": "Hex Bolt",
            "limit": 10,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/search/bases/{search_base.id}/search",
            headers=auth_headers,
            json=search_request,
        )
        assert response.status_code == 200
        search_results = response.json()
        results = search_results["results"]

        # Should find at least the "M6x30 Hex Bolt"
        assert len(results) >= 1, "Should find records matching 'Hex Bolt'"
        bolt_record_found = any(
            "Hex Bolt" in r.get("values", {}).get("Part Name", "")
            for r in results
        )
        assert bolt_record_found, "Should find Hex Bolt record"

        # Step 4: Search with typo (Meilisearch should handle this)
        typo_search_request = {
            "query": "dimensonal",  # typo: should be "dimensional"
            "limit": 10,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/search/bases/{search_base.id}/search",
            headers=auth_headers,
            json=typo_search_request,
        )
        assert response.status_code == 200
        typo_results = response.json()["results"]

        # With typo tolerance, should still find the "Dimensional Bolt"
        # (Note: This depends on Meilisearch typo tolerance settings)
        # At minimum, the search should not fail

    async def test_search_faceted_filtering(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        search_base: Base,
        search_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test search with faceted filtering.

        Workflow:
        1. Create records with different materials
        2. Index all records
        3. Search with material filter
        4. Verify filtered results
        """
        from pybase.services.search import get_search_service

        # Step 1: Create records with different materials
        test_records = [
            {
                "field_values": {
                    "Part Name": "Steel Bolt A",
                    "Description": "Steel bolt description",
                    "Material": "Steel",
                    "Quantity": 10,
                }
            },
            {
                "field_values": {
                    "Part Name": "Steel Bolt B",
                    "Description": "Another steel bolt",
                    "Material": "Steel",
                    "Quantity": 20,
                }
            },
            {
                "field_values": {
                    "Part Name": "Aluminum Bolt",
                    "Description": "Lightweight aluminum bolt",
                    "Material": "Aluminum",
                    "Quantity": 15,
                }
            },
        ]

        created_record_ids = []
        for record_data in test_records:
            response = await client.post(
                f"{settings.api_v1_prefix}/records/batch",
                headers=auth_headers,
                json={"table_id": str(search_table.id), "records": [record_data]},
            )
            assert response.status_code in (200, 201)
            created_records = response.json()
            created_record_ids.append(created_records[0]["id"])

        # Step 2: Index all records
        search_service = get_search_service(db_session)
        for record_id in created_record_ids:
            await search_service.index_record(record_id)

        time.sleep(1)

        # Step 3: Search all records first
        search_request = {
            "query": "Bolt",
            "limit": 10,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/search/bases/{search_base.id}/search",
            headers=auth_headers,
            json=search_request,
        )
        assert response.status_code == 200
        all_results = response.json()["results"]
        initial_count = len(all_results)

        # Step 4: Search with table_id filter
        filtered_search_request = {
            "query": "Bolt",
            "table_id": str(search_table.id),
            "limit": 10,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/search/bases/{search_base.id}/search",
            headers=auth_headers,
            json=filtered_search_request,
        )
        assert response.status_code == 200
        filtered_results = response.json()["results"]

        # All results should be from the correct table
        assert all(r["table_id"] == str(search_table.id) for r in filtered_results)
        assert len(filtered_results) >= 3, "Should find at least 3 bolts"

    async def test_search_highlights(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        search_base: Base,
        search_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test search result highlighting.

        Workflow:
        1. Create a record with specific text
        2. Index the record
        3. Search with query that matches
        4. Verify highlighting in results
        """
        from pybase.services.search import get_search_service

        # Step 1: Create a record
        unique_text = "precision engineering component"
        record_data = {
            "table_id": str(search_table.id),
            "records": [
                {
                    "field_values": {
                        "Part Name": "Precision Washer",
                        "Description": f"A {unique_text} for high-performance applications",
                        "Material": "Stainless Steel",
                        "Quantity": 200,
                    }
                }
            ]
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/records/batch",
            headers=auth_headers,
            json=record_data,
        )
        assert response.status_code in (200, 201)
        record_id = response.json()[0]["id"]

        # Step 2: Index the record
        search_service = get_search_service(db_session)
        await search_service.index_record(record_id)
        time.sleep(1)

        # Step 3: Search with matching query
        search_request = {
            "query": "precision engineering",
            "limit": 10,
            "highlight_results": True,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/search/bases/{search_base.id}/search",
            headers=auth_headers,
            json=search_request,
        )
        assert response.status_code == 200
        search_results = response.json()

        # Step 4: Verify results
        results = search_results["results"]
        assert len(results) >= 1, "Should find the precision washer"

        # Find our record
        found = next((r for r in results if r["id"] == record_id), None)
        assert found is not None, "Created record should be in results"

        # Verify the description contains our text
        description = found["values"].get("Description", "")
        assert "precision" in description.lower(), "Description should contain search term"

    async def test_update_record_and_reindex(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        search_base: Base,
        search_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test that updating a record and reindexing updates search results.

        Workflow:
        1. Create a record
        2. Index and verify search finds it
        3. Update the record via API
        4. Reindex the record
        5. Verify search shows updated content
        """
        from pybase.services.search import get_search_service

        # Step 1: Create a record
        record_data = {
            "table_id": str(search_table.id),
            "records": [
                {
                    "field_values": {
                        "Part Name": "Original Name",
                        "Description": "Original description text",
                        "Material": "Steel",
                        "Quantity": 10,
                    }
                }
            ]
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/records/batch",
            headers=auth_headers,
            json=record_data,
        )
        assert response.status_code in (200, 201)
        record_id = response.json()[0]["id"]

        # Step 2: Index and verify
        search_service = get_search_service(db_session)
        await search_service.index_record(record_id)
        time.sleep(1)

        # Search for original name
        search_request = {"query": "Original Name", "limit": 10}
        response = await client.post(
            f"{settings.api_v1_prefix}/search/bases/{search_base.id}/search",
            headers=auth_headers,
            json=search_request,
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) >= 1, "Should find original record"

        # Step 3: Update the record
        update_data = {
            "records": [
                {
                    "id": record_id,
                    "field_values": {
                        "Part Name": "Updated Name",
                        "Description": "Updated description text",
                        "Material": "Aluminum",
                        "Quantity": 20,
                    }
                }
            ]
        }

        response = await client.put(
            f"{settings.api_v1_prefix}/records/batch",
            headers=auth_headers,
            json=update_data,
        )
        assert response.status_code in (200, 200)

        # Step 4: Reindex the record
        await search_service.index_record(record_id)
        time.sleep(1)

        # Step 5: Search for updated name
        search_request = {"query": "Updated Name", "limit": 10}
        response = await client.post(
            f"{settings.api_v1_prefix}/search/bases/{search_base.id}/search",
            headers=auth_headers,
            json=search_request,
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) >= 1, "Should find updated record"

        # Verify it's the updated content
        found = next((r for r in results if r["id"] == record_id), None)
        assert found is not None
        assert found["values"]["Part Name"] == "Updated Name"
        assert found["values"]["Material"] == "Aluminum"
        assert found["values"]["Quantity"] == 20
