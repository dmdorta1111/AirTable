# Monitoring Stack

## Overview
PyBase implements comprehensive monitoring using Prometheus and Grafana to track application performance, resource utilization, and business metrics. The monitoring stack provides real-time visibility into API performance, CAD extraction tasks, database operations, and system health.

## Technology Stack
- **Metrics Collection**: Prometheus (time-series database)
- **Visualization**: Grafana (dashboarding and alerting)
- **Metrics Format**: Prometheus exposition format
- **Client Library**: prometheus_client for Python
- **Deployment**: Docker Compose with persistent storage

## Architecture

### Monitoring Components
```mermaid
graph TD
    API[FastAPI Backend]
    Worker[Celery Workers]
    Metrics[Prometheus Middleware]
    Endpoint[/metrics Endpoint]
    Prometheus[Prometheus Server]
    Grafana[Grafana Dashboards]
    AlertManager[Alert Manager]

    API --> Metrics
    Metrics --> Endpoint
    Worker --> Metrics
    Endpoint --> Prometheus
    Prometheus --> Grafana
    Prometheus --> AlertManager
```

### Data Flow
1. **Metrics Collection**: Application code and middleware collect metrics using prometheus_client
2. **Metrics Exposition**: /metrics endpoint exposes metrics in Prometheus text format
3. **Scraping**: Prometheus scrapes metrics from all targets every 15 seconds
4. **Storage**: Prometheus stores time-series data locally
5. **Visualization**: Grafana queries Prometheus for dashboard rendering
6. **Alerting**: Prometheus evaluates alert rules and triggers notifications

## Metrics Categories

### Application Metrics

#### API Performance Metrics
- **http_requests_total**: Total HTTP requests count
  - Labels: `method`, `endpoint`, `status`
  - Use case: Track request volume and error rates
- **http_request_duration_seconds**: API request latency histogram
  - Labels: `method`, `endpoint`
  - Buckets: 5ms, 10ms, 25ms, 50ms, 75ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s, 7.5s, 10s
  - Use case: Monitor API response times, identify slow endpoints

#### CAD Extraction Metrics
- **extraction_tasks_total**: Total extraction tasks count
  - Labels: `task_type` (pdf, dxf, ifc, step), `status` (success, failure)
  - Use case: Track extraction volume and success rates
- **extraction_duration_seconds**: Extraction task duration histogram
  - Labels: `task_type`
  - Buckets: 1s, 5s, 10s, 30s, 1m, 2m, 5m, 10m
  - Use case: Monitor extraction performance, identify slow files

#### Database Metrics
- **db_query_duration_seconds**: Database query duration histogram
  - Labels: `operation` (select, insert, update, delete)
  - Buckets: 1ms, 5ms, 10ms, 25ms, 50ms, 100ms, 250ms, 500ms, 1s, 2.5s, 5s
  - Use case: Identify slow database queries

#### Cache Metrics
- **cache_operations_total**: Cache operation counter
  - Labels: `operation` (get, set, delete), `status` (hit, miss)
  - Use case: Monitor cache effectiveness

#### Real-time Metrics
- **websocket_connections_active**: Active WebSocket connections gauge
  - Buckets: 10, 50, 100, 500, 1000
  - Use case: Track real-time connection load

### Infrastructure Metrics
Prometheus also collects standard metrics from:
- **PostgreSQL**: Connection counts, query performance, replication lag
- **Redis**: Memory usage, hit rates, connection counts
- **Container Resources**: CPU, memory, disk I/O (via cAdvisor)

## Grafana Dashboards

### Available Dashboards

#### 1. Overview Dashboard
**Location**: `monitoring/grafana-dashboards/overview.json`
- System health at a glance
- Request rate and error rate
- Active WebSocket connections
- Database and cache health
- Extraction task throughput

#### 2. API Performance Dashboard
**Location**: `monitoring/grafana-dashboards/api-performance.json`
- Request rate by endpoint
- Response time percentiles (p50, p95, p99)
- Error rate breakdown
- Slowest endpoints
- Traffic patterns over time

