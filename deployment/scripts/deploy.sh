#!/usr/bin/env bash
set -euo pipefail

#=============================================================================
# Zambia Health Platform - Deployment Script
# Supports: EKS, AKS, GKE, OKE, and bare-metal/edge deployments
#=============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly TIMESTAMP=$(date +%Y%m%d-%H%M%S)
readonly LOG_FILE="/var/log/zambia-health/deploy-${TIMESTAMP}.log"

# Defaults
NAMESPACE="production"
CLUSTER_TYPE="eks"
IMAGE_TAG="latest"
DRY_RUN=false
ROLLBACK_ON_FAILURE=true
HEALTH_CHECK_TIMEOUT=300

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()   { echo -e "${GREEN}[$(date +%H:%M:%S)]${NC} $*" | tee -a "${LOG_FILE}"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "${LOG_FILE}"; }
error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "${LOG_FILE}" >&2; }

usage() {
    cat <<EOF
Zambia Health Platform - Deployment Script

Usage: $(basename "$0") [options]

Options:
  -n, --namespace NAME     Kubernetes namespace (default: production)
  -c, --cluster TYPE       Cluster type: eks|aks|gke|oke|baremetal (default: eks)
  -t, --tag TAG            Docker image tag to deploy (default: latest)
  -m, --manifest-dir DIR   Kubernetes manifest directory
  -e, --environment ENV    Deployment environment: prod|staging|dev|edge
  -d, --dry-run           Perform dry-run (no changes)
  -r, --no-rollback       Disable automatic rollback on failure
  -h, --help              Show this help message

Examples:
  $(basename "$0") --tag v1.2.3 --namespace production
  $(basename "$0") --cluster baremetal --environment edge --dry-run
EOF
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -n|--namespace)      NAMESPACE="$2"; shift 2 ;;
            -c|--cluster)        CLUSTER_TYPE="$2"; shift 2 ;;
            -t|--tag)            IMAGE_TAG="$2"; shift 2 ;;
            -m|--manifest-dir)   MANIFEST_DIR="$2"; shift 2 ;;
            -e|--environment)    ENVIRONMENT="$2"; shift 2 ;;
            -d|--dry-run)        DRY_RUN=true; shift ;;
            -r|--no-rollback)    ROLLBACK_ON_FAILURE=false; shift ;;
            -h|--help)           usage ;;
            *)                   error "Unknown option: $1"; usage ;;
        esac
    done

    MANIFEST_DIR="${MANIFEST_DIR:-${PROJECT_ROOT}/k8s/${ENVIRONMENT:-${NAMESPACE}}}"
    if [[ ! -d "${MANIFEST_DIR}" ]]; then
        error "Manifest directory not found: ${MANIFEST_DIR}"
        exit 1
    fi
}

check_prerequisites() {
    log "Checking prerequisites..."

    command -v kubectl >/dev/null 2>&1 || { error "kubectl required"; exit 1; }
    command -v docker >/dev/null 2>&1 || { error "docker required"; exit 1; }

    # Cluster-specific tools
    case "${CLUSTER_TYPE}" in
        eks) command -v aws >/dev/null 2>&1 || { error "aws CLI required for EKS"; exit 1; } ;;
        aks) command -v az >/dev/null 2>&1 || { error "az CLI required for AKS"; exit 1; } ;;
        gke) command -v gcloud >/dev/null 2>&1 || { error "gcloud CLI required for GKE"; exit 1; } ;;
        oke) command -v oci >/dev/null 2>&1 || { error "oci CLI required for OKE"; exit 1; } ;;
        baremetal) log "Bare-metal mode - skipping cloud CLI checks" ;;
    esac

    log "All prerequisites satisfied"
}

authenticate_cluster() {
    log "Authenticating to ${CLUSTER_TYPE} cluster..."

    case "${CLUSTER_TYPE}" in
        eks)
            aws eks update-kubeconfig \
                --name "${EKS_CLUSTER:-zambia-health-${ENVIRONMENT:-prod}}" \
                --region "${AWS_REGION:-af-south-1}"
            ;;
        aks)
            az aks get-credentials \
                --resource-group "${AZURE_RG:-zambia-health-prod}" \
                --name "${AKS_CLUSTER:-zambia-health-prod}"
            ;;
        gke)
            gcloud container clusters get-credentials \
                "${GKE_CLUSTER:-zambia-health-prod}" \
                --region "${GCP_REGION:-africa-south1}"
            ;;
        oke)
            oci ce cluster create-kubeconfig \
                --cluster-id "${OKE_CLUSTER_OCID}" \
                --file "${HOME}/.kube/config" \
                --region "${OCI_REGION:-af-johannesburg-1}"
            ;;
        baremetal)
            log "Bare-metal mode - assuming kubeconfig already configured"
            ;;
    esac

    # Verify cluster access
    if ! kubectl cluster-info >/dev/null 2>&1; then
        error "Cannot connect to cluster"
        exit 1
    fi
    log "Cluster authentication successful"
}

