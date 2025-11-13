#!/bin/bash
# GCS Helper Scripts for Easy File Management
# Project: image-detection-478105
# Bucket: gs://image_detection_b

set -e

# Configuration
PROJECT_ID="image-detection-478105"
BUCKET="gs://image_detection_b"
LOCAL_ROOT="/home/byron/dev/image_detection"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper function for colored output
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verify gcloud authentication
check_auth() {
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &>/dev/null; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi

    # Set project
    gcloud config set project "$PROJECT_ID" &>/dev/null
    log_info "Authenticated as: $(gcloud config get-value account)"
}

# Upload config files
upload_configs() {
    log_info "Uploading configuration files to GCS..."

    gsutil -m cp configs/colab_phase2_iqa_gcs.yaml "$BUCKET/configs/" || true
    gsutil -m cp configs/colab_phase3_yolov8_gcs.yaml "$BUCKET/configs/" || true

    log_info "✓ Configs uploaded"
}

# Upload Phase 2 dataset
upload_phase2_dataset() {
    local dataset_dir="$LOCAL_ROOT/datasets/iqa_phase2"

    if [ ! -d "$dataset_dir" ]; then
        log_error "Dataset directory not found: $dataset_dir"
        log_info "Run: python scripts/prepare_phase2_data.py first"
        exit 1
    fi

    log_info "Uploading Phase 2 dataset to GCS..."
    log_info "This may take 10-30 minutes for ~10GB..."

    # Upload train/val/test splits in parallel
    gsutil -m -o "GSUtil:parallel_process_count=4" cp -r \
        "$dataset_dir/train" \
        "$dataset_dir/val" \
        "$dataset_dir/test" \
        "$BUCKET/datasets/iqa_phase2/"

    # Verify upload
    log_info "Verifying upload..."
    gsutil du -sh "$BUCKET/datasets/iqa_phase2/"

    log_info "✓ Phase 2 dataset uploaded"
}

# Download Phase 2 dataset from GCS
download_phase2_dataset() {
    local dataset_dir="$LOCAL_ROOT/datasets/iqa_phase2"

    log_info "Downloading Phase 2 dataset from GCS..."
    log_info "This may take 10-30 minutes for ~10GB..."

    mkdir -p "$dataset_dir"

    # Download in parallel
    gsutil -m -o "GSUtil:parallel_process_count=4" cp -r \
        "$BUCKET/datasets/iqa_phase2/*" \
        "$dataset_dir/"

    log_info "✓ Phase 2 dataset downloaded to: $dataset_dir"
}

# Sync local checkpoints to GCS
sync_checkpoints() {
    local phase="${1:-phase2}"
    local checkpoint_dir="$LOCAL_ROOT/checkpoints/${phase}_iqa"

    if [ ! -d "$checkpoint_dir" ]; then
        log_warn "No checkpoints found at: $checkpoint_dir"
        return
    fi

    log_info "Syncing checkpoints to GCS..."
    gsutil -m rsync -r -d "$checkpoint_dir" "$BUCKET/checkpoints/${phase}_iqa/"

    log_info "✓ Checkpoints synced"
}

# Download checkpoints from GCS
download_checkpoints() {
    local phase="${1:-phase2}"
    local checkpoint_dir="$LOCAL_ROOT/checkpoints/${phase}_iqa"

    log_info "Downloading checkpoints from GCS..."
    mkdir -p "$checkpoint_dir"

    gsutil -m rsync -r "$BUCKET/checkpoints/${phase}_iqa/" "$checkpoint_dir"

    log_info "✓ Checkpoints downloaded to: $checkpoint_dir"
}

# Upload final models
upload_models() {
    local phase="${1:-phase2}"
    local model_dir="$LOCAL_ROOT/models/${phase}_iqa"

    if [ ! -d "$model_dir" ]; then
        log_error "Model directory not found: $model_dir"
        exit 1
    fi

    log_info "Uploading models to GCS..."
    gsutil -m cp -r "$model_dir/*" "$BUCKET/models/${phase}_iqa/"

    log_info "✓ Models uploaded"
}

# List GCS bucket contents
list_bucket() {
    log_info "Bucket contents:"
    gsutil ls -lh "$BUCKET/" | head -50
}

# Show bucket size and costs
show_storage_info() {
    log_info "Storage usage by directory:"
    gsutil du -sh "$BUCKET/*"

    echo ""
    log_info "Total bucket size:"
    gsutil du -sh "$BUCKET"

    echo ""
    log_info "Estimated monthly cost (Standard storage @ \$0.020/GB):"
    total_gb=$(gsutil du -s "$BUCKET" | awk '{print $1/1024/1024/1024}')
    cost=$(echo "$total_gb * 0.020" | bc -l)
    printf "%.2f GB × \$0.020 = \$%.2f/month\n" "$total_gb" "$cost"
}

# Main menu
show_menu() {
    echo ""
    echo "=== GCS Helper Script ==="
    echo "Project: $PROJECT_ID"
    echo "Bucket: $BUCKET"
    echo ""
    echo "Available commands:"
    echo "  upload-configs          - Upload training configs"
    echo "  upload-phase2           - Upload Phase 2 dataset (~10GB)"
    echo "  download-phase2         - Download Phase 2 dataset"
    echo "  sync-checkpoints [phase] - Sync checkpoints to GCS"
    echo "  download-checkpoints [phase] - Download checkpoints from GCS"
    echo "  upload-models [phase]   - Upload trained models"
    echo "  list                    - List bucket contents"
    echo "  info                    - Show storage usage and costs"
    echo ""
    echo "Usage: $0 <command> [args]"
    echo ""
}

# Main script
main() {
    check_auth

    local command="${1:-help}"
    shift || true

    case "$command" in
        upload-configs)
            upload_configs
            ;;
        upload-phase2)
            upload_phase2_dataset
            ;;
        download-phase2)
            download_phase2_dataset
            ;;
        sync-checkpoints)
            sync_checkpoints "$@"
            ;;
        download-checkpoints)
            download_checkpoints "$@"
            ;;
        upload-models)
            upload_models "$@"
            ;;
        list)
            list_bucket
            ;;
        info)
            show_storage_info
            ;;
        help|--help|-h|"")
            show_menu
            ;;
        *)
            log_error "Unknown command: $command"
            show_menu
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
