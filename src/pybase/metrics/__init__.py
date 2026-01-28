"""Prometheus metrics for PyBase."""

from prometheus_client import Counter, Histogram

# API request counter - tracks total number of API requests
# Labels: method (HTTP method), endpoint (API path), status (HTTP status code)
api_request_counter = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

# API latency histogram - tracks request duration in seconds
# Labels: method (HTTP method), endpoint (API path)
# Buckets: common latency thresholds (ms converted to seconds)
api_latency_histogram = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

# CAD extraction task counter
extraction_task_counter = Counter(
    "extraction_tasks_total",
    "Total number of CAD extraction tasks",
    ["task_type", "status"],
)

# CAD extraction duration histogram
extraction_duration_histogram = Histogram(
    "extraction_duration_seconds",
    "CAD extraction task duration in seconds",
    ["task_type"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

# Active WebSocket connections
websocket_connections_gauge = Histogram(
    "websocket_connections_active",
    "Number of active WebSocket connections",
    buckets=(10, 50, 100, 500, 1000),
)

# Database query metrics
db_query_duration_histogram = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Cache operation metrics
cache_operation_counter = Counter(
    "cache_operations_total",
    "Total number of cache operations",
    ["operation", "status"],
)

__all__ = [
    "api_request_counter",
    "api_latency_histogram",
    "extraction_task_counter",
    "extraction_duration_histogram",
    "websocket_connections_gauge",
    "db_query_duration_histogram",
    "cache_operation_counter",
]