deploy_manifests() {
    log "Deploying manifests from ${MANIFEST_DIR}..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would apply the following manifests:"
        find "${MANIFEST_DIR}" -name "*.yaml" -o -name "*.yml" | sort | while read -r f; do
            echo "  - ${f}"
        done
        return 0
    fi

    # Create namespace if needed
    kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

    # Apply manifests
    if ! kubectl apply -f "${MANIFEST_DIR}" --namespace="${NAMESPACE}" --recursive; then
        error "Failed to apply manifests"
        return 1
    fi

    log "Manifests applied successfully"
}

wait_for_rollout() {
    log "Waiting for rollout to complete..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Skipping rollout wait"
        return 0
    fi

    local deployments
    deployments=$(kubectl get deployments -n "${NAMESPACE}" -o name 2>/dev/null || true)

    if [[ -z "${deployments}" ]]; then
        warn "No deployments found in namespace ${NAMESPACE}"
        return 0
    fi

    for dep in ${deployments}; do
        log "Waiting for ${dep}..."
        if ! kubectl rollout status "${dep}" -n "${NAMESPACE}" --timeout="${HEALTH_CHECK_TIMEOUT}s"; then
            error "Rollout timed out for ${dep}"
            return 1
        fi
    done

    log "All rollouts complete"
}

health_check() {
    log "Running health checks..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would run health checks against:"
        echo "  - https://api.zambia-health.example.com/health"
        return 0
    fi

    local endpoints=(
        "https://api.zambia-health.example.com/health"
        "https://api.zambia-health.example.com/ready"
    )

    for endpoint in "${endpoints[@]}"; do
        log "Checking ${endpoint}..."
        local status
        status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${endpoint}" 2>/dev/null || echo "000")
        if [[ "${status}" =~ ^(200|204|301)$ ]]; then
            log "  Health check passed (HTTP ${status})"
        else
            error "  Health check failed (HTTP ${status})"
            return 1
        fi
    done

    log "All health checks passed"
}

rollback() {
    warn "Initiating rollback..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would rollback deployments"
        return 0
    fi

    local deployments
    deployments=$(kubectl get deployments -n "${NAMESPACE}" -o name 2>/dev/null || true)

    for dep in ${deployments}; do
        local revision
        revision=$(kubectl rollout history "${dep}" -n "${NAMESPACE}" | tail -2 | head -1 | awk '{print $1}')
        if [[ -n "${revision}" ]] && [[ "${revision}" -gt 1 ]]; then
            log "Rolling back ${dep} to revision $((revision - 1))..."
            kubectl rollout undo "${dep}" -n "${NAMESPACE}" --to-revision=$((revision - 1))
        fi
    done

    # Wait for rollback
    for dep in ${deployments}; do
        kubectl rollout status "${dep}" -n "${NAMESPACE}" --timeout=120s || true
    done

    log "Rollback completed"
}

cleanup() {
    log "Cleaning up old resources..."

    if [[ "${DRY_RUN}" == "true" ]]; then
        log "DRY-RUN: Would clean up completed/failed pods"
        return 0
    fi

    # Remove completed pods
    kubectl delete pod -n "${NAMESPACE}" \
        --field-selector status.phase=Succeeded \
        --ignore-not-found 2>/dev/null || true

    # Remove failed pods
    kubectl delete pod -n "${NAMESPACE}" \
        --field-selector status.phase=Failed \
        --ignore-not-found 2>/dev/null || true

    log "Cleanup complete"
}

main() {
    # Ensure log directory exists
    mkdir -p "$(dirname "${LOG_FILE}")"

    log "=== Zambia Health Platform Deployment ==="
    log "Namespace:    ${NAMESPACE}"
    log "Cluster:      ${CLUSTER_TYPE}"
    log "Image Tag:    ${IMAGE_TAG}"
    log "Environment:  ${ENVIRONMENT:-${NAMESPACE}}"
    log "Dry Run:      ${DRY_RUN}"
    log ""

    check_prerequisites
    authenticate_cluster
    deploy_manifests || {
        if [[ "${ROLLBACK_ON_FAILURE}" == "true" ]]; then
            rollback
        fi
        exit 1
    }
    wait_for_rollout || {
        if [[ "${ROLLBACK_ON_FAILURE}" == "true" ]]; then
            rollback
        fi
        exit 1
    }
    health_check || {
        if [[ "${ROLLBACK_ON_FAILURE}" == "true" ]]; then
            rollback
        fi
        exit 1
    }
    cleanup

    log ""
    log "=== Deployment completed successfully ==="
}

parse_args "$@"
main
