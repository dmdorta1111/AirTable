#!/bin/bash
# PyBase Kubernetes Tear-Down Script
#
# This script removes a PyBase deployment from a Kubernetes cluster.
# Supports both Kustomize and Helm deployments.
#
# Usage:
#   ./k8s/tear-down.sh [namespace]
#
# Arguments:
#   namespace - Kubernetes namespace (default: pybase)
#
# Options:
#   --helm           - Remove Helm deployment (default: auto-detect)
#   --kustomize      - Remove Kustomize deployment (default: auto-detect)
#   --delete-pvcs    - Also delete PVCs and their data
#   --delete-secrets - Also delete secrets
#   --delete-all     - Delete everything (namespace, PVCs, secrets)
#   --dry-run        - Show what would be deleted without deleting
#
# WARNING: This action cannot be undone! Always backup important data first.

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

NAMESPACE="${1:-pybase}"
HELM_RELEASE_NAME="pybase"
DEPLOYMENT_TYPE=""
DELETE_PVCS=false
DELETE_SECRETS=false
DELETE_ALL=false
DRY_RUN=false
FORCE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD_RED='\033[1;31m'
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

print_warning_header() {
    echo ""
    echo -e "${BOLD_RED}=============================================================================="
    echo -e "${BOLD_RED}$1"
    echo -e "${BOLD_RED}==============================================================================${NC}"
    echo ""
}

# =============================================================================
# Confirmation Dialogs
# =============================================================================

confirm_deletion() {
    local resource="$1"
    local additional_warning="${2:-}"

    if [[ "$FORCE" == true ]]; then
        return 0
    fi

    print_warning_header "⚠️  WARNING: Irreversible Action ⚠️"
    echo "You are about to delete: $resource"
    echo ""
    echo "This action cannot be undone!"

    if [[ -n "$additional_warning" ]]; then
        echo ""
        echo -e "${YELLOW}$additional_warning${NC}"
    fi

    echo ""
    read -p "Are you sure you want to continue? (yes/NO): " -r
    echo

    if [[ "$REPLY" =~ ^[Yy][Ee][Ss]$ ]]; then
        return 0
    else
        log_info "Deletion cancelled"
        exit 0
    fi
}

# =============================================================================
# Prerequisites Checks
# =============================================================================

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    log_success "kubectl is installed"

    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot access Kubernetes cluster"
        exit 1
    fi
    log_success "Kubernetes cluster is accessible"

    echo ""
}

# =============================================================================
# Deployment Detection
# =============================================================================

detect_deployment_type() {
    print_header "Detecting Deployment Type"

    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace '$NAMESPACE' does not exist"
        log_info "Nothing to delete"
        exit 0
    fi

    # Check for Helm deployment
    if command -v helm &> /dev/null; then
        if helm list -n "$NAMESPACE" | grep -q "^$HELM_RELEASE_NAME"; then
            log_success "Detected Helm deployment: $HELM_RELEASE_NAME"
            DEPLOYMENT_TYPE="helm"
            return
        fi
    fi

    # Check for Kustomize deployment (look for PyBase resources)
    if kubectl get deployment -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" &> /dev/null; then
        log_success "Detected Kustomize deployment"
        DEPLOYMENT_TYPE="kustomize"
        return
    fi

    log_warning "No PyBase deployment detected in namespace '$NAMESPACE'"

    # Check if there are any resources at all
    RESOURCE_COUNT=$(kubectl get all -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l || echo "0")
    if [[ "$RESOURCE_COUNT" -gt 0 ]]; then
        log_info "Found $RESOURCE_COUNT resource(s) in namespace '$NAMESPACE'"
        log_warning "These may be resources from a partial deployment"
    else
        log_info "Namespace is empty or contains only non-PyBase resources"
    fi

    echo ""
}

# =============================================================================
# Resource Listing
# =============================================================================

