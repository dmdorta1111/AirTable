"""
Fixed Alembic environment configuration for PyBase.

This version avoids importing problematic modules that cause database connections.
"""

from logging.config import fileConfig
from alembic import context
import os

# Get the database URL from environment - this must be set
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable must be set. "
        "This is required for Alembic migrations to connect to the database."
    )

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Create empty metadata for non-autogenerate migrations
target_metadata = None


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    from sqlalchemy import create_engine

    # Use plain SQLAlchemy connection (not async)
    connectable = create_engine(DATABASE_URL)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


# Determine which mode to run in - use offline since we don't want to connect
try:
    # Try online first, fallback to offline
    run_migrations_online()
except Exception:
    # If online fails, use offline mode
    run_migrations_offline()
