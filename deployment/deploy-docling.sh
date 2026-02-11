#!/bin/bash
# Deploy Docling OCR Server to Docker VM
#
# Usage:
#   ./deploy-docling.sh [standard|vlm]
#
# Prerequisites:
#   1. SSH access to Docker VM (192.168.1.209)
#   2. NFS share for datasets mounted on Docker VM
#   3. Port 5001 available

set -euo pipefail

DOCKER_HOST="${DOCKER_HOST:-byron@192.168.1.209}"
DEPLOY_DIR="${DEPLOY_DIR:-/data/compose/docling}"
MODE="${1:-standard}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Select compose file based on mode
if [[ "$MODE" == "vlm" ]]; then
    COMPOSE_FILE="docker-compose.docling-vlm.yml"
    log_info "Deploying Docling with GraniteDocling VLM (higher accuracy)"
else
    COMPOSE_FILE="docker-compose.docling.yml"
    log_info "Deploying Docling standard mode (faster)"
fi

# Check SSH connectivity
log_info "Checking SSH connectivity to $DOCKER_HOST..."
if ! ssh -o ConnectTimeout=5 "$DOCKER_HOST" "echo 'Connected'" &>/dev/null; then
    log_error "Cannot connect to Docker VM at $DOCKER_HOST"
    exit 1
fi

# Create deployment directory on Docker VM
log_info "Creating deployment directory..."
ssh "$DOCKER_HOST" "sudo mkdir -p $DEPLOY_DIR && sudo chown \$(whoami) $DEPLOY_DIR"

# Copy compose file to Docker VM
log_info "Copying compose file..."
scp "$(dirname "$0")/$COMPOSE_FILE" "$DOCKER_HOST:$DEPLOY_DIR/docker-compose.yml"

# Check NFS mount for datasets
log_info "Checking dataset mount..."
if ! ssh "$DOCKER_HOST" "test -d /mnt/unraid/datasets"; then
    log_warn "Dataset mount not found at /mnt/unraid/datasets"
    log_warn "Please create NFS share on Unraid and mount it first"
    log_warn "See deployment/README.md for instructions"
fi

# Create output directory
log_info "Creating output directory..."
ssh "$DOCKER_HOST" "sudo mkdir -p /mnt/unraid/appdata/docling/output && sudo chmod 755 /mnt/unraid/appdata/docling/output && sudo chown \$(whoami) /mnt/unraid/appdata/docling/output"

# Pull the image
log_info "Pulling Docling image..."
ssh "$DOCKER_HOST" "cd $DEPLOY_DIR && docker compose pull"

# Stop existing container if running
log_info "Stopping existing container (if any)..."
ssh "$DOCKER_HOST" "cd $DEPLOY_DIR && docker compose down 2>/dev/null || true"

# Start the container
log_info "Starting Docling container..."
ssh "$DOCKER_HOST" "cd $DEPLOY_DIR && docker compose up -d"

# Wait for health check
log_info "Waiting for container to be healthy..."
for i in {1..30}; do
    if ssh "$DOCKER_HOST" "curl -sf http://localhost:5001/health" &>/dev/null; then
        log_info "Docling server is healthy!"
        break
    fi
    if [[ $i -eq 30 ]]; then
        log_warn "Health check timeout - checking logs..."
        ssh "$DOCKER_HOST" "docker logs docling-serve --tail 50"
        exit 1
    fi
    echo -n "."
    sleep 10
done

# Print access information
echo ""
log_info "=== Deployment Complete ==="
echo ""
echo "  API Endpoint:  http://192.168.1.209:5001"
echo "  Web UI:        http://192.168.1.209:5001/ui"
echo "  API Docs:      http://192.168.1.209:5001/docs"
echo "  Health Check:  http://192.168.1.209:5001/health"
echo ""
echo "  Mode: $MODE"
if [[ "$MODE" == "vlm" ]]; then
    echo "  Model: ibm-granite/granite-docling-258M"
    echo "  Expected throughput: ~8-10 pages/second"
else
    echo "  Model: RapidOCR (default)"
    echo "  Expected throughput: ~12 pages/second"
fi
echo ""
log_info "Test with: curl http://192.168.1.209:5001/health"