list_resources() {
    print_header "Resources to be Deleted"

    local resource_count=0

    echo "Namespace: $NAMESPACE"
    echo ""

    # List deployments
    echo "Deployments:"
    kubectl get deployments -n "$NAMESPACE" -o name 2>/dev/null | while read -r line; do
        echo "  - $line"
        ((resource_count++)) || true
    done

    # List statefulsets
    echo ""
    echo "StatefulSets:"
    kubectl get statefulsets -n "$NAMESPACE" -o name 2>/dev/null | while read -r line; do
        echo "  - $line"
        ((resource_count++)) || true
    done

    # List services
    echo ""
    echo "Services:"
    kubectl get services -n "$NAMESPACE" -o name 2>/dev/null | while read -r line; do
        echo "  - $line"
        ((resource_count++)) || true
    done

    # List PVCs
    echo ""
    echo "PersistentVolumeClaims:"
    kubectl get pvc -n "$NAMESPACE" -o name 2>/dev/null | while read -r line; do
        echo "  - $line"
        ((resource_count++)) || true
    done

    # List ConfigMaps
    echo ""
    echo "ConfigMaps:"
    kubectl get configmaps -n "$NAMESPACE" -o name 2>/dev/null | while read -r line; do
        echo "  - $line"
        ((resource_count++)) || true
    done

    # List Secrets
    echo ""
    echo "Secrets:"
    kubectl get secrets -n "$NAMESPACE" -o name 2>/dev/null | while read -r line; do
        echo "  - $line"
        ((resource_count++)) || true
    done

    echo ""
    log_info "Total resources found: $resource_count"
    echo ""

    if [[ "$DELETE_ALL" == true ]]; then
        log_warning "Entire namespace will be deleted (all resources)"
    elif [[ "$DELETE_PVCS" == true ]]; then
        log_warning "PVCs will be deleted and their data will be lost"
    else
        log_info "PVCs will be preserved (data will not be deleted)"
    fi

    echo ""
}

# =============================================================================
# Helm Uninstall
# =============================================================================

helm_uninstall() {
    print_header "Uninstalling Helm Release"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "Dry-run: Would uninstall Helm release '$HELM_RELEASE_NAME'"
        echo ""
        echo "Command: helm uninstall $HELM_RELEASE_NAME -n $NAMESPACE"
        return
    fi

    local uninstall_args=("$HELM_RELEASE_NAME" -n "$NAMESPACE")

    # Add flags based on options
    if [[ "$DELETE_PVCS" == false ]]; then
        # Helm doesn't delete PVCs by default, but we note it here
        log_info "PVCs will be preserved (use --delete-pvcs to delete them)"
    fi

    log_info "Uninstalling Helm release: $HELM_RELEASE_NAME"

    if helm uninstall "${uninstall_args[@]}"; then
        log_success "Helm release uninstalled"
    else
        log_error "Failed to uninstall Helm release"
        log_info "Continuing with cleanup..."
    fi

    echo ""
}

# =============================================================================
# Kustomize Cleanup
# =============================================================================

kustomize_cleanup() {
    print_header "Removing Kustomize Resources"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "Dry-run: Would delete Kustomize resources"
        return
    fi

    # Delete resources in reverse order of dependencies
    # Ingress -> Services -> Deployments/StatefulSets -> ConfigMaps -> PVCs

    log_info "Deleting ingress..."
    kubectl delete ingress -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true

    log_info "Deleting HPAs..."
    kubectl delete hpa -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true

    log_info "Deleting PodDisruptionBudgets..."
    kubectl delete pdb -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true

    log_info "Deleting NetworkPolicies..."
    kubectl delete networkpolicy -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true

    log_info "Deleting services..."
    kubectl delete service -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true

    log_info "Deleting deployments..."
    kubectl delete deployment -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true

    log_info "Deleting statefulsets..."
    kubectl delete statefulset -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true

    log_info "Deleting Jobs..."
    kubectl delete job -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true

    log_info "Deleting ConfigMaps..."
    kubectl delete configmap -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true

    if [[ "$DELETE_SECRETS" == true ]]; then
        log_info "Deleting secrets..."
        kubectl delete secret -n "$NAMESPACE" -l "app.kubernetes.io/name=pybase" --ignore-not-found=true
    fi

    log_success "Kustomize resources removed"

    echo ""
}

# =============================================================================
# PVC Cleanup
# =============================================================================

cleanup_pvcs() {
    if [[ "$DELETE_PVCS" == false ]]; then
        log_info "Skipping PVC deletion (data preserved)"
        return
    fi

    print_header "Deleting PersistentVolumeClaims"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "Dry-run: Would delete PVCs and their data"
        return
    fi

    confirm_deletion "all PVCs and their data" \
        "This will permanently delete all stored data including database, cache, and file storage."

    log_info "Deleting PVCs..."
    kubectl delete pvc -n "$NAMESPACE" --all --ignore-not-found=true

    log_success "PVCs deleted"
    echo ""
}

