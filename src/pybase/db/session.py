"""
Database session management for PyBase.

Provides async database sessions using SQLAlchemy 2.0 async features.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from pybase.core.config import settings
from pybase.core.logging import get_logger

logger = get_logger(__name__)


def _prepare_asyncpg_url(database_url: str) -> tuple[str, dict[str, Any]]:
    """
    Prepare database URL for asyncpg by removing libpq-specific parameters.

    asyncpg doesn't accept libpq parameters like 'sslmode', 'channel_binding', etc.
    This function removes them from URL and returns appropriate connect_args.
    """
    # libpq parameters that asyncpg doesn't accept
    LIBPQ_PARAMS = {
        "sslmode", "channel_binding", "sslcert", "sslkey", "sslrootcert",
        "sslcrl", "requirepeer", "krbsrvname", "gsslib", "service",
        "target_session_attrs", "options", "application_name",
    }

    parsed = urlparse(database_url)
    query_params = parse_qs(parsed.query)
    connect_args: dict[str, Any] = {}

    # Extract sslmode before removing it
    sslmode = query_params.get("sslmode", [None])[0]

    # Remove all libpq-specific parameters
    for param in LIBPQ_PARAMS:
        query_params.pop(param, None)

    # Handle SSL based on sslmode value
    if sslmode in ("require", "verify-ca", "verify-full"):
        import ssl
        ssl_context = ssl.create_default_context()
        if sslmode == "require":
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context
    elif sslmode == "prefer":
        connect_args["ssl"] = "prefer"
    # 'disable' or 'allow' - no ssl needed

    # Rebuild URL without libpq params
    new_query = urlencode(query_params, doseq=True)
    clean_url = urlunparse(parsed._replace(query=new_query))

    return clean_url, connect_args


def create_engine() -> AsyncEngine:
    """
    Create async database engine.

    Uses connection pooling for production and NullPool for testing.
    """
    # Prepare URL for asyncpg (handle sslmode conversion)
    database_url, connect_args = _prepare_asyncpg_url(settings.database_url)

    engine_kwargs: dict[str, Any] = {
        "echo": settings.debug and settings.environment == "development",
        "future": True,
    }

    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    # Use NullPool for testing to avoid connection issues
    if settings.environment == "test":
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = settings.db_pool_size
        engine_kwargs["max_overflow"] = settings.db_max_overflow
        engine_kwargs["pool_timeout"] = settings.db_pool_timeout
        engine_kwargs["pool_pre_ping"] = True  # Verify connections before use

    return create_async_engine(
        database_url,
        **engine_kwargs,
    )


# Create the async engine
engine = create_engine()

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that yields a database session.

    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.

    Usage:
        async with get_db_context() as db:
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database connection.

    Called during application startup to verify database connectivity.
    """
    try:
        async with engine.begin() as conn:
            # Simple query to verify connection
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_db() -> None:
    """
    Close database connections.

    Called during application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")
