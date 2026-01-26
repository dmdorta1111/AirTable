#!/usr/bin/env python3
"""
Direct Neon database connection test.
"""

import os
import sys
import asyncio
import subprocess

# Set environment variables
# NOTE: Replace with your actual database credentials from environment or .env file
if "DATABASE_URL" not in os.environ:
    print("❌ ERROR: DATABASE_URL environment variable not set")
    print("Please set DATABASE_URL in your .env file or environment")
    print("Example: postgresql://user:password@host:port/database?sslmode=require")
    sys.exit(1)
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"


def test_sync_connection():
    """Test using psycopg2 for synchronous connection."""
    print("Testing synchronous database connection...")

    try:
        import psycopg2

        url = os.environ["DATABASE_URL"]
        print(f"Connecting to: {url[:70]}...")

        # Connect using psycopg2
        conn = psycopg2.connect(url)
        print("✅ Database connection successful!")

        # Create cursor
        cursor = conn.cursor()

        # Test query
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"Database version: {version[:50]}...")

        # Check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print(f"Found {len(tables)} tables in public schema")

        for table in tables[:5]:
            print(f"  - {table[0]}")

        if len(tables) > 5:
            print(f"  ... and {len(tables) - 5} more tables")

        cursor.close()
        conn.close()
        return True

    except ImportError:
        print("psycopg2 not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        return test_sync_connection()

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_alembic_migration():
    """Test alembic migration capability."""
    print("\nTesting alembic migration...")

    try:
        # Update alembic.ini with correct URL
        with open("alembic.ini", "r") as f:
            content = f.read()

        # Check if alembic.ini exists
        if os.path.exists("alembic.ini"):
            print("✅ alembic.ini exists")

            # Run alembic current
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "current"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__),
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    print(f"✅ Current migration: {output}")
                else:
                    print("✅ No migrations applied")
            else:
                print(f"⚠️ Could not check current migration: {result.stderr[:200]}")

        else:
            print("❌ alembic.ini not found")

    except Exception as e:
        print(f"❌ Alembic test failed: {e}")
        return False


def main():
    """Main test function."""
    print("=" * 60)
    print("PyBase Neon Database Connection Test")
    print("=" * 60)

    # Test database connection
    connection_ok = test_sync_connection()

    # Test alembic
    test_alembic_migration()

    print("\n" + "=" * 60)

    if connection_ok:
        print("✅ Database connection tests PASSED")
        print("\nNext steps:")
        print("1. Run: python -m alembic upgrade head")
        print("2. Start API: uvicorn src.pybase.main:app --reload")
        print("3. Test endpoints: curl http://localhost:8000/api/v1/health")
        return 0
    else:
        print("❌ Database connection tests FAILED")
        print("\nCheck:")
        print("1. Neon database is active")
        print("2. Connection URL is correct")
        print("3. Network connectivity to Neon")
        return 1


if __name__ == "__main__":
    sys.exit(main())
