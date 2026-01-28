"""Prometheus metrics for PyBase workers."""

from prometheus_client import Counter, Histogram, Gauge

# Task counter - tracks total number of tasks processed by workers
# Labels: task_type (e.g., extraction, search, report), status (success, failure, retry)
task_counter = Counter(
    "worker_tasks_total",
    "Total number of tasks processed by workers",
    ["task_type", "status"],
)

# Task duration histogram - tracks task execution time in seconds
# Labels: task_type (e.g., extraction, search, report)
# Buckets: common task duration thresholds
task_duration = Histogram(
    "worker_task_duration_seconds",
    "Worker task execution duration in seconds",
    ["task_type"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0),
)

# Task retry counter - tracks number of task retries
# Labels: task_type, reason (e.g., timeout, error, rate_limit)
task_retry_counter = Counter(
    "worker_task_retries_total",
    "Total number of task retries",
    ["task_type", "reason"],
)

# Queue size gauge - tracks current number of tasks in queue
# Labels: queue_name (e.g., extraction, search, reports)
queue_size_gauge = Gauge(
    "worker_queue_size",
    "Current number of tasks in worker queue",
    ["queue_name"],
)

# Active workers gauge - tracks number of active worker processes
active_workers_gauge = Gauge(
    "worker_processes_active",
    "Number of active worker processes",
)

# Task failure counter - tracks task failures with error types
# Labels: task_type, error_type
task_failure_counter = Counter(
    "worker_task_failures_total",
    "Total number of task failures",
    ["task_type", "error_type"],
)

# Worker memory usage gauge - tracks memory consumption per worker
# Labels: worker_type
worker_memory_gauge = Gauge(
    "worker_memory_bytes",
    "Worker memory usage in bytes",
    ["worker_type"],
)

# Database operation duration for workers
worker_db_duration = Histogram(
    "worker_db_operation_duration_seconds",
    "Worker database operation duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

__all__ = [
    "task_counter",
    "task_duration",
    "task_retry_counter",
    "queue_size_gauge",
    "active_workers_gauge",
    "task_failure_counter",
    "worker_memory_gauge",
    "worker_db_duration",
]
