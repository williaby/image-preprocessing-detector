#!/bin/bash
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

# Modal helper functions for image-detection project
# Simplifies common Modal operations

set -euo pipefail
IFS=$'\n\t'

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Modal CLI is installed
check_modal_installed() {
    if ! command -v modal &> /dev/null; then
        echo -e "${RED}Error: Modal CLI not installed${NC}"
        echo "Install with: poetry add modal && poetry install"
        exit 1
    fi
}

# Check if authenticated
check_modal_auth() {
    # Check if token file exists
    if [ ! -f "$HOME/.modal.toml" ]; then
        echo -e "${RED}Error: Not authenticated with Modal${NC}"
        echo "Run: modal token new"
        exit 1
    fi
}

# Setup Modal secrets for GCS (base64 format for consistency)
setup_gcs_secret() {
    local key_path="$1"

    if [ -z "$key_path" ]; then
        echo -e "${RED}Error: GCS service account key path required${NC}"
        echo "Usage: $0 setup-gcs-secret /path/to/key.json"
        exit 1
    fi

    if [ ! -f "$key_path" ]; then
        echo -e "${RED}Error: Key file not found: $key_path${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Encoding service account key to base64...${NC}"
    # Encode to base64 (single line, no wrapping)
    # Portable approach: works on both GNU (Linux) and BSD (macOS) base64
    GCP_SA_KEY_B64=$(base64 < "$key_path" | tr -d '\n')

    # Verify base64 encoding succeeded and is not empty
    if [ -z "$GCP_SA_KEY_B64" ]; then
        echo -e "${RED}Error: Failed to encode service account key to base64${NC}"
        echo "Check that the file is readable and contains valid JSON"
        exit 1
    fi

    # Verify the encoded value looks like valid base64 (basic sanity check)
    if ! echo "$GCP_SA_KEY_B64" | grep -qE '^[A-Za-z0-9+/=]+$'; then
        echo -e "${RED}Error: Base64 encoding produced invalid characters${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Creating Modal secret 'gcs-credentials' with GCP_SA_KEY...${NC}"
    if ! modal secret create gcs-credentials GCP_SA_KEY="$GCP_SA_KEY_B64"; then
        echo -e "${RED}Error: Failed to create Modal secret${NC}"
        echo "Check that you are authenticated with Modal (modal token new)"
        exit 1
    fi

    echo -e "${GREEN}✅ GCS secret created successfully (base64 format)${NC}"
    echo -e "${GREEN}   Secret name: gcs-credentials${NC}"
    echo -e "${GREEN}   Environment variable: GCP_SA_KEY${NC}"
}

# Test GPU access
test_gpu() {
    echo -e "${YELLOW}Testing GPU access...${NC}"
    poetry run modal run modal/app.py::hello_gpu
}

# Run Phase 2 training
train_phase2() {
    echo -e "${YELLOW}Starting Phase 2 IQA training...${NC}"
    echo "Monitor at: https://modal.com/apps"
    poetry run modal run modal/train_phase2_iqa.py
}

# Run Phase 3 training
train_phase3() {
    echo -e "${YELLOW}Starting Phase 3 YOLOv8 training...${NC}"
    echo "Monitor at: https://modal.com/apps"
    poetry run modal run modal/train_phase3_yolov8.py
}

# Monitor Modal app
monitor() {
    echo -e "${YELLOW}Opening Modal dashboard...${NC}"
    if command -v xdg-open &> /dev/null; then
        xdg-open https://modal.com/apps
    elif command -v open &> /dev/null; then
        open https://modal.com/apps
    else
        echo "Visit: https://modal.com/apps"
    fi
}

# Show usage costs
show_costs() {
    echo -e "${YELLOW}Checking Modal usage...${NC}"
    poetry run modal profile current
}

# List secrets
list_secrets() {
    echo -e "${YELLOW}Listing Modal secrets...${NC}"
    poetry run modal secret list
}

# Main command router
case "${1:-}" in
    setup-gcs-secret)
        check_modal_installed
        check_modal_auth
        setup_gcs_secret "$2"
        ;;
    test-gpu)
        check_modal_installed
        check_modal_auth
        test_gpu
        ;;
    train-phase2)
        check_modal_installed
        check_modal_auth
        train_phase2
        ;;
    train-phase3)
        check_modal_installed
        check_modal_auth
        train_phase3
        ;;
    monitor)
        monitor
        ;;
    costs)
        check_modal_installed
        check_modal_auth
        show_costs
        ;;
    secrets)
        check_modal_installed
        check_modal_auth
        list_secrets
        ;;
    *)
        echo "Usage: $0 {setup-gcs-secret|test-gpu|train-phase2|train-phase3|monitor|costs|secrets}"
        echo ""
        echo "Commands:"
        echo "  setup-gcs-secret <path>  - Setup GCS credentials in Modal"
        echo "  test-gpu                 - Test GPU access"
        echo "  train-phase2             - Run Phase 2 IQA training"
        echo "  train-phase3             - Run Phase 3 YOLOv8 training"
        echo "  monitor                  - Open Modal dashboard"
        echo "  costs                    - Show Modal usage and costs"
        echo "  secrets                  - List Modal secrets"
        exit 1
        ;;
esac
