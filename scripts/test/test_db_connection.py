#!/usr/bin/env python3
"""
Test Neon database connection for PyBase.
"""

import os
import sys
import asyncio
from pathlib import Path

# Set the database URL from user input
os.environ["DATABASE_URL"] = (
    "postgresql://neondb_owner:npg_0KrSgPup6IOB@ep-divine-morning-ah0xhu01-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"


async def test_connection():
    """Test the database connection."""
    print("🔧 Testing Neon database connection...")

    try:
        # Test asyncpg connection
        import asyncpg

        # Parse the URL to extract connection parameters
        url = os.environ["DATABASE_URL"]

        # Convert to asyncpg format
        # postgresql://neondb_owner:npg_0KrSgPup6IOB@ep-divine-morning-ah0xhu01-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
        # Remove the +asyncpg prefix
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://")

        print(f"Connecting to: {url[:70]}...")

        # Extract connection parameters
        parts = url.split("://")[1].split("/")
        auth_host = parts[0]
        database = parts[1].split("?")[0]

        auth, host = auth_host.split("@")
        user, password = auth.split(":")

        print(f"User: {user}")
        print(f"Host: {host}")
        print(f"Database: {database}")

        # Connect using asyncpg
        conn = await asyncpg.connect(
            user=user,
            password=password,
            host=host.split(":")[0],
            port=host.split(":")[1] if ":" in host else 5432,
            database=database,
            ssl="require",
        )

        print("✅ Database connection successful!")

        # Test basic query
        version = await conn.fetchval("SELECT version()")
        print(f"Database version: {version[:50]}...")

        # Check if pybase schema exists
        try:
            tables = await conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
            print(f"Found {len(tables)} tables in public schema")

            for table in tables[:5]:
                print(f"  - {table['table_name']}")

            if len(tables) > 5:
                print(f"  ... and {len(tables) - 5} more tables")

        except Exception as e:
            print(f"Warning: Could not list tables: {e}")

        await conn.close()
        return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_alembic():
    """Test alembic migration status."""
    print("\n🔧 Testing alembic migration status...")

    try:
        import subprocess
        import time

        # Run alembic current
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__),
            timeout=30,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            if output:
                print(f"✅ Alembic current: {output}")
            else:
                print("✅ Alembic: No migrations applied")

            # Check if we can run upgrade
            print("Testing alembic upgrade...")
            upgrade_result = subprocess.run(
                ["alembic", "upgrade", "head", "--sql"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__),
                timeout=30,
            )

            if upgrade_result.returncode == 0:
                print("✅ Alembic can generate migration SQL")
            else:
                print(f"⚠️ Alembic upgrade check: {upgrade_result.stderr[:200]}")

        else:
            print(f"❌ Alembic check failed: {result.stderr[:200]}")

    except Exception as e:
        print(f"❌ Alembic test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("=" * 60)
    print("PyBase Neon Database Connection Test")
    print("=" * 60)

    # Test database connection
    connection_ok = await test_connection()

    # Test alembic
    await test_alembic()

    print("\n" + "=" * 60)

    if connection_ok:
        print("✅ Database connection tests PASSED")
        print("\nNext steps:")
        print("1. Run: alembic upgrade head")
        print("2. Start API: uvicorn src.pybase.main:app --reload")
        print("3. Test endpoints: curl http://localhost:8000/api/v1/health")
    else:
        print("❌ Database connection tests FAILED")
        print("\nCheck:")
        print("1. Neon database is active")
        print("2. Connection URL is correct")
        print("3. Network connectivity to Neon")

    return 0 if connection_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
