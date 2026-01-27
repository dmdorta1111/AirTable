@echo off
REM End-to-End Verification of Prometheus/Grafana Monitoring Stack for Windows
REM This script verifies all components of the monitoring stack are working correctly

setlocal enabledelayedexpansion

REM Configuration
set API_METRICS_URL=http://localhost:8000/api/v1/metrics
set PROMETHEUS_URL=http://localhost:9090
set GRAFANA_URL=http://localhost:3000

echo ========================================
echo E2E Verification: Monitoring Stack
echo ========================================
echo.

REM Step 1: Check Docker services
echo Step 1: Verifying Docker services...
echo --------------------------------------

docker-compose ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose not accessible. Start services with:
    echo   docker-compose up -d
    echo   docker-compose --profile worker up -d
    exit /b 1
)
echo [PASS] Docker Compose is accessible

REM Step 2: Verify API metrics endpoint
echo.
echo Step 2: Verifying API /metrics endpoint...
echo --------------------------------------

curl -s "%API_METRICS_URL%" | findstr "http_requests_total" >nul
if errorlevel 1 (
    echo [FAIL] API /metrics endpoint does not return http_requests_total
    echo Start the API service with: docker-compose up -d api
    exit /b 1
)
echo [PASS] API /metrics endpoint returns http_requests_total

curl -s "%API_METRICS_URL%" | findstr "api_latency_histogram" >nul
if errorlevel 1 (
    echo [WARN] API /metrics endpoint missing api_latency_histogram
) else (
    echo [PASS] API /metrics endpoint returns api_latency_histogram
)

REM Step 3: Verify Prometheus targets
echo.
echo Step 3: Verifying Prometheus targets...
echo --------------------------------------

curl -s "%PROMETHEUS_URL%/-/healthy" | findstr "Prometheus is Healthy" >nul
if errorlevel 1 (
    echo [FAIL] Prometheus is not healthy
    echo Check Prometheus logs: docker-compose logs prometheus
    exit /b 1
)
echo [PASS] Prometheus is healthy

REM Check targets
echo Checking Prometheus targets...
curl -s "%PROMETHEUS_URL%/api/v1/targets" > targets_temp.json
findstr /C:"\"health\":\"up\"" targets_temp.json | find /C "\"health\":\"up\"" > up_count.txt
set /p UP_COUNT=<up_count.txt
echo   Targets UP: !UP_COUNT!

if !UP_COUNT! GEQ 2 (
    echo [PASS] At least 2 Prometheus targets are UP
) else (
    echo [WARN] Only !UP_COUNT! targets UP, expected at least 2
)

REM Cleanup temp files
del targets_temp.json up_count.txt 2>nul

REM Step 4: Verify Grafana
echo.
echo Step 4: Verifying Grafana...
echo --------------------------------------

curl -s "%GRAFANA_URL%/api/health" | findstr "database" >nul
if errorlevel 1 (
    echo [WARN] Grafana health check inconclusive
) else (
    echo [PASS] Grafana is responding
)

REM Check datasources
curl -s "%GRAFANA_URL%/api/datasources" | findstr "Prometheus" >nul
if errorlevel 1 (
    echo [FAIL] Prometheus datasource not configured in Grafana
    echo Check provisioning: docker/grafana/provisioning/datasources/prometheus.yml
    exit /b 1
)
echo [PASS] Prometheus datasource configured in Grafana

REM Check dashboards
curl -s "%GRAFANA_URL%/api/search" | findstr "Overview" >nul
if errorlevel 1 (
    echo [WARN] Overview dashboard not found
) else (
    echo [PASS] Overview dashboard is available
)

curl -s "%GRAFANA_URL%/api/search" | findstr "API Performance" >nul
if errorlevel 1 (
    echo [WARN] API Performance dashboard not found
) else (
    echo [PASS] API Performance dashboard is available
)

REM Step 5: Summary
echo.
echo ========================================
echo Verification Summary
echo ========================================
echo.
echo Monitoring Stack URLs:
echo   - Prometheus: %PROMETHEUS_URL%
echo   - Grafana: %GRAFANA_URL% (admin/admin)
echo   - API Metrics: %API_METRICS_URL%
echo.
echo Next Steps:
echo   1. Open Grafana at %GRAFANA_URL%
echo   2. Login with admin/admin
echo   3. View the Overview dashboard
echo   4. Check API Performance dashboard
echo   5. Review alerts at %PROMETHEUS_URL%/alerts
echo.
echo All critical checks passed!
echo.

endlocal
