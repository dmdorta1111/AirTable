# End-to-End Testing Guide for Horizontal Scaling

This guide explains how to run end-to-end verification tests for the horizontal scaling with load balancer implementation.

## Overview

The horizontal scaling implementation includes:
- Nginx load balancer with sticky sessions
- Multiple API instances (api-1, api-2, api-3)
- Redis pub/sub for WebSocket cross-instance messaging
- Shared PostgreSQL and Redis for stateless API instances

## Prerequisites

Before running e2e tests, ensure you have:

1. **Docker and Docker Compose** installed and running
   ```bash
   docker --version
   docker compose version
   ```

2. **Required ports available** on your machine:
   - Port 80 (nginx load balancer)
   - Port 5432 (PostgreSQL)
   - Port 6379 (Redis)
   - Port 9000 (MinIO)

3. **Bash shell** (for verification script)
   - Linux/macOS: Built-in
   - Windows: Use Git Bash or WSL

## Quick Start

### Option 1: Automated Verification Script (Recommended)

Run the comprehensive infrastructure verification:

```bash
# Run full verification (starts infrastructure, runs tests, shows results)
./tests/e2e/verify_horizontal_scaling.sh verify

# Or just start infrastructure
./tests/e2e/verify_horizontal_scaling.sh start

# Cleanup when done
./tests/e2e/verify_horizontal_scaling.sh cleanup
```

The verification script will:
- ✅ Start Docker infrastructure with docker-compose.scaling.yml
- ✅ Verify nginx load balancer is running
- ✅ Verify all 3 API instances are healthy
- ✅ Test API request distribution across instances
- ✅ Verify health check endpoints work
- ✅ Verify Redis connectivity
- ✅ Run load test with 10 concurrent users
- ✅ Display detailed results and metrics

### Option 2: Manual Testing

#### Step 1: Start Infrastructure

```bash
# Start all services (nginx + 3 API instances + dependencies)
docker compose -f docker-compose.yml -f docker-compose.scaling.yml up -d

# Wait for services to be healthy (30-60 seconds)
docker compose -f docker-compose.yml -f docker-compose.scaling.yml ps
```

#### Step 2: Verify Nginx Load Balancer

```bash
# Check nginx container is running
docker ps | grep pybase-nginx

# Test health endpoint through load balancer
curl http://localhost/health

# Expected response:
# {"status":"healthy","environment":"development","version":"0.1.0"}
```

#### Step 3: Verify API Instances

```bash
# Check all API instances are running
docker ps | grep pybase-api

# Test each API instance directly
docker exec pybase-api-1 curl http://localhost:8000/api/v1/health
docker exec pybase-api-2 curl http://localhost:8000/api/v1/health
docker exec pybase-api-3 curl http://localhost:8000/api/v1/health

# Expected response from each:
# {"status":"healthy","environment":"development","version":"0.1.0"}
```

#### Step 4: Test Request Distribution

```bash
# Make multiple requests through load balancer
for i in {1..20}; do
  curl -s http://localhost/api/v1/info | grep -o '"instance_id":"[^"]*"'
done

# You should see different instance IDs in responses
# (api-1, api-2, api-3)
```

#### Step 5: Test Health Check Endpoints

```bash
# Basic health check
curl http://localhost/health

# Readiness check (DB + Redis)
curl http://localhost/ready

# Liveness check (lightweight)
curl http://localhost/live

# Metrics endpoint (for auto-scaling)
curl http://localhost/metrics
```

#### Step 6: Verify Redis Connectivity

```bash
# Check Redis is running
docker ps | grep pybase-redis

# Check API instances can reach Redis
docker exec pybase-api-1 ping -c 1 redis
docker exec pybase-api-2 ping -c 1 redis
docker exec pybase-api-3 ping -c 1 redis

# Test Redis pub/sub manager (Python)
docker exec pybase-api-1 python -c "
from src.pybase.realtime.redis_pubsub import get_pubsub_manager
manager = get_pubsub_manager()
print('Redis pub/sub manager initialized:', manager is not None)
"
```

#### Step 7: Run Python E2E Tests

```bash
# Run all horizontal scaling e2e tests
pytest tests/e2e/test_horizontal_scaling.py -v -s

# Run specific test
pytest tests/e2e/test_horizontal_scaling.py::TestHorizontalScalingE2E::test_load_balancer_distributes_requests -v -s
```

#### Step 8: Cleanup

```bash
# Stop and remove all containers
docker compose -f docker-compose.yml -f docker-compose.scaling.yml down -v

# Verify cleanup
docker ps
```

## Verification Checklist

Use this checklist to verify all components are working correctly:

### Infrastructure
- [ ] Docker and Docker Compose installed
- [ ] Ports 80, 5432, 6379, 9000 available
- [ ] All containers start successfully
- [ ] No container crashes or restarts

### Nginx Load Balancer
- [ ] Nginx container is running
- [ ] Nginx configuration is valid (`docker exec pybase-nginx nginx -t`)
- [ ] Health endpoint responds: `curl http://localhost/health`
- [ ] Proxying to API instances works

### API Instances
- [ ] All 3 API instances running (api-1, api-2, api-3)
- [ ] Each instance responds to health checks
- [ ] Each instance can reach PostgreSQL
- [ ] Each instance can reach Redis
- [ ] Each instance has unique INSTANCE_ID

### Health Check Endpoints
- [ ] `/health` returns basic status
- [ ] `/ready` checks database and Redis connectivity
- [ ] `/live` returns lightweight liveness status
- [ ] `/metrics` returns resource utilization data