#### 3. Celery Workers Dashboard
**Location**: `monitoring/grafana-dashboards/celery-workers.json`
- Task throughput by type
- Task duration percentiles
- Task failure rates
- Worker queue depth
- Task retry statistics

#### 4. Database & Redis Dashboard
**Location**: `monitoring/grafana-dashboards/database-redis.json`
- PostgreSQL connection pool usage
- Query performance metrics
- Cache hit/miss ratios
- Redis memory usage
- Slow query log

## Alerting Rules

### High Error Rate Alerts
**File**: `monitoring/alerts/high-error-rate.yml`

Triggers when:
- API error rate exceeds 5% for 5 minutes
- Extraction task failure rate exceeds 10% for 10 minutes
- Database query error rate exceeds 1% for 5 minutes

### Slow Task Alerts
**File**: `monitoring/alerts/slow-tasks.yml`

Triggers when:
- API p95 latency exceeds 1 second for 5 minutes
- CAD extraction tasks exceed 10 minutes
- Database query p95 exceeds 500ms for 5 minutes

### Resource Exhaustion Alerts
**File**: `monitoring/alerts/resource-exhaustion.yml`

Triggers when:
- PostgreSQL connection pool exceeds 90% capacity
- Redis memory usage exceeds 80%
- Disk space below 10% free
- WebSocket connections exceed 1000

## Configuration

### Prometheus Configuration
**File**: `monitoring/prometheus.yml`

Key settings:
- **Scrape Interval**: 15 seconds
- **Retention Period**: 15 days
- **Targets**:
  - FastAPI Backend: `http://backend:8000/api/v1/metrics`
  - Extraction Worker: `http://extraction-worker:9090/metrics`
  - Search Worker: `http://search-worker:9091/metrics`
  - PostgreSQL: `postgres_exporter:9187`
  - Redis: `redis_exporter:9121`

### Application Configuration
**File**: `src/pybase/core/config.py`

```python
# Prometheus settings
prometheus_enabled: bool = True
prometheus_multiproc_dir: str = "/tmp/prometheus"
```

### Environment Variables
```bash
# Enable/disable metrics
PROMETHEUS_ENABLED=true

# Metrics endpoint (configured in API)
METRICS_ENDPOINT=/api/v1/metrics
```

## Accessing Monitoring Tools

### Prometheus UI
- **URL**: http://localhost:9090
- **Features**:
  - Query metrics with PromQL
  - View targets and their health
  - Inspect alert rules
  - Check configuration

### Grafana Dashboards
- **URL**: http://localhost:3000
- **Default Credentials**: `admin/admin` (change on first login)
- **Data Source**: Prometheus at `http://prometheus:9090`
- **Dashboards**: Pre-imported from `monitoring/grafana-dashboards/`

### Metrics Endpoint
- **Backend**: http://localhost:8000/api/v1/metrics
- **Extraction Worker**: http://localhost:9090/metrics
- **Search Worker**: http://localhost:9091/metrics

## Integration with Existing Infrastructure

### Docker Compose Integration
The monitoring stack integrates with existing services:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/alerts:/etc/prometheus/alerts:ro
      - prometheus-data:/prometheus

  grafana:
    image: grafana/grafana:latest
    volumes:
      - ./monitoring/grafana-dashboards:/etc/grafana/provisioning/dashboards:ro
      - grafana-data:/var/lib/grafana
```

### Middleware Integration
Prometheus middleware automatically tracks all HTTP requests:

```python
from pybase.middleware.prometheus_middleware import PrometheusMiddleware

app.add_middleware(PrometheusMiddleware)
```

### Custom Metrics
Add custom metrics in your code:

```python
from pybase.metrics import extraction_task_counter

