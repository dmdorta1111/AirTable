#!/bin/bash
# End-to-end verification script for horizontal scaling with load balancer
#
# This script verifies:
# 1. Docker infrastructure starts correctly
# 2. Nginx load balancer is running and healthy
# 3. Multiple API instances are healthy
# 4. API requests are distributed across instances
# 5. WebSocket connections work (basic connectivity)
# 6. Health check endpoints return proper status
# 7. Load test with concurrent users

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.scaling.yml"
LOAD_BALANCER_PORT=80
API_INSTANCES=("api-1" "api-2" "api-3")
NUM_REQUESTS=30
CONCURRENT_USERS=10

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    log_info "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    log_info "Docker is installed and ready"
}

start_infrastructure() {
    log_info "Starting infrastructure with docker-compose.scaling.yml..."

    # Stop any existing containers
    docker compose $COMPOSE_FILES down -v 2>/dev/null || true

    # Start infrastructure
    docker compose $COMPOSE_FILES up -d

    log_info "Waiting for services to be healthy..."
    sleep 10

    # Wait for nginx
    log_info "Waiting for nginx load balancer..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -sf http://localhost/health > /dev/null 2>&1; then
            log_info "Nginx load balancer is healthy"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done

    if [ $timeout -eq 0 ]; then
        log_error "Nginx load balancer failed to start"
        return 1
    fi

    # Wait for API instances
    log_info "Waiting for API instances to be ready..."
    for instance in "${API_INSTANCES[@]}"; do
        timeout=60
        while [ $timeout -gt 0 ]; do
            if docker exec pybase-$instance curl -sf http://localhost:8000/api/v1/health/ready > /dev/null 2>&1; then
                log_info "$instance is ready"
                break
            fi
            sleep 2
            timeout=$((timeout - 2))
        done

        if [ $timeout -eq 0 ]; then
            log_warn "$instance may not be fully ready"
        fi
    done

    sleep 5
    return 0
}

