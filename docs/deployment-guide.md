# Deployment Guide

## Overview
PyBase can be deployed in various environments, from local development machines to production-grade Kubernetes clusters.

## Development Setup

### 1. Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+ (optional if using Docker)
- Redis 7+ (optional if using Docker)

### 2. Local Installation
```bash
# Clone and enter repo
git clone https://github.com/pybase/pybase.git
cd pybase

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -e ".[all,dev]"
```

### 3. Environment Configuration
Create a `.env` file in the root directory (see `README.md` for template).

### 4. Running with Docker Compose
```bash
docker compose up -d
```
This starts PostgreSQL, Redis, MinIO, and the PyBase API.

## Production Deployment Considerations

### 1. Containerization
The project includes a `Dockerfile` for the FastAPI backend. In production, use multi-stage builds to keep image sizes small.

### 2. Database
- Use a managed PostgreSQL service (e.g., AWS RDS, GCP Cloud SQL) instead of running it in a container.
- Enable automated backups and point-in-time recovery.

### 3. Kubernetes Deployment

PyBase includes production-ready Kubernetes manifests and Helm chart for deploying to any Kubernetes cluster.

#### Quick Start

**Option A: Kustomize (Development)**
```bash
# Create namespace and secrets
kubectl create namespace pybase
kubectl create secret generic pybase-api-secret \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=database-url="postgresql+asyncpg://pybase:CHANGE_ME@pybase-postgres:5432/pybase" \
  --from-literal=redis-url="redis://:CHANGE_ME@pybase-redis:6379/0" \
  -n pybase

# Deploy all resources
kubectl apply -k k8s/base
```

**Option B: Helm Chart (Production)**
```bash
# Install with default configuration
helm install pybase helm/pybase -n pybase --create-namespace

# Or customize with values file
helm install pybase helm/pybase -n pybase -f custom-values.yaml
```

#### Platform-Specific Guides

Detailed deployment instructions for different Kubernetes platforms:

- **[AWS EKS](../k8s/deploy-eks.md)** - Amazon Elastic Kubernetes Service
  - IAM roles for service accounts (IRSA)
  - AWS Load Balancer Controller
  - Integration with RDS, ElastiCache, S3

- **[Google GKE](../k8s/deploy-gke.md)** - Google Kubernetes Engine
  - Workload Identity setup
  - Managed Certificate for HTTPS
  - Integration with Cloud SQL, Memorystore, Cloud Storage

- **[Azure AKS](../k8s/deploy-aks.md)** - Azure Kubernetes Service
  - Azure AD integration
  - Application Gateway ingress
  - Integration with Azure Database, Cache, Blob Storage

- **[Bare Metal](../k8s/deploy-bare-metal.md)** - Self-hosted clusters
  - Minikube (development)
  - k3s/MicroK8s (production)
  - MetalLB ingress setup

#### Features

**Included Components:**
- PostgreSQL StatefulSet with persistent storage
- Redis Deployment with persistence
- MinIO StatefulSet for S3-compatible storage
- Meilisearch Deployment for search functionality
- FastAPI backend with health checks
- Celery extraction and search workers
- React frontend served by nginx
- Horizontal Pod Autoscalers for all components
- PodDisruptionBudgets for high availability
- NetworkPolicies for security isolation
- Comprehensive RBAC configuration

**Production Capabilities:**
- Horizontal Pod Autoscaling (HPA) based on CPU/memory
- Rolling deployments with zero downtime
- Graceful shutdown for long-running tasks
- Prometheus metrics integration
- Secret management support (external secrets, sealed secrets)
- Configurable resource limits and requests
- Pod security policies and network isolation

#### Documentation

- **[Kubernetes README](../k8s/README.md)** - Complete deployment guide, configuration, troubleshooting
- **[Helm Chart README](../helm/pybase/README.md)** - Helm chart usage, configuration reference, examples

#### Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured
- Helm 3.0+ (if using Helm)
- StorageClass for dynamic provisioning
- Ingress controller (nginx, traefik, or cloud provider)

**Cluster Resources:**
- Minimum: 4 CPU cores, 8Gi RAM (development)
- Recommended: 8 CPU cores, 16Gi RAM (production)
- Storage: 30Gi+ for databases and object storage

### 4. Monitoring & Logging
- **Logging**: Use a centralized logging system (e.g., ELK stack, Datadog).
- **Monitoring**: (Future) Prometheus for metrics collection and Grafana for visualization.
- **Alerting**: Set up alerts for high error rates or latency.

## Object Storage
PyBase uses S3-compatible storage for attachments and CAD files.
- **Development**: MinIO (included in `docker-compose.yml`).
- **Production**: AWS S3, Google Cloud Storage, or Azure Blob Storage.

## Security Hardening
- Change the `SECRET_KEY` in production.
- Use HTTPS for all communication.
- Restrict database and Redis access to the backend VPC/Network.
- Regularly update dependencies to fix security vulnerabilities.
