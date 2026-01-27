# End-to-End Verification Guide
## Prometheus/Grafana Monitoring Stack

This guide provides comprehensive instructions for verifying the entire monitoring stack is working correctly.

---

## Prerequisites

Before running the verification, ensure you have:

1. **Docker Desktop** running and accessible
2. **Docker Compose** available (v2.0+)
3. **curl** or **wget** for API testing
4. All monitoring components deployed:
   - Prometheus
   - Grafana
   - PyBase API with metrics
   - (Optional) Celery workers with metrics

---

## Quick Start Verification

### Linux/macOS
```bash
# Make script executable
chmod +x scripts/e2e-verification.sh

# Run verification
./scripts/e2e-verification.sh
```

### Windows
```batch
# Run verification batch file
scripts\e2e-verification.bat
```

---

## Manual Verification Steps

### Step 1: Start All Services

Start the core infrastructure:
```bash
docker-compose up -d
```

Start workers (optional but recommended):
```bash
docker-compose --profile worker up -d
```

Verify containers are running:
```bash
docker-compose ps
```

Expected output:
- `pybase-postgres` - running
- `pybase-redis` - running
- `pybase-minio` - running
- `pybase-prometheus` - running
- `pybase-grafana` - running
- `pybase-api` - running
- `pybase-celery-extraction-worker` - running (if profile enabled)
- `pybase-celery-search-worker` - running (if profile enabled)

---

### Step 2: Verify API /metrics Endpoint

The PyBase API should expose Prometheus metrics at `/api/v1/metrics`.

**Test:**
```bash
curl http://localhost:8000/api/v1/metrics
```

**Expected Output:** Prometheus text format with metrics like:
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/api/v1/metrics",method="GET",status="200"} 1.0

# HELP api_latency_histogram API request latency
# TYPE api_latency_histogram histogram
api_latency_histogram_bucket{endpoint="/api/v1/metrics",method="GET",le="0.005"} 1.0
...
```

**Troubleshooting:**
- If connection refused: Ensure API container is running (`docker-compose up -d api`)
- If no metrics: Check `prometheus_enabled` setting in config
- If 404: Verify metrics router is registered in `src/pybase/main.py`

---

### Step 3: Verify Prometheus Targets

Prometheus should be scraping metrics from all configured targets.

**Access Prometheus UI:**
```
http://localhost:9090/targets
```

**Expected Targets:**
1. **prometheus** - `http://localhost:9090/metrics` (UP)
2. **pybase-api** - `http://api:8000/api/v1/metrics` (UP)
3. **celery-extraction-worker** - `http://celery-extraction-worker:9090/metrics` (UP, if running)
4. **celery-search-worker** - `http://celery-search-worker:9090/metrics` (UP, if running)

**Check via API:**
```bash
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health, lastError: .lastError}'
```

**Expected:** All targets show `"health": "up"`

**Troubleshooting:**
- If targets are down: Check container logs (`docker-compose logs <service>`)
- If 403 forbidden: Verify Prometheus configuration in `monitoring/prometheus.yml`
- If unreachable: Check Docker network connectivity

---

### Step 4: Verify Grafana Dashboards

Grafana should auto-provision dashboards on startup.

**Access Grafana:**
```
URL: http://localhost:3000
Username: admin
Password: admin
```

**Expected Dashboards:**
1. **Overview** - System-wide metrics summary
2. **API Performance** - Request rates, latency, errors
3. **Celery Workers** - Task throughput, duration, failures
4. **Database & Redis** - DB connections, cache performance

**Verify via API:**
```bash
curl -s http://localhost:3000/api/search | jq '.[] | {title: .title, uid: .uid}'
```

**Check Dashboard Data:**
1. Open any dashboard
2. Ensure panels show data (not "No Data")
3. Verify time range is set to "Last 5 minutes"
4. Refresh browser if no data appears

**Troubleshooting:**
- If dashboards missing: Check provisioning logs (`docker-compose logs grafana`)
- If no data in panels: Verify Prometheus datasource is configured
- If 401 unauthorized: Re-login with admin/admin

---

### Step 5: Verify Alert Rules

Prometheus should have alert rules loaded.

**Access Alerts UI:**
```
http://localhost:9090/alerts
```

**Expected Alert Groups:**
1. **high_error_rate** - API error rate alerts
2. **slow_tasks** - Performance degradation alerts
3. **resource_exhaustion** - Resource usage alerts

**Check via API:**
```bash
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | {name: .name, rules: [.rules[] | .name]}'
```

**Trigger a Test Alert:**

To verify alerting works, intentionally trigger a condition:

```bash
# Method 1: Generate API errors
for i in {1..100}; do
  curl -s http://localhost:8000/api/v1/nonexistent > /dev/null
done

# Method 2: Check alert state after 2-5 minutes
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing") | {alert: .labels.alertname, state: .state}'
```

**Troubleshooting:**
- If no alerts: Check `monitoring/alerts/` files are mounted in Prometheus
- If alerts inactive: Verify evaluation interval in `prometheus.yml`
- If rules not loading: Check YAML syntax in alert files

---

### Step 6: Generate Test Traffic

To populate dashboards with meaningful data:

**1. Generate API traffic:**
```bash
# Successful requests
for i in {1..50}; do
  curl -s http://localhost:8000/api/v1/health > /dev/null
  curl -s http://localhost:8000/api/v1/metrics > /dev/null
done

# Failed requests (to test error metrics)
for i in {1..10}; do
  curl -s http://localhost:8000/api/v1/invalid > /dev/null
done
```

**2. Monitor metrics in Prometheus:**
```bash
# Query request count
curl -s "http://localhost:9090/api/v1/query?query=http_requests_total" | jq .

# Query error rate
curl -s "http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~\"5..\"}[5m])" | jq .
```

