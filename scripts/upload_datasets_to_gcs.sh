#!/bin/bash
# Upload datasets to GCS bucket for backup and Colab training access
#
# Usage:
#   ./scripts/upload_datasets_to_gcs.sh               # Upload all datasets
#   ./scripts/upload_datasets_to_gcs.sh --dry-run     # Show what would be uploaded
#   ./scripts/upload_datasets_to_gcs.sh --dataset signatr6k  # Upload specific dataset

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/data"
GCS_BUCKET="gs://image_detection_b"
GCS_PREFIX="image-preprocessing-detector/datasets"

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

log_section() {
    echo -e "${BLUE}[====]${NC} $1"
}

# Check if GCS authentication is configured
check_gcs_auth() {
    if ! command -v gsutil &> /dev/null; then
        log_error "gsutil not found. Please install Google Cloud SDK."
        exit 1
    fi

    if ! gsutil ls "${GCS_BUCKET}/" &> /dev/null; then
        log_error "Cannot access GCS bucket: ${GCS_BUCKET}"
        log_warn "Run: source scripts/auth_gcs.sh"
        exit 1
    fi

    log_info "✓ GCS authentication confirmed"
}

# Upload a dataset to GCS
upload_dataset() {
    local dataset_name="$1"
    local dataset_path="$2"
    local dry_run="${3:-false}"

    if [ ! -d "$dataset_path" ]; then
        log_warn "Dataset not found: $dataset_path (skipping)"
        return 0
    fi

    # Skip empty directories
    if [ -z "$(ls -A "$dataset_path")" ]; then
        log_warn "Dataset is empty: $dataset_name (skipping)"
        return 0
    fi

    # Calculate size
    local size=$(du -sh "$dataset_path" | cut -f1)
    log_section "Uploading: $dataset_name ($size)"

    local gcs_dest="${GCS_BUCKET}/${GCS_PREFIX}/${dataset_name}/"

    if [ "$dry_run" = true ]; then
        log_info "[DRY-RUN] Would upload: $dataset_path -> $gcs_dest"
        log_info "[DRY-RUN] Command: gsutil -m rsync -r -d $dataset_path $gcs_dest"
        return 0
    fi

    # Use gsutil rsync for efficient upload
    # -m: parallel upload
    # -r: recursive
    # -d: delete extra files in destination
    log_info "Syncing to: $gcs_dest"

    if gsutil -m rsync -r -d "$dataset_path" "$gcs_dest"; then
        log_info "✓ Upload complete: $dataset_name"
    else
        log_error "✗ Upload failed: $dataset_name"
        return 1
    fi
}

