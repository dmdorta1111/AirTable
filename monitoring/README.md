# Prometheus/Grafana Monitoring Stack

Comprehensive monitoring solution for PyBase with Prometheus metrics collection, Grafana dashboards, and alerting rules.

---

## Quick Start

### 1. Start All Services

```bash
# Start core infrastructure
docker-compose up -d

# Start workers (optional but recommended)
docker-compose --profile worker up -d

# Verify all containers are running
docker-compose ps
```

### 2. Run End-to-End Verification

```bash
# Linux/macOS
./scripts/e2e-verification.sh

# Windows
scripts\e2e-verification.bat
```

### 3. Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Prometheus | http://localhost:9090 | None |
| Grafana | http://localhost:3000 | admin/admin |
| API Metrics | http://localhost:8000/api/v1/metrics | None |
| Extraction Worker | http://localhost:9091/metrics | None |
| Search Worker | http://localhost:9092/metrics | None |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│   PyBase API    │────▶│                  │
│  (port 8000)    │     │                  │
│  /metrics       │     │                  │
└─────────────────┘     │                  │
                        │  Prometheus      │     ┌───────────┐
┌─────────────────┐     │  (port 9090)     │────▶│ Grafana   │
│ Extraction      │     │                  │     │ (port 3000)│
│ Worker          │────▶│  Scrapes every   │     └───────────┘
│ (port 9091)     │     │  15 seconds      │          ▲
└─────────────────┘     │                  │          │
                        │  Stores metrics  │          │
┌─────────────────┐     │  for 15 days     │──────────┘
│ Search Worker   │     │                  │  Dashboards
│ (port 9092)     │────▶│                  │
└─────────────────┘     └──────────────────┘
```

---

## Components

### Prometheus

**Role:** Metrics collection and storage

**Configuration:** `monitoring/prometheus.yml`

**Scrape Targets:**
- Prometheus itself (self-monitoring)
- PyBase API (HTTP metrics, business metrics)
- Celery extraction worker (task metrics)
- Celery search worker (task metrics)

**Data Retention:** 15 days (default)

**Alert Rules:**
- High error rates
- Slow API/queries
- Resource exhaustion

### Grafana

**Role:** Metrics visualization and dashboards

**Provisioning:**
- Datasources: `docker/grafana/provisioning/datasources/`
- Dashboards: `docker/grafana/provisioning/dashboards/`

**Available Dashboards:**
1. **Overview** - System-wide health summary
2. **API Performance** - Request rate, latency, errors
3. **Celery Workers** - Task throughput, duration, failures
4. **Database & Redis** - DB connections, cache performance

### PyBase API Metrics

**Endpoint:** `/api/v1/metrics`

**Metrics Collected:**
```promql
# HTTP request metrics
http_requests_total{method, endpoint, status}
api_latency_histogram{method, endpoint}

# Business metrics
extraction_task_total{task_type, status}
extraction_task_duration_seconds{task_type}
websocket_connections_current
db_query_duration_seconds{query_type}
cache_operations_total{operation, status}
```

### Worker Metrics

**Endpoints:**
- Extraction worker: `http://localhost:9091/metrics`
- Search worker: `http://localhost:9092/metrics`

**Metrics Collected:**
```promql
# Task metrics
celery_task_total{task_name, status}
celery_task_duration_seconds{task_name}
celery_task_retries_total{task_name}
celery_queue_length{worker_name}
celery_active_workers{worker_name}
```

---

## Alerting

### Alert Rules

All alert rules are defined in `monitoring/alerts/`:

| File | Alerts | Severity |
|------|--------|----------|
| `high-error-rate.yml` | API/Worker error rates | Warning, Critical |
| `slow-tasks.yml` | API/Query/Task latency | Warning, Critical |
| `resource-exhaustion.yml` | Memory, Disk, CPU | Warning, Critical |

### Example Alerts

**High API Error Rate:**
```yaml
- alert: HighAPIErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
  for: 5m
  labels:
    severity: warning
```

**Critical API Latency:**
```yaml
- alert: CriticalAPILatency
  expr: histogram_quantile(0.95, api_latency_histogram) > 5
  for: 2m
  labels:
    severity: critical
```

### View Alerts

**Prometheus UI:**
```
http://localhost:9090/alerts
```

**Grafana:**
Navigate to the Alerting section or view alert status on Overview dashboard.

---

## Troubleshooting

### Prometheus Targets Down

**Symptoms:** Targets show "DOWN" in Prometheus UI

**Diagnosis:**
```bash
# Check container status
docker-compose ps

# Check Prometheus logs
docker-compose logs prometheus | tail -50

# Test connectivity
docker-compose exec prometheus ping api
```

**Solutions:**
1. Restart failed containers: `docker-compose restart <service>`
2. Check network: Verify all containers are on `pybase-network`
3. Verify metrics endpoint: `curl http://localhost:8000/api/v1/metrics`
4. Reload Prometheus config: `curl -X POST http://localhost:9090/-/reload`

### Grafana No Data

**Symptoms:** Dashboards show "No Data"

**Diagnosis:**
1. Check datasource: Configuration → Data Sources → Prometheus → Test
2. Verify Prometheus has data: http://localhost:9090/graph
3. Check time range in dashboard

