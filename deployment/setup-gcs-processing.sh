#!/bin/bash
# Set up GCS-based Docling processing on Docker VM
#
# This script:
#   1. Installs gcloud CLI
#   2. Sets up service account authentication
#   3. Creates processing directories
#   4. Deploys Docling container
#   5. Installs Python processing script
#
# Usage:
#   ./setup-gcs-processing.sh

set -euo pipefail

DOCKER_HOST="byron@192.168.1.209"
DEPLOY_DIR="/data/compose/docling"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check SSH connectivity
log_info "Checking SSH connectivity..."
if ! ssh -o ConnectTimeout=5 "$DOCKER_HOST" "echo 'Connected'" &>/dev/null; then
    log_error "Cannot connect to Docker VM"
    exit 1
fi

# Step 1: Install gcloud CLI if not present
log_info "Checking gcloud CLI..."
if ! ssh "$DOCKER_HOST" "which gcloud" &>/dev/null; then
    log_info "Installing gcloud CLI..."
    ssh "$DOCKER_HOST" "bash -s" << 'EOF'
        # Add Google Cloud SDK repo
        echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
        curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
        sudo apt-get update && sudo apt-get install -y google-cloud-cli
EOF
else
    log_info "gcloud CLI already installed"
fi

# Step 2: Create directories
log_info "Creating directories..."
ssh "$DOCKER_HOST" "sudo mkdir -p /data/docling/{input,output,secrets,scripts} && sudo chown -R byron:byron /data/docling"

# Step 3: Copy service account credentials
log_info "Setting up GCS credentials..."
if [[ -f ~/.config/gcloud/application_default_credentials.json ]]; then
    scp ~/.config/gcloud/application_default_credentials.json "$DOCKER_HOST:/data/docling/secrets/gcs-credentials.json"
    ssh "$DOCKER_HOST" "chmod 600 /data/docling/secrets/gcs-credentials.json"
    log_info "Copied application default credentials"
elif [[ -f ~/gcs-service-account.json ]]; then
    scp ~/gcs-service-account.json "$DOCKER_HOST:/data/docling/secrets/gcs-credentials.json"
    ssh "$DOCKER_HOST" "chmod 600 /data/docling/secrets/gcs-credentials.json"
    log_info "Copied service account credentials"
else
    log_warn "No GCS credentials found locally"
    log_warn "Please copy your service account JSON to:"
    log_warn "  $DOCKER_HOST:/data/docling/secrets/gcs-credentials.json"
    log_warn ""
    log_warn "Or authenticate interactively:"
    log_warn "  ssh $DOCKER_HOST"
    log_warn "  gcloud auth application-default login"
fi

# Step 4: Copy processing scripts
log_info "Copying processing scripts..."
scp "$SCRIPT_DIR/scripts/gcs_processor.py" "$DOCKER_HOST:/data/docling/scripts/"
scp "$SCRIPT_DIR/scripts/process-dataset-gcs.sh" "$DOCKER_HOST:/data/docling/scripts/"
ssh "$DOCKER_HOST" "chmod +x /data/docling/scripts/*.sh"

# Step 5: Install Python dependencies for processor
log_info "Installing Python dependencies..."
ssh "$DOCKER_HOST" "pip3 install --user httpx google-cloud-storage"

# Step 6: Deploy Docling container
log_info "Deploying Docling container..."
ssh "$DOCKER_HOST" "sudo mkdir -p $DEPLOY_DIR"
scp "$SCRIPT_DIR/docker-compose.docling-gcs.yml" "$DOCKER_HOST:$DEPLOY_DIR/docker-compose.yml"
scp -r "$SCRIPT_DIR/scripts" "$DOCKER_HOST:$DEPLOY_DIR/"

ssh "$DOCKER_HOST" "cd $DEPLOY_DIR && docker compose pull && docker compose up -d"

# Step 7: Wait for health
log_info "Waiting for Docling to be healthy..."
for i in {1..30}; do
    if ssh "$DOCKER_HOST" "curl -sf http://localhost:5001/health" &>/dev/null; then
        log_info "Docling is healthy!"
        break
    fi
    if [[ $i -eq 30 ]]; then
        log_warn "Health check timeout - container may still be starting"
    fi
    echo -n "."
    sleep 5
done

# Step 8: Test GCS access
log_info "Testing GCS access..."
if ssh "$DOCKER_HOST" "GOOGLE_APPLICATION_CREDENTIALS=/data/docling/secrets/gcs-credentials.json gsutil ls gs://image_detection_b/ 2>/dev/null | head -3"; then
    log_info "GCS access confirmed!"
else
    log_warn "GCS access test failed - check credentials"
fi

echo ""
log_info "=== Setup Complete ==="
echo ""
echo "Docling API:  http://192.168.1.209:5001"
echo "Web UI:       http://192.168.1.209:5001/ui"
echo ""
echo "To process a dataset:"
echo "  ssh $DOCKER_HOST"
echo "  cd /data/docling/scripts"
echo "  export GOOGLE_APPLICATION_CREDENTIALS=/data/docling/secrets/gcs-credentials.json"
echo "  python3 gcs_processor.py pubtabnet --workers 8"
echo ""
echo "Or from this machine:"
echo "  ssh $DOCKER_HOST 'cd /data/docling/scripts && GOOGLE_APPLICATION_CREDENTIALS=/data/docling/secrets/gcs-credentials.json python3 gcs_processor.py pubtabnet'"
