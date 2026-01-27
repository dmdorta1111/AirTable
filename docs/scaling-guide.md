# Scaling Guide

## Overview
PyBase is designed to scale horizontally across multiple dimensions - API instances, worker processes, caching layers, and database connections. This guide provides infrastructure recommendations based on your user count and workload characteristics.

## Scaling Dimensions

### 1. Application Layer
- **API Instances**: FastAPI workers handling HTTP/WebSocket requests
- **Worker Processes**: Celery workers for async tasks (CAD extraction, file processing)
- **Load Balancer**: Distributes traffic and manages session affinity

### 2. Data Layer
- **PostgreSQL**: Primary database with connection pooling
- **Redis**: Distributed caching, session storage, Celery broker
- **Object Storage**: S3-compatible storage for attachments and CAD files

### 3. Caching Layer
- **Application Cache**: Redis for frequently accessed data
- **Session Store**: Redis for WebSocket session management
- **Query Cache**: Database-level query result caching

## Deployment Tiers

### Small Deployment (1-50 Users)
**Use Case**: Small teams, single-tenant deployments, development/staging environments

**Infrastructure**:
- **API Instances**: 1-2 instances (4 vCPU, 8 GB RAM each)
- **Workers**: 1-2 worker processes
- **Database**: Managed PostgreSQL (db.t3.medium - 2 vCPU, 4 GB RAM)
- **Redis**: Single node (cache.t3.small - 1 vCPU, 1.5 GB RAM)
- **Load Balancer**: Cloud provider LB or single nginx instance

**Configuration**:
```bash
# .env settings
WORKERS_PER_INSTANCE=2
MAX_CONNECTIONS=50
REDIS_MAX_CONNECTIONS=20
CELERY_WORKER_CONCURRENCY=2
```

**Estimated Cost**: $100-300/month (AWS)

**Scaling Strategy**: Vertical scale until you hit 50 concurrent users

---

### Medium Deployment (50-500 Users)
**Use Case**: Mid-sized engineering teams, growing organizations

**Infrastructure**:
- **API Instances**: 3-5 instances behind load balancer (4 vCPU, 16 GB RAM each)
- **Workers**: 3-5 worker processes (can scale independently)
- **Database**: Managed PostgreSQL with read replicas (db.m5.large - 2 vCPU, 8 GB RAM)
- **Redis**: Redis Cluster (cache.m5.medium - 2 vCPU, 5.2 GB RAM)
- **Load Balancer**: Application Load Balancer with sticky sessions