### Request Distribution
- [ ] Requests are distributed across API instances
- [ ] Load balancer uses least_conn algorithm
- [ ] Sticky sessions enabled (ip_hash)
- [ ] No single instance is overloaded

### Redis Connectivity
- [ ] Redis container is running
- [ ] API instances can ping Redis
- [ ] Redis pub/sub manager initializes
- [ ] Session store works across instances

### WebSocket Infrastructure
- [ ] WebSocket endpoint accessible: `curl -I http://localhost/api/v1/realtime`
- [ ] Nginx has WebSocket location block configured
- [ ] Long timeout settings configured (7 days)
- [ ] Proxy buffering disabled for WebSockets

### Load Testing
- [ ] 10 concurrent users can make requests simultaneously
- [ ] Success rate >= 80%
- [ ] Average response time < 5 seconds
- [ ] No connection errors or timeouts

## Troubleshooting

### Issue: Port 80 already in use

**Solution:** Stop the service using port 80 or change the nginx port:

```bash
# Find what's using port 80
sudo lsof -i :80

# Or change nginx port in docker-compose.scaling.yml
ports:
  - "8080:80"  # Use port 8080 instead

# Then access via http://localhost:8080
```

### Issue: API instances not starting

**Solution:** Check logs for specific errors:

```bash
# Check logs for api-1
docker logs pybase-api-1

# Check logs for all API instances
docker compose -f docker-compose.scaling.yml logs api-1 api-2 api-3
```

Common issues:
- Database not ready: Wait 30-60 seconds for PostgreSQL to initialize
- Redis connection failed: Check Redis container is healthy
- Module import errors: Verify all dependencies are installed

### Issue: Requests not distributed evenly

**Explanation:** This is normal behavior with `least_conn` algorithm and low traffic.
With only 3 instances and light testing, distribution may not appear perfectly even.

**Verification:** Increase request count to 100+ for better distribution visibility:

```bash
for i in {1..100}; do
  curl -s http://localhost/api/v1/info | grep -o '"instance_id":"[^"]*"'
done | sort | uniq -c
```

### Issue: WebSocket connections fail

**Solution:** Verify nginx WebSocket configuration:

```bash
# Check nginx configuration
docker exec pybase-nginx cat /etc/nginx/nginx.conf | grep -A 20 "location /api/v1/realtime"

# Verify proxy headers are correct (Upgrade, Connection)
# Check timeout settings (7d for WebSockets)
```

### Issue: Redis pub/sub not working

**Solution:** Verify Redis is accessible and pub/sub manager initializes:

```bash
# Test Redis from API instance
docker exec pybase-api-1 redis-cli -h redis ping

# Should return: PONG

# Test pub/sub manager
docker exec pybase-api-1 python -c "
from src.pybase.realtime.redis_pubsub import get_pubsub_manager
import asyncio

async def test():
    manager = get_pubsub_manager()
    result = await manager.publish('test:channel', {'message': 'test'})
    print('Publish result:', result)

asyncio.run(test())
"
```

## Expected Results

When everything is working correctly, you should see:

### Container Status
```
NAME            IMAGE         STATUS
pybase-nginx    nginx:alpine  Up X seconds (healthy)
pybase-api-1    pybase:latest Up X seconds (healthy)
pybase-api-2    pybase:latest Up X seconds (healthy)
pybase-api-3    pybase:latest Up X seconds (healthy)
pybase-postgres postgres:15   Up X seconds (healthy)
pybase-redis    redis:7       Up X seconds (healthy)
pybase-minio    minio/minio   Up X seconds (healthy)
```

### Load Test Results
```
Load test results:
  Total requests: 50
  Successful: 50
  Failed: 0
  Success rate: 100.0%
  Avg response time: 45ms
```

### Request Distribution
```
Request distribution across instances:
  pybase-api-1: 10 requests (33.3%)
  pybase-api-2: 10 requests (33.3%)
  pybase-api-3: 10 requests (33.3%)
```

## Continuous Integration

For CI/CD pipelines, use the following commands:

```bash
# Start infrastructure
docker compose -f docker-compose.yml -f docker-compose.scaling.yml up -d

# Wait for health
timeout 120 bash -c 'until curl -sf http://localhost/health > /dev/null; do sleep 2; done'

# Run e2e tests
pytest tests/e2e/test_horizontal_scaling.py -v --tb=short

# Cleanup on exit (even if tests fail)
docker compose -f docker-compose.yml -f docker-compose.scaling.yml down -v

# Exit with test result
exit $?
```

## Performance Benchmarks

Expected performance on typical development hardware:

| Metric | Target | Acceptable |
|--------|--------|------------|
| Load balancer response time | < 50ms | < 100ms |
| API instance response time | < 100ms | < 500ms |
| Concurrent users (10 users, 5 req each) | 100% success | >= 80% success |
| Request distribution | Even (~33% each) | No single instance > 80% |

## Next Steps

After e2e verification passes:

1. **Review metrics:** Check `/metrics` endpoint for resource utilization
2. **Test WebSockets:** Use WebSocket client to test real-time messaging
3. **Load testing:** Use tools like Locust or Apache Bench for heavy load testing
4. **Monitor logs:** Check container logs for errors or warnings
5. **Production deployment:** Follow production deployment guide

## Additional Resources

- [Nginx Load Balancing Guide](https://docs.nginx.com/nginx/admin-guide/load-balancer/)
- [Docker Compose Scaling](https://docs.docker.com/compose/compose-file/compose-file-v3/#scale)
- [Horizontal Scaling Best Practices](./docs/scaling-guide.md)
- [WebSocket Protocol RFC](https://tools.ietf.org/html/rfc6455)
