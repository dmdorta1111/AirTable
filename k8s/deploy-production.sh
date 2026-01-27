#!/bin/bash
# PyBase Production Kubernetes Deployment Script
#
# This script deploys PyBase to a production Kubernetes cluster using Helm.
# Suitable for production deployments on EKS, GKE, AKS, or bare metal.
#
# Usage:
#   ./k8s/deploy-production.sh [namespace] [release-name]
#
# Arguments:
#   namespace    - Kubernetes namespace (default: pybase)
#   release-name - Helm release name (default: pybase)
#
# Prerequisites:
#   - kubectl installed and configured
#   - helm installed (v3+)
#   - Production Kubernetes cluster running
#   - secrets configured in values.yaml or existing secret
#   - PVs provisioned (storage classes configured)

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

NAMESPACE="${1:-pybase}"
RELEASE_NAME="${2:-pybase}"
CHART_PATH="helm/pybase"
VALUES_FILE=""
DRY_RUN=false
TIMEOUT="15m"
WAIT=true
ATOMIC=false

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

    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        echo "Install helm: https://helm.sh/docs/intro/install/"
        exit 1
    fi

    # Check helm version
    HELM_VERSION=$(helm version --short | cut -d'.' -f1)
    if [[ "$HELM_VERSION" -lt 3 ]]; then
        log_error "Helm v3+ is required (current: v$HELM_VERSION)"
        exit 1
    fi
    log_success "helm v3+ is installed"

    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        echo "Check your kubeconfig and cluster connectivity"
        exit 1
    fi
    log_success "Kubernetes cluster is accessible"

    # Check cluster context
    CONTEXT=$(kubectl config current-context)
    log_info "Current context: $CONTEXT"

    # Warn if this appears to be a local cluster
    if [[ "$CONTEXT" =~ (minikube|kind|k3s|microk8s|docker-desktop) ]]; then
        log_warning "This appears to be a local cluster, not a production cluster"
        read -p "Continue with production deployment? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi

    # Check if chart exists
    if [[ ! -d "$CHART_PATH" ]]; then
        log_error "Helm chart not found at: $CHART_PATH"
        echo "This script must be run from the project root directory"
        exit 1
    fi
    log_success "Helm chart found at: $CHART_PATH"

    # Check storage classes
    log_info "Checking storage classes..."
    if ! kubectl get storageclass &> /dev/null; then
        log_warning "No storage classes found"
        log_warning "PVCs may fail to provision without a storage class"
    else
        SC_COUNT=$(kubectl get storageclass --no-headers | wc -l)
        log_success "Found $SC_COUNT storage class(es)"
    fi

    echo ""
}

# =============================================================================
# Pre-Deployment Checks
# =============================================================================

check_existing_deployment() {
    print_header "Checking Existing Deployment"

    # Check if namespace exists
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace '$NAMESPACE' already exists"

        # Check for existing Helm release
        if helm list -n "$NAMESPACE" | grep -q "^$RELEASE_NAME"; then
            log_warning "Helm release '$RELEASE_NAME' already exists in namespace '$NAMESPACE'"
            echo ""
            echo "Existing release details:"
            helm status "$RELEASE_NAME" -n "$NAMESPACE" | head -20
            echo ""

            read -p "Upgrade existing release? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Deployment cancelled"
                exit 0
            fi

            log_info "Will upgrade existing release..."
        fi
    else
        log_info "Namespace '$NAMESPACE' will be created"
    fi

    echo ""
}

# =============================================================================
# Secret Management
# =============================================================================

check_secrets() {
    print_header "Checking Secrets Configuration"

    # Check if secret values file exists
    if [[ -f "$VALUES_FILE" ]]; then
        # Check if secret values are configured (not placeholders)
        if grep -q "CHANGE_ME\|REPLACE_WITH" "$VALUES_FILE" 2>/dev/null; then
            log_warning "Values file contains placeholder secrets"
            log_warning "Please update $VALUES_FILE with actual secret values before deploying"
            echo ""
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Deployment cancelled"
                exit 0
            fi
        else
            log_success "Secret values configured in: $VALUES_FILE"
        fi
    else
        log_warning "No custom values file provided"
        log_warning "Ensure required secrets are pre-created or use --set flags"
        echo ""

        # Check for existing secrets
        if kubectl get namespace "$NAMESPACE" &> /dev/null; then
            SECRET_COUNT=$(kubectl get secrets -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l || echo "0")
            log_info "Found $SECRET_COUNT existing secret(s) in namespace '$NAMESPACE'"
        fi
    fi

    echo ""
}

# =============================================================================
# Helm Deployment
# =============================================================================

deploy_helm_chart() {
    print_header "Deploying PyBase with Helm"

    local helm_args=(
        upgrade
        --install
        "$RELEASE_NAME"
        "$CHART_PATH"
        --namespace "$NAMESPACE"
        --create-namespace
        --timeout "$TIMEOUT"
    )

    # Add optional flags
    if [[ "$DRY_RUN" == true ]]; then
        helm_args+=(--dry-run --debug)
        log_info "Running in dry-run mode (no changes will be made)"
    fi

    if [[ "$WAIT" == true ]]; then
        helm_args+=(--wait)
        log_info "Will wait for deployment to complete"
    fi

    if [[ "$ATOMIC" == true ]]; then
        helm_args+=(--atomic)
        log_info "Atomic install enabled (will rollback on failure)"
    fi

    # Add values file if provided
    if [[ -n "$VALUES_FILE" ]]; then
        helm_args+=(--values "$VALUES_FILE")
        log_info "Using values file: $VALUES_FILE"
    fi

    # Run helm command
    log_info "Running helm command..."
    echo ""

    if helm "${helm_args[@]}"; then
        log_success "Helm deployment successful"
    else
        log_error "Helm deployment failed"
        log_info "Check the error messages above for details"
        exit 1
    fi

    echo ""
}

