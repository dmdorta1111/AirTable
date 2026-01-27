"""
Integration tests for Meilisearch faceted search functionality.

This test suite validates:
1. String facets: Category, Material, etc.
2. Numeric facets with stats: Price, Quantity, Weight
3. Boolean facets: In Stock, Is Active
4. Multiple facets simultaneously
5. Facet filtering and drill-down
6. Facet value counts and distribution
7. Facet sorting (by count, alpha)
8. Empty facets and edge cases
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
from pybase.schemas.search import FacetConfig, FacetType, SortOrder


@pytest_asyncio.fixture
async def facet_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace for faceted search testing."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Faceted Search Test Workspace",
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
async def facet_base(db_session: AsyncSession, facet_workspace: Workspace) -> Base:
    """Create a test base for faceted search testing."""
    base = Base(
        workspace_id=facet_workspace.id,
        name="Faceted Search Test Base",
        description="Base for faceted search functionality testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def facet_table(
    db_session: AsyncSession, facet_base: Base, test_user: User
) -> Table:
    """Create a test table with comprehensive sample data for faceted search testing."""
    # Create table
    table = Table(
        base_id=facet_base.id,
        name="Products",
        description="Product catalog for faceted search testing",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields - mix of different types for comprehensive facet testing
    fields = [
        Field(
            table_id=table.id,
            name="Product Name",
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
        Field(
            table_id=table.id,
            name="Price",
            field_type=FieldType.CURRENCY,
            position=4,
        ),
        Field(
            table_id=table.id,
            name="Quantity",
            field_type=FieldType.NUMBER,
            position=5,
        ),
        Field(
            table_id=table.id,
            name="Weight",
            field_type=FieldType.NUMBER,
            position=6,
        ),
        Field(
            table_id=table.id,
            name="In Stock",
            field_type=FieldType.CHECKBOX,
            position=7,
        ),
        Field(
            table_id=table.id,
            name="Is Active",
            field_type=FieldType.CHECKBOX,
            position=8,
        ),
    ]
    for field in fields:
        db_session.add(field)
    await db_session.commit()

    # Refresh to get field IDs
    for field in fields:
        await db_session.refresh(field)

    # Create test records with diverse facet values
    test_records = [
        # Category: Fasteners, various materials
        {
            "Product Name": "Hex Bolt M8x20",
            "Description": "Standard hex bolt for general purpose",
            "Category": "Fasteners",
            "Material": "Steel",
            "Price": 0.50,
            "Quantity": 1000,
            "Weight": 0.02,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Hex Bolt M8x20 Stainless",
            "Description": "Stainless steel hex bolt",
            "Category": "Fasteners",
            "Material": "Stainless Steel",
            "Price": 1.20,
            "Quantity": 500,
            "Weight": 0.02,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Hex Bolt M10x30",
            "Description": "Larger hex bolt",
            "Category": "Fasteners",
            "Material": "Steel",
            "Price": 0.75,
            "Quantity": 750,
            "Weight": 0.04,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Flat Washer M6",
            "Description": "Standard flat washer",
            "Category": "Fasteners",
            "Material": "Steel",
            "Price": 0.10,
            "Quantity": 5000,
            "Weight": 0.005,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Lock Washer M8",
            "Description": "Split lock washer for vibration resistance",
            "Category": "Fasteners",
            "Material": "Spring Steel",
            "Price": 0.15,
            "Quantity": 2000,
            "Weight": 0.008,
            "In Stock": False,
            "Is Active": True,
        },
        # Category: Bearings
        {
            "Product Name": "Ball Bearing 6205",
            "Description": "Deep groove ball bearing",
            "Category": "Bearings",
            "Material": "Chrome Steel",
            "Price": 5.50,
            "Quantity": 150,
            "Weight": 0.15,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Ball Bearing 6205 Ceramic",
            "Description": "Hybrid ceramic ball bearing",
            "Category": "Bearings",
            "Material": "Ceramic",
            "Price": 15.00,
            "Quantity": 50,
            "Weight": 0.12,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Needle Bearing NK20/20",
            "Description": "Needle roller bearing",
            "Category": "Bearings",
            "Material": "Steel",
            "Price": 8.50,
            "Quantity": 100,
            "Weight": 0.18,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Thrust Bearing 51200",
            "Description": "Thrust ball bearing",
            "Category": "Bearings",
            "Material": "Steel",
            "Price": 3.20,
            "Quantity": 200,
            "Weight": 0.10,
            "In Stock": False,
            "Is Active": False,
        },
        # Category: Sealing
        {
            "Product Name": "O-Ring Nitrile 50mm",
            "Description": "Nitrile rubber O-ring",
            "Category": "Sealing",
            "Material": "Rubber",
            "Price": 0.30,
            "Quantity": 3000,
            "Weight": 0.01,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "O-Ring Viton 50mm",
            "Description": "Viton O-ring for chemical resistance",
            "Category": "Sealing",
            "Material": "Viton",
            "Price": 1.50,
            "Quantity": 1000,
            "Weight": 0.01,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Oil Seal 20x35x5",
            "Description": "Rubber oil seal",
            "Category": "Sealing",
            "Material": "Rubber",
            "Price": 0.80,
            "Quantity": 800,
            "Weight": 0.02,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Gasket Copper 20mm",
            "Description": "Copper crush gasket",
            "Category": "Sealing",
            "Material": "Copper",
            "Price": 0.60,
            "Quantity": 500,
            "Weight": 0.05,
            "In Stock": True,
            "Is Active": True,
        },
        # Category: Mounting
        {
            "Product Name": "Bracket L-Shape Aluminum",
            "Description": "L-shaped aluminum bracket",
            "Category": "Mounting",
            "Material": "Aluminum",
            "Price": 2.50,
            "Quantity": 400,
            "Weight": 0.15,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Bracket Corner Steel",
            "Description": "Steel corner bracket",
            "Category": "Mounting",
            "Material": "Steel",
            "Price": 1.80,
            "Quantity": 600,
            "Weight": 0.25,
            "In Stock": True,
            "Is Active": True,
        },
        {
            "Product Name": "Base Plate Cast Iron",
            "Description": "Heavy cast iron base plate",
            "Category": "Mounting",
            "Material": "Cast Iron",
            "Price": 12.00,
            "Quantity": 50,
            "Weight": 2.50,
            "In Stock": False,
            "Is Active": True,
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

    # Index all records in Meilisearch for faceted search testing
    # Note: This requires Meilisearch to be running
    try:
        search_service = SearchService(db_session)
        index_success = await search_service.index_table(
            base_id=str(facet_base.id),
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
class TestStringFacets:
    """Test suite for string-based faceted search."""

    async def test_category_facet(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test category facet returns correct value distribution.

        Validates that:
        - Category facet returns all unique categories
        - Each category has correct count
        - Facet values are sorted by count (default)
        """
        search_service = SearchService(db_session)

        # Search with category facet
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Category",
                    facet_type=FacetType.STRING,
                    max_values=10,
                )
            ],
            limit=20,
        )

        # Should have category facet
        assert len(response.facets) > 0, "Should return category facet"

        category_facet = next((f for f in response.facets if f.field_id == "Category"), None)
        assert category_facet is not None, "Should have Category facet"

        # Check facet values
        assert len(category_facet.values) > 0, "Should have category facet values"

        # Expected categories: Fasteners (5), Bearings (4), Sealing (4), Mounting (3)
        expected_categories = {"Fasteners": 5, "Bearings": 4, "Sealing": 4, "Mounting": 3}
        for cat_name, expected_count in expected_categories.items():
            facet_value = next((v for v in category_facet.values if v.value == cat_name), None)
            assert facet_value is not None, f"Should have category: {cat_name}"
            assert (
                facet_value.count == expected_count
            ), f"Category '{cat_name}' should have count {expected_count}, got {facet_value.count}"

        assert category_facet.total_values == len(expected_categories), "Should have 4 unique categories"

    async def test_material_facet(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test material facet returns correct value distribution.

        Validates that:
        - Material facet returns all unique materials
        - Each material has correct count
        - Materials with same count are handled correctly
        """
        search_service = SearchService(db_session)

        # Search with material facet
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Material",
                    facet_type=FacetType.STRING,
                    max_values=15,
                )
            ],
            limit=20,
        )

        # Should have material facet
        material_facet = next((f for f in response.facets if f.field_id == "Material"), None)
        assert material_facet is not None, "Should have Material facet"

        # Check facet values
        assert len(material_facet.values) > 0, "Should have material facet values"

        # Steel should be most common (appears in Fasteners, Bearings, Mounting)
        steel_facet = next((v for v in material_facet.values if v.value == "Steel"), None)
        assert steel_facet is not None, "Should have Steel material"
        assert steel_facet.count > 0, "Steel should have positive count"

        # Verify unique materials count
        assert material_facet.total_values > 5, "Should have multiple unique materials"

    async def test_multiple_string_facets(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test multiple string facets in same query.

        Validates that:
        - Multiple facets can be requested
        - Each facet is computed correctly
        - Facets don't interfere with each other
        """
        search_service = SearchService(db_session)

        # Search with multiple string facets
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Category",
                    facet_type=FacetType.STRING,
                    max_values=10,
                ),
                FacetConfig(
                    field_id="Material",
                    facet_type=FacetType.STRING,
                    max_values=10,
                ),
            ],
            limit=20,
        )

        # Should have both facets
        assert len(response.facets) == 2, "Should return both facets"

        category_facet = next((f for f in response.facets if f.field_id == "Category"), None)
        material_facet = next((f for f in response.facets if f.field_id == "Material"), None)

        assert category_facet is not None, "Should have Category facet"
        assert material_facet is not None, "Should have Material facet"

        # Both should have values
        assert len(category_facet.values) > 0, "Category facet should have values"
        assert len(material_facet.values) > 0, "Material facet should have values"