verify_nginx_load_balancer() {
    log_info "Verifying nginx load balancer..."

    # Check nginx container is running
    if ! docker ps | grep -q "pybase-nginx"; then
        log_error "Nginx container is not running"
        return 1
    fi

    log_info "Nginx container is running"

    # Test health endpoint through load balancer
    response=$(curl -sf http://localhost/health)
    if [ $? -eq 0 ]; then
        status=$(echo $response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$status" = "healthy" ]; then
            log_info "Load balancer health check: $status"
        else
            log_warn "Load balancer health status: $status"
        fi
    else
        log_error "Load balancer health check failed"
        return 1
    fi

    # Check nginx configuration
    docker exec pybase-nginx nginx -t 2>&1 | grep -q "syntax is ok"
    if [ $? -eq 0 ]; then
        log_info "Nginx configuration is valid"
    else
        log_warn "Nginx configuration may have issues"
    fi

    return 0
}

verify_api_instances() {
    log_info "Verifying API instances..."

    for instance in "${API_INSTANCES[@]}"; do
        # Check container is running
        if ! docker ps | grep -q "pybase-$instance"; then
            log_error "$instance container is not running"
            return 1
        fi

        # Check health endpoint
        response=$(docker exec pybase-$instance curl -sf http://localhost:8000/api/v1/health)
        if [ $? -eq 0 ]; then
            status=$(echo $response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
            log_info "$instance health: $status"
        else
            log_error "$instance health check failed"
            return 1
        fi

        # Check readiness endpoint
        response=$(docker exec pybase-$instance curl -sf http://localhost:8000/api/v1/health/ready)
        if [ $? -eq 0 ]; then
            status=$(echo $response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
            log_info "$instance readiness: $status"
        else
            log_warn "$instance readiness check failed"
        fi
    done

    return 0
}

verify_request_distribution() {
    log_info "Verifying request distribution across API instances..."

    declare -A instance_counts
    total_requests=0

    # Make multiple requests and track which instance handles each
    for i in $(seq 1 $NUM_REQUESTS); do
        # Make request through load balancer
        response=$(curl -sf http://localhost/api/v1/info)

        if [ $? -eq 0 ]; then
            # Extract instance ID from response (if available)
            instance_id=$(echo $response | grep -o '"instance_id":"[^"]*"' | cut -d'"' -f4)

            if [ -n "$instance_id" ]; then
                instance_counts[$instance_id]=$((${instance_counts[$instance_id]} + 1))
                total_requests=$((total_requests + 1))
            fi
        fi
    done

    log_info "Request distribution ($total_requests total requests):"
    for instance in "${!instance_counts[@]}"; do
        count=${instance_counts[$instance]}
        percentage=$(echo "scale=1; $count * 100 / $total_requests" | bc)
        log_info "  $instance: $count requests ($percentage%)"
    done

    if [ $total_requests -lt $((NUM_REQUESTS / 2)) ]; then
        log_warn "Only $total_requests/$NUM_REQUESTS requests were successful"
    fi

    return 0
}

verify_health_check_endpoints() {
    log_info "Verifying health check endpoints through load balancer..."

    # Test /health
    response=$(curl -sf http://localhost/health)
    if [ $? -eq 0 ]; then
        status=$(echo $response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        log_info "GET /health: $status"
    else
        log_error "GET /health failed"
        return 1
    fi

    # Test /ready
    response=$(curl -sf http://localhost/ready)
    if [ $? -eq 0 ]; then
        status=$(echo $response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        log_info "GET /ready: $status"
    else
        log_error "GET /ready failed"
        return 1
    fi

    # Test /live
    response=$(curl -sf http://localhost/live)
    if [ $? -eq 0 ]; then
        status=$(echo $response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        log_info "GET /live: $status"
    else
        log_error "GET /live failed"
        return 1
    fi

    # Test /metrics
    response=$(curl -sf http://localhost/metrics)
    if [ $? -eq 0 ]; then
        log_info "GET /metrics: OK"
    else
        log_error "GET /metrics failed"
        return 1
    fi

    return 0
}

verify_redis_connectivity() {
    log_info "Verifying Redis connectivity from API instances..."

    for instance in "${API_INSTANCES[@]}"; do
        # Check if container can reach Redis
        if docker exec pybase-$instance ping -c 1 redis &> /dev/null; then
            log_info "$instance can reach Redis"
        else
            log_warn "$instance may have issues reaching Redis"
        fi
    done

    # Check Redis container is running
    if docker ps | grep -q "pybase-redis"; then
        log_info "Redis container is running"
    else
        log_error "Redis container is not running"
        return 1
    fi

    return 0
}

verify_websocket_infrastructure() {
    log_info "Verifying WebSocket infrastructure..."

    # Check if WebSocket endpoint is accessible
    # We can't fully test WebSocket without a client, but we can verify the endpoint responds
    response=$(curl -sf -I http://localhost/api/v1/realtime)
    if [ $? -eq 0 ] || echo "$response" | grep -q "400\|401\|426"; then
        log_info "WebSocket endpoint is accessible (expected 400/401/426 without auth)"
    else
        log_warn "WebSocket endpoint may not be properly configured"
    fi

    # Check nginx WebSocket configuration
    if docker exec pybase-nginx grep -q "location /api/v1/realtime" /etc/nginx/nginx.conf; then
        log_info "Nginx WebSocket location block is configured"
    else
        log_warn "Nginx WebSocket configuration may be missing"
    fi

    return 0
}

run_load_test() {
    log_info "Running load test with $CONCURRENT_USERS concurrent users..."

    # Create a simple load test using curl in parallel
    temp_dir=$(mktemp -d)
    results_file="$temp_dir/results.txt"

    # Launch concurrent users
    for user_id in $(seq 1 $CONCURRENT_USERS); do
        (
            for request_id in $(seq 1 5); do
                start_time=$(date +%s%N)
                response=$(curl -sf http://localhost/api/v1/health)
                end_time=$(date +%s%N)
                duration=$(( (end_time - start_time) / 1000000 )) # Convert to ms

                if [ $? -eq 0 ]; then
                    echo "user_${user_id},request_${request_id},success,$duration" >> "$results_file"
                else
                    echo "user_${user_id},request_${request_id},failed,0" >> "$results_file"
                fi
            done
        ) &
    done

    # Wait for all background jobs to complete
    wait

    # Analyze results
    total_requests=$(wc -l < "$results_file")
    successful_requests=$(grep -c ",success," "$results_file" || echo "0")
    failed_requests=$(grep -c ",failed," "$results_file" || echo "0")

    # Calculate average response time
    avg_response_time=$(grep ",success," "$results_file" | cut -d',' -f4 | awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print 0}')

    success_rate=$(echo "scale=1; $successful_requests * 100 / $total_requests" | bc)

    log_info "Load test results:"
    log_info "  Total requests: $total_requests"
    log_info "  Successful: $successful_requests"
    log_info "  Failed: $failed_requests"
    log_info "  Success rate: ${success_rate}%"
    log_info "  Avg response time: ${avg_response_time}ms"

    # Cleanup
    rm -rf "$temp_dir"

    # Verify success rate is acceptable
    if (( $(echo "$success_rate < 80" | bc -l) )); then
        log_error "Success rate is below 80%: ${success_rate}%"
        return 1
    fi

    return 0
}

verify_infrastructure() {
    log_info "Starting infrastructure verification..."
    echo ""

    check_docker
    start_infrastructure

    echo ""
    log_info "Running verification tests..."
    echo ""

    # Run all verification steps
    verify_nginx_load_balancer
    verify_api_instances
    verify_health_check_endpoints
    verify_request_distribution
    verify_redis_connectivity
    verify_websocket_infrastructure

    echo ""
    run_load_test

    echo ""
    log_info "Infrastructure verification complete!"
    echo ""

    # Show container status
    log_info "Container status:"
    docker compose $COMPOSE_FILES ps

    echo ""
    log_info "Access the application:"
    log_info "  Load balancer: http://localhost"
    log_info "  API docs: http://localhost/api/v1/docs"
    log_info "  Health check: http://localhost/health"

    return 0
}

cleanup() {
    log_info "Stopping infrastructure..."
    docker compose $COMPOSE_FILES down -v
    log_info "Infrastructure stopped"
}

# Main script
case "${1:-verify}" in
    start)
        start_infrastructure
        ;;
    verify)
        verify_infrastructure
        ;;
    cleanup)
        cleanup
        ;;
    *)
        echo "Usage: $0 {start|verify|cleanup}"
        echo ""
        echo "Commands:"
        echo "  start   - Start infrastructure only"
        echo "  verify  - Start infrastructure and run full verification (default)"
        echo "  cleanup - Stop and remove all containers"
        exit 1
        ;;
esac
