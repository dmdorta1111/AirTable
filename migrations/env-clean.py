"""
Clean Alembic environment configuration for PyBase.
This version handles database connection cleanly.
"""

from logging.config import fileConfig
from alembic import context
import os

# Get Neon database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url
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