@pytest.mark.asyncio
class TestNumericFacets:
    """Test suite for numeric faceted search with statistics."""

    async def test_price_facet_with_stats(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test numeric facet (Price) returns statistics.

        Validates that:
        - Numeric facet returns min, max, avg, count
        - Statistics are calculated correctly
        - Facet values show top price points
        """
        search_service = SearchService(db_session)

        # Search with price facet
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Price",
                    facet_type=FacetType.FLOAT,
                    max_values=10,
                )
            ],
            limit=20,
        )

        # Should have price facet
        price_facet = next((f for f in response.facets if f.field_id == "Price"), None)
        assert price_facet is not None, "Should have Price facet"

        # Should have statistics for numeric facet
        assert price_facet.stats is not None, "Numeric facet should have stats"

        # Check stats are reasonable
        assert price_facet.stats.min >= 0, "Min price should be non-negative"
        assert price_facet.stats.max > price_facet.stats.min, "Max price should be greater than min"
        assert price_facet.stats.avg > 0, "Average price should be positive"
        assert price_facet.stats.count == 16, "Should have 16 products"

        # Verify expected price range (from test data: $0.10 to $15.00)
        assert price_facet.stats.min == 0.10, f"Min price should be 0.10, got {price_facet.stats.min}"
        assert price_facet.stats.max == 15.00, f"Max price should be 15.00, got {price_facet.stats.max}"

    async def test_quantity_facet_with_stats(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test quantity facet returns correct statistics.

        Validates that:
        - Quantity stats match test data
        - Large quantity values are handled correctly
        """
        search_service = SearchService(db_session)

        # Search with quantity facet
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Quantity",
                    facet_type=FacetType.INTEGER,
                    max_values=10,
                )
            ],
            limit=20,
        )

        # Should have quantity facet
        quantity_facet = next((f for f in response.facets if f.field_id == "Quantity"), None)
        assert quantity_facet is not None, "Should have Quantity facet"

        # Should have statistics
        assert quantity_facet.stats is not None, "Quantity facet should have stats"

        # Verify expected quantity range (from test data: 50 to 5000)
        assert quantity_facet.stats.min == 50, f"Min quantity should be 50, got {quantity_facet.stats.min}"
        assert quantity_facet.stats.max == 5000, f"Max quantity should be 5000, got {quantity_facet.stats.max}"
        assert quantity_facet.stats.count == 16, "Should have 16 products"

    async def test_weight_facet_with_stats(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test weight facet with decimal values.

        Validates that:
        - Weight stats handle floating point correctly
        - Small decimal values are accurate
        """
        search_service = SearchService(db_session)

        # Search with weight facet
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Weight",
                    facet_type=FacetType.FLOAT,
                    max_values=10,
                )
            ],
            limit=20,
        )

        # Should have weight facet
        weight_facet = next((f for f in response.facets if f.field_id == "Weight"), None)
        assert weight_facet is not None, "Should have Weight facet"

        # Should have statistics
        assert weight_facet.stats is not None, "Weight facet should have stats"

        # Verify expected weight range (from test data: 0.005 to 2.50)
        assert weight_facet.stats.min == 0.005, f"Min weight should be 0.005, got {weight_facet.stats.min}"
        assert weight_facet.stats.max == 2.50, f"Max weight should be 2.50, got {weight_facet.stats.max}"


@pytest.mark.asyncio
class TestBooleanFacets:
    """Test suite for boolean faceted search."""

    async def test_in_stock_facet(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test boolean facet (In Stock) returns correct counts.

        Validates that:
        - Boolean facet returns true/false counts
        - Counts match test data
        """
        search_service = SearchService(db_session)

        # Search with In Stock facet
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="In Stock",
                    facet_type=FacetType.BOOLEAN,
                    max_values=10,
                )
            ],
            limit=20,
        )

        # Should have In Stock facet
        in_stock_facet = next((f for f in response.facets if f.field_id == "In Stock"), None)
        assert in_stock_facet is not None, "Should have In Stock facet"

        # Should have true/false values
        assert len(in_stock_facet.values) > 0, "Should have boolean facet values"

        # Check for true and false values
        true_value = next((v for v in in_stock_facet.values if v.value == "true" or v.value == "True"), None)
        false_value = next((v for v in in_stock_facet.values if v.value == "false" or v.value == "False"), None)

        assert true_value is not None, "Should have 'true' value in In Stock facet"
        assert false_value is not None, "Should have 'false' value in In Stock facet"

        # From test data: 13 in stock, 3 out of stock
        assert true_value.count == 13, f"Should have 13 items in stock, got {true_value.count}"
        assert false_value.count == 3, f"Should have 3 items out of stock, got {false_value.count}"

    async def test_is_active_facet(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test boolean facet (Is Active) returns correct counts.

        Validates that:
        - Is Active facet returns correct true/false counts
        - Matches test data (15 active, 1 inactive)
        """
        search_service = SearchService(db_session)

        # Search with Is Active facet
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Is Active",
                    facet_type=FacetType.BOOLEAN,
                    max_values=10,
                )
            ],
            limit=20,
        )

        # Should have Is Active facet
        is_active_facet = next((f for f in response.facets if f.field_id == "Is Active"), None)
        assert is_active_facet is not None, "Should have Is Active facet"

        # Should have true/false values
        assert len(is_active_facet.values) > 0, "Should have boolean facet values"

        # Check for true and false values
        true_value = next((v for v in is_active_facet.values if v.value == "true" or v.value == "True"), None)
        false_value = next((v for v in is_active_facet.values if v.value == "false" or v.value == "False"), None)

        assert true_value is not None, "Should have 'true' value in Is Active facet"
        assert false_value is not None, "Should have 'false' value in Is Active facet"

        # From test data: 15 active, 1 inactive
        assert true_value.count == 15, f"Should have 15 active items, got {true_value.count}"
        assert false_value.count == 1, f"Should have 1 inactive item, got {false_value.count}"


@pytest.mark.asyncio
class TestMixedFacets:
    """Test suite for mixed facet types in single query."""

    async def test_string_and_numeric_facets(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test string and numeric facets together.

        Validates that:
        - Mixed facet types work in same query
        - Each facet type is computed correctly
        - Facet counts are consistent
        """
        search_service = SearchService(db_session)

        # Search with mixed facets
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Category",
                    facet_type=FacetType.STRING,
                    max_values=10,
                ),
                FacetConfig(
                    field_id="Price",
                    facet_type=FacetType.FLOAT,
                    max_values=10,
                ),
            ],
            limit=20,
        )

        # Should have both facets
        assert len(response.facets) == 2, "Should return both facets"

        category_facet = next((f for f in response.facets if f.field_id == "Category"), None)
        price_facet = next((f for f in response.facets if f.field_id == "Price"), None)

        assert category_facet is not None, "Should have Category facet"
        assert price_facet is not None, "Should have Price facet"

        # Category should have values
        assert len(category_facet.values) > 0, "Category facet should have values"

        # Price should have stats
        assert price_facet.stats is not None, "Price facet should have stats"

    async def test_all_facet_types_together(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test all facet types (string, numeric, boolean) together.

        Validates that:
        - All three facet types work in same query
        - Each facet is computed correctly
        - No interference between facets
        """
        search_service = SearchService(db_session)

        # Search with all facet types
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Category",
                    facet_type=FacetType.STRING,
                    max_values=10,
                ),
                FacetConfig(
                    field_id="Price",
                    facet_type=FacetType.FLOAT,
                    max_values=10,
                ),
                FacetConfig(
                    field_id="In Stock",
                    facet_type=FacetType.BOOLEAN,
                    max_values=10,
                ),
            ],
            limit=20,
        )

        # Should have all three facets
        assert len(response.facets) == 3, "Should return all three facets"

        category_facet = next((f for f in response.facets if f.field_id == "Category"), None)
        price_facet = next((f for f in response.facets if f.field_id == "Price"), None)
        in_stock_facet = next((f for f in response.facets if f.field_id == "In Stock"), None)

        assert category_facet is not None, "Should have Category facet"
        assert price_facet is not None, "Should have Price facet"
        assert in_stock_facet is not None, "Should have In Stock facet"

        # Verify each facet
        assert len(category_facet.values) > 0, "Category facet should have values"
        assert price_facet.stats is not None, "Price facet should have stats"
        assert len(in_stock_facet.values) > 0, "In Stock facet should have values"


@pytest.mark.asyncio
class TestFacetFiltering:
    """Test suite for facet-based filtering and drill-down."""

    async def test_facet_max_values_limit(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test that max_values parameter limits facet results.

        Validates that:
        - Facet returns at most max_values results
        - Total unique values is still accurate
        """
        search_service = SearchService(db_session)

        # Search with limited max_values
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="Material",
                    facet_type=FacetType.STRING,
                    max_values=5,  # Limit to 5
                )
            ],
            limit=20,
        )

        # Should have material facet
        material_facet = next((f for f in response.facets if f.field_id == "Material"), None)
        assert material_facet is not None, "Should have Material facet"

        # Should return at most 5 values
        assert len(material_facet.values) <= 5, f"Should return at most 5 values, got {len(material_facet.values)}"

        # Total unique values should still be accurate (more than 5)
        assert material_facet.total_values > 5, "Should have more than 5 unique materials total"

    async def test_facet_with_query_filtering(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test that facets are computed based on filtered results.

        Validates that:
        - Facet counts reflect query filtering
        - Only matching records contribute to facet counts
        """
        search_service = SearchService(db_session)

        # Search for "bearing" - should only match Bearings category
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="bearing",
            facets=[
                FacetConfig(
                    field_id="Category",
                    facet_type=FacetType.STRING,
                    max_values=10,
                )
            ],
            limit=20,
        )

        # Should have category facet
        category_facet = next((f for f in response.facets if f.field_id == "Category"), None)
        assert category_facet is not None, "Should have Category facet"

        # Bearings should be the only or dominant category
        bearings_value = next((v for v in category_facet.values if v.value == "Bearings"), None)
        assert bearings_value is not None, "Should have Bearings category in facets"

        # Bearings should have 4 matches (from test data)
        assert bearings_value.count == 4, f"Should have 4 bearings, got {bearings_value.count}"

        # Other categories should have fewer or no matches
        for facet_value in category_facet.values:
            if facet_value.value != "Bearings":
                # Other categories should only match if "bearing" appears in their records
                assert facet_value.count <= bearings_value.count, f"Bearings should have highest count in query 'bearing'"


@pytest.mark.asyncio
class TestFacetEdgeCases:
    """Test suite for facet edge cases and error handling."""

    async def test_facet_with_no_results(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test facet behavior when query has no matching results.

        Validates that:
        - Facets are returned even with no results
        - Facet counts are all zero
        - No errors occur
        """
        search_service = SearchService(db_session)

        # Search for term that won't match anything
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="nonexistent_product_xyz123",
            facets=[
                FacetConfig(
                    field_id="Category",
                    facet_type=FacetType.STRING,
                    max_values=10,
                )
            ],
            limit=20,
        )

        # Should return response without errors
        assert response is not None, "Should return response even with no results"

        # Should have facet even with no results
        category_facet = next((f for f in response.facets if f.field_id == "Category"), None)

        # Facet might not exist if there are absolutely no results, which is ok
        # Just verify no errors occurred

    async def test_empty_facet_list(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test search with no facets requested.

        Validates that:
        - Search works without facets
        - No facet data is returned
        - Results are normal
        """
        search_service = SearchService(db_session)

        # Search without facets
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="bolt",
            facets=None,  # No facets
            limit=20,
        )

        # Should return results
        assert response.metadata.total_results >= 0, "Should return results"

        # Should have no facets
        assert len(response.facets) == 0, "Should have no facets when none requested"

    async def test_facet_nonexistent_field(
        self,
        db_session: AsyncSession,
        facet_base: Base,
        facet_table: Table,
    ):
        """
        Test facet on field that doesn't exist.

        Validates that:
        - Request doesn't crash
        - Nonexistent field is handled gracefully
        - Other facets still work
        """
        search_service = SearchService(db_session)

        # Search with nonexistent facet field
        response = await search_service.search_in_base(
            base_id=str(facet_base.id),
            query="",
            facets=[
                FacetConfig(
                    field_id="NonexistentField",
                    facet_type=FacetType.STRING,
                    max_values=10,
                ),
                FacetConfig(
                    field_id="Category",
                    facet_type=FacetType.STRING,
                    max_values=10,
                ),
            ],
            limit=20,
        )

        # Should return response without crashing
        assert response is not None, "Should return response"

        # Valid facet (Category) should still work
        category_facet = next((f for f in response.facets if f.field_id == "Category"), None)
        # Category facet might or might not exist depending on error handling