# Main upload function
upload_all_datasets() {
    local dry_run="${1:-false}"
    local specific_dataset="$2"

    log_section "GCS Dataset Upload"
    log_info "Project root: $PROJECT_ROOT"
    log_info "Data directory: $DATA_DIR"
    log_info "GCS bucket: $GCS_BUCKET"
    log_info "GCS prefix: $GCS_PREFIX"
    echo ""

    # Check authentication
    check_gcs_auth
    echo ""

    # Define datasets to upload
    # Note: We exclude doclaynet (symlink to another project)
    # and empty directories (docbank, rvl-cdip, tobacco800)

    declare -A DATASETS

    # Training datasets (Phase 2)
    DATASETS[receipts_hitl]="${DATA_DIR}/training/receipts_hitl"
    DATASETS[mobile_receipts_voxel51]="${DATA_DIR}/training/mobile_receipts_voxel51"
    DATASETS[invoices_kaggle]="${DATA_DIR}/training/invoices_kaggle"

    # Training datasets (Phase 3+)
    DATASETS[docsynth300k]="${DATA_DIR}/training/layout/docsynth300k"
    DATASETS[pubtables1m]="${DATA_DIR}/training/tables/pubtables1m"
    DATASETS[iam_handwriting]="${DATA_DIR}/training/specialized/handwriting/iam"

    # Benchmark datasets
    DATASETS[funsd]="${DATA_DIR}/benchmarks/external_iqa/funsd"
    DATASETS[signatr6k]="${DATA_DIR}/benchmarks/signatr6k"
    DATASETS[synthetic_iqa]="${DATA_DIR}/benchmarks/synthetic_iqa"
    DATASETS[cocotext]="${DATA_DIR}/benchmarks/cocotext"
    DATASETS[omnidocbench]="${DATA_DIR}/benchmarks/omnidocbench"
    DATASETS[wili_2018]="${DATA_DIR}/benchmarks/wili_2018"
    DATASETS[tablebank]="${DATA_DIR}/benchmarks/tablebank"
    DATASETS[pubtabnet]="${DATA_DIR}/benchmarks/pubtabnet"
    DATASETS[fintabnet]="${DATA_DIR}/benchmarks/fintabnet"

    # Benchmark datasets (Phase 3+)
    DATASETS[ohr_bench]="${DATA_DIR}/benchmarks/ohr-bench"

    # If specific dataset requested, filter
    if [ -n "$specific_dataset" ]; then
        if [ -z "${DATASETS[$specific_dataset]}" ]; then
            log_error "Unknown dataset: $specific_dataset"
            log_info "Available datasets: ${!DATASETS[@]}"
            return 1
        fi

        log_info "Uploading specific dataset: $specific_dataset"
        upload_dataset "$specific_dataset" "${DATASETS[$specific_dataset]}" "$dry_run"
    else
        # Upload all datasets
        log_info "Uploading all datasets..."
        echo ""

        local success_count=0
        local total_count=${#DATASETS[@]}

        for dataset_name in "${!DATASETS[@]}"; do
            if upload_dataset "$dataset_name" "${DATASETS[$dataset_name]}" "$dry_run"; then
                ((success_count++))
            fi
            echo ""
        done

        log_section "Upload Summary"
        log_info "Successfully uploaded: $success_count/$total_count datasets"

        if [ "$success_count" -eq "$total_count" ]; then
            log_info "✓ All uploads complete!"
        else
            log_warn "Some uploads failed. Check errors above."
            return 1
        fi
    fi
}

# List what's currently in GCS
list_gcs_contents() {
    log_section "Current GCS Contents"
    log_info "Bucket: ${GCS_BUCKET}/${GCS_PREFIX}/"
    echo ""

    check_gcs_auth

    if gsutil ls -lh "${GCS_BUCKET}/${GCS_PREFIX}/" | head -100; then
        echo ""
        log_info "Use 'gsutil ls -lhr ${GCS_BUCKET}/${GCS_PREFIX}/' for full recursive listing"
    else
        log_warn "No datasets found in GCS (or bucket is empty)"
    fi
}

# Parse arguments
DRY_RUN=false
SPECIFIC_DATASET=""
ACTION="upload"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --dataset)
            SPECIFIC_DATASET="$2"
            shift 2
            ;;
        --list)
            ACTION="list"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run           Show what would be uploaded without uploading"
            echo "  --dataset NAME      Upload specific dataset only"
            echo "  --list              List current GCS contents"
            echo "  --help              Show this help message"
            echo ""
            echo "Available datasets:"
            echo ""
            echo "Training datasets (Phase 2):"
            echo "  - receipts_hitl           : HITL receipt OCR dataset (192 images, CC0 1.0)"
            echo "  - mobile_receipts_voxel51 : Voxel51 scanned receipts (713 images, CC BY 4.0)"
            echo "  - invoices_kaggle         : Kaggle invoice dataset (1,414 images, ODbL 1.0)"
            echo ""
            echo "Training datasets (Phase 3+):"
            echo "  - docsynth300k       : DocSynth-300K layout detection (~113 GB, Research)"
            echo "  - pubtables1m        : PubTables-1M table structure (~25 GB, MIT)"
            echo "  - iam_handwriting    : IAM Handwriting dataset (~266 MB, MIT)"
            echo ""
            echo "Benchmark datasets:"
            echo "  - funsd           : FUNSD government forms (199 images, MIT)"
            echo "  - signatr6k       : Signature detection dataset (~116 MB)"
            echo "  - synthetic_iqa   : Synthetic IQA dataset (~345 KB)"
            echo "  - cocotext        : COCO-Text annotations (~52 MB)"
            echo "  - omnidocbench    : OmniDocBench benchmark (~1.16 GB)"
            echo "  - wili_2018       : WiLI language identification (~128 MB)"
            echo "  - tablebank       : TableBank table detection (~74 GB)"
            echo "  - pubtabnet       : PubTabNet table structure (~27 GB)"
            echo "  - fintabnet       : FinTabNet financial tables (~14 GB)"
            echo ""
            echo "Benchmark datasets (Phase 3+):"
            echo "  - ohr_bench       : OHR-Bench RAG evaluation (~10 GB, CC-BY-4.0)"
            echo ""
            echo "Examples:"
            echo "  $0                          # Upload all datasets"
            echo "  $0 --dry-run                # Preview upload"
            echo "  $0 --dataset tablebank      # Upload specific dataset"
            echo "  $0 --list                   # Show GCS contents"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Execute action
case $ACTION in
    upload)
        upload_all_datasets "$DRY_RUN" "$SPECIFIC_DATASET"
        ;;
    list)
        list_gcs_contents
        ;;
    *)
        log_error "Unknown action: $ACTION"
        exit 1
        ;;
esac
