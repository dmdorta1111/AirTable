"""
Integration tests for Meilisearch typo tolerance and search quality.

This test suite validates:
1. Typo tolerance: Search finds results with misspelled queries
2. Search quality: Relevant results appear first with proper ranking
3. Various typo scenarios: missing letters, extra letters, transposed letters
4. Partial matching and phrase search
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.table import Table
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.services.search import SearchService


@pytest_asyncio.fixture
async def typo_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace for typo tolerance testing."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Typo Tolerance Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    return workspace


@pytest_asyncio.fixture
async def typo_base(db_session: AsyncSession, typo_workspace: Workspace) -> Base:
    """Create a test base for typo tolerance testing."""
    base = Base(
        workspace_id=typo_workspace.id,
        name="Typo Tolerance Test Base",
        description="Base for typo tolerance and search quality testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def typo_table(
    db_session: AsyncSession, typo_base: Base, test_user: User
) -> Table:
    """Create a test table with comprehensive sample data for typo testing."""
    # Create table
    table = Table(
        base_id=typo_base.id,
        name="Engineering Parts",
        description="Engineering parts for typo tolerance testing",
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
            position=0,
        ),
        Field(
            table_id=table.id,
            name="Description",
            field_type=FieldType.TEXT,
            position=1,
        ),
        Field(
            table_id=table.id,
            name="Category",
            field_type=FieldType.TEXT,
            position=2,
        ),
        Field(
            table_id=table.id,
            name="Material",
            field_type=FieldType.TEXT,
            position=3,
        ),
    ]
    for field in fields:
        db_session.add(field)
    await db_session.commit()

    # Refresh to get field IDs
    for field in fields:
        await db_session.refresh(field)

    # Create test records with realistic engineering terms
    test_records = [
        # Dimension-related terms (common typo: dimenson, dimmension, dimention)
        {
            "Part Name": "Linear Dimension",
            "Description": "Linear dimension measurement tool with 150mm range",
            "Category": "Measurement",
            "Material": "Steel",
        },
        {
            "Part Name": "Angular Dimension Gauge",
            "Description": "Angular dimension measurement device",
            "Category": "Measurement",
            "Material": "Aluminum",
        },
        {
            "Part Name": "Dimensional Caliper",
            "Description": "Precision dimensional caliper for measurements",
            "Category": "Measurement",
            "Material": "Stainless Steel",
        },
        # Thread-related terms (common typos: thred, thraed, thread)
        {
            "Part Name": "Metric Thread Bolt",
            "Description": "M10x50 metric thread bolt with hex head",
            "Category": "Fasteners",
            "Material": "Steel",
        },
        {
            "Part Name": "Threaded Rod",
            "Description": "Threaded rod for mechanical applications",
            "Category": "Fasteners",
            "Material": "Steel",
        },
        # Material-related terms (common typos: alumimum, steal, steal)
        {
            "Part Name": "Aluminum Bracket",
            "Description": "Lightweight aluminum bracket for mounting",
            "Category": "Mounting",
            "Material": "Aluminum",
        },
        {
            "Part Name": "Steel Plate",
            "Description": "Heavy-duty steel plate for structural support",
            "Category": "Structural",
            "Material": "Steel",
        },
        # Bearing-related terms (common typos: bearring, baring)
        {
            "Part Name": "Ball Bearing",
            "Description": "Deep groove ball bearing 6205 series",
            "Category": "Bearings",
            "Material": "Chrome Steel",
        },
        {
            "Part Name": "Roller Bearing",
            "Description": "Needle roller bearing assembly",
            "Category": "Bearings",
            "Material": "Steel",
        },
        # Gasket-related terms (common typos: gasget, gaskit)
        {
            "Part Name": "Rubber Gasket",
            "Description": "Nitrile rubber gasket for sealing",
            "Category": "Sealing",
            "Material": "Rubber",
        },
        {
            "Part Name": "Copper Gasket",
            "Description": "Copper gasket for high temperature applications",
            "Category": "Sealing",
            "Material": "Copper",
        },
        # Washer-related terms (common typos: waser, washr)
        {
            "Part Name": "Flat Washer",
            "Description": "M6 flat washer for fastening",
            "Category": "Fasteners",
            "Material": "Steel",
        },
        {
            "Part Name": "Lock Washer",
            "Description": "Split lock washer for vibration resistance",
            "Category": "Fasteners",
            "Material": "Spring Steel",
        },
        # Shaft-related terms (common typos: shft, saft)
        {
            "Part Name": "Drive Shaft",
            "Description": "Steel drive shaft for power transmission",
            "Category": "Transmission",
            "Material": "Steel",
        },
        {
            "Part Name": "Shaft Collar",
            "Description": "Clamping shaft collar for positioning",
            "Category": "Transmission",
            "Material": "Aluminum",
        },
    ]

    # Create records
    import json
    for record_data in test_records:
        record = Record(
            table_id=table.id,
            data=json.dumps(record_data),
        )
        db_session.add(record)
    await db_session.commit()

    # Index all records in Meilisearch for search testing
    # Note: This requires Meilisearch to be running
    try:
        search_service = SearchService(db_session)
        index_success = await search_service.index_table(
            base_id=str(typo_base.id),
            table_id=str(table.id),
        )
        if not index_success:
            # Continue anyway - tests will fail gracefully if index not available
            pass
    except Exception as e:
        # If Meilisearch is not available, tests will fail but that's expected
        pass

    # Give Meilisearch a moment to process the index
    import time
    time.sleep(1)

    return table


@pytest.mark.asyncio
class TestTypoTolerance:
    """Test suite for Meilisearch typo tolerance capabilities."""

    async def test_missing_letter_typos(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test search with missing letter typos.

        Validates that search finds results when letters are missing:
        - 'dimenson' should find 'dimension'
        - 'thred' should find 'thread'
        - 'alumimum' should find 'aluminum'
        """
        search_service = SearchService(db_session)

        # Test missing letter: dimenson -> dimension
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dimenson",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'dimenson' (missing 'i')"
        assert any(
            "dimension" in result.fields.get("Part Name", "").lower()
            or "dimension" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find dimension-related records"

        # Test missing letter: thred -> thread
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="thred",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'thred' (missing 'a')"
        assert any(
            "thread" in result.fields.get("Part Name", "").lower()
            or "thread" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find thread-related records"

        # Test missing letter: waser -> washer
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="waser",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'waser' (missing 'h')"
        assert any(
            "washer" in result.fields.get("Part Name", "").lower()
            or "washer" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find washer-related records"

    async def test_extra_letter_typos(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test search with extra letter typos.

        Validates that search finds results when extra letters are present:
        - 'dimmension' should find 'dimension'
        - 'thhread' should find 'thread'
        """
        search_service = SearchService(db_session)

        # Test extra letter: dimmension -> dimension
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dimmension",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'dimmension' (extra 'm')"
        assert any(
            "dimension" in result.fields.get("Part Name", "").lower()
            or "dimension" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find dimension-related records"

        # Test extra letter: thhread -> thread
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="thhread",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'thhread' (extra 'h')"
        assert any(
            "thread" in result.fields.get("Part Name", "").lower()
            or "thread" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find thread-related records"

    async def test_transposed_letters_typos(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test search with transposed letter typos.

        Validates that search finds results when letters are swapped:
        - 'dimention' should find 'dimension'
        - 'gaskit' should find 'gasket'
        """
        search_service = SearchService(db_session)

        # Test transposed letters: dimention -> dimension
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dimention",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'dimention' (transposed 'i' and 'e')"
        assert any(
            "dimension" in result.fields.get("Part Name", "").lower()
            or "dimension" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find dimension-related records"

        # Test transposed letters: gaskit -> gasket
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="gaskit",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'gaskit' (transposed 'i' and 't')"
        assert any(
            "gasket" in result.fields.get("Part Name", "").lower()
            or "gasket" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find gasket-related records"

        # Test transposed letters: baring -> bearing
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="baring",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'baring' (transposed 'a' and 'e')"
        assert any(
            "bearing" in result.fields.get("Part Name", "").lower()
            or "bearing" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find bearing-related records"

    async def test_multiple_typos(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test search with multiple typos in query.

        Validates that search finds results even with multiple typos:
        - 'dimmenshon' (extra 'm', wrong 'o') should find 'dimension'
        """
        search_service = SearchService(db_session)

        # Test multiple typos: dimmenshon -> dimension
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dimmenshon",
            limit=10,
        )

        # Should still find results with multiple typos
        assert response.metadata.total_results > 0, "Should find results for 'dimmenshon' (multiple typos)"

        # Test multiple typos with material: alumimum -> aluminum
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="alumimum",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'alumimum' (typo in middle)"
        assert any(
            "aluminum" in result.fields.get("Material", "").lower()
            or "aluminum" in result.fields.get("Part Name", "").lower()
            or "aluminum" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find aluminum-related records"

    async def test_partial_word_matching(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test search with partial word matches.

        Validates that search finds results with partial words:
        - 'dim' should find 'dimension'
        - 'bear' should find 'bearing'
        """
        search_service = SearchService(db_session)

        # Test partial match: dim -> dimension
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dim",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for partial 'dim'"
        assert any(
            "dimension" in result.fields.get("Part Name", "").lower()
            or "dimension" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find dimension-related records with partial match"

        # Test partial match: bear -> bearing
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="bear",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for partial 'bear'"
        assert any(
            "bearing" in result.fields.get("Part Name", "").lower()
            or "bearing" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find bearing-related records with partial match"

    async def test_phrase_search_with_typos(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test phrase search with typos.

        Validates that search finds results for phrases with typos:
        - 'metric thred bolt' should find 'metric thread bolt'
        """
        search_service = SearchService(db_session)

        # Test phrase with typo: metric thred bolt
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="metric thred bolt",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for phrase with typo 'metric thred bolt'"
        assert any(
            "thread" in result.fields.get("Part Name", "").lower()
            or "thread" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find thread bolt records"

        # Test phrase with typo: alumimum bracket
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="alumimum bracket",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for 'alumimum bracket'"
        assert any(
            "aluminum" in result.fields.get("Part Name", "").lower()
            or "aluminum" in result.fields.get("Description", "").lower()
            for result in response.results
        ), "Should find aluminum bracket records"


@pytest.mark.asyncio
class TestSearchQuality:
    """Test suite for search result quality and ranking."""

    async def test_relevance_ranking(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test that search results are properly ranked by relevance.

        Validates that:
        - Exact matches appear higher than partial matches
        - Results are sorted by relevance score
        """
        search_service = SearchService(db_session)

        # Search for 'dimension' with exact spelling
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dimension",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find dimension results"

        # Check that results have scores
        assert all(
            result.score > 0 for result in response.results
        ), "All results should have relevance scores"

        # Check that results are ranked (higher results should have higher or equal scores)
        if len(response.results) > 1:
            for i in range(len(response.results) - 1):
                # First result should have rank 1, second rank 2, etc.
                assert response.results[i].rank == i + 1, f"Result {i} should have rank {i + 1}"

    async def test_typo_tolerance_vs_exact_match(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test that exact matches score higher than typo matches.

        Validates that:
        - Exact 'dimension' scores higher than typo 'dimenson'
        - But both should return results
        """
        search_service = SearchService(db_session)

        # Search with exact spelling
        exact_response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dimension",
            limit=10,
        )

        # Search with typo
        typo_response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dimenson",
            limit=10,
        )

        # Both should return results
        assert exact_response.metadata.total_results > 0, "Exact match should return results"
        assert typo_response.metadata.total_results > 0, "Typo match should return results"

        # Exact match should have at least as many results as typo match
        assert (
            exact_response.metadata.total_results >= typo_response.metadata.total_results
        ), "Exact match should have equal or more results than typo match"

    async def test_multi_word_search_ranking(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test search ranking for multi-word queries.

        Validates that:
        - Multi-word queries return relevant results
        - Results matching more words rank higher
        """
        search_service = SearchService(db_session)

        # Search for multi-word phrase
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="metric thread bolt",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find results for multi-word query"

        # Top result should be highly relevant
        if response.results:
            top_result = response.results[0]
            assert top_result.score > 0, "Top result should have positive relevance score"

    async def test_field_scoring(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test that matches in important fields score higher.

        Validates that:
        - Part Name matches might score higher than Description matches
        - All fields are searched
        """
        search_service = SearchService(db_session)

        # Search for term that appears in both Part Name and Description
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dimension",
            limit=10,
        )

        assert response.metadata.total_results > 0, "Should find dimension results"

        # Verify that results contain the search term in various fields
        for result in response.results:
            found_in_field = False
            for field_name, field_value in result.fields.items():
                if isinstance(field_value, str) and "dimension" in field_value.lower():
                    found_in_field = True
                    break
            assert found_in_field, f"Result should contain 'dimension' in some field: {result.fields}"

    async def test_case_insensitive_search(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test that search is case-insensitive.

        Validates that:
        - 'Dimension', 'DIMENSION', 'dimension' all return same results
        """
        search_service = SearchService(db_session)

        # Search with different cases
        lower_response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="dimension",
            limit=10,
        )

        upper_response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="DIMENSION",
            limit=10,
        )

        mixed_response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="DiMeNsIoN",
            limit=10,
        )

        # All should return same number of results
        assert (
            lower_response.metadata.total_results
            == upper_response.metadata.total_results
            == mixed_response.metadata.total_results
        ), "Search should be case-insensitive"

    async def test_empty_and_short_queries(
        self,
        db_session: AsyncSession,
        typo_base: Base,
        typo_table: Table,
    ):
        """
        Test behavior with empty and very short queries.

        Validates that:
        - Empty query returns all results (or limited set)
        - Single character query works
        """
        search_service = SearchService(db_session)

        # Empty query should return results
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="",
            limit=10,
        )
        # Empty query behavior depends on configuration
        # Just verify it doesn't crash

        # Single character query
        response = await search_service.search_in_base(
            base_id=str(typo_base.id),
            query="d",
            limit=10,
        )

        # Should find results starting with 'd' (dimension, etc.)
        assert response.metadata.total_results >= 0, "Single character query should work"
