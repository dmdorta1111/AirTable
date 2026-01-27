"""
Performance tests for Meilisearch search functionality.

Tests verify that search meets acceptance criteria:
- Search returns results in under 100ms for databases with 100K+ records
- Typo-tolerant search performs adequately
- Faceted search performance is acceptable
"""

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
async def perf_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace for performance testing."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Performance Test Workspace",
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
async def perf_base(db_session: AsyncSession, perf_workspace: Workspace) -> Base:
    """Create a test base for performance testing."""
    base = Base(
        workspace_id=perf_workspace.id,
        name="Performance Test Base",
        description="Base for search performance testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def perf_table(db_session: AsyncSession, perf_base: Base) -> Table:
    """Create a test table with sample fields for performance testing."""
    # Create table
    table = Table(
        base_id=perf_base.id,
        name="Large Parts Inventory",
        description="Large table for performance testing",
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
            name="Category",
            field_type=FieldType.TEXT,
            order=3,
        ),
        Field(
            table_id=table.id,
            name="Quantity",
            field_type=FieldType.NUMBER,
            order=4,
        ),
    ]
    for field in fields:
        db_session.add(field)
    await db_session.commit()

    return table


@pytest.mark.asyncio
class TestSearchPerformance:
    """Performance test suite for search functionality."""

    async def test_search_performance_with_100k_records(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        perf_base: Base,
        perf_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test search performance with 100K records.

        Acceptance criteria:
        - Search returns results in under 100ms for databases with 100K+ records

        This test:
        1. Creates 100K test records in the database
        2. Indexes them in Meilisearch
        3. Performs multiple search queries
        4. Measures and verifies search response times
        """
        from pybase.services.search import get_search_service

        # Constants
        NUM_RECORDS = 100000
        BATCH_SIZE = 1000
        TARGET_LATENCY_MS = 100

        # Materials and categories for variety
        materials = ["Steel", "Aluminum", "Stainless Steel", "Brass", "Titanium", "Plastic", "Rubber", "Ceramic"]
        categories = ["Fasteners", "Bearings", "Electrical", "Hydraulic", "Pneumatic", "Structural", "Consumables"]

        print(f"\n=== Search Performance Test with {NUM_RECORDS:,} records ===")
        print(f"Target latency: <{TARGET_LATENCY_MS}ms")

        # Step 1: Create 100K records in batches
        print(f"\n1. Creating {NUM_RECORDS:,} records...")
        start_time = time.time()

        records_created = 0
        for batch_num in range(NUM_RECORDS // BATCH_SIZE):
            batch_records = []
            for i in range(BATCH_SIZE):
                record_num = batch_num * BATCH_SIZE + i
                record = Record(
                    table_id=perf_table.id,
                    created_by_id=test_user.id,
                    data=f'''{{
                        "Part Name": "Part-{record_num:06d}",
                        "Description": "Engineering component part {record_num} for testing search performance with large datasets",
                        "Material": "{materials[record_num % len(materials)]}",
                        "Category": "{categories[record_num % len(categories)]}",
                        "Quantity": {record_num % 1000}
                    }}'''.replace('\n', ' ')
                )
                batch_records.append(record)

            db_session.add_all(batch_records)
            await db_session.commit()
            records_created += len(batch_records)

            if (batch_num + 1) % 10 == 0:
                elapsed = time.time() - start_time
                rate = records_created / elapsed
                print(f"   Created {records_created:,}/{NUM_RECORDS:,} records ({rate:.0f} records/sec)")

        creation_time = time.time() - start_time
        print(f"   ✓ Created {records_created:,} records in {creation_time:.1f}s")

        # Step 2: Index all records in Meilisearch
        print(f"\n2. Indexing {records_created:,} records in Meilisearch...")
        index_start = time.time()

        search_service = get_search_service(db_session)
        index_success = await search_service.index_table(
            base_id=str(perf_base.id),
            table_id=str(perf_table.id),
            batch_size=BATCH_SIZE,
        )

        index_time = time.time() - index_start

        if index_success:
            print(f"   ✓ Indexed {records_created:,} records in {index_time:.1f}s")
            print(f"   Indexing rate: {records_created / index_time:.0f} records/sec")
        else:
            print(f"   ⚠ Indexing failed or Meilisearch not available")
            pytest.skip("Meilisearch indexing failed - skipping performance test")

        # Give Meilisearch time to process the index
        print(f"\n3. Waiting for index to be processed...")
        time.sleep(2)

        # Step 4: Perform search queries and measure performance
        print(f"\n4. Running search performance tests...")

        test_queries = [
            ("Part-000001", "Exact match search"),
            ("Part-005", "Partial match search"),
            ("engineering component", "Full-text search"),
            ("Steel", "Single term search"),
            ("Fasteners", "Category search"),
            ("performance testing", "Multi-word search"),
        ]

        results = []

        for query, description in test_queries:
            # Perform multiple searches to get average
            latencies = []
            results_found = []

            for run in range(5):  # 5 runs per query type
                search_request = {
                    "query": query,
                    "limit": 20,
                }

                search_start = time.time()
                response = await client.post(
                    f"{settings.api_v1_prefix}/search/bases/{perf_base.id}/search",
                    headers=auth_headers,
                    json=search_request,
                )
                search_end = time.time()

                latency_ms = (search_end - search_start) * 1000
                latencies.append(latency_ms)

                if response.status_code == 200:
                    search_results = response.json()
                    results_found.append(len(search_results.get("results", [])))
                else:
                    results_found.append(0)

            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            avg_results = sum(results_found) / len(results_found)

            passed = avg_latency < TARGET_LATENCY_MS
            status = "✓" if passed else "✗"

            results.append({
                "query": query,
                "description": description,
                "avg_latency_ms": avg_latency,
                "min_latency_ms": min_latency,
                "max_latency_ms": max_latency,
                "avg_results": avg_results,
                "passed": passed,
            })

            print(f"   {status} {description:30s} | Avg: {avg_latency:6.2f}ms | Min: {min_latency:6.2f}ms | Max: {max_latency:6.2f}ms | Results: {avg_results:6.1f}")

        # Step 5: Verify overall performance
        print(f"\n5. Performance Summary:")
        print(f"   Total records: {records_created:,}")
        print(f"   Target latency: <{TARGET_LATENCY_MS}ms")

        all_passed = all(r["passed"] for r in results)
        passed_count = sum(1 for r in results if r["passed"])
        total_count = len(results)

        avg_overall_latency = sum(r["avg_latency_ms"] for r in results) / len(results)

        print(f"   Queries passed: {passed_count}/{total_count}")
        print(f"   Overall average latency: {avg_overall_latency:.2f}ms")

        if all_passed:
            print(f"\n   ✓✓✓ ALL TESTS PASSED ✓✓✓")
            print(f"   Search performance meets the <{TARGET_LATENCY_MS}ms requirement!")
        else:
            print(f"\n   ✗✗✗ SOME TESTS FAILED ✗✗✗")
            print(f"   {total_count - passed_count} queries exceeded {TARGET_LATENCY_MS}ms threshold")

        # Assert that at least 80% of queries meet the target
        # This allows for some variance while ensuring overall good performance
        assert passed_count >= total_count * 0.8, (
            f"At least 80% of search queries should be under {TARGET_LATENCY_MS}ms, "
            f"but only {passed_count}/{total_count} passed"
        )

        # Assert that overall average is under target
        assert avg_overall_latency < TARGET_LATENCY_MS, (
            f"Overall average search latency ({avg_overall_latency:.2f}ms) "
            f"exceeds target of {TARGET_LATENCY_MS}ms"
        )

    async def test_search_performance_with_facets(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        perf_base: Base,
        perf_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test search performance with faceted filtering.

        Verifies that faceted search still performs well under load.
        """
        from pybase.services.search import get_search_service

        # Create a smaller dataset for faceted search test
        NUM_RECORDS = 10000
        TARGET_LATENCY_MS = 100

        print(f"\n=== Faceted Search Performance Test with {NUM_RECORDS:,} records ===")

        # Create records
        materials = ["Steel", "Aluminum", "Stainless Steel", "Brass", "Titanium"]
        categories = ["Fasteners", "Bearings", "Electrical", "Hydraulic", "Pneumatic"]

        print(f"\n1. Creating {NUM_RECORDS:,} records for faceted search test...")
        batch_records = []
        for i in range(NUM_RECORDS):
            record = Record(
                table_id=perf_table.id,
                created_by_id=test_user.id,
                data=f'''{{"Part Name": "Part-{i:06d}", "Description": "Test part {i}", "Material": "{materials[i % len(materials)]}", "Category": "{categories[i % len(categories)]}", "Quantity": {i % 100}}}'''.replace('\n', ' ')
            )
            batch_records.append(record)

            if len(batch_records) >= 1000:
                db_session.add_all(batch_records)
                await db_session.commit()
                batch_records = []

        if batch_records:
            db_session.add_all(batch_records)
            await db_session.commit()

        print(f"   ✓ Created {NUM_RECORDS:,} records")

        # Index records
        print(f"\n2. Indexing records...")
        search_service = get_search_service(db_session)
        index_success = await search_service.index_table(
            base_id=str(perf_base.id),
            table_id=str(perf_table.id),
            batch_size=1000,
        )

        if not index_success:
            pytest.skip("Meilisearch indexing failed - skipping faceted search test")

        print(f"   ✓ Indexed records")
        time.sleep(1)

        # Test faceted search performance
        print(f"\n3. Testing faceted search performance...")

        search_request = {
            "query": "Part",
            "limit": 20,
            "facets": [
                {"field_id": "Material", "facet_type": "string", "max_values": 10},
                {"field_id": "Category", "facet_type": "string", "max_values": 10},
            ],
        }

        latencies = []
        for run in range(10):
            search_start = time.time()
            response = await client.post(
                f"{settings.api_v1_prefix}/search/bases/{perf_base.id}/search",
                headers=auth_headers,
                json=search_request,
            )
            search_end = time.time()

            latency_ms = (search_end - search_start) * 1000
            latencies.append(latency_ms)

        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        print(f"   Faceted search performance:")
        print(f"   Average: {avg_latency:.2f}ms")
        print(f"   Min: {min_latency:.2f}ms")
        print(f"   Max: {max_latency:.2f}ms")

        status = "✓" if avg_latency < TARGET_LATENCY_MS else "✗"
        print(f"   {status} Target: <{TARGET_LATENCY_MS}ms")

        assert avg_latency < TARGET_LATENCY_MS, (
            f"Faceted search latency ({avg_latency:.2f}ms) exceeds target of {TARGET_LATENCY_MS}ms"
        )

    async def test_typo_tolerance_performance(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        perf_base: Base,
        perf_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test search performance with typo-tolerant queries.

        Verifies that typo-tolerant search still performs well.
        """
        from pybase.services.search import get_search_service

        NUM_RECORDS = 10000
        TARGET_LATENCY_MS = 100

        print(f"\n=== Typo Tolerance Performance Test ===")

        # Create records with specific names for typo testing
        print(f"\n1. Creating {NUM_RECORDS:,} records...")
        batch_records = []
        for i in range(NUM_RECORDS):
            # Use "dimension" in some records to test typo tolerance
            part_name = f"Dimension-Part-{i:04d}" if i % 10 == 0 else f"Part-{i:06d}"
            record = Record(
                table_id=perf_table.id,
                created_by_id=test_user.id,
                data=f'''{{"Part Name": "{part_name}", "Description": "Test description", "Material": "Steel", "Category": "Test", "Quantity": {i % 100}}}'''.replace('\n', ' ')
            )
            batch_records.append(record)

            if len(batch_records) >= 1000:
                db_session.add_all(batch_records)
                await db_session.commit()
                batch_records = []

        if batch_records:
            db_session.add_all(batch_records)
            await db_session.commit()

        print(f"   ✓ Created {NUM_RECORDS:,} records")

        # Index records
        print(f"\n2. Indexing records...")
        search_service = get_search_service(db_session)
        index_success = await search_service.index_table(
            base_id=str(perf_base.id),
            table_id=str(perf_table.id),
            batch_size=1000,
        )

        if not index_success:
            pytest.skip("Meilisearch indexing failed - skipping typo tolerance test")

        print(f"   ✓ Indexed records")
        time.sleep(1)

        # Test typo-tolerant search
        print(f"\n3. Testing typo-tolerant search performance...")

        typo_queries = [
            ("dimenson", "Should match 'dimension'"),
            ("dimmension", "Should match 'dimension'"),
            ("dimention", "Should match 'dimension'"),
        ]

        for query, description in typo_queries:
            latencies = []
            for run in range(5):
                search_start = time.time()
                response = await client.post(
                    f"{settings.api_v1_prefix}/search/bases/{perf_base.id}/search",
                    headers=auth_headers,
                    json={"query": query, "limit": 20},
                )
                search_end = time.time()

                latency_ms = (search_end - search_start) * 1000
                latencies.append(latency_ms)

            avg_latency = sum(latencies) / len(latencies)
            status = "✓" if avg_latency < TARGET_LATENCY_MS else "✗"

            print(f"   {status} Query '{query}' | Avg: {avg_latency:.2f}ms | {description}")

            assert avg_latency < TARGET_LATENCY_MS, (
                f"Typo-tolerant search for '{query}' ({avg_latency:.2f}ms) exceeds target of {TARGET_LATENCY_MS}ms"
            )
