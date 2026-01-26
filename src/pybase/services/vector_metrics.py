"""
Vector search metrics collection for CAD retrieval.

Tracks query latency, recall@k, cache hit rate, index health,
and exports metrics for Prometheus or JSON consumption.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QueryMetric:
    """Single query metric record."""
    timestamp: datetime
    query_type: str
    execution_time_ms: float
    results_count: int
    cache_hit: bool
    ef_search: int | None = None
    recall_at_k: float | None = None
    query_summary: str = ""


@dataclass
class IndexHealthMetric:
    """Index health snapshot."""
    timestamp: datetime
    index_name: str
    index_size_mb: float
    cache_hit_ratio: float
    fragmentation_ratio: float
    total_rows: int
    idx_scan_count: int


@dataclass
class GPUMetric:
    """GPU usage snapshot (if available)."""
    timestamp: datetime
    gpu_id: int
    gpu_utilization: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: float | None = None
    power_draw_w: float | None = None


class VectorMetricsCollector:
    """
    Collect and aggregate vector search performance metrics.

    Metrics collected:
    - Query latency (p50, p95, p99)
    - Recall@k for quality tracking
    - Cache hit ratio
    - Index health (fragmentation, size)
    - GPU utilization (if available)

    Export formats:
    - JSON for direct consumption
    - Prometheus text format for scraping
    """

    # Alert thresholds
    ALERT_LATENCY_MS = 100.0
    ALERT_RECALL_MIN = 0.85
    ALERT_CACHE_HIT_MIN = 0.5
    ALERT_FRAGMENTATION_MAX = 0.3

    def __init__(self, max_samples: int = 10000):
        self._max_samples = max_samples

        # Query metrics
        self._query_metrics: list[QueryMetric] = []

        # Index health metrics
        self._index_health: dict[str, list[IndexHealthMetric]] = defaultdict(list)

        # GPU metrics
        self._gpu_metrics: dict[int, list[GPUMetric]] = defaultdict(list)

        # Counters
        self._counters: dict[str, int] = defaultdict(int)

    async def record_query(
        self,
        query_type: str,
        execution_time_ms: float,
        results_count: int,
        cache_hit: bool,
        ef_search: int | None = None,
        recall_at_k: float | None = None,
        query_summary: str = "",
    ) -> None:
        """Record a query metric."""
        metric = QueryMetric(
            timestamp=datetime.now(timezone.utc),
            query_type=query_type,
            execution_time_ms=execution_time_ms,
            results_count=results_count,
            cache_hit=cache_hit,
            ef_search=ef_search,
            recall_at_k=recall_at_k,
            query_summary=query_summary,
        )

        self._query_metrics.append(metric)
        self._counters["total_queries"] += 1
        self._counters[f"query_type_{query_type}"] += 1

        if cache_hit:
            self._counters["cache_hits"] += 1
        else:
            self._counters["cache_misses"] += 1

        # Trim if needed
        if len(self._query_metrics) > self._max_samples:
            self._query_metrics.pop(0)

    async def collect_index_health(self, session: AsyncSession) -> dict[str, IndexHealthMetric]:
        """Collect index health metrics from database."""
        metrics = {}

        # Get vector index statistics
        sql = text("""
            SELECT
                schemaname || '.' || indexname as index_name,
                pg_relation_size(indexrelid) / 1024.0 / 1024.0 as index_size_mb,
                COALESCE(idx_blks_hit::float / NULLIF(idx_blks_hit + idx_blks_read, 0), 0) as cache_hit_ratio,
                COALESCE(idx_tup_read::float / NULLIF(idx_tup_fetch, 0), 1) as fragmentation_ratio,
                idx_scan as scan_count
            FROM pg_statio_user_indexes
            WHERE indexname LIKE '%vector%' OR indexname LIKE '%hnsw%' OR indexname LIKE '%sdf%'
        """)

        try:
            result = await session.execute(sql)
            rows = result.fetchall()

            for row in rows:
                metric = IndexHealthMetric(
                    timestamp=datetime.now(timezone.utc),
                    index_name=row.index_name,
                    index_size_mb=float(row.index_size_mb),
                    cache_hit_ratio=float(row.cache_hit_ratio),
                    fragmentation_ratio=float(row.fragmentation_ratio),
                    total_rows=0,  # Not available in this query
                    idx_scan_count=int(row.scan_count),
                )

                metrics[row.index_name] = metric
                self._index_health[row.index_name].append(metric)

                # Trim per-index
                if len(self._index_health[row.index_name]) > 1000:
                    self._index_health[row.index_name].pop(0)

        except Exception as e:
            logger.warning(f"Failed to collect index health: {e}")

        return metrics

    async def collect_gpu_metrics(self, session: AsyncSession) -> dict[int, GPUMetric]:
        """Collect GPU metrics if pgvector-gpu is available."""
        gpu_metrics = {}

        # Check if vector_gpu extension exists
        check_sql = text("SELECT 1 FROM pg_extension WHERE extname = 'vector_gpu'")
        try:
            result = await session.execute(check_sql)
            has_gpu = result.scalar() is not None

            if not has_gpu:
                return gpu_metrics

            # Get GPU device status
            gpu_sql = text("""
                SELECT
                    device_id,
                    gpu_utilization,
                    memory_used,
                    memory_total,
                    temperature,
                    power_draw
                FROM vector_gpu_device_status()
            """)

            result = await session.execute(gpu_sql)
            rows = result.fetchall()

            for row in rows:
                metric = GPUMetric(
                    timestamp=datetime.now(timezone.utc),
                    gpu_id=int(row.device_id),
                    gpu_utilization=float(row.gpu_utilization),
                    memory_used_mb=float(row.memory_used) / 1024 / 1024,
                    memory_total_mb=float(row.memory_total) / 1024 / 1024,
                    temperature_c=float(row.temperature) if row.temperature else None,
                    power_draw_w=float(row.power_draw) if row.power_draw else None,
                )

                gpu_metrics[row.device_id] = metric
                self._gpu_metrics[row.device_id].append(metric)

                # Trim
                if len(self._gpu_metrics[row.device_id]) > 1000:
                    self._gpu_metrics[row.device_id].pop(0)

        except Exception as e:
            logger.debug(f"GPU metrics not available: {e}")

        return gpu_metrics

    def get_query_stats(self, minutes: int = 5) -> dict[str, Any]:
        """Get query statistics for recent time window."""
        cutoff = datetime.now(timezone.utc).timestamp() - (minutes * 60)

        recent = [
            m for m in self._query_metrics
            if m.timestamp.timestamp() > cutoff
        ]

        if not recent:
            return {
                "count": 0,
                "avg_latency_ms": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
                "cache_hit_rate": 0,
                "avg_recall_at_k": 0,
            }

        latencies = sorted([m.execution_time_ms for m in recent])
        cache_hits = sum(1 for m in recent if m.cache_hit)

        recalls = [m.recall_at_k for m in recent if m.recall_at_k is not None]
        avg_recall = sum(recalls) / len(recalls) if recalls else 0

        n = len(latencies)
        return {
            "count": n,
            "avg_latency_ms": round(sum(latencies) / n, 2),
            "p50_latency_ms": round(latencies[n // 2], 2),
            "p95_latency_ms": round(latencies[int(n * 0.95)] if n > 20 else latencies[-1], 2),
            "p99_latency_ms": round(latencies[int(n * 0.99)] if n > 100 else latencies[-1], 2),
            "cache_hit_rate": round(cache_hits / n, 3) if n > 0 else 0,
            "avg_recall_at_k": round(avg_recall, 3),
            "queries_by_type": self._get_query_type breakdown(recent),
        }

    def _get_query_type_breakdown(self, metrics: list[QueryMetric]) -> dict[str, int]:
        """Get count of queries by type."""
        counts: dict[str, int] = defaultdict(int)
        for m in metrics:
            counts[m.query_type] += 1
        return dict(counts)

    def get_index_health(self) -> dict[str, Any]:
        """Get current index health summary."""
        summary = {}

        for index_name, metrics in self._index_health.items():
            if not metrics:
                continue

            latest = metrics[-1]
            summary[index_name] = {
                "size_mb": round(latest.index_size_mb, 2),
                "cache_hit_ratio": round(latest.cache_hit_ratio, 3),
                "fragmentation_ratio": round(latest.fragmentation_ratio, 3),
                "scan_count": latest.idx_scan_count,
                "needs_rebuild": latest.fragmentation_ratio > self.ALERT_FRAGMENTATION_MAX,
            }

        return summary

    def get_gpu_stats(self) -> dict[str, Any]:
        """Get current GPU stats summary."""
        summary = {}

        for gpu_id, metrics in self._gpu_metrics.items():
            if not metrics:
                continue

            latest = metrics[-1]
            summary[f"gpu_{gpu_id}"] = {
                "utilization_percent": round(latest.gpu_utilization, 1),
                "memory_used_mb": round(latest.memory_used_mb, 1),
                "memory_total_mb": round(latest.memory_total_mb, 1),
                "memory_usage_percent": round(
                    latest.memory_used_mb / latest.memory_total_mb * 100, 1
                ) if latest.memory_total_mb > 0 else 0,
                "temperature_c": latest.temperature_c,
                "power_draw_w": latest.power_draw_w,
            }

        return summary

    def check_alerts(self) -> list[dict[str, Any]]:
        """Check if any metrics exceed alert thresholds."""
        alerts = []
        stats = self.get_query_stats()

        # High latency alert
        if stats["p95_latency_ms"] > self.ALERT_LATENCY_MS:
            alerts.append({
                "type": "high_latency",
                "severity": "warning",
                "message": f"P95 latency {stats['p95_latency_ms']}ms exceeds threshold",
                "value": stats["p95_latency_ms"],
                "threshold": self.ALERT_LATENCY_MS,
            })

        # Low recall alert
        if stats["avg_recall_at_k"] < self.ALERT_RECALL_MIN and stats["avg_recall_at_k"] > 0:
            alerts.append({
                "type": "low_recall",
                "severity": "critical",
                "message": f"Recall@K {stats['avg_recall_at_k']:.1%} below threshold",
                "value": stats["avg_recall_at_k"],
                "threshold": self.ALERT_RECALL_MIN,
            })

        # Low cache hit rate
        if stats["cache_hit_rate"] < self.ALERT_CACHE_HIT_MIN and stats["count"] > 10:
            alerts.append({
                "type": "low_cache_hit",
                "severity": "info",
                "message": f"Cache hit rate {stats['cache_hit_rate']:.1%} below threshold",
                "value": stats["cache_hit_rate"],
                "threshold": self.ALERT_CACHE_HIT_MIN,
            })

        # Index fragmentation alerts
        for index_name, health in self.get_index_health().items():
            if health.get("needs_rebuild"):
                alerts.append({
                    "type": "index_fragmentation",
                    "severity": "warning",
                    "message": f"Index {index_name} fragmented ({health['fragmentation_ratio']:.1%})",
                    "index_name": index_name,
                    "value": health["fragmentation_ratio"],
                    "threshold": self.ALERT_FRAGMENTATION_MAX,
                })

        return alerts

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        stats = self.get_query_stats()
        index_health = self.get_index_health()
        gpu_stats = self.get_gpu_stats()

        # Query metrics
        lines.append(f"# HELP vector_query_latency_ms Query latency in milliseconds")
        lines.append(f"# TYPE vector_query_latency_ms gauge")
        lines.append(f"vector_query_latency_ms {{percentile=\"p50\"}} {stats['p50_latency_ms']}")
        lines.append(f"vector_query_latency_ms {{percentile=\"p95\"}} {stats['p95_latency_ms']}")
        lines.append(f"vector_query_latency_ms {{percentile=\"p99\"}} {stats['p99_latency_ms']}")

        lines.append(f"# HELP vector_query_count_total Total query count")
        lines.append(f"# TYPE vector_query_count_total counter")
        lines.append(f"vector_query_count_total {stats['count']}")

        lines.append(f"# HELP vector_cache_hit_ratio Cache hit rate")
        lines.append(f"# TYPE vector_cache_hit_ratio gauge")
        lines.append(f"vector_cache_hit_ratio {stats['cache_hit_rate']}")

        lines.append(f"# HELP vector_recall_at_k Average recall@k")
        lines.append(f"# TYPE vector_recall_at_k gauge")
        lines.append(f"vector_recall_at_k {stats['avg_recall_at_k']}")

        # Index metrics
        lines.append(f"# HELP vector_index_size_mb Index size in MB")
        lines.append(f"# TYPE vector_index_size_mb gauge")
        for index_name, health in index_health.items():
            safe_name = index_name.replace(".", "_").replace("-", "_")
            lines.append(f'vector_index_size_mb{{index="{safe_name}"}} {health["size_mb"]}')

        lines.append(f"# HELP vector_index_cache_hit_ratio Index cache hit ratio")
        lines.append(f"# TYPE vector_index_cache_hit_ratio gauge")
        for index_name, health in index_health.items():
            safe_name = index_name.replace(".", "_").replace("-", "_")
            lines.append(f'vector_index_cache_hit_ratio{{index="{safe_name}"}} {health["cache_hit_ratio"]}')

        # GPU metrics
        lines.append(f"# HELP vector_gpu_utilization_percent GPU utilization")
        lines.append(f"# TYPE vector_gpu_utilization_percent gauge")
        for gpu_name, stats in gpu_stats.items():
            lines.append(f'vector_gpu_utilization_percent{{gpu="{gpu_name}"}} {stats["utilization_percent"]}')

        lines.append(f"# HELP vector_gpu_memory_usage_percent GPU memory usage")
        lines.append(f"# TYPE vector_gpu_memory_usage_percent gauge")
        for gpu_name, stats in gpu_stats.items():
            lines.append(f'vector_gpu_memory_usage_percent{{gpu="{gpu_name}"}} {stats["memory_usage_percent"]}')

        return "\n".join(lines) + "\n"

    def export_json(self) -> dict[str, Any]:
        """Export all metrics as JSON."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query_stats": self.get_query_stats(),
            "index_health": self.get_index_health(),
            "gpu_stats": self.get_gpu_stats(),
            "alerts": self.check_alerts(),
            "counters": dict(self._counters),
        }

    def reset(self) -> None:
        """Reset all collected metrics."""
        self._query_metrics.clear()
        self._index_health.clear()
        self._gpu_metrics.clear()
        self._counters.clear()


# Global metrics instance
_default_collector: VectorMetricsCollector | None = None


def get_vector_metrics_collector() -> VectorMetricsCollector:
    """Get global vector metrics collector."""
    global _default_collector
    if _default_collector is None:
        _default_collector = VectorMetricsCollector()
    return _default_collector
