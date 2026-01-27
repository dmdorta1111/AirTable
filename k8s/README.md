# PyBase Kubernetes Deployment

> Production-ready Kubernetes manifests and Helm chart for deploying PyBase to any Kubernetes cluster

[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.24+-326ce5.svg)](https://kubernetes.io/)
[![Helm](https://img.shields.io/badge/Helm-3.0+-0f168e.svg)](https://helm.sh/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-dc382d.svg)](https://redis.io/)

## Overview

This directory contains production-ready Kubernetes manifests and a comprehensive Helm chart for deploying PyBase to Kubernetes clusters. The deployment includes all necessary components: PostgreSQL, Redis, MinIO (S3-compatible storage), Meilisearch, FastAPI backend, Celery workers, and React frontend.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Kubernetes Cluster                       │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Frontend   │    │  API Server  │    │ Ingress      │      │
│  │   (Nginx)    │◄───│  (FastAPI)   │◄───│ (Nginx/TLS)  │      │
│  │   Port: 8080 │    │  Port: 8000  │    │ Port: 80/443 │      │
│  └──────────────┘    └──────┬───────┘    └──────────────┘      │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Extraction   │    │   Search     │    │   PostgreSQL │      │
│  │   Worker     │    │   Worker     │    │   StatefulSet│      │
│  │  (Celery)    │    │  (Celery)    │    │   Port: 5432 │      │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘      │
│         │                   │                                   │
│         └─────────┬─────────┘                                   │
│                   ▼                                             │
│         ┌─────────────────┐      ┌──────────────┐              │
│         │     Redis       │      │    MinIO     │              │
│         │ Deployment+PVC  │      │ StatefulSet  │              │
│         │   Port: 6379    │      │ Port: 9000   │              │
│         └─────────────────┘      │   9001 (Web) │              │
│                                  └──────────────┘              │
│                                                                  │
│  ┌──────────────┐                                            │
│  │ Meilisearch  │ (Optional - for search functionality)      │
│  │ Deployment   │                                            │
│  │ Port: 7700   │                                            │
│  └──────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘

Features:
- Horizontal Pod Autoscaler (HPA) for all components
- PodDisruptionBudgets for high availability
- NetworkPolicies for security isolation
- PersistentVolumes for data persistence
- Prometheus metrics for monitoring
- Graceful shutdown with long-running task support
```

## Quick Start

### Prerequisites

Before deploying PyBase to Kubernetes, ensure you have:

- **Kubernetes cluster** (version 1.24+)
  - [EKS](deploy-eks.md) / [GKE](deploy-gke.md) / [AKS](deploy-aks.md) / [Bare Metal](deploy-bare-metal.md)
- **kubectl** configured to access your cluster
- **Helm 3.0+** (if using Helm chart)
- **StorageClass** configured for dynamic provisioning (or use pre-provisioned PVs)
- **Ingress controller** installed (nginx, traefik, or cloud provider's ingress)

**Cluster Resource Requirements:**
- **Minimum**: 4 CPU cores, 8Gi RAM (development)
- **Recommended**: 8 CPU cores, 16Gi RAM (production)
- **Storage**: 30Gi+ for PostgreSQL, Redis, MinIO, Meilisearch

### Option A: Deploy with Kustomize (Recommended for Development)

```bash
# 1. Create the namespace
kubectl create namespace pybase

# 2. Create secrets (REQUIRED before deploying)
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  --from-literal=s3-endpoint-url="http://pybase-minio:9000" \
  --from-literal=s3-access-key="minioadmin" \
  --from-literal=s3-secret-key="CHANGE_ME" \
  -n pybase

# 3. Deploy all resources
kubectl apply -k k8s/base

# 4. Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=pybase -n pybase --timeout=300s

# 5. Get the Ingress URL
kubectl get ingress -n pybase
```

**Local Testing with port-forwarding:**
```bash
# Forward API port
kubectl port-forward -n pybase svc/pybase-api 8000:8000

# Forward frontend port
kubectl port-forward -n pybase svc/pybase-frontend 8080:8080

# Access at http://localhost:8080
```

### Option B: Deploy with Helm (Recommended for Production)

```bash
# 1. Add repository (when published)
# helm repo add pybase https://charts.pybase.dev
# helm repo update

# 2. Install from local directory
helm install pybase helm/pybase -n pybase --create-namespace

# 3. Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=pybase -n pybase --timeout=300s

# 4. Get application credentials
helm status pybase -n pybase

# 5. Access the application
kubectl get ingress -n pybase
```

**Customize deployment with values file:**
```bash
# Create your values file
cat > my-values.yaml <<EOF
pybase:
  domain: pybase.example.com

api:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 512Mi

postgresql:
  enabled: true  # Set to false to use external PostgreSQL

redis:
  enabled: true  # Set to false to use external Redis

minio:
  enabled: true  # Set to false to use AWS S3 or compatible
EOF

# Deploy with custom values
helm install pybase helm/pybase -n pybase -f my-values.yaml
```

## Configuration

### Secrets Management

PyBase requires several secrets for operation. **Never commit secrets to version control.**

**Required Secrets:**

| Secret Key | Description | Example |
|------------|-------------|---------|
| `secret-key` | JWT signing key | Generate with: `openssl rand -hex 32` |
| `database-url` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `redis-url` | Redis connection string | `redis://:password@host:6379/0` |
| `s3-endpoint-url` | S3-compatible storage endpoint | `http://minio:9000` or `https://s3.amazonaws.com` |
| `s3-access-key` | S3 access key | AWS access key or MinIO username |
| `s3-secret-key` | S3 secret key | AWS secret key or MinIO password |

**Optional Secrets:**

| Secret Key | Description |
|------------|-------------|
| `meilisearch-api-key` | Meilisearch master key (if using built-in) |
| `werk24-api-key` | Werk24 API key for CAD extraction |
| `smtp-password` | SMTP password for email notifications |
| `sentry-dsn` | Sentry DSN for error tracking |

**Creating Secrets:**

```bash
# Option 1: From literal values (kubectl)
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key="$(openssl rand -hex 32)" \
  --from-literal=database-url="postgresql+asyncpg://..." \
  -n pybase

# Option 2: From file (Helm)
cat > secret-values.yaml <<EOF
secrets:
  secretKey: "$(openssl rand -hex 32)"
  databaseUrl: "postgresql+asyncpg://..."
  redisUrl: "redis://..."
EOF

helm install pybase helm/pybase -n pybase -f secret-values.yaml

# Option 3: Using external secrets operator
# Install: external-secrets.io
# Configure: ExternalSecret with AWS Secrets Manager, Vault, etc.
```

### Using External Services

PyBase can use external managed services instead of bundled ones:

**External PostgreSQL (AWS RDS, GCP Cloud SQL, Azure Database):**
```yaml
# values.yaml (Helm)
postgresql:
  enabled: false

externalServices:
  databaseUrl: "postgresql+asyncpg://user:pass@prod-db.example.com:5432/pybase?sslmode=require"
```

**External Redis (ElastiCache, Memorystore, Azure Cache):**
```yaml
# values.yaml (Helm)
redis:
  enabled: false

externalServices:
  redisUrl: "redis://:password@redis.example.com:6379/0"
```

**External S3 (AWS S3, GCS, Azure Blob):**
```yaml
# values.yaml (Helm)
minio:
  enabled: false

externalServices:
  s3:
    enabled: true
    endpointUrl: "https://s3.amazonaws.com"
    accessKey: "AKIAIOSFODNN7EXAMPLE"
    secretKey: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    bucketName: "pybase-production"
    region: "us-east-1"
```

**External Meilisearch:**
```yaml
# values.yaml (Helm)
meilisearch:
  enabled: false

externalServices:
  meilisearch:
    enabled: true
    url: "https://meilisearch.example.com"
    apiKey: "your-master-key"
```

### Resource Limits

Default resource limits are configured for small-to-medium deployments. Adjust based on your load:

```yaml
# values.yaml (Helm)
api:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

extractionWorker:
  replicas: 2
  concurrency: 2
  resources:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 2Gi
```

### Autoscaling

Horizontal Pod Autoscaler is configured for API and workers:

```bash
# View HPA status
kubectl get hpa -n pybase

# Manually scale (if HPA disabled)
kubectl scale deployment pybase-api --replicas=5 -n pybase

# Adjust HPA thresholds
kubectl edit hpa pybase-api -n pybase
```

## Security

### Network Policies

NetworkPolicies restrict pod-to-pod communication for security:

```yaml
# Default policy: least-privilege access
# - Ingress: Only from Ingress controller and specific components
# - Egress: Only to required services (PostgreSQL, Redis, MinIO, etc.)
# - DNS: All pods can resolve DNS

# View network policies
kubectl get networkpolicy -n pybase

# Disable for testing (NOT recommended for production)
kubectl annotate networkpolicy pybase-policy "networkpolicy.k8s.io/allow-all-" -n pybase
```

### Pod Security

- **Non-root users**: All containers run as non-root users
- **ServiceAccounts**: Minimal permissions per component
- **PodDisruptionBudgets**: Ensure availability during maintenance
- **Security Contexts**: Defined for all pods

### TLS/HTTPS

**For production deployments, always enable TLS:**

```yaml
# values.yaml (Helm)
ingress:
  tls:
    - hosts:
        - pybase.example.com
      secretName: pybase-tls-cert

# Create TLS secret
kubectl create secret tls pybase-tls-cert \
  --cert=path/to/cert.crt \
  --key=path/to/cert.key \
  -n pybase

# Or use cert-manager for automatic certificates
# https://cert-manager.io/
```

## Monitoring and Observability

### Health Checks

```bash
# Check all pod health
kubectl get pods -n pybase

# Detailed pod status
kubectl describe pod -l app.kubernetes.io/component=api -n pybase

# View health endpoint
kubectl exec -n pybase <api-pod> -- curl http://localhost:8000/api/v1/health
```

### Logs

```bash
# API logs
kubectl logs -f -n pybase deployment/pybase-api

# Worker logs
kubectl logs -f -n pybase deployment/pybase-extraction-worker

# All pods logs
kubectl logs -f -n pybase -l app.kubernetes.io/name=pybase --all-containers=true

# Previous container logs (if crashed)
kubectl logs -n pybase <pod-name> --previous
```

### Metrics (Prometheus)

Prometheus annotations are included for scraping:

```yaml
# Enable ServiceMonitor (if using Prometheus Operator)
# values.yaml
monitoring:
  serviceMonitor:
    enabled: true
    namespace: monitoring
    interval: 30s
    scrapeTimeout: 10s
```

**Metrics endpoints:**
- API: `http://pybase-api:8000/metrics`
- Workers: Celery metrics (if configured)

## Backup and Restore

### PostgreSQL Backup

```bash
# Manual backup
kubectl exec -n pybase pybase-postgres-0 -- pg_dump -U pybase pybase > backup.sql

# Using Kubernetes CronJob (recommended)
# Create: k8s/base/postgres-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:16-alpine
            command:
            - sh
            - -c
            - |
              pg_dump -U pybase -h pybase-postgres pybase | \
              gzip > /backup/$(date +%Y%m%d-%H%M%S).sql.gz
            volumeMounts:
            - name: backup
              mountPath: /backup
          volumes:
          - name: backup
            persistentVolumeClaim:
              claimName: postgres-backup-pvc
          restartPolicy: OnFailure
```

### MinIO Backup

MinIO data is stored in a PersistentVolumeClaim. Use:

1. **Volume Snapshots** (if your storage provider supports it)
2. **MinIO mirroring** to replicate to another MinIO instance
3. **Regular mc mirror** commands

```bash
# Mirror MinIO to local
kubectl exec -n pybase pybase-minio-0 -- sh -c "
  mc mirror /data /backup/$(date +%Y%m%d)
"
```

## Troubleshooting

### Pods Not Starting

**1. Check pod status:**
```bash
kubectl get pods -n pybase
kubectl describe pod <pod-name> -n pybase
```

**2. Common issues:**

| Issue | Solution |
|-------|----------|
| `ImagePullBackOff` | Check image name/tag, verify registry access |
| `CrashLoopBackOff` | Check logs: `kubectl logs <pod> -n pybase` |
| `Pending` (PVC) | Check StorageClass: `kubectl get storageclass` |
| `Pending` (resources) | Check cluster resources: `kubectl top nodes` |

### Database Connection Issues

**1. Verify PostgreSQL is running:**
```bash
kubectl exec -n pybase pybase-postgres-0 -- pg_isready
```

**2. Test connection from API pod:**
```bash
kubectl exec -n pybase <api-pod> -- sh -c "
  psql $DATABASE_URL -c 'SELECT 1'
"
```

**3. Check secrets:**
```bash
kubectl get secret pybase-api-secret -n pybase -o jsonpath='{.data}' | \
  jq -r 'to_entries | .[] | "\(.key): \(if .value == "" then "" else @base64decode end)"'
```

### Worker Issues

**1. Check Celery connectivity:**
```bash
kubectl exec -n pybase <extraction-worker-pod> -- celery -A workers.celery_extraction_worker inspect active
```

**2. View task queue:**
```bash
kubectl exec -n pybase <api-pod> -- python -c "
from src.pybase.db.session import get_db
from src.pybase.models.extraction import ExtractionJob
# Add inspection code
"
```

### Performance Issues

**1. Check resource usage:**
```bash
kubectl top pods -n pybase
kubectl top nodes
```

**2. Review HPA status:**
```bash
kubectl get hpa -n pybase
kubectl describe hpa pybase-api -n pybase
```

**3. Adjust resource limits:**
```bash
kubectl edit deployment pybase-api -n pybase
# Edit resources.requests and resources.limits
```

### Network Issues

**1. Test pod-to-pod connectivity:**
```bash
# From API to PostgreSQL
kubectl exec -n pybase <api-pod> -- nc -zv pybase-postgres 5432

# From API to Redis
kubectl exec -n pybase <api-pod> -- nc -zv pybase-redis 6379
```

**2. Check NetworkPolicies:**
```bash
kubectl get networkpolicy -n pybase
kubectl describe networkpolicy pybase-policy -n pybase
```

**3. View Ingress configuration:**
```bash
kubectl get ingress -n pybase
kubectl describe ingress pybase-ingress -n pybase
```

## Upgrading

### Kustomize Upgrades

```bash
# Apply latest manifests
kubectl apply -k k8s/base

# Watch rollout status
kubectl rollout status deployment/pybase-api -n pybase

# Rollback if needed
kubectl rollout undo deployment/pybase-api -n pybase
```

### Helm Upgrades

```bash
# Upgrade with new values
helm upgrade pybase helm/pybase -n pybase -f my-values.yaml

# Upgrade specific chart version
helm upgrade pybase helm/pybase -n pybase --version 0.2.0

# View upgrade history
helm history pybase -n pybase

# Rollback to previous version
helm rollback pybase -n pybase
```

### Database Migrations

Database migrations run automatically in an init container before API startup. To verify:

```bash
# Check migration container logs
kubectl logs -n pybase <api-pod> -c migration

# Run migrations manually (if needed)
kubectl exec -n pybase <api-pod> -c api -- alembic upgrade head
```

## Platform-Specific Guides

Detailed deployment guides for specific Kubernetes platforms:

- **[Amazon EKS](deploy-eks.md)** - AWS Elastic Kubernetes Service
- **Google GKE** - Google Kubernetes Engine
- **Azure AKS** - Azure Kubernetes Service
- **[Bare Metal / Local](deploy-bare-metal.md)** - Minikube, k3s, bare metal

## Uninstalling

### Remove Kustomize Deployment

```bash
# Delete all resources
kubectl delete -k k8s/base

# Delete namespace (optional)
kubectl delete namespace pybase

# Delete PVCs (WARNING: This deletes all data!)
kubectl delete pvc -n pybase --all
```

### Remove Helm Deployment

```bash
# Uninstall release
helm uninstall pybase -n pybase

# Delete PVCs (WARNING: This deletes all data!)
kubectl delete pvc -n pybase --all

# Delete namespace (optional)
kubectl delete namespace pybase
```

## Additional Resources

- **[Helm Chart Documentation](../helm/pybase/README.md)** - Detailed Helm chart reference
- **[Main Deployment Guide](../docs/deployment-guide.md)** - General deployment options
- **[Project Documentation](../docs/)** - Complete project documentation
- **[GitHub Issues](https://github.com/pybase/pybase/issues)** - Bug reports and feature requests

## Support

- **Documentation**: https://pybase.dev/docs
- **Community**: https://github.com/pybase/pybase/discussions
- **Issues**: https://github.com/pybase/pybase/issues

## License

MIT License - see [LICENSE](../LICENSE) for details.
