#!/bin/bash
# PyBase Kubernetes Smoke Test
#
# This script validates that a PyBase Kubernetes deployment is healthy.
# It checks deployments, pods, services, PVCs, and connectivity.
#
# Usage:
#   ./k8s/smoke-test.sh [namespace]
#
# Arguments:
#   namespace - Kubernetes namespace (default: pybase)

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

NAMESPACE="${1:-pybase}"
TIMEOUT_SECONDS=300
API_NAMESPACE="pybase"
COMPONENT_NAMESPACE="pybase"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0
WARNINGS=0

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED++)) || true
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" >&2
    ((FAILED++)) || true
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
    ((WARNINGS++)) || true
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
        exit 1
    fi
    log_success "Kubernetes cluster is accessible"

    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace '$NAMESPACE' does not exist"
        echo "Create namespace with: kubectl create namespace $NAMESPACE"
        exit 1
    fi
    log_success "Namespace '$NAMESPACE' exists"

    echo ""
}

# =============================================================================
# Deployment Checks
# =============================================================================

check_deployments() {
    print_header "Checking Deployments"

    local required_deployments=(
        "pybase-api"
        "pybase-extraction-worker"
        "pybase-search-worker"
        "pybase-frontend"
    )

    local optional_deployments=(
        "pybase-postgres"
        "pybase-redis"
        "pybase-minio"
        "pybase-meilisearch"
    )

    # Check required deployments
    log_info "Checking required deployments..."
    for deployment in "${required_deployments[@]}"; do
        if kubectl get deployment "$deployment" -n "$NAMESPACE" &> /dev/null; then
            local ready_replicas
            ready_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
            local desired_replicas
            desired_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "1")

            if [[ "$ready_replicas" -eq "$desired_replicas" ]] && [[ "$ready_replicas" -gt 0 ]]; then
                log_success "Deployment $deployment: $ready_replicas/$desired_replicas replicas ready"
            else
                log_error "Deployment $deployment: $ready_replicas/$desired_replicas replicas ready (expected $desired_replicas)"
            fi
        else
            log_error "Deployment $deployment not found"
        fi
    done

    # Check optional deployments
    echo ""
    log_info "Checking optional deployments..."
    for deployment in "${optional_deployments[@]}"; do
        if kubectl get deployment "$deployment" -n "$NAMESPACE" &> /dev/null; then
            local ready_replicas
            ready_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
            local desired_replicas
            desired_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "1")

            if [[ "$ready_replicas" -eq "$desired_replicas" ]] && [[ "$ready_replicas" -gt 0 ]]; then
                log_success "Deployment $deployment: $ready_replicas/$desired_replicas replicas ready"
            else
                log_warning "Deployment $deployment: $ready_replicas/$desired_replicas replicas ready"
            fi
        else
            log_info "Optional deployment $deployment not found (may be using external services)"
        fi
    done

    echo ""
}

# =============================================================================
# Pod Health Checks
# =============================================================================

check_pods() {
    print_header "Checking Pod Health"

    # Get all pods in the namespace
    local pods
    pods=$(kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)

    if [[ -z "$pods" ]]; then
        log_error "No pods found in namespace '$NAMESPACE'"
        return
    fi

    local pod_count=0
    local ready_count=0

    for pod in $pods; do
        ((pod_count++)) || true

        local phase
        phase=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null)

        local ready
        ready=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)

        if [[ "$phase" == "Running" ]] && [[ "$ready" == "True" ]]; then
            log_success "Pod $pod is running and ready"
            ((ready_count++)) || true
        else
            log_error "Pod $pod: phase=$phase, ready=$ready"

            # Show pod events if there's an error
            local pod_events
            pod_events=$(kubectl get events -n "$NAMESPACE" --field-selector involvedObject.name="$pod" --sort-by='.lastTimestamp' -o jsonpath='{.items[-1].message}' 2>/dev/null || echo "")
            if [[ -n "$pod_events" ]]; then
                echo "  Last event: $pod_events"
            fi
        fi
    done

    echo ""
    log_info "Pod summary: $ready_count/$pod_count pods ready"
    echo ""
}

# =============================================================================
# Service Checks
# =============================================================================

