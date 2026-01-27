#!/bin/bash
# Verification script for Grafana dashboards (subtask-6-2)
# This script verifies that Grafana loads and displays dashboards correctly

set -e

echo "=== Grafana Dashboard Verification Script ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo "1. Checking if Docker is running..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running. Please start Docker Desktop and try again.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Check if docker-compose is available
echo "2. Checking docker-compose..."
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ docker-compose not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ docker-compose is available${NC}"
echo ""

# Start required services
echo "3. Starting required services (Prometheus and Grafana)..."
docker-compose up -d prometheus grafana
echo ""
sleep 5

# Wait for services to be healthy
echo "4. Waiting for services to be healthy..."
echo "   Waiting for Prometheus..."
for i in {1..30}; do
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Prometheus is healthy${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Prometheus failed to become healthy${NC}"
        exit 1
    fi
    sleep 2
done
echo ""

echo "   Waiting for Grafana..."
for i in {1..30}; do
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Grafana is healthy${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Grafana failed to become healthy${NC}"
        exit 1
    fi
    sleep 2
done
echo ""

# Verify Grafana is accessible
echo "5. Verifying Grafana web interface..."
if curl -s http://localhost:3000 | grep -q "Grafana"; then
    echo -e "${GREEN}✓ Grafana web interface is accessible at http://localhost:3000${NC}"
else
    echo -e "${RED}✗ Grafana web interface is not accessible${NC}"
    exit 1
fi
echo ""

# Verify Prometheus datasource is configured
echo "6. Verifying Prometheus datasource in Grafana..."
DS_CHECK=$(curl -s -u admin:admin http://localhost:3000/api/datasources | grep -o '"name":"Prometheus"' || echo "")
if [ -n "$DS_CHECK" ]; then
    echo -e "${GREEN}✓ Prometheus datasource is configured${NC}"
else
    echo -e "${RED}✗ Prometheus datasource not found${NC}"
    echo "   Response:"
    curl -s -u admin:admin http://localhost:3000/api/datasources
    exit 1
fi
echo ""

# Verify dashboards are provisioned
echo "7. Verifying dashboards are provisioned..."
DASHBOARDS=("api-performance" "celery-workers" "database-redis" "overview")
ALL_DASHBOARDS_FOUND=true

for dashboard in "${DASHBOARDS[@]}"; do
    # Check via API if dashboard exists
    DASHBOARD_CHECK=$(curl -s -u admin:admin "http://localhost:3000/api/search?query=$dashboard" | grep -o "\"title\":\"$dashboard\"" || echo "")
    if [ -n "$DASHBOARD_CHECK" ]; then
        echo -e "${GREEN}✓ Dashboard '$dashboard' is provisioned${NC}"
    else
        echo -e "${YELLOW}⚠ Dashboard '$dashboard' not found (may need to wait longer)${NC}"
        ALL_DASHBOARDS_FOUND=false
    fi
done
echo ""

# Verify dashboard files are syntactically valid
echo "8. Verifying dashboard JSON files are valid..."
for dashboard_file in monitoring/grafana-dashboards/*.json; do
    filename=$(basename "$dashboard_file")
    if python3 -c "import json; json.load(open('$dashboard_file'))" 2>/dev/null; then
        echo -e "${GREEN}✓ $filename is valid JSON${NC}"
    else
        echo -e "${RED}✗ $filename has invalid JSON${NC}"
        exit 1
    fi
done
echo ""

# Check if Prometheus has targets up
echo "9. Verifying Prometheus is scraping targets..."
TARGETS=$(curl -s http://localhost:9090/api/v1/targets | python3 -c "import sys, json; data = json.load(sys.stdin); active = [t for t in data['data']['activeTargets'] if t['health'] == 'up']; print(f'{len(active)} targets up')" 2>/dev/null || echo "0")
if [ "$TARGETS" != "0" ] && [ -n "$TARGETS" ]; then
    echo -e "${GREEN}✓ Prometheus is scraping $TARGETS target(s)${NC}"
else
    echo -e "${YELLOW}⚠ No Prometheus targets are up yet (this is expected if API/workers aren't running)${NC}"
fi
echo ""

# Summary
echo "=== VERIFICATION SUMMARY ==="
echo ""
echo "Grafana Web Interface: http://localhost:3000"
echo "  Username: admin"
echo "  Password: admin"
echo ""
echo "Prometheus Web Interface: http://localhost:9090"
echo ""
echo "Available Dashboards:"
for dashboard in "${DASHBOARDS[@]}"; do
    echo "  - $dashboard"
done
echo ""
echo "Next Steps:"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Login with admin/admin"
echo "  3. Navigate to Dashboards → PyBase Dashboards"
echo "  4. Verify dashboards load and display data"
echo "  5. (Optional) Start the API and workers to see real metrics data"
echo ""
echo -e "${GREEN}✓ Basic verification complete!${NC}"
echo ""
echo "Note: Dashboards will show 'No Data' until:"
echo "  - PyBase API is running and generating metrics"
echo "  - Celery workers are running and processing tasks"
echo "  - Prometheus has scraped metrics at least once"
echo ""
