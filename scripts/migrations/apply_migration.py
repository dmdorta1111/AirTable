#!/usr/bin/env python3
"""
Apply database migration to Neon database.
This script tests the database connection and applies the initial migration.
"""

import os
import subprocess
import sys
import time


def set_neon_env():
    """Set environment variables for Neon database."""
    # Get database URL from environment variable
    neon_url = os.getenv("DATABASE_URL")
    if not neon_url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Please set it before running this script."
        )

    # Set environment variables
    os.environ["DATABASE_URL"] = neon_url
    os.environ["ENVIRONMENT"] = os.getenv("ENVIRONMENT", "development")
    os.environ["DEBUG"] = os.getenv("DEBUG", "true")

    # Also create sync URL for alembic (alembic needs synchronous URL)
    if neon_url.startswith("postgresql+asyncpg://"):
        sync_url = neon_url.replace("postgresql+asyncpg://", "postgresql://")
    else:
        sync_url = neon_url

    print(f"Using database URL: {neon_url[:80]}...")
    return sync_url


def test_connection():
    """Test database connection with psycopg2."""
    print("\n🔧 Testing database connection...")
    try:
        import psycopg2

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful!")
        print(f"   Database version: {version.split(',')[0]}")

        # Check tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"   Found {len(tables)} tables in public schema")

        if tables:
            print("   Existing tables:")
            for table in tables[:10]:  # Show first 10 tables
                print(f"     - {table[0]}")
            if len(tables) > 10:
                print(f"     ... and {len(tables) - 10} more tables")

        cursor.close()
        conn.close()
        return True

    except ImportError:
        print("Installing psycopg2-binary...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
        return test_connection()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def run_migration():
    """Run alembic migration."""
    print("\n🔧 Running database migration with alembic...")

    # First check if alembic can connect
    try:
        print("Running: alembic current")
        result = subprocess.run(["alembic", "current"], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✅ Alembic current: {result.stdout.strip()}")
        else:
            print(f"⚠️  Alembic check: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⚠️  Alembic connection timed out")
    except Exception as e:
        print(f"⚠️  Error checking alembic: {e}")

    # Try to run upgrade
    print("Running: alembic upgrade head")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=60,  # Longer timeout for migration
        )

        if result.returncode == 0:
            print("✅ Database migration applied successfully!")
            print(f"Output: {result.stdout}")
            return True
        else:
            print(f"❌ Migration failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Migration timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False


def create_simple_test_schema():
    """Create a simple test schema if migration fails."""
    print("\n🔄 Creating simple test schema with raw SQL...")
    try:
        import psycopg2

        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cursor = conn.cursor()

        # Check if any tables exist
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public'
                LIMIT 1
            )
        """)
        has_tables = cursor.fetchone()[0]

        if has_tables:
            print("✅ Tables already exist in database")
        else:
            print("ℹ️  No tables found - database appears to be fresh")

            # Create a simple test table to verify write permissions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pybase_test (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("✅ Created test table successfully")

            cursor.execute("INSERT INTO pybase_test (name) VALUES ('migration_test')")
            conn.commit()
            print("✅ Inserted test data successfully")

            cursor.execute("SELECT COUNT(*) FROM pybase_test")
            count = cursor.fetchone()[0]
            print(f"✅ Test table has {count} rows")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Simple schema test failed: {e}")
        return False


def main():
    """Main function."""
    print("🚀 PyBase Neon Database Migration")
    print("=" * 60)

    # Set environment
    sync_url = set_neon_env()

    # Test connection
    if not test_connection():
        print("\n❌ Cannot proceed without database connection")
        return 1

    # Try migration
    migration_success = run_migration()

    if not migration_success:
        print("\n⚠️  Alembic migration failed. Creating simple test schema...")
        if create_simple_test_schema():
            print("\n✅ Database is accessible but migration needs debugging")
        else:
            print("\n❌ Database connection works but cannot create schema")
            return 1

    # Final check
    print("\n" + "=" * 60)
    print("📊 Migration Summary")
    print("=" * 60)

    test_connection()

    print("\n✅ Database migration sequence completed!")
    print("\nNext steps:")
    print("1. Start API: uvicorn src.pybase.main:app --reload")
    print("2. Test health endpoint: curl http://localhost:8000/api/v1/health")
    print("3. Verify authentication: curl -X POST http://localhost:8000/api/v1/auth/login")

    return 0


if __name__ == "__main__":
    sys.exit(main())
