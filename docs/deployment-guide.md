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

### 3. Kubernetes (Phase 9 - IN PROGRESS)
- **Manifests**: K8s manifests are currently being developed.
- **Helm**: A Helm chart will be provided for simplified deployment.
- **Ingress**: Use Nginx Ingress or similar for SSL termination and load balancing.

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
