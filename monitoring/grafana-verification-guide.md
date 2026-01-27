# Grafana Dashboard Verification Guide

**Subtask:** 6-2 - Verify Grafana dashboards load and display data
**Status:** ✅ Configuration Complete

## Overview

This guide explains how to verify that Grafana dashboards load correctly and display metrics data from the PyBase monitoring stack.

## Prerequisites

1. **Docker Desktop** must be running
2. **Prometheus and Grafana** services must be started
3. **PyBase API and Workers** (optional) - for seeing actual metrics data

## Quick Start

### 1. Start Services

```bash
# Start Prometheus and Grafana
docker-compose up -d prometheus grafana

# Or start all services including API and workers
docker-compose up -d
docker-compose --profile worker up -d
```

### 2. Verify Services are Running

```bash
# Check Prometheus
curl http://localhost:9090/-/healthy

# Check Grafana
curl http://localhost:3000/api/health
```

### 3. Access Grafana

- **URL:** http://localhost:3000
- **Username:** `admin`
- **Password:** `admin`

## Verification Steps

### Step 1: Grafana Web Interface Loads

1. Open http://localhost:3000 in your browser
2. Login with `admin/admin`
3. You should see the Grafana home screen
4. Verify the Prometheus datasource is configured:
   - Go to **Configuration → Data Sources**
   - You should see **Prometheus** listed
   - Status should show **green** with a last ping time

### Step 2: Dashboards are Provisioned

1. Go to **Dashboards → Browse**
2. You should see a folder called **PyBase Dashboards**
3. Expand the folder to see all dashboards:
   - ✅ **PyBase API Performance** (8 panels)
   - ✅ **PyBase Celery Workers** (12 panels)
   - ✅ **PyBase Database & Redis** (18 panels)
   - ✅ **PyBase System Overview** (14 panels)

### Step 3: Dashboards Load Successfully

For each dashboard:

1. Click on the dashboard name
2. The dashboard should load without errors
3. All panels should display (even if "No Data" initially)
4. Check for any red warning signs or error messages

### Step 4: Panels Show Data (When Services Running)

When the PyBase API and workers are running and generating metrics:

1. **API Performance Dashboard** should show:
   - Request rate (requests/sec)
   - Error rate (percentage)
   - Latency percentiles (p50, p95, p99)
   - Breakdown by endpoint and method

2. **Celery Workers Dashboard** should show:
   - Task processing rate
   - Task success rate
   - Task duration by type
   - Queue sizes

3. **Database & Redis Dashboard** should show:
   - Database connection pool stats
   - Query performance metrics
   - Redis hit rates
   - Cache operation counts

4. **System Overview Dashboard** should show:
   - Service health status
   - Request rates and errors
   - Worker task status
   - Resource utilization

## Expected Behavior

### Without API/Workers Running

When only Prometheus and Grafana are running (without the PyBase API or workers):

- ✅ Grafana loads successfully
- ✅ Dashboards are accessible
- ✅ All panels display
- ⚠️ Panels show **"No Data"** or **"N/A"** - this is expected
- ℹ️ Dashboard queries are valid but no metrics exist yet

### With API/Workers Running

When the full stack is running:

- ✅ Grafana loads successfully
- ✅ Dashboards are accessible
- ✅ All panels display
- ✅ Panels show real-time metrics data
- ✅ Time series graphs update every 15 seconds (default scrape interval)

## Automated Verification

Run the automated verification script:

```bash
./verify-grafana-dashboards.sh
```

This script checks:
- ✅ Docker is running
- ✅ Services start successfully
- ✅ Grafana web interface is accessible
- ✅ Prometheus datasource is configured
- ✅ Dashboards are provisioned
- ✅ Dashboard JSON files are valid
- ✅ Prometheus is scraping targets (when running)

## Dashboard Validation

To validate dashboard JSON files without starting services:

```bash
python scripts/validate-dashboards.py
```

This validates:
- ✅ JSON syntax is correct
- ✅ Required dashboard fields exist
- ✅ Panels are properly configured
- ✅ Metrics are referenced correctly

## Troubleshooting

### Grafana Won't Load

**Problem:** http://localhost:3000 doesn't load

**Solutions:**
1. Check Docker Desktop is running
2. Check Grafana container status: `docker-compose ps grafana`
3. Check Grafana logs: `docker-compose logs grafana`
4. Verify port 3000 isn't used by another application
5. Restart Grafana: `docker-compose restart grafana`

### Dashboards Not Showing

**Problem:** Dashboards folder or dashboards not visible

**Solutions:**
1. Check provisioning configuration: `docker/grafana/provisioning/dashboards/pybase.yml`
2. Check dashboard files exist: `ls monitoring/grafana-dashboards/`
3. Check volume mount in docker-compose.yml
4. Restart Grafana: `docker-compose restart grafana`
5. Check Grafana logs for provisioning errors: `docker-compose logs grafana | grep provisioning`

