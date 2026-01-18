#!/usr/bin/env python3
"""
Test database migration and configuration.
"""

import os
import sys

# Set environment variables for the test
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://neondb_owner:npg_0KrSgPup6IOB@ep-divine-morning-ah0xhu01-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)
os.environ["SECRET_KEY"] = "test-secret-key-for-development"
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from pybase.core.config import settings

    print("✅ Configuration loaded successfully")
    print(f"  App name: {settings.app_name}")
    print(f"  Database URL: {settings.database_url[:60]}...")
    print(f"  Sync Database URL: {settings.sync_database_url[:60]}...")
    print(f"  Environment: {settings.environment}")

    # Test database connection via alembic
    import subprocess

    print("\n🔧 Running database migration check...")

    # Check alembic status
    result = subprocess.run(
        ["alembic", "current"], capture_output=True, text=True, cwd=os.path.dirname(__file__)
    )

    if result.returncode == 0:
        print("✅ Alembic status command succeeded")
        print(f"  Output: {result.stdout.strip()}")

        # Run upgrade if needed
        if "8481bfd7da02" not in result.stdout:
            print("🔼 Running database migration...")
            upgrade_result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__),
            )
            if upgrade_result.returncode == 0:
                print("✅ Database migration completed successfully")
            else:
                print(f"❌ Migration failed: {upgrade_result.stderr}")
        else:
            print("✅ Database schema already up to date")
    else:
        print(f"❌ Alembic check failed: {result.stderr}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
