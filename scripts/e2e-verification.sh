#!/bin/bash
# End-to-End Verification of Prometheus/Grafana Monitoring Stack
# This script verifies all components of the monitoring stack are working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_METRICS_URL="http://localhost:8000/api/v1/metrics"
PROMETHEUS_URL="http://localhost:9090"
GRAFANA_URL="http://localhost:3000"
EXTRACTION_WORKER_METRICS="http://localhost:9091/metrics"
SEARCH_WORKER_METRICS="http://localhost:9092/metrics"

echo "========================================"
echo "E2E Verification: Monitoring Stack"
echo "========================================"
echo ""

# Helper function for check results
check_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $1"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}: $1"
        return 1
    fi
}

warn_result() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

# Step 1: Check Docker services are running
echo "Step 1: Verifying Docker services..."
echo "--------------------------------------"

# Check if containers are running
RUNNING_CONTAINERS=$(docker-compose ps --services --filter "status=running" | wc -l)
if [ "$RUNNING_CONTAINERS" -lt 3 ]; then
    echo -e "${RED}Error: Not enough containers running. Start services with:${NC}"
    echo "  docker-compose up -d"
    echo "  docker-compose --profile worker up -d"
    exit 1
fi
check_result "Docker containers are running ($RUNNING_CONTAINERS containers)"

# Step 2: Verify /metrics endpoint returns data
echo ""
echo "Step 2: Verifying API /metrics endpoint..."
echo "--------------------------------------"

# Check API metrics endpoint
API_METRICS=$(curl -s "$API_METRICS_URL" 2>&1)
if echo "$API_METRICS" | grep -q "http_requests_total"; then
    check_result "API /metrics endpoint returns http_requests_total"
else
    check_result "API /metrics endpoint returns http_requests_total"
    echo "  Response: $API_METRICS"
    exit 1
fi

if echo "$API_METRICS" | grep -q "api_latency_histogram"; then
    check_result "API /metrics endpoint returns api_latency_histogram"
else
    warn_result "API /metrics endpoint missing api_latency_histogram"
fi

# Step 3: Verify Prometheus is accessible and targets are UP
echo ""
echo "Step 3: Verifying Prometheus targets..."
echo "--------------------------------------"

# Check Prometheus is running
PROMETHEUS_HEALTH=$(curl -s "$PROMETHEUS_URL/-/healthy" 2>&1)
if echo "$PROMETHEUS_HEALTH" | grep -q "Prometheus is Healthy"; then
    check_result "Prometheus is healthy"
else
    check_result "Prometheus is healthy"
    exit 1
fi

# Check targets via API
TARGETS_JSON=$(curl -s "$PROMETHEUS_URL/api/v1/targets" 2>&1)

# Count targets with health "up"
UP_COUNT=$(echo "$TARGETS_JSON" | grep -o '"health":"up"' | wc -l)
TOTAL_TARGETS=$(echo "$TARGETS_JSON" | grep -o '"health":"' | wc -l)

echo "  Targets status: $UP_COUNT/$TOTAL_TARGETS UP"

if [ "$UP_COUNT" -ge 2 ]; then
    check_result "At least 2 Prometheus targets are UP"
else
    check_result "At least 2 Prometheus targets are UP"
    echo "  Only $UP_COUNT targets UP, need at least 2"
fi

# List all targets and their health
echo ""
echo "  Target Details:"
echo "$TARGETS_JSON" | grep -o '"scrapeUrl":"[^"]*","health":"[^"]*"' | sed 's/"scrapeUrl":"//g' | sed 's/","health":"/ -> /g' | sed 's/"$//g' | while read line; do
    echo "    $line"
done

# Step 4: Verify Grafana is accessible
echo ""
echo "Step 4: Verifying Grafana..."
echo "--------------------------------------"

# Check Grafana is running
GRAFANA_HEALTH=$(curl -s "$GRAFANA_URL/api/health" 2>&1)
if echo "$GRAFANA_HEALTH" | grep -q "database.*ok"; then
    check_result "Grafana is healthy"
