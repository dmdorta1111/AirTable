#!/usr/bin/env python3
"""
Setup script to create audit_logs table.

Run with: python tests/e2e/setup_audit_table.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from pybase.core.config import settings


def convert_database_url_for_asyncpg(url: str) -> str:
    """Convert PostgreSQL database URL to asyncpg-compatible format."""
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

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
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


async def setup_audit_table():
    """Create audit_logs table and indexes."""

    print("Setting up audit_logs table...")

    # Setup database connection
    test_database_url = convert_database_url_for_asyncpg(settings.database_url)
    engine = create_async_engine(test_database_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Create pybase schema if it doesn't exist
            print("Creating pybase schema...")
            try:
                await conn.execute(text("CREATE SCHEMA IF NOT EXISTS pybase"))
                print("  ✓ Schema created/verified")
            except Exception as e:
                print(f"  ! Schema creation note: {e}")

            # Create audit_logs table (without foreign key for now)
            print("Creating pybase.audit_logs table...")
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS pybase.audit_logs (
                    id VARCHAR PRIMARY KEY,
                    -- Actor information
                    user_id VARCHAR,
                    user_email VARCHAR(255),
                    -- Action details
                    action VARCHAR(50) NOT NULL,
                    resource_type VARCHAR(50) NOT NULL,
                    resource_id VARCHAR,
                    -- Table context
                    table_id VARCHAR,
                    -- Data changes
                    old_value TEXT,
                    new_value TEXT,
                    -- Request context
                    ip_address VARCHAR(45),
                    user_agent VARCHAR(500),
                    request_id VARCHAR(255),
                    -- Tamper-evident storage
                    integrity_hash VARCHAR(64) NOT NULL,
                    previous_log_hash VARCHAR(64),
                    -- Additional context
                    meta TEXT DEFAULT '{}',
                    -- Timestamps
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                )
            """))
            print("  ✓ Table created")

            # Create indexes
            print("Creating indexes...")
            indexes = [
                "ix_audit_logs_user_id",
                "ix_audit_logs_user_email",
                "ix_audit_logs_action",
                "ix_audit_logs_resource_type",
                "ix_audit_logs_resource_id",
                "ix_audit_logs_table_id",
                "ix_audit_logs_request_id",
                "ix_audit_logs_integrity_hash",
                "ix_audit_logs_user_action",
                "ix_audit_logs_table_action",
                "ix_audit_logs_resource",
                "ix_audit_logs_created_at",
            ]

            index_statements = [
                f"CREATE INDEX IF NOT EXISTS {idx} ON pybase.audit_logs({col})"
                for idx, col in [
                    ("ix_audit_logs_user_id", "user_id"),
                    ("ix_audit_logs_user_email", "user_email"),
                    ("ix_audit_logs_action", "action"),
                    ("ix_audit_logs_resource_type", "resource_type"),
                    ("ix_audit_logs_resource_id", "resource_id"),
                    ("ix_audit_logs_table_id", "table_id"),
                    ("ix_audit_logs_request_id", "request_id"),
                    ("ix_audit_logs_integrity_hash", "integrity_hash"),
                ]
            ]

            # Add composite indexes
            index_statements.extend([
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_action ON pybase.audit_logs(user_id, action)",
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_table_action ON pybase.audit_logs(table_id, action)",
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_resource ON pybase.audit_logs(resource_type, resource_id)",
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON pybase.audit_logs(created_at)",
            ])

            for stmt in index_statements:
                await conn.execute(text(stmt))

            print(f"  ✓ Created {len(index_statements)} indexes")

        print("\n✅ audit_logs table setup complete!")
        print("\nYou can now run: python tests/e2e/verify_audit_flow.py")

        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(setup_audit_table())
    sys.exit(0 if success else 1)