**Solutions:**
1. Ensure datasource URL is `http://prometheus:9090`
2. Set time range to "Last 5 minutes"
3. Generate test traffic: `for i in {1..50}; do curl http://localhost:8000/api/v1/health; done`

### Worker Metrics Not Accessible

**Symptoms:** Worker metrics endpoints return connection refused

**Diagnosis:**
```bash
# Check worker logs
docker-compose logs celery-extraction-worker | grep "prometheus"

# Check if port is exposed
docker-compose ps | grep worker
```

**Solutions:**
1. Verify `PROMETHEUS_METRICS_PORT` environment variable is set
2. Restart workers: `docker-compose restart celery-extraction-worker`
3. Check worker code has `start_http_server()` call

---

## Configuration

### Prometheus

**Configuration file:** `monitoring/prometheus.yml`

**Key settings:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'pybase-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/api/v1/metrics'
```

**Reload config without restart:**
```bash
curl -X POST http://localhost:9090/-/reload
```

### Grafana

**Datasource config:** `docker/grafana/provisioning/datasources/prometheus.yml`

**Dashboard provider:** `docker/grafana/provisioning/dashboards/dashboard-provider.yml`

**Environment variables:**
```yaml
GF_SECURITY_ADMIN_USER: admin
GF_SECURITY_ADMIN_PASSWORD: admin
```

### PyBase API

**Settings:** `src/pybase/core/config.py`

```python
prometheus_enabled: bool = True
prometheus_port: int = 9090
prometheus_path: str = "/metrics"
```

**Disable metrics:** Set `PROMETHEUS_ENABLED=false` in environment

### Workers

**Environment variables:**
```bash
PROMETHEUS_METRICS_PORT=9090  # Port for metrics HTTP server
WORKER_NAME=extraction         # Worker identifier
```

---

## Maintenance

### Backup Data

**Prometheus data:**
```bash
docker run --rm -v pybase-prometheus-data:/data \
  -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz /data
```

**Grafana data:**
```bash
docker run --rm -v pybase-grafana-data:/data \
  -v $(pwd):/backup alpine tar czf /backup/grafana-backup.tar.gz /data
```

### Restore Data

```bash
# Stop containers
docker-compose down

# Restore data
docker run --rm -v pybase-prometheus-data:/data \
  -v $(pwd):/backup alpine sh -c "cd /data && tar xzf /backup/prometheus-backup.tar.gz --strip 1"

# Restart
docker-compose up -d
```

### Update Dashboards

1. Edit JSON in `monitoring/grafana-dashboards/`
2. Restart Grafana: `docker-compose restart grafana`
3. Dashboards auto-provision on startup

### Add New Metrics

**In API:**
```python
# src/pybase/metrics/__init__.py
from prometheus_client import Counter

my_custom_metric = Counter(
    'my_custom_metric_total',
    'Description of metric',
    ['label1', 'label2']
)
```

**In Workers:**
```python
# workers/worker_metrics.py
from prometheus_client import Counter

my_task_metric = Counter(
    'my_task_metric_total',
    'Description',
    ['task_name']
)
```

---

## Performance Tuning

### Prometheus

**Memory usage:** ~100MB + 2KB per active time series

**Optimize queries:**
```promql
# BAD - High cardinality
http_requests_total

# GOOD - Aggregate
sum(http_requests_total) by (endpoint)
```

**Reduce retention:**
```yaml
# prometheus.yml
storage:
  tsdb:
    retention.time: 7d  # Default 15d
```

### Grafana

**Reduce refresh interval:**
- Dashboard settings → Variables → Refresh → Off or 30s

**Optimize panels:**
- Use `rate()` for counters
- Limit query time range
- Use summary instead of raw data

---

## Security Considerations

### Production Deployment

1. **Change default credentials:**
   ```yaml
   GF_SECURITY_ADMIN_PASSWORD: <strong-password>
   ```

2. **Expose only reverse proxy:**
   ```yaml
   ports:
     - "127.0.0.1:9090:9090"  # Prometheus
     - "127.0.0.1:3000:3000"  # Grafana
   ```

3. **Enable TLS:**
   - Use Nginx/Apache reverse proxy
   - Enable HTTPS for external access

4. **Network isolation:**
   - Run monitoring on separate network
   - Firewall rules for access control

5. **Authentication:**
   - Configure Grafana OAuth/LDAP
   - Use Prometheus basic_auth

---

## Integration with Existing Monitoring

### External Prometheus

Add to your existing Prometheus:

```yaml
# external-prometheus.yml
scrape_configs:
  - job_name: 'pybase'
    static_configs:
      - targets: ['pybase.example.com:8000']
    metrics_path: '/api/v1/metrics'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'pybase-prod'
```

### Remote Write

Configure Prometheus remote write:

```yaml
# prometheus.yml
remote_write:
  - url: "https://prometheus-remote.example.com/api/v1/write"
    headers:
      Authorization: "Bearer <token>"
```

---

## Further Reading

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Best Practices](https://prometheus.io/docs/practices/)

---

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review logs: `docker-compose logs <service>`
3. Consult detailed guide: `monitoring/E2E_VERIFICATION_GUIDE.md`
4. Run verification: `./scripts/e2e-verification.sh`

---

**Version:** 1.0
**Last Updated:** 2026-01-27
