#!/bin/bash
# Process dataset from GCS through Docling
#
# Usage:
#   ./process-dataset-gcs.sh <dataset_name> [batch_size]
#
# Example:
#   ./process-dataset-gcs.sh pubtabnet 10000
#   ./process-dataset-gcs.sh tablebank

set -euo pipefail

# Configuration
GCS_BUCKET="${GCS_BUCKET:-gs://image_detection_b/image-preprocessing-detector}"
DOCLING_API="${DOCLING_API:-http://docling-serve:5001}"
INPUT_DIR="/data/input"
OUTPUT_DIR="/data/output"
BATCH_SIZE="${2:-5000}"  # Default 5000 files per batch

# Dataset mapping
declare -A DATASET_PATHS=(
    ["pubtabnet"]="datasets/pubtabnet"
    ["tablebank"]="datasets/tablebank"
    ["fintabnet"]="datasets/fintabnet"
    ["doclaynet"]="datasets/doclaynet"
    ["rvl-cdip"]="datasets/rvl_cdip"
    ["funsd"]="datasets/funsd"
    ["sroie"]="datasets/sroie"
    ["nist-sd2"]="datasets/nist_db2"
    ["nist-sd6"]="datasets/nist_sd6"
    ["signatr6k"]="datasets/signatr6k"
    ["tobacco800"]="datasets/tobacco800"
    ["mathverse"]="datasets/mathverse"
    ["cc-ocr"]="datasets/cc_ocr"
    ["mlt19"]="datasets/mlt19"
)

DATASET="${1:-}"
if [[ -z "$DATASET" ]]; then
    echo "Usage: $0 <dataset_name> [batch_size]"
    echo "Available datasets: ${!DATASET_PATHS[*]}"
    exit 1
fi

GCS_PATH="${DATASET_PATHS[$DATASET]:-}"
if [[ -z "$GCS_PATH" ]]; then
    echo "Unknown dataset: $DATASET"
    echo "Available: ${!DATASET_PATHS[*]}"
    exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')]${NC} $1"; }
log_error() { echo -e "${RED}[$(date '+%H:%M:%S')]${NC} $1"; }

# Check Docling API health
check_docling() {
    if ! curl -sf "${DOCLING_API}/health" > /dev/null; then
        log_error "Docling API not available at ${DOCLING_API}"
        exit 1
    fi
    log_info "Docling API is healthy"
}

# List files in GCS
list_gcs_files() {
    gsutil ls -r "${GCS_BUCKET}/${GCS_PATH}/**" 2>&1 | \
        grep -E '\.(png|jpg|jpeg|pdf|tiff|tif)$' || true
}

# Download batch of files
download_batch() {
    local batch_file="$1"
    local batch_num="$2"

    log_info "Downloading batch $batch_num..."

    # Create batch input directory
    local batch_dir="${INPUT_DIR}/batch_${batch_num}"
    mkdir -p "$batch_dir"

    # Download files in parallel (gsutil cp -I expects newline-delimited paths)
    gsutil -m cp -I "$batch_dir/" < "$batch_file"

    echo "$batch_dir"
}

# Process batch through Docling
process_batch() {
    local batch_dir="$1"
    local batch_num="$2"

    log_info "Processing batch $batch_num..."

    local output_batch="${OUTPUT_DIR}/${DATASET}/batch_${batch_num}"
    mkdir -p "$output_batch"

    # Process each file
    local processed=0
    local failed=0

    for file in "$batch_dir"/*; do
        [[ -f "$file" ]] || continue

        local filename
        filename=$(basename "$file")
        local output_file="${output_batch}/${filename%.*}.json"

        # Call Docling API
        if curl -sf -X POST "${DOCLING_API}/v1/convert/file" \
            -F "file=@${file}" \
            -F "output_format=json" \
            -o "$output_file"; then
            processed=$((processed + 1))
        else
            failed=$((failed + 1))
            log_warn "Failed to process: $filename"
        fi

        # Progress every 100 files
        if (( (processed + failed) % 100 == 0 )); then
            log_info "Progress: $processed processed, $failed failed"
        fi
    done

    log_info "Batch $batch_num complete: $processed processed, $failed failed"
    echo "$output_batch"
}

# Upload results to GCS
upload_results() {
    local output_batch="$1"
    local batch_num="$2"

    log_info "Uploading batch $batch_num results to GCS..."

    gsutil -m cp -r "$output_batch" \
        "${GCS_BUCKET}/extracted_text/${DATASET}/"

    log_info "Uploaded to ${GCS_BUCKET}/extracted_text/${DATASET}/batch_${batch_num}/"
}

# Cleanup local files
cleanup_batch() {
    local batch_dir="$1"
    local output_batch="$2"

    log_info "Cleaning up local files..."
    rm -rf "$batch_dir" "$output_batch"
}

# Main processing loop
main() {
    log_info "=== Processing dataset: $DATASET ==="
    log_info "GCS path: ${GCS_BUCKET}/${GCS_PATH}"
    log_info "Batch size: $BATCH_SIZE"

    # Check dependencies
    check_docling

    # Create directories
    mkdir -p "$INPUT_DIR" "$OUTPUT_DIR/${DATASET}"

    # List all files to a temp file (avoids loading entire listing into memory)
    log_info "Listing files in GCS..."
    local file_list
    file_list=$(mktemp)
    trap 'rm -f "$file_list" "${file_list}".batch_*' EXIT

    list_gcs_files > "$file_list"

    local total_files
    total_files=$(wc -l < "$file_list")

    if [[ $total_files -eq 0 ]]; then
        log_error "No image files found in ${GCS_BUCKET}/${GCS_PATH}"
        exit 1
    fi

    log_info "Found $total_files files to process"

    # Calculate batches
    local num_batches=$(( (total_files + BATCH_SIZE - 1) / BATCH_SIZE ))
    log_info "Will process in $num_batches batches"

    # Split file list into batch files (preserves newline-delimited format)
    split -l "$BATCH_SIZE" -d --additional-suffix=".txt" "$file_list" "${file_list}.batch_"

    # Process each batch file
    local batch_num=1
    for batch_file in "${file_list}".batch_*; do
        [[ -f "$batch_file" ]] || continue

        local batch_count
        batch_count=$(wc -l < "$batch_file")
        log_info "=== Batch $batch_num of $num_batches ($batch_count files) ==="

        # Download
        local batch_dir
        batch_dir=$(download_batch "$batch_file" "$batch_num")

        # Process
        local output_batch
        output_batch=$(process_batch "$batch_dir" "$batch_num")

        # Upload
        upload_results "$output_batch" "$batch_num"

        # Cleanup
        cleanup_batch "$batch_dir" "$output_batch"

        batch_num=$((batch_num + 1))
    done

    log_info "=== Dataset $DATASET processing complete ==="
    log_info "Results at: ${GCS_BUCKET}/extracted_text/${DATASET}/"
}

main "$@"
