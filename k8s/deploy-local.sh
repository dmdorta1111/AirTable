#!/bin/bash
# PyBase Local Kubernetes Deployment Script
#
# This script deploys PyBase to a local Kubernetes cluster (minikube, kind, k3s)
# using kubectl and kustomize. Suitable for development and testing.
#
# Usage:
#   ./k8s/deploy-local.sh [namespace]
#
# Arguments:
#   namespace - Kubernetes namespace (default: pybase)
#
# Prerequisites:
#   - kubectl installed and configured
#   - Local Kubernetes cluster running (minikube, kind, k3s)
#   - Secrets created (or create with --create-secrets flag)

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

NAMESPACE="${1:-pybase}"
CREATE_SECRETS=false
SKIP_SECRETS=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_header() {
    echo ""
    echo "=============================================================================="
    echo "$1"
    echo "=============================================================================="
    echo ""
}

# =============================================================================
# Prerequisites Checks
# =============================================================================

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        echo "Install kubectl: https://kubernetes.io/docs/tasks/tools/"
        exit 1
    fi
    log_success "kubectl is installed"

    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        echo "Check your kubeconfig and cluster connectivity"
        echo ""
        echo "For minikube: minikube start"
        echo "For kind: kind create cluster"
        echo "For k3s: sudo systemctl start k3s"
        exit 1
    fi
    log_success "Kubernetes cluster is accessible"

    # Check cluster context (warn if not a local cluster)
    CONTEXT=$(kubectl config current-context)
    log_info "Current context: $CONTEXT"

    if [[ ! "$CONTEXT" =~ (minikube|kind|k3s|microk8s|docker-desktop) ]]; then
        log_warning "This doesn't appear to be a local cluster"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi

    echo ""
}

# =============================================================================
# Secret Management
# =============================================================================

generate_secret_key() {
    openssl rand -hex 32
}

generate_password() {
    openssl rand -base64 16 | tr -d "=+/" | cut -c1-16
}

create_secrets() {
    print_header "Creating Secrets"

    # Check if secrets already exist
    if kubectl get secret pybase-api-secret -n "$NAMESPACE" &> /dev/null; then
        log_warning "Secret 'pybase-api-secret' already exists"
        read -p "Overwrite existing secrets? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping secret creation"
            return
        fi
        kubectl delete secret pybase-api-secret -n "$NAMESPACE" &> /dev/null || true
    fi

    # Generate secret values
    SECRET_KEY=$(generate_secret_key)
    DB_PASSWORD=$(generate_password)
    REDIS_PASSWORD=$(generate_password)
    MINIO_ROOT_PASSWORD=$(generate_password)
    MINIO_ACCESS_KEY=$(generate_password | tr '[:lower:]' '[:upper:]')

    # Get database service host
    DB_HOST="pybase-postgres.$NAMESPACE.svc.cluster.local"
    DB_PORT="5432"
    DB_NAME="pybase"
    DB_USER="pybase"

    # Get Redis service host
    REDIS_HOST="pybase-redis.$NAMESPACE.svc.cluster.local"
    REDIS_PORT="6379"

    # Get MinIO service host
    MINIO_ENDPOINT="http://pybase-minio.$NAMESPACE.svc.cluster.local:9000"

    # Create DATABASE_URL
    DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}?sslmode=prefer"

    # Create REDIS_URL
    REDIS_URL="redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/0"

    # Create the secret
    kubectl create secret generic pybase-api-secret -n "$NAMESPACE" \
        --from-literal=secret-key="$SECRET_KEY" \
        --from-literal=database-url="$DATABASE_URL" \
        --from-literal=redis-url="$REDIS_URL" \
        --from-literal=s3-endpoint-url="$MINIO_ENDPOINT" \
        --from-literal=s3-access-key-id="$MINIO_ACCESS_KEY" \
        --from-literal=s3-secret-access-key="$MINIO_ROOT_PASSWORD" \
        --from-literal=meilisearch-api-key="$(generate_secret_key)" \
        --from-literal=smtp-password="" \
        --from-literal=werk24-api-key="" \
        --from-literal=sentry-dsn="" \
        --from-literal=otel-exporter-otlp-endpoint="" \
        --dry-run=client -o yaml | kubectl apply -n "$NAMESPACE" -f -

    # Create PostgreSQL secret
    kubectl create secret generic pybase-postgres-secret -n "$NAMESPACE" \
        --from-literal=postgres-password="$DB_PASSWORD" \
        --from-literal=password="$DB_PASSWORD" \
        --dry-run=client -o yaml | kubectl apply -n "$NAMESPACE" -f -

    # Create Redis secret
    kubectl create secret generic pybase-redis-secret -n "$NAMESPACE" \
        --from-literal=redis-password="$REDIS_PASSWORD" \
        --dry-run=client -o yaml | kubectl apply -n "$NAMESPACE" -f -

    # Create MinIO secret
    kubectl create secret generic pybase-minio-secret -n "$NAMESPACE" \
        --from-literal=root-user="$MINIO_ACCESS_KEY" \
        --from-literal=root-password="$MINIO_ROOT_PASSWORD" \
        --dry-run=client -o yaml | kubectl apply -n "$NAMESPACE" -f -

    # Save credentials to a file for reference
    cat > "./pybase-local-credentials.txt" <<EOF
# PyBase Local Deployment Credentials
# Generated: $(date)

## Application
SECRET_KEY=$SECRET_KEY