else
    check_result "Grafana is healthy"
    warn_result "Grafana health check response: $GRAFANA_HEALTH"
fi

# Check if Prometheus datasource exists
DATASOURCES=$(curl -s "$GRAFANA_URL/api/datasources" 2>&1)
if echo "$DATASOURCES" | grep -q "Prometheus"; then
    check_result "Prometheus datasource configured in Grafana"
else
    check_result "Prometheus datasource configured in Grafana"
    warn_result "Datasources: $DATASOURCES"
fi

# Check dashboards are provisioned
DASHBOARDS=$(curl -s "$GRAFANA_URL/api/search" 2>&1)
DASHBOARD_COUNT=$(echo "$DASHBOARDS" | grep -o '"id":' | wc -l)
echo "  Found $DASHBOARD_COUNT dashboards in Grafana"

EXPECTED_DASHBOARDS=("Overview" "API Performance" "Celery Workers" "Database & Redis")
for dash in "${EXPECTED_DASHBOARDS[@]}"; do
    if echo "$DASHBOARDS" | grep -qi "$dash"; then
        check_result "Dashboard '$dash' is available"
    else
        warn_result "Dashboard '$dash' not found"
    fi
done

# Step 5: Generate some traffic for metrics
echo ""
echo "Step 5: Generating test traffic..."
echo "--------------------------------------"

# Make some API calls to generate metrics
curl -s "$API_METRICS_URL" > /dev/null 2>&1
curl -s "$PROMETHEUS_URL/api/v1/query?query=up" > /dev/null 2>&1

# Wait for metrics to be scraped
echo "  Waiting 15 seconds for Prometheus to scrape metrics..."
sleep 15

# Check if Prometheus has scraped some data
QUERY_RESULT=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=http_requests_total" 2>&1)
if echo "$QUERY_RESULT" | grep -q '"result"'; then
    check_result "Prometheus has scraped http_requests_total metrics"
else
    warn_result "Prometheus may not have scraped metrics yet (can take up to 30s)"
fi

# Step 6: Check for alert rules
echo ""
echo "Step 6: Verifying alert rules..."
echo "--------------------------------------"

ALERTS=$(curl -s "$PROMETHEUS_URL/api/v1/rules" 2>&1)
ALERT_COUNT=$(echo "$ALERTS" | grep -o '"name":"[^"]*"' | wc -l)
echo "  Found $ALERT_COUNT alert rules"

if [ "$ALERT_COUNT" -gt 0 ]; then
    check_result "Alert rules are loaded in Prometheus"

    # List a few sample alerts
    echo ""
    echo "  Sample Alert Rules:"
    echo "$ALERTS" | grep -o '"name":"[^"]*","state":"[^"]*"' | head -3 | sed 's/"name":"/    - /g' | sed 's/","state":"/ (state: /g' | sed 's/"$//g' | sed 's/$/)/g'
else
    warn_result "No alert rules found (may need to check prometheus.yml configuration)"
fi

# Step 7: Summary
echo ""
echo "========================================"
echo "Verification Summary"
echo "========================================"
echo ""
echo "Monitoring Stack URLs:"
echo "  - Prometheus: $PROMETHEUS_URL"
echo "  - Grafana: $GRAFANA_URL (admin/admin)"
echo "  - API Metrics: $API_METRICS_URL"
echo ""
echo "Next Steps:"
echo "  1. Open Grafana at $GRAFANA_URL"
echo "  2. Login with admin/admin"
echo "  3. View the Overview dashboard for system health"
echo "  4. Check API Performance dashboard for latency metrics"
echo "  5. Review alert rules in Prometheus: $PROMETHEUS_URL/alerts"
echo ""
echo "To trigger a test alert:"
echo "  - Make many failed API requests to increase error rate"
echo "  - Monitor alerts at $PROMETHEUS_URL/alerts"
echo ""