check_services() {
    print_header "Checking Services"

    local required_services=(
        "pybase-api"
        "pybase-frontend"
    )

    local optional_services=(
        "pybase-postgres"
        "pybase-redis"
        "pybase-minio"
        "pybase-minio-console"
        "pybase-meilisearch"
    )

    # Check required services
    log_info "Checking required services..."
    for service in "${required_services[@]}"; do
        if kubectl get service "$service" -n "$NAMESPACE" &> /dev/null; then
            local service_type
            service_type=$(kubectl get service "$service" -n "$NAMESPACE" -o jsonpath='{.spec.type}' 2>/dev/null)

            local cluster_ip
            cluster_ip=$(kubectl get service "$service" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)

            if [[ "$cluster_ip" != "None" ]] && [[ -n "$cluster_ip" ]]; then
                log_success "Service $service: type=$service_type, clusterIP=$cluster_ip"
            else
                log_error "Service $service: no cluster IP assigned"
            fi
        else
            log_error "Service $service not found"
        fi
    done

    # Check optional services
    echo ""
    log_info "Checking optional services..."
    for service in "${optional_services[@]}"; do
        if kubectl get service "$service" -n "$NAMESPACE" &> /dev/null; then
            local cluster_ip
            cluster_ip=$(kubectl get service "$service" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)

            if [[ "$cluster_ip" != "None" ]] && [[ -n "$cluster_ip" ]]; then
                log_success "Service $service: clusterIP=$cluster_ip"
            else
                log_warning "Service $service: no cluster IP assigned"
            fi
        else
            log_info "Optional service $service not found"
        fi
    done

    echo ""
}

# =============================================================================
# PVC Checks
# =============================================================================

check_pvcs() {
    print_header "Checking Persistent Volume Claims"

    local pvcs
    pvcs=$(kubectl get pvc -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)

    if [[ -z "$pvcs" ]]; then
        log_info "No PVCs found in namespace '$NAMESPACE'"
        echo ""
        return
    fi

    for pvc in $pvcs; do
        local status
        status=$(kubectl get pvc "$pvc" -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null)

        local capacity
        capacity=$(kubectl get pvc "$pvc" -n "$NAMESPACE" -o jsonpath='{.status.capacity.storage}' 2>/dev/null)

        if [[ "$status" == "Bound" ]]; then
            log_success "PVC $pvc: $status ($capacity)"
        else
            log_error "PVC $pvc: $status (expected: Bound)"
        fi
    done

    echo ""
}

# =============================================================================
# Resource Limits Checks
# =============================================================================

check_resource_limits() {
    print_header "Checking Resource Limits"

    local deployments
    deployments=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)

    if [[ -z "$deployments" ]]; then
        log_warning "No deployments found to check resource limits"
        echo ""
        return
    fi

    for deployment in $deployments; do
        local has_limits
        has_limits=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].resources}' 2>/dev/null)

        if [[ -n "$has_limits" ]]; then
            local requests_cpu
            requests_cpu=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].resources.requests.cpu}' 2>/dev/null || echo "N/A")

            local limits_cpu
            limits_cpu=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].resources.limits.cpu}' 2>/dev/null || echo "N/A")

            local requests_memory
            requests_memory=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].resources.requests.memory}' 2>/dev/null || echo "N/A")

            local limits_memory
            limits_memory=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].resources.limits.memory}' 2>/dev/null || echo "N/A")

            log_success "Deployment $deployment has resource limits defined"
            echo "  Requests: CPU=$requests_cpu, Memory=$requests_memory"
            echo "  Limits:   CPU=$limits_cpu, Memory=$limits_memory"
        else
            log_warning "Deployment $deployment has no resource limits defined"
        fi
    done

    echo ""
}

# =============================================================================
# Health Endpoint Checks
# =============================================================================