**Configuration**:
```bash
# .env settings
WORKERS_PER_INSTANCE=4
MAX_CONNECTIONS=200
REDIS_MAX_CONNECTIONS=50
CELERY_WORKER_CONCURRENCY=4
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

**Estimated Cost**: $800-2,000/month (AWS)

**Scaling Strategy**:
- Horizontal scaling for API instances
- Auto-scale workers based on Celery queue depth
- Database read replicas for reporting queries

---

### Large Deployment (500-5,000 Users)
**Use Case**: Large enterprises, multi-tenant SaaS deployments

**Infrastructure**:
- **API Instances**: 5-10 instances (8 vCPU, 32 GB RAM each)
- **Workers**: Dedicated worker node group (8-16 workers)
- **Database**: Managed PostgreSQL with HA and read replicas (db.m5.2xlarge - 8 vCPU, 32 GB RAM)
- **Redis**: Redis Cluster in sharded mode (3+ nodes)
- **Load Balancer**: Network Load Balancer + Application Load Balancer
- **CDN**: CloudFront/Cloud CDN for static assets

**Configuration**:
```bash
# .env settings
WORKERS_PER_INSTANCE=8
MAX_CONNECTIONS=500
REDIS_MAX_CONNECTIONS=100
CELERY_WORKER_CONCURRENCY=8
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
```

**Estimated Cost**: $5,000-15,000/month (AWS)

**Scaling Strategy**:
- Auto-scaling groups for API instances (based on CPU/memory)
- Separate auto-scaling for worker nodes (based on queue depth)
- Database connection pooling with PgBouncer
- Redis clustering for high availability

---

### Enterprise Deployment (5,000+ Users)
**Use Case**: Very large organizations, high-throughput scenarios

**Infrastructure**:
- **API Instances**: 10+ instances across multiple availability zones
- **Workers**: Multiple worker pools by task type (extraction, processing, notifications)
- **Database**: PostgreSQL with connection pooling + read replicas + hot standby
- **Redis**: Redis Cluster with automatic failover
- **Load Balancer**: Multi-tier load balancing (NLB + ALB)
- **Message Queue**: RabbitMQ or Amazon MQ for advanced routing
- **Monitoring**: Prometheus + Grafana + AlertManager
- **Logging**: ELK Stack or Cloud Logging

**Configuration**:
```bash
# .env settings
WORKERS_PER_INSTANCE=16
MAX_CONNECTIONS=1000
REDIS_MAX_CONNECTIONS=200
CELERY_WORKER_CONCURRENCY=16
DB_POOL_SIZE=100
DB_MAX_OVERFLOW=200
```

**Estimated Cost**: $20,000+/month (AWS)

**Scaling Strategy**:
- Kubernetes deployment with HPA (Horizontal Pod Autoscaler)
- Database sharding for multi-tenant isolation
- Multi-region deployment for disaster recovery
- Advanced caching strategies (edge caching, CDN)

## Load Balancing Configuration

### Sticky Sessions (WebSocket Support)
PyBase uses WebSocket connections for real-time collaboration. Configure your load balancer for session affinity:

**AWS Application Load Balancer**:
```json
{
  "TargetGroupAttributes": [
    {
      "Key": "stickiness.enabled",
      "Value": "true"
    },
    {
      "Key": "stickiness.type",
      "Value": "lb_cookie"
    },
    {
      "Key": "stickiness.duration_seconds",
      "Value": "3600"
    }
  ]
}
```

**Nginx**:
```nginx
upstream pybase_backend {
    ip_hash;  # Sticky sessions based on client IP
    server api1.pybase.internal:8000;
    server api2.pybase.internal:8000;
    server api3.pybase.internal:8000;
}
```

**HAProxy**:
```
backend pybase_backend
    balance roundrobin
    cookie SERVERID insert indirect nocache
    server api1 api1.pybase.internal:8000 cookie api1
    server api2 api2.pybase.internal:8000 cookie api2
    server api3 api3.pybase.internal:8000 cookie api3
```

## Database Scaling Strategies

### Connection Pooling
Use PgBouncer or SQLAlchemy's built-in pooling:

```python
# sqlalchemy/pool.py
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,          # Base connection count
    max_overflow=40,       # Additional connections under load
    pool_timeout=30,       # Wait time for connection
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

### Read Replicas
Route read queries to replicas for better performance:

```python
# Read/write splitting
async def get_db_read():
    async with read_replica_session() as session:
        yield session

async def get_db_write():
    async with primary_session() as session:
        yield session
```

### Query Optimization
- Add indexes on frequently filtered columns
- Use `EXPLAIN ANALYZE` to identify slow queries
- Consider materialized views for complex aggregations

## Caching Strategy

### Redis Caching Patterns

**1. Application-Level Caching**:
```python
from functools import lru_cache
from src.pybase.core.cache import cache_manager

@cache_manager.cache(ttl=3600)
async def get_table_schema(table_id: UUID):
    # Cache table schemas for 1 hour
    return await fetch_table_schema(table_id)
```

**2. Query Result Caching**:
```python
@cache_manager.cache(ttl=300)
async def get_record_count(table_id: UUID):
    return await db.execute(
        select(func.count()).where(Record.table_id == table_id)
    )
```

**3. Session Caching**:
```python
# WebSocket sessions stored in Redis
await redis.setex(
    f"session:{user_id}:{table_id}",
    3600,
    json.dumps(session_data)
)
```

### Cache Invalidation
- **Time-based**: Set appropriate TTL values
- **Event-based**: Invalidate cache on data updates
- **Versioned**: Include data version in cache keys

## Worker Scaling

### Celery Queue Configuration
Create separate queues for different task types:

```python
# celery_config.py
task_routes = {
    'src.pybase.extraction.cad.*': {'queue': 'cad_extraction'},
    'src.pybase.extraction.pdf.*': {'queue': 'pdf_extraction'},
    'src.pybase.services.notification.*': {'queue': 'notifications'},
    'src.pybase.services.email.*': {'queue': 'email'},
}
```

