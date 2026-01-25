#!/usr/bin/env python3
"""
Run alembic migration command.
"""

import os
import sys

# Set environment for Neon database from environment variable
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError(
        "DATABASE_URL environment variable not set. "
        "Please set it before running this script."
    )
os.environ["DATABASE_URL"] = database_url

# Import alembic command module
from alembic.config import CommandLine
from alembic.config import Config


def main():
    """Run alembic command."""
    try:
        # Create config
        config = Config()
        config.set_main_option("script_location", "migrations")

        # Convert async URL to sync URL for alembic
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable not set. "
                "Please set it before running this script."
            )

        # Convert asyncpg URL to synchronous URL for alembic
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        config.set_main_option("sqlalchemy.url", sync_url)

        # Run alembic current
        print("Running alembic current...")
        from alembic import command

        command.current(config, verbose=True)

    except Exception as e:
        print(f"Error running alembic: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