# Track a task completion
extraction_task_counter.labels(
    task_type="dxf",
    status="success"
).inc()
```

## Querying Metrics

### Common PromQL Queries

**Request rate by endpoint:**
```promql
rate(http_requests_total{status!~"5.."}[5m])
```

**P95 latency:**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Error rate:**
```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
```

**Extraction success rate:**
```promql
sum(rate(extraction_tasks_total{status="success"}[5m])) / sum(rate(extraction_tasks_total[5m]))
```

**Cache hit ratio:**
```promql
sum(rate(cache_operations_total{status="hit"}[5m])) / sum(rate(cache_operations_total[5m]))
```

## Troubleshooting

### Metrics Not Appearing

1. **Check if Prometheus is running:**
   ```bash
   docker ps | grep prometheus
   ```

2. **Verify target health:**
   - Go to http://localhost:9090/targets
   - Ensure all targets show "UP" state

3. **Check metrics endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/metrics
   ```

4. **Review Prometheus logs:**
   ```bash
   docker logs pybase-prometheus
   ```

### Grafana Not Showing Data

1. **Verify Prometheus data source:**
   - Configuration → Data Sources → Prometheus
   - Test connection

2. **Check time range:**
   - Ensure dashboard time range includes recent data
   - Try "Last 5 minutes" to verify data is flowing

3. **Verify queries:**
   - Click panel title → Edit
   - Run query manually to check for errors

### High Memory Usage

Prometheus memory usage depends on:
- Number of active time series
- Scrape interval
- Retention period

Mitigation strategies:
- Reduce scrape interval (default: 15s)
- Decrease retention period (default: 15 days)
- Use metric relabeling to drop unused series
- Add recording rules for pre-aggregation

## Best Practices

### Metric Design
- **Use appropriate types**: Counter for cumulative values, Histogram for distributions, Gauge for current state
- **Label cardinality**: Keep label values bounded (avoid high-cardinality labels like user IDs)
- **Naming**: Follow Prometheus naming conventions (suffix with `_total`, `_seconds`, `_bytes`)

### Dashboard Design
- **Meaningful titles**: Clearly indicate what the panel shows
- **Thresholds**: Use visual indicators for warning/critical states
- **Context**: Include related metrics for correlation
- **Refresh rate**: Balance between freshness and performance (30s recommended)

### Alert Design
- **Actionable alerts**: Only alert on conditions requiring human intervention
- **Severity levels**: Use appropriate severity (warning, critical)
- **Runbook links**: Include documentation in alert annotations
- **Testing**: Validate alert thresholds before enabling

## Performance Impact

### Metrics Collection Overhead
- **Middleware**: <1ms per request
- **Memory**: ~50MB base + ~1KB per active time series
- **CPU**: Negligible for scrape intervals >15s

### Mitigation Strategies
1. **Disable metrics in development**:
   ```bash
   PROMETHEUS_ENABLED=false
   ```

2. **Increase scrape interval** for low-traffic environments

3. **Use sampling** for high-cardinality metrics

4. **Optimize metric cardinality** by reducing label values

## Security Considerations

### Access Control
- **Prometheus**: No built-in authentication (use reverse proxy)
- **Grafana**: Configure authentication provider (OAuth, LDAP)
- **Metrics Endpoint**: Consider network policies to restrict access

### Data Sensitivity
- Metrics may contain sensitive information in labels
- Avoid logging user IDs, email addresses, or tokens in metric labels
- Use metric relabeling to strip sensitive labels

### Recommendations
- Deploy monitoring tools in private network
- Use TLS/SSL for all communications
- Implement authentication at reverse proxy level
- Regularly review metrics for sensitive data leakage

## Maintenance

### Data Retention
- **Default**: 15 days
- **Configure**: Modify `--storage.tsdb.retention.time` in Prometheus command
- **Storage planning**: ~1-2 bytes per data point

### Backup and Recovery
- **Prometheus data**: Backup `/prometheus` volume
- **Grafana dashboards**: Export JSON files (already in version control)
- **Configuration**: Already in version control (prometheus.yml, alerts/*.yml)

### Updates
- **Prometheus**: Rolling updates supported
- **Grafana**: Use official Docker images
- **Test upgrades** in staging environment first

## Further Reading
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Best Practices](https://prometheus.io/docs/practices/naming/)
