"""
Alembic environment configuration for PyBase using Neon database.

This configuration directly uses the Neon database URL for migrations.
"""

from logging.config import fileConfig
from alembic import context
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Prevent pybase package initialization
import importlib.util

def import_from_file(module_name, file_path):
    """Import module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import Base class directly
base_module = import_from_file("pybase.db.base", src_path / "pybase" / "db" / "base.py")
Base = base_module.Base

# Import model base
model_base_module = import_from_file("pybase.models.base", src_path / "pybase" / "models" / "base.py")

# Import models directly
user_module = import_from_file("pybase.models.user", src_path / "pybase" / "models" / "user.py")
workspace_module = import_from_file("pybase.models.workspace", src_path / "pybase" / "models" / "workspace.py")
table_module = import_from_file("pybase.models.table", src_path / "pybase" / "models" / "table.py")
field_module = import_from_file("pybase.models.field", src_path / "pybase" / "models" / "field.py")
record_module = import_from_file("pybase.models.record", src_path / "pybase" / "models" / "record.py")
view_module = import_from_file("pybase.models.view", src_path / "pybase" / "models" / "view.py")
automation_module = import_from_file("pybase.models.automation", src_path / "pybase" / "models" / "automation.py")
werk24_usage_module = import_from_file("pybase.models.werk24_usage", src_path / "pybase" / "models" / "werk24_usage.py")
comment_module = import_from_file("pybase.models.comment", src_path / "pybase" / "models" / "comment.py")
saml_config_module = import_from_file("pybase.models.saml_config", src_path / "pybase" / "models" / "saml_config.py")
oidc_config_module = import_from_file("pybase.models.oidc_config", src_path / "pybase" / "models" / "oidc_config.py")
user_identity_module = import_from_file("pybase.models.user_identity", src_path / "pybase" / "models" / "user_identity.py")

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is set. Please configure it before running migrations.")

# Convert async URL to sync format for Alembic migrations
# postgresql+asyncpg:// → postgresql://
SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg://", "://")

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with database URL from environment
config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)

# Set target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    context.configure(
        url=SYNC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="pybase",
        include_schemas=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects to only include those in the pybase schema.
    This prevents alembic from detecting tables in other schemas.
    """
    # Only include tables in the pybase schema
    if type_ == "table":
        # If this is from reflection (existing database), only include pybase schema
        if reflected and hasattr(object, 'schema'):
            return object.schema == "pybase"
        # If this is from our models, it should go into pybase schema
        return True
    return True


def run_migrations_online():
    """Run migrations online."""
    from sqlalchemy import create_engine, pool, text

    # Create sync engine for alembic
    engine = create_engine(
        SYNC_DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with engine.connect() as connection:
        # Set search path to pybase schema
        connection.execute(text("SET search_path TO pybase, public"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="pybase",
            include_schemas=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


# Check if we're in offline mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
