#!/usr/bin/env python3
"""
Run database migration for PyBase on Neon database.
"""

import os
import sys
import subprocess


def run_migration():
    print("🚀 Running database migration for PyBase...")

    # Set environment variables from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Please set it before running this script."
        )

    os.environ["DATABASE_URL"] = database_url
    os.environ["SECRET_KEY"] = os.getenv("SECRET_KEY", "test-secret-key-for-development")
    os.environ["ENVIRONMENT"] = os.getenv("ENVIRONMENT", "development")

    print("📊 Checking current migration status...")

    # Run alembic current to check status
    result = subprocess.run(
        ["alembic", "current"], capture_output=True, text=True, cwd=os.path.dirname(__file__)
    )

    if result.returncode == 0:
        current_output = result.stdout.strip()
        print(f"✅ Alembic status: {current_output}")

        # Check if migration is already applied
        if "8481bfd7da02" in current_output:
            print("✅ Database schema already up to date (migration 8481bfd7da02 applied)")
            return True
        else:
            print("🔼 Running migration upgrade...")

            # Run alembic upgrade head
            upgrade_result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__),
            )

            if upgrade_result.returncode == 0:
                print("✅ Database migration completed successfully!")
                print(f"Output: {upgrade_result.stdout}")
                return True
            else:
                print(f"❌ Migration failed with error:")
                print(f"Stderr: {upgrade_result.stderr}")
                print(f"Stdout: {upgrade_result.stdout}")
                return False
    else:
        print(f"❌ Failed to check alembic status:")
        print(f"Error: {result.stderr}")

        # Try to run upgrade anyway
        print("🔄 Attempting to run migration upgrade directly...")
        upgrade_result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__),
        )

        if upgrade_result.returncode == 0:
            print("✅ Database migration completed successfully!")
            return True
        else:
            print(f"❌ Direct migration also failed:")
            print(f"Error: {upgrade_result.stderr}")
            return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