**3. Verify dashboards update:**
- Open Grafana Overview dashboard
- Set refresh to "5s"
- Watch panels populate with data

---

## Health Check Summary

### Expected Service Status

| Service | Health Check | Command |
|---------|--------------|---------|
| PostgreSQL | `pg_isready` | `docker-compose exec postgres pg_isready` |
| Redis | `PING` | `docker-compose exec redis redis-cli ping` |
| Prometheus | HTTP 200 | `curl http://localhost:9090/-/healthy` |
| Grafana | HTTP 200 | `curl http://localhost:3000/api/health` |
| PyBase API | HTTP 200 | `curl http://localhost:8000/api/v1/health` |
| Extraction Worker | Metrics | `curl http://localhost:9091/metrics` |
| Search Worker | Metrics | `curl http://localhost:9092/metrics` |

---

## Common Issues and Solutions

### Issue: Prometheus targets show "down"

**Diagnosis:**
```bash
docker-compose logs prometheus | grep "scrape failed"
```

**Solutions:**
1. Check if target containers are running
2. Verify network connectivity (try `docker-compose exec prometheus ping api`)
3. Check metrics endpoint is accessible from Prometheus container
4. Verify scrape interval in `prometheus.yml`

### Issue: Grafana dashboards show "No Data"

**Diagnosis:**
1. Check datasource: Configuration → Data Sources → Prometheus → Test
2. Verify Prometheus has data: http://localhost:9090/graph

**Solutions:**
1. Ensure datasource URL is `http://prometheus:9090`
2. Check time range in dashboard (should be recent)
3. Verify Prometheus is scraping targets successfully
4. Query Prometheus directly: `http_requests_total`

### Issue: Alert rules not firing

**Diagnosis:**
```bash
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.state=="inactive") | .name'
```

**Solutions:**
1. Alert evaluation interval may be too long (default 15s)
2. Alert threshold may not be reached
3. Query may need more data points
4. Check alert rule syntax and query logic

### Issue: Worker metrics not accessible

**Diagnosis:**
```bash
docker-compose logs celery-extraction-worker | grep "prometheus"
```

**Solutions:**
1. Verify `PROMETHEUS_METRICS_PORT` environment variable is set
2. Check worker code has `start_http_server()` call
3. Ensure port mapping is correct in `docker-compose.yml`
4. Verify worker container is running

---

## Verification Checklist

Complete this checklist to verify the monitoring stack:

### Infrastructure
- [ ] Docker Desktop is running
- [ ] All containers started successfully
- [ ] No container restart loops (`docker-compose ps` shows healthy)

### Metrics Collection
- [ ] API `/metrics` endpoint returns Prometheus format
- [ ] Prometheus is scraping at least 2 targets successfully
- [ ] Workers expose metrics on ports 9091/9092 (if running)

### Data Visualization
- [ ] Grafana is accessible at http://localhost:3000
- [ ] Prometheus datasource is configured and tests successfully
- [ ] At least 3 dashboards are provisioned (Overview, API, Workers)
- [ ] Dashboard panels show data (not "No Data")

### Alerting
- [ ] Alert rules are loaded in Prometheus UI
- [ ] Alert groups are visible at http://localhost:9090/alerts
- [ ] Test alert can be triggered and appears in UI

### Documentation
- [ ] Monitoring documentation exists at `docs/monitoring.md`
- [ ] README has monitoring section
- [ ] Verification scripts are executable

---

## Performance Baseline

After successful deployment, establish baselines:

### API Metrics
- Request rate: ~10-100 req/s (varies by load)
- Latency p50: <100ms
- Latency p95: <500ms
- Error rate: <1%

### Worker Metrics
- Task throughput: Depends on task type
- Task duration: Extraction <30s, Search <10s
- Queue size: <100 tasks

### Resource Metrics
- API memory: <500MB
- Worker memory: <300MB each
- Prometheus memory: <500MB
- Grafana memory: <200MB

---

## Next Steps

After successful verification:

1. **Configure persistent storage**: Volumes for Prometheus and Grafana data
2. **Set up alert notifications**: Configure Alertmanager or Grafana notifications
3. **Tune alert thresholds**: Adjust based on actual traffic patterns
4. **Add custom metrics**: Business-specific metrics for your use case
5. **Document runbooks**: Create SOPs for handling common alerts
6. **Set up log aggregation**: Integrate with Loki/ELK for logs

---

## Support and Troubleshooting

### Logs Collection
```bash
# Collect all monitoring logs
docker-compose logs prometheus > prometheus.log
docker-compose logs grafana > grafana.log
docker-compose logs api > api.log
docker-compose logs celery-extraction-worker > extraction-worker.log
```

### Diagnostic Queries
```bash
# Prometheus scrape health
curl -s 'http://localhost:9090/api/v1/query?query=up' | jq .

# Target scrape failures
curl -s 'http://localhost:9090/api/v1/query?query=scrape_duration_seconds' | jq .

# Alert states
curl -s 'http://localhost:9090/api/v1/alerts' | jq '.data.alerts[] | {alert: .labels.alertname, state: .state}'
```

### Reset Everything
```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Restart fresh
docker-compose up -d
docker-compose --profile worker up -d

# Re-run verification
./scripts/e2e-verification.sh
```

---

## Success Criteria

The monitoring stack verification is successful when:

✅ All Docker containers are healthy
✅ API metrics endpoint returns Prometheus-formatted data
✅ Prometheus shows all targets as "UP"
✅ Grafana dashboards are accessible and show data
✅ Alert rules are loaded and evaluable
✅ Test traffic generates visible metrics
✅ Verification script completes without errors

---

**Last Updated:** 2026-01-27
**Version:** 1.0
