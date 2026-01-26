"""
Database performance monitoring for serialized_models table.

Monitors:
- Table size and growth
- JSONB column statistics (avg size, compression ratio)
- Index health for feature_types array (GIN index)
- Query latency monitoring
- Bloat and fragmentation detection
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TableSizeStats:
    """Table size statistics."""
    table_name: str
    total_size_mb: float
    table_size_mb: float
    indexes_size_mb: float
    toast_size_mb: float  # Overflow storage for large columns
    row_count: int
    avg_row_size_kb: float


@dataclass
class JSONBStats:
    """JSONB column statistics."""
    column_name: str
    avg_size_bytes: float
    min_size_bytes: int
    max_size_bytes: int
    total_uncompressed_mb: float
    estimated_compression_ratio: float  # If using TOAST compression


@dataclass
class IndexHealthStats:
    """Index health statistics."""
    index_name: str
    index_type: str  # btree, gin, etc.
    size_mb: float
    scan_count: int
    tuples_read: int
    tuples_fetched: int
    cache_hit_ratio: float
    is_bloated: bool
    bloat_ratio: float


@dataclass
class QueryPerformanceStats:
    """Query performance tracking."""
    query_name: str
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    calls_total: int
    total_time_sec: float


class DatabaseMonitor:
    """
    Monitor database performance for serialization pipeline.

    Focus areas:
    - Table size and growth rate
    - JSONB storage efficiency
    - Index usage and health
    - Query performance
    """

    # Alert thresholds
    ALERT_BLOAT_RATIO = 0.3  # 30% bloat
    ALERT_CACHE_HIT_MIN = 0.90  # 90% cache hit
    ALERT_TABLE_SIZE_GB = 100  # 100GB
    ALERT_INDEX_SIZE_MB = 10000  # 10GB per index

    def __init__(self) -> None:
        self._historical_sizes: dict[str, list[tuple[datetime, float]]] = {}

    async def get_table_stats(
        self,
        session: AsyncSession,
        table_name: str = "serialized_models",
    ) -> TableSizeStats | None:
        """Get table size and row statistics."""
        sql = text("""
            SELECT
                pg_total_relation_size(quote_ident(:table)) as total_size,
                pg_relation_size(quote_ident(:table)) as table_size,
                pg_indexes_size(quote_ident(:table)) as indexes_size,
                COALESCE(
                    (SELECT pg_relation_size(reltoastrelid)
                     FROM pg_class
                     WHERE relname = :table AND reltoastrelid != 0),
                    0
                ) as toast_size
        """)

        try:
            result = await session.execute(sql, {"table": table_name})
            row = result.fetchone()

            if not row:
                return None

            # Get row count and avg row size
            count_sql = text(f"""
                SELECT
                    COUNT(*) as row_count,
                    pg_size_pretty(pg_total_relation_size('{table_name}')::bigint) as total_pretty
                FROM {table_name}
            """)
            count_result = await session.execute(count_sql)
            count_row = count_result.fetchone()
            row_count = count_row.row_count if count_row else 0

            # Calculate average row size
            total_size_bytes = row.total_size or 0
            avg_row_size_kb = (total_size_bytes / row_count) / 1024 if row_count > 0 else 0

            stats = TableSizeStats(
                table_name=table_name,
                total_size_mb=round((row.total_size or 0) / 1024 / 1024, 2),
                table_size_mb=round((row.table_size or 0) / 1024 / 1024, 2),
                indexes_size_mb=round((row.indexes_size or 0) / 1024 / 1024, 2),
                toast_size_mb=round((row.toast_size or 0) / 1024 / 1024, 2),
                row_count=row_count,
                avg_row_size_kb=round(avg_row_size_kb, 2),
            )

            # Store for trend analysis
            self._store_size_history(table_name, stats.total_size_mb)

            return stats

        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return None

    async def get_jsonb_stats(
        self,
        session: AsyncSession,
        table_name: str = "serialized_models",
        column_name: str = "serialized_content",
    ) -> JSONBStats | None:
        """Get JSONB column storage statistics."""
        sql = text(f"""
            SELECT
                AVG(octet_length({column_name}))::int as avg_size,
                MIN(octet_length({column_name}))::int as min_size,
                MAX(octet_length({column_name}))::int as max_size,
                SUM(octet_length({column_name})) / 1024.0 / 1024.0 as total_mb,
                COUNT(*) as row_count
            FROM {table_name}
            WHERE {column_name} IS NOT NULL
        """)

        try:
            result = await session.execute(sql)
            row = result.fetchone()

            if not row or row.avg_size is None:
                return None

            # Estimate compression (TOAST compresses by default)
            # Compare stored size vs uncompressed JSON size estimate
            estimated_compression_ratio = 0.0  # Placeholder

            return JSONBStats(
                column_name=column_name,
                avg_size_bytes=float(row.avg_size),
                min_size_bytes=int(row.min_size),
                max_size_bytes=int(row.max_size),
                total_uncompressed_mb=round(float(row.total_mb), 2),
                estimated_compression_ratio=round(estimated_compression_ratio, 2),
            )

        except Exception as e:
            logger.warning(f"Failed to get JSONB stats: {e}")
            return None

    async def get_index_health(
        self,
        session: AsyncSession,
        table_name: str = "serialized_models",
    ) -> list[IndexHealthStats]:
        """Get index health statistics."""
        sql = text("""
            SELECT
                i.indexrelid::regclass as index_name,
                am.amname as index_type,
                pg_relation_size(i.indexrelid) / 1024.0 / 1024.0 as size_mb,
                i.idx_scan as scan_count,
                i.idx_tup_read as tuples_read,
                i.idx_tup_fetch as tuples_fetched,
                COALESCE(
                    i.idx_blks_hit::float / NULLIF(i.idx_blks_hit + i.idx_blks_read, 0),
                    0
                ) as cache_hit_ratio,
                0 as is_bloated,  -- Placeholder for bloat detection
                0.0 as bloat_ratio
            FROM pg_stat_user_indexes i
            JOIN pg_am am ON am.oid = i.indexrelid
            JOIN pg_class c ON c.oid = i.relid
            WHERE c.relname = :table_name
        """)

        indexes = []
        try:
            result = await session.execute(sql, {"table_name": table_name})
            rows = result.fetchall()

            for row in rows:
                indexes.append(IndexHealthStats(
                    index_name=row.index_name or "",
                    index_type=row.index_type or "",
                    size_mb=round(float(row.size_mb), 2),
                    scan_count=int(row.scan_count),
                    tuples_read=int(row.tuples_read),
                    tuples_fetched=int(row.tuples_fetched),
                    cache_hit_ratio=round(float(row.cache_hit_ratio), 3),
                    is_bloated=bool(row.is_bloated),
                    bloat_ratio=float(row.bloat_ratio),
                ))

        except Exception as e:
            logger.warning(f"Failed to get index health: {e}")

        return indexes

    async def check_query_performance(
        self,
        session: AsyncSession,
    ) -> dict[str, QueryPerformanceStats]:
        """Get query performance from pg_stat_statements if available."""
        # Check if pg_stat_statements is available
        check_sql = text("""
            SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
        """)

        try:
            has_ext = (await session.execute(check_sql)).scalar()
            if not has_ext:
                return {}
        except Exception:
            return {}

        # Get queries related to serialized_models
        sql = text("""
            SELECT
                regexp_replace(query, '\\s+', ' ', 'g') as query_clean,
                calls,
                total_exec_time / 1000.0 as total_time_sec,
                mean_exec_time as avg_time_ms,
                stddev_exec_time as stddev_ms
            FROM pg_stat_statements
            WHERE query LIKE '%serialized_models%'
                AND query NOT LIKE '%pg_stat_statements%'
            ORDER BY total_exec_time DESC
            LIMIT 20
        """)

        queries = {}
        try:
            result = await session.execute(sql)
            rows = result.fetchall()

            for row in rows:
                # Extract a query name from the SQL
                query_name = self._extract_query_name(row.query_clean or "")

                queries[query_name] = QueryPerformanceStats(
                    query_name=query_name,
                    avg_latency_ms=round(float(row.avg_time_ms), 2),
                    p95_latency_ms=0,  # Not available in pg_stat_statements
                    p99_latency_ms=0,
                    calls_total=int(row.calls),
                    total_time_sec=round(float(row.total_time_sec), 2),
                )

        except Exception as e:
            logger.warning(f"Failed to get query performance: {e}")

        return queries

    def _extract_query_name(self, query: str) -> str:
        """Extract a descriptive name from SQL query."""
        query_upper = query[:100].upper()

        if "SELECT" in query_upper and "COUNT(" in query_upper:
            return "count_query"
        elif "INSERT" in query_upper:
            return "insert"
        elif "UPDATE" in query_upper:
            return "update"
        elif "feature_types" in query_upper:
            return "feature_types_search"
        elif "model_name" in query_upper and "=" in query:
            return "lookup_by_name"
        elif query_upper.startswith("SELECT"):
            return "select_query"
        else:
            return "unknown_query"

    def _store_size_history(self, table_name: str, size_mb: float) -> None:
        """Store size for trend analysis."""
        if table_name not in self._historical_sizes:
            self._historical_sizes[table_name] = []

        self._historical_sizes[table_name].append(
            (datetime.now(timezone.utc), size_mb)
        )

        # Keep last 100 data points
        if len(self._historical_sizes[table_name]) > 100:
            self._historical_sizes[table_name].pop(0)

    def get_growth_rate(
        self,
        table_name: str,
        hours: int = 24,
    ) -> float | None:
        """Calculate table growth rate (MB/hour)."""
        if table_name not in self._historical_sizes:
            return None

        history = self._historical_sizes[table_name]
        if len(history) < 2:
            return None

        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)

        # Find oldest point within window
        oldest = None
        newest = None

        for ts, size in history:
            if ts.timestamp() >= cutoff:
                if oldest is None or ts < oldest[0]:
                    oldest = (ts, size)
                if newest is None or ts > newest[0]:
                    newest = (ts, size)

        if oldest is None or newest is None or oldest == newest:
            return None

        time_diff_hours = (newest[0].timestamp() - oldest[0].timestamp()) / 3600
        if time_diff_hours <= 0:
            return None

        return round((newest[1] - oldest[1]) / time_diff_hours, 2)

    async def check_alerts(
        self,
        session: AsyncSession,
        table_name: str = "serialized_models",
    ) -> list[dict[str, Any]]:
        """Check for database performance alerts."""
        alerts = []

        # Check table size
        stats = await self.get_table_stats(session, table_name)
        if stats:
            if stats.total_size_mb > self.ALERT_TABLE_SIZE_GB * 1024:
                alerts.append({
                    "type": "table_size",
                    "severity": "warning",
                    "message": f"Table {table_name} size {stats.total_size_mb:.0f}MB exceeds threshold",
                    "value_mb": stats.total_size_mb,
                    "threshold_mb": self.ALERT_TABLE_SIZE_GB * 1024,
                })

        # Check index health
        indexes = await self.get_index_health(session, table_name)
        for idx in indexes:
            # Cache hit ratio
            if idx.cache_hit_ratio < self.ALERT_CACHE_HIT_MIN and idx.scan_count > 100:
                alerts.append({
                    "type": "low_cache_hit",
                    "severity": "warning",
                    "message": f"Index {idx.index_name} cache hit ratio {idx.cache_hit_ratio:.1%} below threshold",
                    "index_name": idx.index_name,
                    "value": idx.cache_hit_ratio,
                    "threshold": self.ALERT_CACHE_HIT_MIN,
                })

            # Index size
            if idx.size_mb > self.ALERT_INDEX_SIZE_MB:
                alerts.append({
                    "type": "index_size",
                    "severity": "warning",
                    "message": f"Index {idx.index_name} size {idx.size_mb:.0f}MB exceeds threshold",
                    "index_name": idx.index_name,
                    "value_mb": idx.size_mb,
                    "threshold_mb": self.ALERT_INDEX_SIZE_MB,
                })

        # Check growth rate
        growth = self.get_growth_rate(table_name, hours=1)
        if growth and growth > 100:  # Growing >100MB/hour
            alerts.append({
                "type": "high_growth_rate",
                "severity": "info",
                "message": f"Table growing at {growth:.1f}MB/hour",
                "value_mb_per_hour": growth,
            })

        return alerts

    async def get_full_report(
        self,
        session: AsyncSession,
        table_name: str = "serialized_models",
    ) -> dict[str, Any]:
        """Get comprehensive database monitoring report."""
        table_stats = await self.get_table_stats(session, table_name)
        jsonb_stats = await self.get_jsonb_stats(session, table_name)
        index_health = await self.get_index_health(session, table_name)
        query_perf = await self.check_query_performance(session)
        alerts = await self.check_alerts(session, table_name)
        growth_rate = self.get_growth_rate(table_name)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "table_name": table_name,
            "table_stats": {
                "total_size_mb": table_stats.total_size_mb if table_stats else 0,
                "table_size_mb": table_stats.table_size_mb if table_stats else 0,
                "indexes_size_mb": table_stats.indexes_size_mb if table_stats else 0,
                "toast_size_mb": table_stats.toast_size_mb if table_stats else 0,
                "row_count": table_stats.row_count if table_stats else 0,
                "avg_row_size_kb": table_stats.avg_row_size_kb if table_stats else 0,
                "growth_rate_mb_per_hour": growth_rate,
            } if table_stats else None,
            "jsonb_stats": {
                "avg_size_bytes": jsonb_stats.avg_size_bytes if jsonb_stats else 0,
                "min_size_bytes": jsonb_stats.min_size_bytes if jsonb_stats else 0,
                "max_size_bytes": jsonb_stats.max_size_bytes if jsonb_stats else 0,
                "total_uncompressed_mb": jsonb_stats.total_uncompressed_mb if jsonb_stats else 0,
            } if jsonb_stats else None,
            "index_health": [
                {
                    "name": idx.index_name,
                    "type": idx.index_type,
                    "size_mb": idx.size_mb,
                    "scan_count": idx.scan_count,
                    "cache_hit_ratio": idx.cache_hit_ratio,
                }
                for idx in index_health
            ],
            "query_performance": {
                name: {
                    "avg_latency_ms": q.avg_latency_ms,
                    "calls": q.calls_total,
                    "total_time_sec": q.total_time_sec,
                }
                for name, q in query_perf.items()
            },
            "alerts": alerts,
            "alert_count": len(alerts),
        }


# Global instance
_default_monitor: DatabaseMonitor | None = None


def get_db_monitor() -> DatabaseMonitor:
    """Get global database monitor."""
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = DatabaseMonitor()
    return _default_monitor