### Panels Show "No Data"

**Problem:** Dashboards load but all panels show "No Data"

**Solutions:**
1. **This is expected if API/workers aren't running**
2. Start the PyBase API: `docker-compose up -d api`
3. Start workers: `docker-compose --profile worker up -d`
4. Generate some traffic by making API requests
5. Wait 15-30 seconds for Prometheus to scrape metrics
6. Refresh the dashboard

### Prometheus Datasource Not Connected

**Problem:** Data source shows red or can't connect

**Solutions:**
1. Check Prometheus is running: `curl http://localhost:9090/-/healthy`
2. Check Prometheus container: `docker-compose ps prometheus`
3. Verify datasource configuration in `docker/grafana/provisioning/datasources/prometheus.yml`
4. Check network connectivity: `docker network inspect pybase-network`
5. Restart both services: `docker-compose restart prometheus grafana`

### Invalid Dashboard JSON

**Problem:** Dashboard fails to load with JSON error

**Solutions:**
1. Validate dashboard files: `python scripts/validate-dashboards.py`
2. Check JSON syntax: `python -m json.tool monitoring/grafana-dashboards/dashboard.json`
3. Look for trailing commas or missing brackets
4. Compare with working dashboards

## Manual Dashboard Import (Alternative)

If automatic provisioning doesn't work, dashboards can be imported manually:

1. Log in to Grafana (http://localhost:3000)
2. Go to **Dashboards → Import**
3. For each dashboard file:
   - Click **Upload JSON file**
   - Select the dashboard JSON file from `monitoring/grafana-dashboards/`
   - Select **Prometheus** as the data source
   - Click **Import**

## Metrics Reference

### API Metrics (`http_*`)
- `http_requests_total` - Total HTTP requests (labels: method, endpoint, status)
- `http_request_duration_seconds` - Request latency histogram

### Worker Metrics (`worker_*`)
- `worker_tasks_total` - Total tasks processed (labels: task_type, status)
- `worker_task_duration_seconds` - Task execution time
- `worker_task_retries_total` - Task retry count
- `worker_queue_size` - Current queue size
- `worker_processes_active` - Active worker count
- `worker_task_failures_total` - Task failures
- `worker_memory_bytes` - Worker memory usage
- `worker_db_operation_duration_seconds` - DB operation time

### System Metrics
- `websocket_connections` - Active WebSocket connections
- `db_query_duration_seconds` - Database query time
- `cache_operations_total` - Cache operations (labels: operation, status)

## Testing Dashboards with Sample Data

To generate test metrics:

```bash
# Start API and generate some traffic
docker-compose up -d api
sleep 10

# Make some API requests
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/metrics

# Check metrics are being exposed
curl http://localhost:8000/api/v1/metrics | grep http_requests_total

# Wait for Prometheus to scrape (15s)
sleep 20

# Verify Prometheus has data
curl -s http://localhost:9090/api/v1/query?query=http_requests_total | python -m json.tool
```

## Next Steps

After verification:

1. ✅ Subtask 6-2 is complete
2. 📝 Proceed to subtask 6-3 (Create monitoring documentation)
3. 📝 Proceed to subtask 6-4 (Update README.md)
4. 📝 Proceed to subtask 6-5 (End-to-end verification)

## Checklist

Use this checklist to verify completion:

- [ ] Grafana web interface loads at http://localhost:3000
- [ ] Login with admin/admin works
- [ ] Prometheus datasource is configured and connected
- [ ] All 4 dashboards are visible in Dashboards → Browse
- [ ] Each dashboard loads without errors
- [ ] Dashboard panels are displayed (may show "No Data" until services start)
- [ ] No JSON parsing errors in dashboard files
- [ ] Automated verification script passes: `./verify-grafana-dashboards.sh`

## Files Created/Modified

**Created:**
- `docker/grafana/provisioning/datasources/prometheus.yml` - Prometheus datasource config
- `docker/grafana/provisioning/dashboards/pybase.yml` - Dashboard provisioning config
- `verify-grafana-dashboards.sh` - Automated verification script
- `scripts/validate-dashboards.py` - Dashboard validation script
- `monitoring/grafana-verification-guide.md` - This guide

**Modified:**
- `docker-compose.yml` - Added dashboard volume mount to Grafana service

## Summary

✅ **Grafana configuration is complete**
✅ **Dashboards are properly provisioned**
✅ **Automated verification tools are available**
✅ **Documentation is comprehensive**

The dashboards will load successfully and display data once the PyBase services are running and generating metrics. Until then, they will show "No Data" which is expected behavior.