# =============================================================================
# Namespace Cleanup
# =============================================================================

cleanup_namespace() {
    if [[ "$DELETE_ALL" == false ]]; then
        log_info "Preserving namespace '$NAMESPACE'"
        return
    fi

    print_header "Deleting Namespace"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "Dry-run: Would delete namespace '$NAMESPACE'"
        return
    fi

    confirm_deletion "entire namespace '$NAMESPACE'" \
        "This will delete ALL resources in the namespace, including non-PyBase resources."

    log_info "Deleting namespace: $NAMESPACE"
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true

    log_success "Namespace deleted"
    echo ""
}

# =============================================================================
# Verification
# =============================================================================

verify_cleanup() {
    print_header "Verifying Cleanup"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "Dry-run: Skipping verification"
        return
    fi

    # Check if namespace still exists
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace '$NAMESPACE' still exists"

        # Count remaining resources
        REMAINING=$(kubectl get all -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l || echo "0")
        if [[ "$REMAINING" -gt 0 ]]; then
            log_info "Remaining resources in namespace: $REMAINING"
            echo ""
            kubectl get all -n "$NAMESPACE"
        else
            log_success "No application resources remaining"
        fi
    else
        log_success "Namespace '$NAMESPACE' has been deleted"
    fi

    echo ""
}

# =============================================================================
# Usage
# =============================================================================

usage() {
    echo "Usage: $0 [OPTIONS] [namespace]"
    echo ""
    echo "Arguments:"
    echo "  namespace - Kubernetes namespace (default: pybase)"
    echo ""
    echo "Options:"
    echo "  --helm           - Force Helm deployment removal"
    echo "  --kustomize      - Force Kustomize deployment removal"
    echo "  --delete-pvcs    - Also delete PVCs and their data"
    echo "  --delete-secrets - Also delete secrets"
    echo "  --delete-all     - Delete everything (namespace, PVCs, secrets)"
    echo "  --dry-run        - Show what would be deleted without deleting"
    echo "  --force          - Skip confirmation prompts"
    echo "  -h, --help       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Remove deployment but keep data"
    echo "  $0"
    echo ""
    echo "  # Remove everything including data"
    echo "  $0 --delete-pvcs"
    echo ""
    echo "  # Remove entire namespace"
    echo "  $0 --delete-all"
    echo ""
    echo "  # Preview what would be deleted"
    echo "  $0 --dry-run"
    echo ""
    echo "  # Remove Helm deployment from production namespace"
    echo "  $0 --helm production"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
    print_header "PyBase Kubernetes Tear-Down"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --helm)
                DEPLOYMENT_TYPE="helm"
                shift
                ;;
            --kustomize)
                DEPLOYMENT_TYPE="kustomize"
                shift
                ;;
            --delete-pvcs)
                DELETE_PVCS=true
                shift
                ;;
            --delete-secrets)
                DELETE_SECRETS=true
                shift
                ;;
            --delete-all)
                DELETE_ALL=true
                DELETE_PVCS=true
                DELETE_SECRETS=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
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
                NAMESPACE="$1"
                shift
                ;;
        esac
    done

    if [[ "$DRY_RUN" == false ]]; then
        confirm_deletion "PyBase deployment"
    fi

    # Check prerequisites
    check_prerequisites

    # Detect deployment type if not specified
    if [[ -z "$DEPLOYMENT_TYPE" ]]; then
        detect_deployment_type
    fi

    # List resources that will be deleted
    list_resources

    # Remove deployment based on type
    if [[ "$DEPLOYMENT_TYPE" == "helm" ]]; then
        helm_uninstall
    elif [[ "$DEPLOYMENT_TYPE" == "kustomize" ]]; then
        kustomize_cleanup
    fi

    # Clean up PVCs if requested
    cleanup_pvcs

    # Delete namespace if requested
    cleanup_namespace

    # Verify cleanup
    verify_cleanup

    print_header "Tear-Down Complete"
    log_success "PyBase deployment removed from namespace '$NAMESPACE'"
    echo ""
}

# Run main function
main "$@"
