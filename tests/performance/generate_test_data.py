"""
Generate test data for performance testing.

This script creates a table with 10,000+ records for performance testing
all view types (Grid, Kanban, Calendar, Form, Gallery, Gantt, Timeline).

Usage:
    python tests/performance/generate_test_data.py --count 10000
    python tests/performance/generate_test_data.py --count 15000 --clean
"""

import argparse
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pybase.core.config import settings
from pybase.core.security import hash_password
from pybase.db.base import Base


# Sample data for realistic records
DEPARTMENTS = ["Engineering", "Manufacturing", "Quality", "Procurement", "Sales"]
STATUSES = ["Not Started", "In Progress", "Review", "Completed", "On Hold"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
MATERIALS = ["Steel", "Aluminum", "Brass", "Copper", "Titanium", "Plastic", "Composite"]
PART_PREFIXES = ["BRK", "SFT", "MTR", "BRG", "GSK", "FLG", "VLV", "HOS"]
ENGINEERS = [
    "Alice Johnson",
    "Bob Smith",
    "Carol Davis",
    "David Wilson",
    "Eve Martinez",
    "Frank Brown",
    "Grace Lee",
    "Henry Taylor",
]


def generate_part_number(index: int) -> str:
    """Generate realistic part number."""
    prefix = random.choice(PART_PREFIXES)
    category = random.randint(100, 999)
    variant = random.randint(1000, 9999)
    return f"{prefix}-{category}-{variant:04d}"


def generate_description(index: int) -> str:
    """Generate realistic part description."""
    types = [
        "Assembly",
        "Component",
        "Bracket",
        "Housing",
        "Shaft",
        "Bearing",
        "Gasket",
        "Seal",
    ]
    adjectives = [
        "Primary",
        "Secondary",
        "Upper",
        "Lower",
        "Front",
        "Rear",
        "Left",
        "Right",
    ]
    return f"{random.choice(adjectives)} {random.choice(types)} Unit"


def generate_random_date(start_days_ago: int, end_days_ago: int = 0) -> str:
    """Generate random date in ISO format."""
    days_ago = random.randint(end_days_ago, start_days_ago)
    date = datetime.now() - timedelta(days=days_ago)
    return date.strftime("%Y-%m-%d")


def generate_dimension() -> str:
    """Generate random dimension value."""
    value = random.uniform(5.0, 500.0)
    tolerance = random.choice(["±0.1", "±0.05", "±0.01", "+0.1/-0", "+0.05/-0.02"])
    return f"{value:.2f} mm {tolerance}"


def generate_quantity() -> int:
    """Generate random quantity."""
    return random.choice([1, 2, 5, 10, 20, 50, 100, 200, 500])


def generate_progress() -> float:
    """Generate random progress percentage."""
    return round(random.uniform(0, 100), 1)


async def create_test_data(record_count: int = 10000, clean: bool = False):
    """
    Create test data for performance testing.

    Args:
        record_count: Number of records to create (default 10000)
        clean: If True, drop and recreate database schema
    """
    print(f"Creating test data with {record_count} records...")

    # Create async engine
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    # Convert database URL for asyncpg
    def convert_url(url: str) -> str:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        params = parse_qs(parsed.query, keep_blank_values=True)
        if "sslmode" in params:
            sslmode = params.pop("sslmode")[0]
            if sslmode in ("require", "verify-ca", "verify-full"):
                params["ssl"] = ["require"]
        params.pop("channel_binding", None)
        new_query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=new_query))

    db_url = convert_url(settings.database_url)
    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)

    # Clean database if requested
    if clean:
        print("Cleaning database schema...")
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            await conn.run_sync(Base.metadata.create_all)
        print("Database schema recreated")

    # Create session maker
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Create test user
        print("Creating test user...")
        user_id = str(uuid4())
        await session.execute(
            text(
                """
            INSERT INTO users (id, email, hashed_password, name, is_active, is_verified, created_at, updated_at)
            VALUES (:id, :email, :password, :name, true, true, NOW(), NOW())
            ON CONFLICT (email) DO UPDATE SET updated_at = NOW()
            RETURNING id
        """
            ),
            {
                "id": user_id,
                "email": "perf@test.com",
                "password": hash_password("testpass"),
                "name": "Performance Test User",
            },
        )

        # Get or create user
        result = await session.execute(
            text("SELECT id FROM users WHERE email = 'perf@test.com'")
        )
        user_id = str(result.scalar())

        # Create workspace
        print("Creating workspace...")
        workspace_id = str(uuid4())
        await session.execute(
            text(
                """
            INSERT INTO workspaces (id, name, slug, owner_id, created_at, updated_at)
            VALUES (:id, :name, :slug, :owner_id, NOW(), NOW())
            ON CONFLICT (slug) DO UPDATE SET updated_at = NOW()
            RETURNING id
        """
            ),
            {
                "id": workspace_id,
                "name": "Performance Test Workspace",
                "slug": "perf-test",
                "owner_id": user_id,
            },
        )

        result = await session.execute(
            text("SELECT id FROM workspaces WHERE slug = 'perf-test'")
        )
        workspace_id = str(result.scalar())

        # Create base
        print("Creating base...")
        base_id = str(uuid4())
        await session.execute(
            text(
                """
            INSERT INTO bases (id, workspace_id, name, description, icon, created_at, updated_at)
            VALUES (:id, :workspace_id, :name, :description, :icon, NOW(), NOW())
            ON CONFLICT DO NOTHING
            RETURNING id
        """
            ),
            {
                "id": base_id,
                "workspace_id": workspace_id,
                "name": "Performance Test Base",
                "description": "Base for performance testing with 10K+ records",
                "icon": "⚡",
            },
        )

        result = await session.execute(
            text(
                "SELECT id FROM bases WHERE workspace_id = :workspace_id AND name = :name"
            ),
            {"workspace_id": workspace_id, "name": "Performance Test Base"},
        )
        base_id = str(result.scalar())

        # Create table
        print("Creating table...")
        table_id = str(uuid4())
        await session.execute(
            text(
                """
            INSERT INTO tables (id, base_id, name, description, icon, position, created_at, updated_at)
            VALUES (:id, :base_id, :name, :description, :icon, 0, NOW(), NOW())
            ON CONFLICT DO NOTHING
            RETURNING id
        """
            ),
            {
                "id": table_id,
                "base_id": base_id,
                "name": "Engineering Parts",
                "description": f"Performance test table with {record_count} records",
                "icon": "🔧",
            },
        )

        result = await session.execute(
            text(
                "SELECT id FROM tables WHERE base_id = :base_id AND name = :name"
            ),
            {"base_id": base_id, "name": "Engineering Parts"},
        )
        table_id = str(result.scalar())

        # Create fields
        print("Creating fields...")
        field_ids = {}
        fields = [
            ("part_number", "Part Number", "text", 0),
            ("description", "Description", "long_text", 1),
            ("status", "Status", "single_select", 2),
            ("priority", "Priority", "single_select", 3),
            ("department", "Department", "single_select", 4),
            ("engineer", "Engineer", "single_select", 5),
            ("material", "Material", "single_select", 6),
            ("quantity", "Quantity", "number", 7),
            ("dimension", "Dimension", "text", 8),
            ("start_date", "Start Date", "date", 9),
            ("end_date", "End Date", "date", 10),
            ("progress", "Progress", "number", 11),
            ("created_date", "Created", "date", 12),
        ]

        for field_name, display_name, field_type, position in fields:
            field_id = str(uuid4())
            field_ids[field_name] = field_id

            # Build field config
            config = {}
            if field_type == "single_select":
                if field_name == "status":
                    config["options"] = STATUSES
                elif field_name == "priority":
                    config["options"] = PRIORITIES
                elif field_name == "department":
                    config["options"] = DEPARTMENTS
                elif field_name == "engineer":
                    config["options"] = ENGINEERS
                elif field_name == "material":
                    config["options"] = MATERIALS

            await session.execute(
                text(
                    """
                INSERT INTO fields (id, table_id, name, type, config, position, created_at, updated_at)
                VALUES (:id, :table_id, :name, :type, :config, :position, NOW(), NOW())
                ON CONFLICT DO NOTHING
            """
                ),
                {
                    "id": field_id,
                    "table_id": table_id,
                    "name": display_name,
                    "type": field_type,
                    "config": json.dumps(config),
                    "position": position,
                },
            )

        # Create default view
        print("Creating default view...")
        view_id = str(uuid4())
        await session.execute(
            text(
                """
            INSERT INTO views (id, table_id, name, type, is_default, position, created_at, updated_at)
            VALUES (:id, :table_id, :name, 'grid', true, 0, NOW(), NOW())
            ON CONFLICT DO NOTHING
        """
            ),
            {
                "id": view_id,
                "table_id": table_id,
                "name": "All Parts",
            },
        )

        # Create records in batches
        print(f"Creating {record_count} records...")
        batch_size = 1000
        batches = (record_count + batch_size - 1) // batch_size

        for batch_num in range(batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, record_count)
            batch_count = end_idx - start_idx

            records_batch = []
            for i in range(start_idx, end_idx):
                record_id = str(uuid4())
                start_date = generate_random_date(180, 30)
                end_date = generate_random_date(30, 0)

                data = {
                    field_ids["part_number"]: generate_part_number(i),
                    field_ids["description"]: generate_description(i),
                    field_ids["status"]: random.choice(STATUSES),
                    field_ids["priority"]: random.choice(PRIORITIES),
                    field_ids["department"]: random.choice(DEPARTMENTS),
                    field_ids["engineer"]: random.choice(ENGINEERS),
                    field_ids["material"]: random.choice(MATERIALS),
                    field_ids["quantity"]: generate_quantity(),
                    field_ids["dimension"]: generate_dimension(),
                    field_ids["start_date"]: start_date,
                    field_ids["end_date"]: end_date,
                    field_ids["progress"]: generate_progress(),
                    field_ids["created_date"]: generate_random_date(365, 0),
                }

                records_batch.append(
                    {
                        "id": record_id,
                        "table_id": table_id,
                        "data": json.dumps(data),
                    }
                )

            # Bulk insert batch
            await session.execute(
                text(
                    """
                INSERT INTO records (id, table_id, data, created_at, updated_at)
                VALUES (:id, :table_id, :data, NOW(), NOW())
            """
                ),
                records_batch,
            )

            await session.commit()
            progress = ((batch_num + 1) / batches) * 100
            print(
                f"Progress: {progress:.1f}% ({end_idx}/{record_count} records created)"
            )

        print(f"\n✓ Successfully created {record_count} records")
        print(f"  Table ID: {table_id}")
        print(f"  View ID: {view_id}")
        print(f"  User: perf@test.com / testpass")
        print(
            f"\n  Access: http://localhost:5173/tables/{table_id}"
        )

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate test data for performance testing"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10000,
        help="Number of records to create (default: 10000)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean database before creating data",
    )

    args = parser.parse_args()

    if args.count < 1000:
        print("Warning: Minimum 1000 records recommended for performance testing")
    if args.count > 100000:
        print("Warning: Very large dataset may take significant time to create")

    try:
        asyncio.run(create_test_data(args.count, args.clean))
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