### Worker Pool Scaling
```bash
# Heavy extraction tasks (CPU-intensive)
celery -A src.pybase.main worker -Q cad_extraction -c 2 --loglevel=info

# Fast notification tasks (I/O-bound)
celery -A src.pybase.main worker -Q notifications -c 8 --loglevel=info
```

### Auto-Scaling Workers
Monitor queue depth and scale workers dynamically:

```python
# workerscaler.py
async def monitor_and_scale():
    queue_depth = await get_celery_queue_depth('cad_extraction')
    if queue_depth > 100:
        await scale_up_workers('cad_extraction', +2)
    elif queue_depth < 10:
        await scale_down_workers('cad_extraction', -1)
```

## Monitoring and Metrics

### Key Metrics to Monitor

**Application Layer**:
- Request latency (p50, p95, p99)
- Error rate (4xx, 5xx)
- Active WebSocket connections
- Worker queue depth
- CPU/Memory utilization

**Database Layer**:
- Connection pool usage
- Query execution time
- Database size growth
- Replication lag
- Deadlocks/locks

**Cache Layer**:
- Cache hit/miss ratio
- Memory usage
- Connection count
- Eviction rate

### Scaling Triggers

**Scale Up When**:
- CPU > 70% for 5+ minutes
- Memory > 80% for 5+ minutes
- Request latency p95 > 2x baseline
- Queue depth > 100 tasks
- Error rate > 5%

**Scale Down When**:
- CPU < 30% for 15+ minutes
- Memory < 40% for 15+ minutes
- Queue depth < 10 tasks
- Excess capacity for 1+ hour

## Performance Tuning

### FastAPI Optimization
```python
# uvicorn startup settings
uvicorn src.pybase.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 300 \
    --access-log
```

### PostgreSQL Optimization
```sql
-- postgresql.conf settings
shared_buffers = 4GB              # 25% of RAM
effective_cache_size = 12GB       # 50-75% of RAM
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1            # For SSD storage
```

### Redis Optimization
```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
tcp-keepalive 300
timeout 0
```

## Cost Optimization

### Right-Sizing
- Start with recommended specs, adjust based on actual usage
- Use reserved instances for steady workloads (>70% utilization)
- Use spot instances for worker nodes (fault-tolerant)

### Resource Efficiency
- Enable auto-scaling to avoid over-provisioning
- Use Graviton/ARM instances for cost savings (30-40% cheaper)
- Implement request batching and compression
- Set up lifecycle policies for object storage

## Migration Path

### From Small to Medium
1. Add load balancer in front of existing instances
2. Deploy second API instance
3. Configure Redis for session storage
4. Test WebSocket connectivity with sticky sessions
5. Add database read replica
6. Gradually shift traffic to load-balanced setup

### From Medium to Large
1. Move to managed Kubernetes (EKS/GKE/AKS)
2. Implement Horizontal Pod Autoscaler
3. Add Redis Cluster
4. Implement PgBouncer for connection pooling
5. Set up comprehensive monitoring
6. Configure multi-AZ deployment

## Troubleshooting

### High Memory Usage
- Check for connection leaks in database/Redis
- Review worker memory limits
- Analyze large query result sets
- Verify cache TTL settings

### Slow API Responses
- Check database query performance
- Verify cache hit rates
- Review connection pool exhaustion
- Analyze worker queue depth

### WebSocket Disconnections
- Verify sticky session configuration
- Check load balancer timeout settings
- Review Redis session storage
- Monitor network stability

### Database Connection Exhaustion
- Increase pool size or max overflow
- Check for long-running transactions
- Verify connection cleanup on app shutdown
- Review connection timeout settings

## Additional Resources

- **Deployment Guide**: See `docs/deployment-guide.md` for setup instructions
- **Architecture**: See `docs/system-architecture.md` for system design
- **Monitoring**: See `docs/monitoring.md` for observability setup (if available)
- **Kubernetes**: See `kubernetes/` directory for K8s manifests

## Support and Community

For scaling questions or issues:
- GitHub Issues: https://github.com/pybase/pybase/issues
- Documentation: https://docs.pybase.io
- Community Discord: https://discord.gg/pybase