check_health_endpoints() {
    print_header "Checking Health Endpoints"

    # Check if API service exists
    if ! kubectl get service pybase-api -n "$NAMESPACE" &> /dev/null; then
        log_error "API service not found, skipping health endpoint checks"
        echo ""
        return
    fi

    # Get API pod
    local api_pod
    api_pod=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=api -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [[ -z "$api_pod" ]]; then
        log_error "No API pods found, skipping health endpoint checks"
        echo ""
        return
    fi

    # Check API health endpoint
    log_info "Checking API health endpoint..."
    local health_status
    health_status=$(kubectl exec "$api_pod" -n "$NAMESPACE" -c pybase-api -- wget -q -O- http://localhost:8000/api/v1/health 2>/dev/null || echo "")

    if [[ -n "$health_status" ]]; then
        log_success "API health endpoint is responding"
        echo "  Response: $health_status"
    else
        log_error "API health endpoint is not responding"
    fi

    echo ""
}

# =============================================================================
# Horizontal Pod Autoscaler Checks
# =============================================================================

check_hpas() {
    print_header "Checking Horizontal Pod Autoscalers"

    local hpas
    hpas=$(kubectl get hpa -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)

    if [[ -z "$hpas" ]]; then
        log_info "No HPAs found in namespace '$NAMESPACE'"
        echo ""
        return
    fi

    for hpa in $hpas; do
        local min_replicas
        min_replicas=$(kubectl get hpa "$hpa" -n "$NAMESPACE" -o jsonpath='{.spec.minReplicas}' 2>/dev/null)

        local max_replicas
        max_replicas=$(kubectl get hpa "$hpa" -n "$NAMESPACE" -o jsonpath='{.spec.maxReplicas}' 2>/dev/null)

        local current_replicas
        current_replicas=$(kubectl get hpa "$hpa" -n "$NAMESPACE" -o jsonpath='{.status.currentReplicas}' 2>/dev/null)

        local target_cpu
        target_cpu=$(kubectl get hpa "$hpa" -n "$NAMESPACE" -o jsonpath='{.spec.metrics[0].resource.target.averageUtilization}' 2>/dev/null || echo "N/A")

        if [[ -n "$current_replicas" ]] && [[ "$current_replicas" -ge "$min_replicas" ]]; then
            log_success "HPA $hpa: $current_replicas replicas (min: $min_replicas, max: $max_replicas, target CPU: ${target_cpu}%)"
        else
            log_warning "HPA $hpa: current replicas=$current_replicas (min: $min_replicas, max: $max_replicas)"
        fi
    done

    echo ""
}

# =============================================================================
# Network Policy Checks
# =============================================================================

check_network_policies() {
    print_header "Checking Network Policies"

    local policies
    policies=$(kubectl get networkpolicy -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)

    if [[ -z "$policies" ]]; then
        log_warning "No NetworkPolicies found in namespace '$NAMESPACE'"
        echo "NetworkPolicies are recommended for production security"
        echo ""
        return
    fi

    for policy in $policies; do
        local pod_selector
        pod_selector=$(kubectl get networkpolicy "$policy" -n "$NAMESPACE" -o jsonpath='{.spec.podSelector.matchLabels.app\.kubernetes\.io/component}' 2>/dev/null || echo "all")

        log_success "NetworkPolicy $policy applies to component: $pod_selector"
    done

    echo ""
}

# =============================================================================
# Pod Disruption Budget Checks
# =============================================================================

check_pdbs() {
    print_header "Checking Pod Disruption Budgets"

    local pdbs
    pdbs=$(kubectl get pdb -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)

    if [[ -z "$pdbs" ]]; then
        log_warning "No PodDisruptionBudgets found in namespace '$NAMESPACE'"
        echo "PDBs are recommended for high availability"
        echo ""
        return
    fi

    for pdb in $pdbs; do
        local min_available
        min_available=$(kubectl get pdb "$pdb" -n "$NAMESPACE" -o jsonpath='{.spec.minAvailable}' 2>/dev/null || echo "N/A")

        local current_pods
        current_pods=$(kubectl get pdb "$pdb" -n "$NAMESPACE" -o jsonpath='{.status.currentHealthy}' 2>/dev/null || echo "N/A")

        local desired_pods
        desired_pods=$(kubectl get pdb "$pdb" -n "$NAMESPACE" -o jsonpath='{.status.desiredHealthy}' 2>/dev/null || echo "N/A")

        if [[ "$current_pods" -ge "$desired_pods" ]]; then
            log_success "PDB $pdb: $current_pods/$desired_pods pods healthy (min available: $min_available)"
        else
            log_error "PDB $pdb: $current_pods/$desired_pods pods healthy (min available: $min_available)"
        fi
    done

    echo ""
}

# =============================================================================
# Summary
# =============================================================================

print_summary() {
    print_header "Smoke Test Summary"

    echo "Namespace: $NAMESPACE"
    echo "Total tests: $((PASSED + FAILED))"
    echo -e "  ${GREEN}Passed: $PASSED${NC}"
    echo -e "  ${RED}Failed: $FAILED${NC}"
    echo -e "  ${YELLOW}Warnings: $WARNINGS${NC}"
    echo ""

    if [[ $FAILED -eq 0 ]]; then
        echo -e "${GREEN}✓ All critical checks passed!${NC}"
        echo ""
        echo "Your PyBase deployment appears to be healthy."
        echo ""
        echo "Next steps:"
        echo "  - Access the application at the Ingress/LoadBalancer URL"
        echo "  - Check logs: kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=pybase"
        echo "  - Monitor resources: kubectl top pods -n $NAMESPACE"
        echo ""
        return 0
    else
        echo -e "${RED}✗ Some checks failed!${NC}"
        echo ""
        echo "Troubleshooting:"
        echo "  - Check pod logs: kubectl logs -n $NAMESPACE <pod-name>"
        echo "  - Describe failed resources: kubectl describe -n $NAMESPACE <resource-type> <name>"
        echo "  - Check events: kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp'"
        echo "  - Review documentation: k8s/README.md"
        echo ""
        return 1
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_header "PyBase Kubernetes Smoke Test"

    echo "Namespace: $NAMESPACE"
    echo "Timeout: ${TIMEOUT_SECONDS}s"
    echo ""

    check_prerequisites
    check_deployments
    check_pods
    check_services
    check_pvcs
    check_resource_limits
    check_health_endpoints
    check_hpas
    check_network_policies
    check_pdbs

    print_summary
}

# Run main function
main "$@"
