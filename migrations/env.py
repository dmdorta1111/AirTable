"""
Alembic environment configuration for PyBase using Neon database.

This configuration directly uses the Neon database URL for migrations.
"""

from logging.config import fileConfig
from alembic import context
import os

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set. Please configure it before running migrations.")

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with database URL from environment
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_online():
    """Run migrations online."""
    from sqlalchemy import create_engine

    # Create sync engine for alembic
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)

        with context.begin_transaction():
            context.run_migrations()


# Always use online mode
run_migrations_online()