## PostgreSQL
Host: ${DB_HOST}
Port: ${DB_PORT}
Database: ${DB_NAME}
Username: ${DB_USER}
Password: ${DB_PASSWORD}
Connection URL: ${DATABASE_URL}

## Redis
Host: ${REDIS_HOST}
Port: ${REDIS_PORT}
Password: ${REDIS_PASSWORD}
Connection URL: ${REDIS_URL}

## MinIO (S3)
Endpoint: ${MINIO_ENDPOINT}
Access Key: ${MINIO_ACCESS_KEY}
Secret: ${MINIO_ROOT_PASSWORD}
Console: http://pybase-minio.$NAMESPACE.svc.cluster.local:9001

## Access URLs (after port-forward)
Frontend: http://localhost:8080
API: http://localhost:8000
MinIO Console: http://localhost:9001
EOF

    log_success "Secrets created"
    log_info "Credentials saved to ./pybase-local-credentials.txt"
    log_warning "Keep this file secure and delete it when done"

    echo ""
}

# =============================================================================
# Namespace Creation
# =============================================================================

create_namespace() {
    print_header "Creating Namespace"

    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace '$NAMESPACE' already exists"
    else
        kubectl create namespace "$NAMESPACE"
        log_success "Namespace '$NAMESPACE' created"
    fi

    echo ""
}

# =============================================================================
# Deployment
# =============================================================================

deploy_manifests() {
    print_header "Deploying PyBase Manifests"

    log_info "Applying Kubernetes manifests..."

    # Apply manifests using kustomize
    if kubectl apply -k k8s/base -n "$NAMESPACE"; then
        log_success "Manifests applied successfully"
    else
        log_error "Failed to apply manifests"
        exit 1
    fi

    echo ""
}

# =============================================================================
# Wait for Deployment
# =============================================================================

wait_for_deployment() {
    print_header "Waiting for Deployment to be Ready"

    log_info "Waiting for deployments to roll out..."
    echo ""

    # Wait for API deployment
    log_info "Waiting for API deployment..."
    if kubectl rollout status deployment/pybase-api -n "$NAMESPACE" --timeout=300s; then
        log_success "API deployment ready"
    else
        log_warning "API deployment timed out (check pods with: kubectl get pods -n $NAMESPACE)"
    fi

    # Wait for extraction worker deployment
    log_info "Waiting for extraction worker deployment..."
    if kubectl rollout status deployment/pybase-extraction-worker -n "$NAMESPACE" --timeout=300s; then
        log_success "Extraction worker deployment ready"
    else
        log_warning "Extraction worker deployment timed out"
    fi

    # Wait for search worker deployment
    log_info "Waiting for search worker deployment..."
    if kubectl rollout status deployment/pybase-search-worker -n "$NAMESPACE" --timeout=300s; then
        log_success "Search worker deployment ready"
    else
        log_warning "Search worker deployment timed out"
    fi

    # Wait for frontend deployment
    log_info "Waiting for frontend deployment..."
    if kubectl rollout status deployment/pybase-frontend -n "$NAMESPACE" --timeout=300s; then
        log_success "Frontend deployment ready"
    else
        log_warning "Frontend deployment timed out"
    fi

    echo ""
}

# =============================================================================
# Post-Deployment Information
# =============================================================================

print_access_info() {
    print_header "Access Information"

    echo "PyBase has been deployed to namespace: $NAMESPACE"
    echo ""
    echo "To access the application, set up port forwarding:"
    echo ""
    echo "  # Frontend (React UI)"
    echo "  kubectl port-forward -n $NAMESPACE svc/pybase-frontend 8080:8080"
    echo ""
    echo "  # API (FastAPI backend)"
    echo "  kubectl port-forward -n $NAMESPACE svc/pybase-api 8000:8000"
    echo ""
    echo "  # MinIO Console (S3-compatible storage)"
    echo "  kubectl port-forward -n $NAMESPACE svc/pybase-minio-console 9001:9001"
    echo ""
    echo "Then open in your browser:"
    echo "  - Frontend: http://localhost:8080"
    echo "  - API: http://localhost:8000"
    echo "  - MinIO: http://localhost:9001"
    echo ""
    echo "Useful commands:"
    echo "  - View pods: kubectl get pods -n $NAMESPACE"
    echo "  - View logs: kubectl logs -n $NAMESPACE -f deployment/pybase-api"
    echo "  - Run smoke test: ./k8s/smoke-test.sh $NAMESPACE"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
    print_header "PyBase Local Deployment"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --create-secrets)
                CREATE_SECRETS=true
                shift
                ;;
            --skip-secrets)
                SKIP_SECRETS=true
                shift
                ;;
            *)
                NAMESPACE="$1"
                shift
                ;;
        esac
    done

    # Check prerequisites
    check_prerequisites

    # Create namespace
    create_namespace

    # Create or check secrets
    if [[ "$SKIP_SECRETS" == true ]]; then
        log_info "Skipping secret creation"
    elif [[ "$CREATE_SECRETS" == true ]] || ! kubectl get secret pybase-api-secret -n "$NAMESPACE" &> /dev/null; then
        create_secrets
    else
        log_info "Secrets already exist, using existing secrets"
        log_info "To regenerate secrets, run with --create-secrets flag"
    fi

    # Deploy manifests
    deploy_manifests

    # Wait for deployment
    wait_for_deployment

    # Print access information
    print_access_info

    print_header "Deployment Complete"
    log_success "PyBase deployed successfully to namespace '$NAMESPACE'"
    echo ""
}

# Run main function
main "$@"
