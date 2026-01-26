"""
Serialization metrics collection for master serialization pipeline.

Tracks:
- Models processed (total, by type, by status)
- Processing time (avg, p50, p95, p99)
- Success/failure rate
- Quality metrics (element_coverage, unrecoverable_unknown)
- Progress tracking for batch jobs
Exports metrics for dashboard consumption.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SerializationMetric:
    """Single serialization operation metric."""
    timestamp: datetime
    model_name: str
    model_type: str  # 'part' or 'assembly'
    status: str  # 'success', 'failed', 'partial'
    processing_time_sec: float
    element_coverage: float | None = None  # % of features with elements
    unrecoverable_unknown: int | None = None
    feature_count: int | None = None
    error_message: str | None = None
    category: str | None = None
    tags: list[str] | None = None


@dataclass
class BatchProgress:
    """Progress tracking for batch serialization jobs."""
    batch_id: str
    started_at: datetime
    total_models: int
    processed_models: int
    successful_models: int
    failed_models: int
    avg_time_per_model: float
    estimated_completion: datetime | None = None


class SerializeMetricsCollector:
    """
    Collect and aggregate serialization pipeline metrics.

    Metrics collected:
    - Total models processed
    - Processing time percentiles
    - Success/failure rate
    - Quality metrics (element_coverage, unrecoverable_unknown)
    - Category/tag breakdown
    - Batch job progress

    Export formats:
    - JSON for dashboard
    - Summary statistics
    """

    # Quality thresholds
    MIN_ELEMENT_COVERAGE = 80.0  # Below this = warning
    CRITICAL_ELEMENT_COVERAGE = 50.0  # Below this = critical

    def __init__(self, max_samples: int = 50000):
        self._max_samples = max_samples
        self._metrics: list[SerializationMetric] = []
        self._batch_jobs: dict[str, BatchProgress] = {}
        self._counters: dict[str, int] = defaultdict(int)

    async def record_serialization(
        self,
        model_name: str,
        model_type: str,
        status: str,
        processing_time_sec: float,
        element_coverage: float | None = None,
        unrecoverable_unknown: int | None = None,
        feature_count: int | None = None,
        error_message: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        """Record a serialization operation metric."""
        metric = SerializationMetric(
            timestamp=datetime.now(timezone.utc),
            model_name=model_name,
            model_type=model_type,
            status=status,
            processing_time_sec=processing_time_sec,
            element_coverage=element_coverage,
            unrecoverable_unknown=unrecoverable_unknown,
            feature_count=feature_count,
            error_message=error_message,
            category=category,
            tags=tags,
        )

        self._metrics.append(metric)
        self._counters["total_serializations"] += 1
        self._counters[f"status_{status}"] += 1
        self._counters[f"type_{model_type}"] += 1

        if category:
            self._counters[f"category_{category}"] += 1

        # Trim if needed
        if len(self._metrics) > self._max_samples:
            self._metrics.pop(0)

    def start_batch_job(
        self,
        batch_id: str,
        total_models: int,
    ) -> BatchProgress:
        """Start tracking a new batch job."""
        job = BatchProgress(
            batch_id=batch_id,
            started_at=datetime.now(timezone.utc),
            total_models=total_models,
            processed_models=0,
            successful_models=0,
            failed_models=0,
            avg_time_per_model=0.0,
        )
        self._batch_jobs[batch_id] = job
        return job

    def update_batch_job(
        self,
        batch_id: str,
        processed: int,
        successful: int,
        failed: int,
    ) -> BatchProgress | None:
        """Update batch job progress."""
        job = self._batch_jobs.get(batch_id)
        if not job:
            return None

        job.processed_models = processed
        job.successful_models = successful
        job.failed_models = failed

        # Calculate avg time
        elapsed = (datetime.now(timezone.utc) - job.started_at).total_seconds()
        if processed > 0:
            job.avg_time_per_model = elapsed / processed

            # Estimate completion
            remaining = job.total_models - processed
            if job.avg_time_per_model > 0:
                eta_seconds = remaining * job.avg_time_per_model
                job.estimated_completion = datetime.now(timezone.utc) + timedelta(seconds=eta_seconds)

        return job

    def get_batch_job(self, batch_id: str) -> BatchProgress | None:
        """Get batch job progress."""
        return self._batch_jobs.get(batch_id)

    def get_stats(self, minutes: int = 60) -> dict[str, Any]:
        """Get serialization statistics for recent time window."""
        cutoff = datetime.now(timezone.utc).timestamp() - (minutes * 60)

        recent = [
            m for m in self._metrics
            if m.timestamp.timestamp() > cutoff
        ]

        if not recent:
            return self._empty_stats()

        # Basic counts
        total = len(recent)
        successful = sum(1 for m in recent if m.status == "success")
        failed = sum(1 for m in recent if m.status == "failed")
        partial = sum(1 for m in recent if m.status == "partial")

        # Timing stats
        times = sorted([m.processing_time_sec for m in recent])
        n = len(times)

        # Quality stats (for successful/partial with quality data)
        quality_metrics = [m for m in recent if m.element_coverage is not None]
        coverages = [m.element_coverage for m in quality_metrics] if quality_metrics else []
        avg_coverage = sum(coverages) / len(coverages) if coverages else 0

        unrecoverable_counts = [
            m.unrecoverable_unknown or 0
            for m in recent
            if m.unrecoverable_unknown is not None
        ]
        avg_unrecoverable = sum(unrecoverable_counts) / len(unrecoverable_counts) if unrecoverable_counts else 0

        # By type
        by_type = defaultdict(lambda: {"count": 0, "success": 0, "failed": 0})
        for m in recent:
            by_type[m.model_type]["count"] += 1
            if m.status == "success":
                by_type[m.model_type]["success"] += 1
            elif m.status == "failed":
                by_type[m.model_type]["failed"] += 1

        # By category
        by_category = defaultdict(lambda: {"count": 0, "success": 0})
        for m in recent:
            if m.category:
                by_category[m.category]["count"] += 1
                if m.status == "success":
                    by_category[m.category]["success"] += 1

        # Calculate throughput
        elapsed_window_sec = minutes * 60
        throughput_per_hour = (total / elapsed_window_sec) * 3600 if elapsed_window_sec > 0 else 0

        return {
            "time_window_minutes": minutes,
            "total_processed": total,
            "successful": successful,
            "failed": failed,
            "partial": partial,
            "success_rate": round(successful / total, 3) if total > 0 else 0,
            "throughput_per_hour": round(throughput_per_hour, 1),
            "timing": {
                "avg_sec": round(sum(times) / n, 2),
                "p50_sec": round(times[n // 2], 2),
                "p95_sec": round(times[int(n * 0.95)] if n > 20 else times[-1], 2),
                "p99_sec": round(times[int(n * 0.99)] if n > 100 else times[-1], 2),
                "min_sec": round(times[0], 2),
                "max_sec": round(times[-1], 2),
            },
            "quality": {
                "avg_element_coverage": round(avg_coverage, 1),
                "models_with_quality_data": len(quality_metrics),
                "avg_unrecoverable_unknown": round(avg_unrecoverable, 1),
                "low_quality_count": sum(1 for c in coverages if c < self.MIN_ELEMENT_COVERAGE),
                "critical_quality_count": sum(1 for c in coverages if c < self.CRITICAL_ELEMENT_COVERAGE),
            },
            "by_type": dict(by_type),
            "by_category": dict(by_category),
            "recent_errors": [
                {"model": m.model_name, "error": m.error_message, "time": m.timestamp.isoformat()}
                for m in recent
                if m.error_message and m.status == "failed"
            ][:10],
        }

    def _empty_stats(self) -> dict[str, Any]:
        """Return empty stats structure."""
        return {
            "time_window_minutes": 60,
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "partial": 0,
            "success_rate": 0,
            "throughput_per_hour": 0,
            "timing": {
                "avg_sec": 0,
                "p50_sec": 0,
                "p95_sec": 0,
                "p99_sec": 0,
                "min_sec": 0,
                "max_sec": 0,
            },
            "quality": {
                "avg_element_coverage": 0,
                "models_with_quality_data": 0,
                "avg_unrecoverable_unknown": 0,
                "low_quality_count": 0,
                "critical_quality_count": 0,
            },
            "by_type": {},
            "by_category": {},
            "recent_errors": [],
        }

    async def get_db_snapshot(
        self,
        session: AsyncSession,
    ) -> dict[str, Any]:
        """Get current state of serialized_models table."""
        result = {}

        # Check if table exists
        check_sql = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'serialized_models'
            )
        """)
        try:
            table_exists = (await session.execute(check_sql)).scalar()
            if not table_exists:
                return {"error": "serialized_models table does not exist"}
        except Exception as e:
            return {"error": f"Failed to check table: {e}"}

        # Get counts
        count_sql = text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE model_type = 'part') as parts,
                COUNT(*) FILTER (WHERE model_type = 'assembly') as assemblies,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as last_hour,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h
            FROM serialized_models
        """)
        try:
            row = (await session.execute(count_sql)).fetchone()
            if row:
                result["counts"] = {
                    "total": row.total or 0,
                    "parts": row.parts or 0,
                    "assemblies": row.assemblies or 0,
                    "last_hour": row.last_hour or 0,
                    "last_24h": row.last_24h or 0,
                }
        except Exception as e:
            logger.warning(f"Failed to get counts: {e}")

        # Get quality stats
        quality_sql = text("""
            SELECT
                AVG(
                    (serialized_content->>'element_coverage')::float
                ) as avg_coverage,
                AVG(
                    (serialized_content->>'unrecoverable_unknown')::int
                ) as avg_unknown,
                COUNT(*) FILTER (
                    WHERE (serialized_content->>'element_coverage')::float < 80
                ) as low_quality
            FROM serialized_models
            WHERE serialized_content ? 'element_coverage'
        """)
        try:
            row = (await session.execute(quality_sql)).fetchone()
            if row and row.avg_coverage is not None:
                result["quality_from_db"] = {
                    "avg_element_coverage": round(float(row.avg_coverage), 1),
                    "avg_unrecoverable_unknown": round(float(row.avg_unknown or 0), 1),
                    "low_quality_count": row.low_quality or 0,
                }
        except Exception as e:
            logger.warning(f"Failed to get quality stats: {e}")

        # Get category breakdown
        category_sql = text("""
            SELECT
                category,
                COUNT(*) as count,
                AVG(feature_count) as avg_features
            FROM serialized_models
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            LIMIT 20
        """)
        try:
            rows = (await session.execute(category_sql)).fetchall()
            result["categories"] = [
                {"category": row.category, "count": row.count, "avg_features": round(row.avg_features or 0, 1)}
                for row in rows
            ]
        except Exception as e:
            logger.warning(f"Failed to get categories: {e}")

        # Get recent activity
        recent_sql = text("""
            SELECT
                model_name,
                model_type,
                feature_count,
                (serialized_content->>'element_coverage')::float as coverage,
                created_at
            FROM serialized_models
            ORDER BY created_at DESC
            LIMIT 10
        """)
        try:
            rows = (await session.execute(recent_sql)).fetchall()
            result["recent_models"] = [
                {
                    "model_name": row.model_name,
                    "model_type": row.model_type,
                    "feature_count": row.feature_count,
                    "element_coverage": round(float(row.coverage), 1) if row.coverage else None,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning(f"Failed to get recent models: {e}")

        return result

    def export_json(self) -> dict[str, Any]:
        """Export all metrics as JSON."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": self.get_stats(),
            "batch_jobs": {
                batch_id: {
                    "total": job.total_models,
                    "processed": job.processed_models,
                    "successful": job.successful_models,
                    "failed": job.failed_models,
                    "progress_pct": round(job.processed_models / job.total_models * 100, 1) if job.total_models > 0 else 0,
                    "avg_time_sec": round(job.avg_time_per_model, 2),
                    "estimated_completion": job.estimated_completion.isoformat() if job.estimated_completion else None,
                }
                for batch_id, job in self._batch_jobs.items()
            },
            "counters": dict(self._counters),
        }

    def reset(self) -> None:
        """Reset all collected metrics."""
        self._metrics.clear()
        self._batch_jobs.clear()
        self._counters.clear()


# Global instance
_default_collector: SerializeMetricsCollector | None = None


def get_serialize_metrics_collector() -> SerializeMetricsCollector:
    """Get global serialization metrics collector."""
    global _default_collector
    if _default_collector is None:
        _default_collector = SerializeMetricsCollector()
    return _default_collector
