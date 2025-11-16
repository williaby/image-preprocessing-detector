#!/bin/bash
# GCS Authentication Helper
# Automatically authenticates with GCS using service account from .env file
#
# Usage:
#   source scripts/auth_gcs.sh        # Authenticate and keep temp file
#   ./scripts/auth_gcs.sh --cleanup   # Authenticate and cleanup on exit

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="image-detection-478105"
ENV_FILE="${ENV_FILE:-.env}"

# Use mktemp for secure temporary file creation with restricted permissions
TEMP_SA_FILE=$(mktemp "${TMPDIR:-/tmp}/gcs-sa.XXXXXX.json")
chmod 600 "$TEMP_SA_FILE"  # Restrict to owner only

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    if [ -f "$TEMP_SA_FILE" ]; then
        rm -f "$TEMP_SA_FILE"
        log_info "Cleaned up temporary service account file"
    fi
}

# Register cleanup on exit if --cleanup flag is provided
if [ "$1" == "--cleanup" ]; then
    trap cleanup EXIT
fi

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    log_error ".env file not found at: $ENV_FILE"
    exit 1
fi

# Extract and decode GCP_SA_KEY from .env using Python
log_info "Reading GCP_SA_KEY from $ENV_FILE..."
python3 << 'EOF'
import os
import sys
from pathlib import Path
import base64

# Read .env file
env_file = os.getenv('ENV_FILE', '.env')
env_path = Path(env_file)

if not env_path.exists():
    print(f"Error: {env_file} not found", file=sys.stderr)
    sys.exit(1)

env_content = env_path.read_text()

# Extract GCP_SA_KEY value
found = False
for line in env_content.split('\n'):
    if line.startswith('GCP_SA_KEY='):
        b64_key = line.split('=', 1)[1]
        try:
            # Decode base64
            json_content = base64.b64decode(b64_key)
            # Write to temp file
            temp_file = os.getenv('TEMP_SA_FILE', f'/tmp/gcs-sa-{os.getenv("USER")}.json')
            Path(temp_file).write_bytes(json_content)
            found = True
            break
        except Exception as e:
            print(f"Error decoding GCP_SA_KEY: {e}", file=sys.stderr)
            sys.exit(1)

if not found:
    print("Error: GCP_SA_KEY not found in .env file", file=sys.stderr)
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    log_error "Failed to extract GCP_SA_KEY from .env"
    exit 1
fi

log_info "Service account key decoded to: $TEMP_SA_FILE"

# Activate service account
log_info "Authenticating with GCP service account..."
if gcloud auth activate-service-account --key-file="$TEMP_SA_FILE" 2>/dev/null; then
    log_info "✓ Authenticated as: $(gcloud config get-value account 2>/dev/null)"
else
    log_error "Failed to authenticate with service account"
    cleanup
    exit 1
fi

# Set project
log_info "Setting GCP project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID" 2>/dev/null || log_warn "Could not set project (non-critical)"

# Verify access to GCS bucket
log_info "Verifying GCS bucket access..."
if gsutil ls gs://image_detection_b/ &>/dev/null; then
    log_info "✓ GCS bucket access confirmed: gs://image_detection_b/"
else
    log_warn "Could not verify GCS bucket access (permissions may be limited)"
fi

echo ""
log_info "=== GCS Authentication Complete ==="
log_info "Service account file: $TEMP_SA_FILE"
log_info "Project: $PROJECT_ID"
log_info "Bucket: gs://image_detection_b/"
echo ""

# Export variables for use in other scripts
export GOOGLE_APPLICATION_CREDENTIALS="$TEMP_SA_FILE"
export GCP_PROJECT="$PROJECT_ID"
export GCS_BUCKET="gs://image_detection_b"

log_info "Environment variables exported:"
log_info "  GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS"
log_info "  GCP_PROJECT=$GCP_PROJECT"
log_info "  GCS_BUCKET=$GCS_BUCKET"
echo ""

# If sourced, don't cleanup automatically
if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    log_info "Script was sourced. Use 'cleanup' function to remove temp file when done."
    log_info "Or run: rm $TEMP_SA_FILE"
fi