# =============================================================================
# Post-Deployment Verification
# =============================================================================

verify_deployment() {
    print_header "Verifying Deployment"

    # Get release status
    log_info "Checking Helm release status..."
    helm status "$RELEASE_NAME" -n "$NAMESPACE"

    echo ""

    # Check pods
    log_info "Checking pod status..."
    if kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"; then
        log_success "Pods are running"
    else
        log_warning "No pods found or pods are not ready"
    fi

    echo ""

    # Check PVCs
    log_info "Checking persistent volume claims..."
    PVC_OUTPUT=$(kubectl get pvc -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" 2>/dev/null || true)
    if [[ -n "$PVC_OUTPUT" ]]; then
        echo "$PVC_OUTPUT"
        # Check if all PVCs are Bound
        PENDING_PVCS=$(echo "$PVC_OUTPUT" | grep -c "Pending" || true)
        if [[ "$PENDING_PVCS" -gt 0 ]]; then
            log_warning "Some PVCs are still in Pending state"
        else
            log_success "All PVCs are Bound"
        fi
    else
        log_info "No PVCs found (may be using external services)"
    fi

    echo ""

    # Check services
    log_info "Checking services..."
    kubectl get svc -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"

    echo ""

    # Run smoke test if available
    if [[ -f "k8s/smoke-test.sh" ]]; then
        log_info "Running smoke tests..."
        if bash k8s/smoke-test.sh "$NAMESPACE"; then
            log_success "Smoke tests passed"
        else
            log_warning "Smoke tests failed (check logs above)"
        fi
    else
        log_info "Smoke test script not found (skipping)"
    fi

    echo ""
}

# =============================================================================
# Post-Deployment Information
# =============================================================================

print_access_info() {
    print_header "Access Information"

    echo "PyBase has been deployed to namespace: $NAMESPACE"
    echo "Helm release: $RELEASE_NAME"
    echo ""

    # Check for ingress
    INGRESS_HOST=$(kubectl get ingress -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null || true)
    if [[ -n "$INGRESS_HOST" ]]; then
        echo "Ingress configured: $INGRESS_HOST"
        echo ""
        echo "Note: Ensure DNS is configured to point to the ingress controller"
        echo "or update your /etc/hosts file for testing"
    else
        echo "No ingress configured. To access the application:"
        echo ""
        echo "Option 1: Set up port forwarding"
        echo "  kubectl port-forward -n $NAMESPACE svc/pybase-api 8000:8000"
        echo "  kubectl port-forward -n $NAMESPACE svc/pybase-frontend 8080:8080"
        echo ""
        echo "Option 2: Configure ingress (see k8s/deploy-{eks,gke,aks}.md)"
    fi

    echo ""
    echo "Useful commands:"
    echo "  - View release: helm status $RELEASE_NAME -n $NAMESPACE"
    echo "  - View pods: kubectl get pods -n $NAMESPACE"
    echo "  - View logs: kubectl logs -n $NAMESPACE -f -l app.kubernetes.io/instance=$RELEASE_NAME"
    echo "  - Get values: helm get values $RELEASE_NAME -n $NAMESPACE"
    echo "  - Run smoke test: ./k8s/smoke-test.sh $NAMESPACE"
    echo ""
}

# =============================================================================
# Usage
# =============================================================================

usage() {
    echo "Usage: $0 [OPTIONS] [namespace] [release-name]"
    echo ""
    echo "Arguments:"
    echo "  namespace    - Kubernetes namespace (default: pybase)"
    echo "  release-name - Helm release name (default: pybase)"
    echo ""
    echo "Options:"
    echo "  -f, --values FILE   Custom values file"
    echo "  --dry-run           Show what would be installed without installing"
    echo "  --no-wait           Don't wait for deployment to complete"
    echo "  --atomic            Install atomically (rollback on failure)"
    echo "  --timeout DURATION  Timeout for helm operations (default: 15m)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Basic deployment"
    echo "  $0"
    echo ""
    echo "  # Deploy with custom values"
    echo "  $0 -f values-production.yaml"
    echo ""
    echo "  # Deploy to production namespace"
    echo "  $0 production pybase-prod"
    echo ""
    echo "  # Dry-run to test deployment"
    echo "  $0 --dry-run"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
    print_header "PyBase Production Deployment"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--values)
                VALUES_FILE="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-wait)
                WAIT=false
                shift
                ;;
            --atomic)
                ATOMIC=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                if [[ -z "$NAMESPACE_SET" ]]; then
                    NAMESPACE="$1"
                    NAMESPACE_SET=true
                    shift
                elif [[ -z "$RELEASE_NAME_SET" ]]; then
                    RELEASE_NAME="$1"
                    RELEASE_NAME_SET=true
                    shift
                else
                    log_error "Too many arguments"
                    usage
                    exit 1
                fi
                ;;
        esac
    done

    # Check prerequisites
    check_prerequisites

    # Check existing deployment
    check_existing_deployment

    # Check secrets configuration
    check_secrets

    # Deploy helm chart
    deploy_helm_chart

    # Verify deployment (skip if dry-run)
    if [[ "$DRY_RUN" == false ]]; then
        verify_deployment
        print_access_info
    fi

    print_header "Deployment Complete"
    log_success "PyBase deployed successfully to namespace '$NAMESPACE' as release '$RELEASE_NAME'"
    echo ""
}

# Run main function
main "$@"
