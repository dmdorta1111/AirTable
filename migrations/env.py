"""
Alembic environment configuration for PyBase using Neon database.

This configuration directly uses the Neon database URL for migrations.
"""

from logging.config import fileConfig
from alembic import context
import os

# Use Neon database URL directly
# This corresponds to the .env.example configuration
NEON_DATABASE_URL = "postgresql://neondb_owner:npg_0KrSgPup6IOB@ep-divine-morning-ah0xhu01-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with Neon database URL
config.set_main_option("sqlalchemy.url", NEON_DATABASE_URL)


def run_migrations_online():
    """Run migrations online."""
    from sqlalchemy import create_engine

    # Create sync engine for alembic using Neon URL
    engine = create_engine(NEON_DATABASE_URL)

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)

        with context.begin_transaction():
            context.run_migrations()


# Always use online mode
run_migrations_online()
