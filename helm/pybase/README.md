# PyBase Helm Chart

> Production-ready Helm chart for deploying PyBase to any Kubernetes cluster

[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.24+-326ce5.svg)](https://kubernetes.io/)
[![Helm](https://img.shields.io/badge/Helm-3.0+-0f168e.svg)](https://helm.sh/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-dc382d.svg)](https://redis.io/)

## Overview

This Helm chart installs PyBase on a Kubernetes cluster using the Helm package manager. It deploys all necessary components including PostgreSQL, Redis, MinIO, Meilisearch, FastAPI backend, Celery workers, and React frontend with production-ready configuration.

## Prerequisites

- **Kubernetes cluster** (version 1.24+)
- **Helm 3.0+** installed
- **kubectl** configured to access your cluster
- **StorageClass** configured for dynamic provisioning
- **Ingress controller** installed (nginx, traefik, or cloud provider's ingress)

**Cluster Resource Requirements:**
- **Minimum**: 4 CPU cores, 8Gi RAM (development)
- **Recommended**: 8 CPU cores, 16Gi RAM (production)
- **Storage**: 30Gi+ for PostgreSQL, Redis, MinIO, Meilisearch

## Quick Start

### Default Installation

```bash
# 1. Add the Helm repository (when published)
# helm repo add pybase https://charts.pybase.dev
# helm repo update

# 2. Install from local directory
helm install pybase . -n pybase --create-namespace

# 3. Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=pybase -n pybase --timeout=300s

# 4. Get the application URL
kubectl get ingress -n pybase
```

### Installation with Custom Values

```bash
# Create a custom values file
cat > my-values.yaml <<EOF
pybase:
  domain: pybase.example.com
  environment: production

api:
  replicaCount: 3
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

postgresql:
  enabled: true

redis:
  enabled: true

minio:
  enabled: true
EOF

# Install with custom values
helm install pybase . -n pybase -f my-values.yaml
```

### Installation with Secrets

```bash
# Generate a secret key
SECRET_KEY=$(openssl rand -hex 32)

# Create secrets file
cat > secret-values.yaml <<EOF
secrets:
  secretKey: "${SECRET_KEY}"
  databaseUrl: "postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgresql:5432/pybase"
  redisUrl: "redis://:CHANGE_ME@pybase-redis:6379/0"
  s3AccessKey: "minioadmin"
  s3SecretKey: "CHANGE_ME"
  smtpPassword: ""
  werk24ApiKey: ""
  sentryDsn: ""
EOF

# Install with secrets
helm install pybase . -n pybase -f secret-values.yaml
```

## Configuration

### Global Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global image registry for all images | `""` |
| `global.imagePullPolicy` | Global image pull policy | `IfNotPresent` |
| `global.imagePullSecrets` | Global image pull secrets | `[]` |
| `global.env` | Global environment variables | `[]` |
| `global.labels` | Global labels for all resources | `{}` |

### PyBase Application Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `pybase.name` | Application name | `"PyBase"` |
| `pybase.version` | Application version | `"0.1.0"` |
| `pybase.domain` | Domain name for Ingress | `pybase.local` |
| `pybase.environment` | Environment (development, staging, production) | `production` |
| `pybase.logLevel` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO` |
| `pybase.debug` | Enable debug mode | `false` |
| `pybase.secretKey` | JWT signing key (**REQUIRED**) | `""` |
| `pybase.corsOrigins` | CORS allowed origins | `"http://localhost:3000,http://localhost:8000"` |
| `pybase.maxUploadSize` | Maximum file upload size (MB) | `100` |
| `pybase.allowedExtensions` | Allowed file extensions | `"pdf,dxf,dwg,ifc,stp,step,png,jpg,jpeg,gif,webp,xlsx,csv"` |

### Feature Flags

| Parameter | Description | Default |
|-----------|-------------|---------|
| `pybase.features.registration` | Enable user registration | `true` |
| `pybase.features.apiKeys` | Enable API key authentication | `true` |
| `pybase.features.extraction` | Enable CAD/PDF extraction | `true` |
| `pybase.features.search` | Enable search functionality | `true` |
| `pybase.features.realtime` | Enable real-time features (WebSockets) | `true` |
| `pybase.features.emailNotifications` | Enable email notifications | `false` |

### API Server Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.enabled` | Enable API server deployment | `true` |
| `api.replicaCount` | Number of API replicas | `2` |
| `api.image.repository` | API image repository | `pybase/api` |
| `api.image.tag` | API image tag | `"0.1.0"` |
| `api.image.pullPolicy` | API image pull policy | `IfNotPresent` |
| `api.container.port` | API container port | `8000` |
| `api.resources` | API resource requests/limits | See values.yaml |
| `api.autoscaling.enabled` | Enable HPA for API | `true` |
| `api.autoscaling.minReplicas` | Minimum API replicas | `2` |
| `api.autoscaling.maxReplicas` | Maximum API replicas | `10` |
| `api.autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization | `70` |
| `api.service.type` | API service type | `ClusterIP` |
| `api.service.port` | API service port | `8000` |

### Extraction Worker Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `extractionWorker.enabled` | Enable extraction worker | `true` |
| `extractionWorker.replicaCount` | Number of worker replicas | `2` |
| `extractionWorker.celery.concurrency` | Concurrent worker processes per pod | `2` |
| `extractionWorker.celery.queues` | Worker queues | `["pdf_extraction", "cad_extraction", "werk24_extraction", "bulk_extraction"]` |
| `extractionWorker.celery.taskTimeLimit` | Task time limit (seconds) | `3600` |
| `extractionWorker.resources` | Worker resource requests/limits | See values.yaml |
| `extractionWorker.terminationGracePeriodSeconds` | Grace period for long tasks | `3600` |

### Search Worker Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `searchWorker.enabled` | Enable search worker | `true` |
| `searchWorker.replicaCount` | Number of worker replicas | `2` |
| `searchWorker.celery.concurrency` | Concurrent worker processes per pod | `4` |
| `searchWorker.celery.queues` | Worker queues | `["search_indexing", "record_updates"]` |
| `searchWorker.celery.taskTimeLimit` | Task time limit (seconds) | `120` |
| `searchWorker.resources` | Worker resource requests/limits | See values.yaml |

### Frontend Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `frontend.enabled` | Enable frontend deployment | `true` |
| `frontend.replicaCount` | Number of frontend replicas | `2` |
| `frontend.image.repository` | Frontend image repository | `pybase/frontend` |
| `frontend.image.tag` | Frontend image tag | `"0.1.0"` |
| `frontend.container.port` | Frontend container port | `8080` |
| `frontend.resources` | Frontend resource requests/limits | See values.yaml |
| `frontend.service.type` | Frontend service type | `ClusterIP` |
| `frontend.service.port` | Frontend service port | `8080` |

### PostgreSQL Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable built-in PostgreSQL | `true` |
| `postgresql.image.repository` | PostgreSQL image repository | `postgres` |
| `postgresql.image.tag` | PostgreSQL image tag | `"16-alpine"` |
| `postgresql.username` | PostgreSQL username | `pybase` |
| `postgresql.database` | PostgreSQL database | `pybase` |
| `postgresql.persistence.size` | PVC size | `10Gi` |
| `postgresql.persistence.storageClass` | StorageClass | `""` (default) |
| `postgresql.resources` | PostgreSQL resource requests/limits | See values.yaml |

**To use external PostgreSQL:**
```yaml
postgresql:
  enabled: false

pybase:
  externalServices:
    databaseUrl: "postgresql+asyncpg://user:password@external-db:5432/pybase"
```

### Redis Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable built-in Redis | `true` |
| `redis.image.repository` | Redis image repository | `redis` |
| `redis.image.tag` | Redis image tag | `"7-alpine"` |
| `redis.port` | Redis port | `6379` |
| `redis.persistence.size` | PVC size | `2Gi` |
| `redis.persistence.storageClass` | StorageClass | `""` (default) |
| `redis.resources` | Redis resource requests/limits | See values.yaml |

**To use external Redis:**
```yaml
redis:
  enabled: false

pybase:
  externalServices:
    redisUrl: "redis://:password@external-redis:6379/0"
```

### MinIO Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `minio.enabled` | Enable built-in MinIO | `true` |
| `minio.image.repository` | MinIO image repository | `minio/minio` |
| `minio.image.tag` | MinIO image tag | `latest` |
| `minio.apiPort` | MinIO API port | `9000` |
| `minio.consolePort` | MinIO console port | `9001` |
| `minio.persistence.size` | PVC size | `10Gi` |
| `minio.persistence.storageClass` | StorageClass | `""` (default) |
| `minio.resources` | MinIO resource requests/limits | See values.yaml |

**To use external S3:**
```yaml
minio:
  enabled: false

pybase:
  externalServices:
    s3:
      enabled: true
      endpoint: "https://s3.amazonaws.com"
      accessKey: "YOUR_ACCESS_KEY"
      secretKey: "YOUR_SECRET_KEY"
      bucket: "pybase-production"
      region: "us-east-1"
```

### Meilisearch Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `meilisearch.enabled` | Enable built-in Meilisearch | `true` |
| `meilisearch.image.repository` | Meilisearch image repository | `getmeili/meilisearch` |
| `meilisearch.image.tag` | Meilisearch image tag | `v1.6` |
| `meilisearch.port` | Meilisearch port | `7700` |
| `meilisearch.persistence.size` | PVC size | `5Gi` |
| `meilisearch.persistence.storageClass` | StorageClass | `""` (default) |
| `meilisearch.resources` | Meilisearch resource requests/limits | See values.yaml |

**To use external Meilisearch:**
```yaml
meilisearch:
  enabled: false

pybase:
  externalServices:
    meilisearch:
      enabled: true
      url: "https://meilisearch.example.com"
      apiKey: "YOUR_MASTER_KEY"
```

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts` | Hosts configuration | See values.yaml |
| `ingress.tls` | TLS configuration | `[]` |
| `ingress.annotations` | Ingress annotations | See values.yaml |

**Enable TLS:**
```yaml
ingress:
  tls:
    - hosts:
        - pybase.example.com
      secretName: pybase-tls-cert
```

### Secrets Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.secretKey` | JWT signing key (**REQUIRED**) | `""` |
| `secrets.databaseUrl` | PostgreSQL connection string | Auto-generated |
| `secrets.redisUrl` | Redis connection string | Auto-generated |
| `secrets.s3AccessKey` | S3 access key | `minioadmin` |
| `secrets.s3SecretKey` | S3 secret key | Auto-generated |
| `secrets.meilisearchApiKey` | Meilisearch master key | Auto-generated |
| `secrets.smtpPassword` | SMTP password | `""` |
| `secrets.werk24ApiKey` | Werk24 API key | `""` |
| `secrets.sentryDsn` | Sentry DSN | `""` |

**Generating secrets:**
```bash
# Generate secret key
openssl rand -hex 32

# Generate PostgreSQL password
openssl rand -base64 32

# Generate Redis password
openssl rand -base64 32

# Generate MinIO password
openssl rand -base64 32

# Generate Meilisearch master key
openssl rand -base64 32
```

### Monitoring Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.enabled` | Enable ServiceMonitor | `false` |
| `monitoring.serviceMonitor.interval` | Scrape interval | `30s` |
| `monitoring.serviceMonitor.scrapeTimeout` | Scrape timeout | `10s` |
| `monitoring.podAnnotations` | Prometheus pod annotations | See values.yaml |

**Enable Prometheus monitoring:**
```yaml
monitoring:
  enabled: true
  serviceMonitor:
    interval: 30s
    scrapeTimeout: 10s
    labels:
      release: prometheus
```

## Advanced Configuration

### Autoscaling

Horizontal Pod Autoscaler is configured for API and workers:

```yaml
api:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
    behavior:
      scaleDown:
        stabilizationWindowSeconds: 300
        policies:
          - type: Percent
            value: 10
            periodSeconds: 60
      scaleUp:
        stabilizationWindowSeconds: 0
        policies:
          - type: Percent
            value: 50
            periodSeconds: 15
```

### Node Selection

Deploy components to specific nodes:

```yaml
api:
  nodeSelector:
    nodepool: application

  tolerations:
    - key: "workload"
      operator: "Equal"
      value: "api"
      effect: "NoSchedule"

  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchExpressions:
                - key: app.kubernetes.io/component
                  operator: In
                  values:
                    - api
            topologyKey: kubernetes.io/hostname
```

### Resource Limits

Configure resource limits based on your workload:

```yaml
api:
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

extractionWorker:
  resources:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 2Gi
```

### Pod Disruption Budgets

Ensure high availability during maintenance:

```yaml
podDisruptionBudget:
  enabled: true
  minAvailable:
    api: 1
    extractionWorker: 1
    searchWorker: 1
    frontend: 1
```

### Network Policies

Control pod-to-pod communication:

```yaml
networkPolicy:
  enabled: true
  policyTypes:
    - Ingress
    - Egress
```

## Upgrade Guide

### Standard Upgrade

```bash
# Upgrade with existing values
helm upgrade pybase . -n pybase

# Upgrade with new values
helm upgrade pybase . -n pybase -f new-values.yaml

# Upgrade specific chart version
helm upgrade pybase . -n pybase --version 0.2.0
```

### Zero-Downtime Upgrade

The chart uses RollingUpdate strategy by default. To ensure zero-downtime upgrades:

```yaml
api:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: "25%"
      maxUnavailable: 0

extractionWorker:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: "50%"
      maxUnavailable: 0
```

### Database Migrations

Database migrations run automatically in an init container during upgrades. To verify migrations:

```bash
# Check migration logs
kubectl logs -n pybase <api-pod> -c migration

# Run migrations manually (if needed)
kubectl exec -n pybase <api-pod> -c api -- alembic upgrade head

# Check migration status
kubectl exec -n pybase <api-pod> -c api -- alembic current
```

### Rollback

```bash
# List revision history
helm history pybase -n pybase

# Rollback to previous release
helm rollback pybase -n pybase

# Rollback to specific revision
helm rollback pybase -n pybase 3
```

## Uninstallation

### Remove Release (Keep Data)

```bash
# Uninstall release
helm uninstall pybase -n pybase

# Note: PVCs are not deleted by default
# To list PVCs:
kubectl get pvc -n pybase
```

### Remove Release and Data

```bash
# Uninstall release
helm uninstall pybase -n pybase

# Delete PVCs (WARNING: This deletes all data!)
kubectl delete pvc -n pybase --all

# Delete namespace (optional)
kubectl delete namespace pybase
```

## Troubleshooting

### Pods Not Starting

**Check pod status:**
```bash
kubectl get pods -n pybase
kubectl describe pod <pod-name> -n pybase
```

**Common issues:**

| Issue | Solution |
|-------|----------|
| `ImagePullBackOff` | Check image name/tag, verify registry access, check imagePullSecrets |
| `CrashLoopBackOff` | Check logs: `kubectl logs <pod> -n pybase` |
| `Pending` (PVC) | Check StorageClass: `kubectl get storageclass` |
| `Pending` (resources) | Check cluster resources: `kubectl top nodes` |

### Database Connection Issues

**Verify PostgreSQL is running:**
```bash
kubectl exec -n pybase pybase-postgresql-0 -- pg_isready
```

**Test connection from API pod:**
```bash
kubectl exec -n pybase <api-pod> -- sh -c "
  psql \$DATABASE_URL -c 'SELECT 1'
"
```

**Check secrets:**
```bash
kubectl get secret pybase-api-secret -n pybase -o jsonpath='{.data}' | \
  jq -r 'to_entries | .[] | "\(.key): \(if .value == "" then "" else @base64decode end)"'
```

### Worker Issues

**Check Celery connectivity:**
```bash
kubectl exec -n pybase <extraction-worker-pod> -- celery -A pybase.services.celery_app inspect active
```

**View active queues:**
```bash
kubectl exec -n pybase <api-pod> -- python -c "
from pybase.services.celery_app import celery_app
print(celery_app.conf.task_routes)
"
```

### Performance Issues

**Check resource usage:**
```bash
kubectl top pods -n pybase
kubectl top nodes
```

**Review HPA status:**
```bash
kubectl get hpa -n pybase
kubectl describe hpa pybase-api -n pybase
```

**Adjust resource limits:**
```bash
helm upgrade pybase . -n pybase -f - <<EOF
api:
  resources:
    requests:
      cpu: 1000m
      memory: 1Gi
    limits:
      cpu: 4000m
      memory: 4Gi
EOF
```

### Network Issues

**Test pod-to-pod connectivity:**
```bash
# From API to PostgreSQL
kubectl exec -n pybase <api-pod> -- nc -zv pybase-postgresql 5432

# From API to Redis
kubectl exec -n pybase <api-pod> -- nc -zv pybase-redis 6379

# From API to MinIO
kubectl exec -n pybase <api-pod> -- nc -zv pybase-minio 9000
```

**Check NetworkPolicies:**
```bash
kubectl get networkpolicy -n pybase
kubectl describe networkpolicy pybase-network-policy -n pybase
```

**View Ingress configuration:**
```bash
kubectl get ingress -n pybase
kubectl describe ingress pybase-ingress -n pybase
```

### Logs Collection

**Collect logs from all components:**
```bash
# API logs
kubectl logs -f -n pybase deployment/pybase-api

# Worker logs
kubectl logs -f -n pybase deployment/pybase-extraction-worker

# Frontend logs
kubectl logs -f -n pybase deployment/pybase-frontend

# All pods logs
kubectl logs -f -n pybase -l app.kubernetes.io/name=pybase --all-containers=true

# Previous container logs (if crashed)
kubectl logs -n pybase <pod-name> --previous
```

## Examples

### Development Deployment

```yaml
# dev-values.yaml
pybase:
  environment: development
  debug: true
  logLevel: DEBUG

api:
  replicaCount: 1
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi

extractionWorker:
  replicaCount: 1

postgresql:
  persistence:
    size: 5Gi

redis:
  persistence:
    size: 1Gi

monitoring:
  enabled: true
```

### Production Deployment

```yaml
# prod-values.yaml
pybase:
  environment: production
  debug: false
  logLevel: INFO
  domain: pybase.example.com

api:
  replicaCount: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20

extractionWorker:
  replicaCount: 3
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10

searchWorker:
  replicaCount: 2
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 8

frontend:
  replicaCount: 3

postgresql:
  persistence:
    size: 50Gi

redis:
  persistence:
    size: 10Gi

minio:
  persistence:
    size: 100Gi

ingress:
  tls:
    - hosts:
        - pybase.example.com
      secretName: pybase-tls-cert

podDisruptionBudget:
  enabled: true
```

### Using External Services

```yaml
# external-services-values.yaml
postgresql:
  enabled: false

redis:
  enabled: false

minio:
  enabled: false

meilisearch:
  enabled: false

pybase:
  externalServices:
    databaseUrl: "postgresql+asyncpg://user:password@aws-rds.example.com:5432/pybase?sslmode=require"
    redisUrl: "redis://:password@aws-elasticache.example.com:6379/0"
    s3:
      enabled: true
      endpoint: "https://s3.amazonaws.com"
      accessKey: "YOUR_ACCESS_KEY"
      secretKey: "YOUR_SECRET_KEY"
      bucket: "pybase-production"
      region: "us-east-1"
    meilisearch:
      enabled: true
      url: "https://meilisearch.example.com"
      apiKey: "YOUR_MASTER_KEY"
```

### High Availability Setup

```yaml
# ha-values.yaml
api:
  replicaCount: 3
  autoscaling:
    minReplicas: 3
    maxReplicas: 20
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/component
                operator: In
                values:
                  - api
          topologyKey: topology.kubernetes.io/zone

postgresql:
  replicas: 3
  persistence:
    size: 50Gi

redis:
  replicas: 3
  persistence:
    size: 10Gi

podDisruptionBudget:
  enabled: true
  minAvailable:
    api: 2
    extractionWorker: 1
    searchWorker: 1
    frontend: 2
```

## Additional Resources

- **[PyBase Documentation](https://pybase.dev/docs)** - Complete project documentation
- **[Kubernetes Documentation](https://kubernetes.io/docs/)** - Kubernetes official docs
- **[Helm Documentation](https://helm.sh/docs/)** - Helm official docs
- **[PostgreSQL on Kubernetes](https://www.postgresql.org/docs/)** - PostgreSQL documentation
- **[Redis on Kubernetes](https://redis.io/docs/)** - Redis documentation

## Support

- **Documentation**: https://pybase.dev/docs
- **Community**: https://github.com/pybase/pybase/discussions
- **Issues**: https://github.com/pybase/pybase/issues
- **Email**: support@pybase.dev

## License

MIT License - see [LICENSE](../../LICENSE) for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for details.
