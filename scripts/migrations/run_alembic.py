#!/usr/bin/env python3
"""
Run alembic migration command.
"""

import os
import sys

# Set environment for Neon database
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://neondb_owner:npg_0KrSgPup6IOB@ep-divine-morning-ah0xhu01-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

# Import alembic command module
from alembic.config import CommandLine
from alembic.config import Config


def main():
    """Run alembic command."""
    try:
        # Create config
        config = Config()
        config.set_main_option("script_location", "migrations")
        config.set_main_option(
            "sqlalchemy.url",
            "postgresql://neondb_owner:npg_0KrSgPup6IOB@ep-divine-morning-ah0xhu01-pooler.c-3.us-east-1.aws.neon.tech/neondd?sslmode=require&channel_binding=require",
        )

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
