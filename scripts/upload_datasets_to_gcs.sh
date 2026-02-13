#!/bin/bash
# Dataset Upload Script for GCS Replication
# Priority: DIQA-5000 -> Language/Script -> Remaining Tier 1
# Excludes: doc3d (209GB - too large)
#
# Usage: ./scripts/upload_datasets_to_gcs.sh [--dry-run] [--tier N]
#   --dry-run: Show what would be uploaded without actually uploading
#   --tier N:  Upload only tier N (1=diqa, 2=language, 3=remaining)

set -euo pipefail

# Configuration
GCS_BUCKET="gs://image_detection_b/image-preprocessing-detector/datasets"
LOCAL_BASE="/mnt/e/image_detection"
LOG_FILE="/home/byron/dev/image_detection/logs/gcs_upload_$(date +%Y%m%d_%H%M%S).log"

# Parse arguments
DRY_RUN=false
TIER_FILTER=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --tier) TIER_FILTER="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Constant for separator line (avoid duplication)
SEPARATOR_LINE="=========================================="

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" | tee -a "$LOG_FILE"
    return 0
}

# Upload function with progress
upload_dataset() {
    local src="$1"
    local dest_name="$2"
    local description="$3"

    if [[ ! -d "$src" && ! -f "$src" ]]; then
        log "SKIP: $src does not exist"
        return 1
    fi

    local dest="${GCS_BUCKET}/${dest_name}/"

    log "START: $description"
    log "  Source: $src"
    log "  Destination: $dest"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "  DRY-RUN: Would upload $(du -sh "$src" 2>/dev/null | cut -f1)"
        return 0
    fi

    # Use gsutil with parallel composite uploads for large files
    if gsutil -m -o GSUtil:parallel_composite_upload_threshold=150M cp -r "$src" "$dest" 2>&1 | tee -a "$LOG_FILE"; then
        log "SUCCESS: $description uploaded"
        return 0
    else
        log "ERROR: Failed to upload $description"
        return 1
    fi
    return 0
}

# ============================================================================
# TIER 1: DIQA-5000 (Benchmark - Currently Working On)
# ============================================================================
upload_tier1() {
    log "$SEPARATOR_LINE"
    log "TIER 1: DIQA-5000 Benchmark Dataset"
    log "$SEPARATOR_LINE"

    upload_dataset \
        "${LOCAL_BASE}/02_benchmark_only/diqa-5000" \
        "diqa-5000" \
        "DIQA-5000 IQA Calibration Benchmark (5.3GB)"
    return 0
}

# ============================================================================
# TIER 2: Language & Script Detection Datasets
# ============================================================================
upload_tier2() {
    log "$SEPARATOR_LINE"
    log "TIER 2: Language & Script Detection"
    log "$SEPARATOR_LINE"

    # Priority order by size and importance

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/mlt19" \
        "mlt19" \
        "MLT-19 Multilingual Text (14GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/arabic_docs_ocr" \
        "arabic_docs_ocr" \
        "Arabic Documents OCR (9.3GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/mdiw13" \
        "mdiw13" \
        "MDIW-13 Script Identification (4.4GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/yarmouk_ocr" \
        "yarmouk_ocr" \
        "Yarmouk OCR Dataset (2.8GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/yarmouk_ocr_images" \
        "yarmouk_ocr_images" \
        "Yarmouk OCR Images (14GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/multilingual_scripts" \
        "multilingual_scripts" \
        "Multilingual Scripts Collection (2.7GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/cc_ocr_extracted" \
        "cc_ocr" \
        "CC-OCR CJK Mixed (1.5GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/nepali_handwritten" \
        "nepali_handwritten" \
        "Nepali Handwritten Dataset (1.5GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/hindi_ocr_synthetic" \
        "hindi_ocr_synthetic" \
        "Hindi OCR Synthetic (920MB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/pucit_ohul_urdu" \
        "pucit_ohul_urdu" \
        "PUCIT-OHUL Urdu Dataset (583MB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/siw13" \
        "siw13" \
        "SIW-13 Script in Wild (104MB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/cvsi" \
        "cvsi" \
        "CVSI-2015 Video Script ID (43MB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/mle2e" \
        "mle2e" \
        "MLe2e Multi-Language E2E (19MB)"

    # MIDV-500 (ID documents - large)
    upload_dataset \
        "${LOCAL_BASE}/01_base_data/language/midv500_data" \
        "midv500_data" \
        "MIDV-500 ID Documents - Language (48GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/documents/midv500" \
        "midv500" \
        "MIDV-500 ID Documents (12GB)"
    return 0
}

# ============================================================================
# TIER 3: Remaining Core Training Datasets
# ============================================================================
upload_tier3() {
    log "$SEPARATOR_LINE"
    log "TIER 3: Remaining Core Training Data"
    log "$SEPARATOR_LINE"

    # Documents
    upload_dataset \
        "${LOCAL_BASE}/01_base_data/documents/rvl_cdip" \
        "rvl_cdip" \
        "RVL-CDIP Document Classification (2.8GB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/documents/bhutan_financial" \
        "bhutan_financial" \
        "Bhutan Financial Statements (58MB)"

    # Handwriting
    upload_dataset \
        "${LOCAL_BASE}/01_base_data/handwriting/nist_sd19_pages" \
        "nist_sd19" \
        "NIST SD-19 Handwriting (351MB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/handwriting/hasyv2_original" \
        "hasyv2" \
        "HASYv2 Math Symbols (140MB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/handwriting/maths_handwriting" \
        "maths_handwriting" \
        "Maths Handwriting (177MB)"

    # Formulas
    upload_dataset \
        "${LOCAL_BASE}/01_base_data/formulas/im2latex" \
        "im2latex" \
        "im2latex-100k Formulas (65MB)"

    # Degraded
    upload_dataset \
        "${LOCAL_BASE}/01_base_data/degraded/tobacco800" \
        "tobacco800" \
        "Tobacco-800 Degraded Docs (88MB)"

    upload_dataset \
        "${LOCAL_BASE}/01_base_data/degraded/historical_degraded" \
        "historical_degraded" \
        "Historical Degraded Collection (4GB)"

    # Camera Captured (excluding doc3d)
    upload_dataset \
        "${LOCAL_BASE}/01_base_data/camera_captured/realdae" \
        "realdae" \
        "RealDAE Camera Captured (2.1GB)"

    # IQA Reference
    upload_dataset \
        "${LOCAL_BASE}/01_base_data/ocr_quality" \
        "ocr_quality" \
        "OCR-Quality IQA Reference (1.2GB)"

    # Benchmarks
    upload_dataset \
        "${LOCAL_BASE}/02_benchmark_only/dibco" \
        "dibco" \
        "DIBCO Binarization Benchmark (423MB)"

    upload_dataset \
        "${LOCAL_BASE}/02_benchmark_only/financebench" \
        "financebench" \
        "FinanceBench RAG QA (27GB)"

    upload_dataset \
        "${LOCAL_BASE}/02_benchmark_only/smartdoc-qa" \
        "smartdoc-qa" \
        "SmartDoc-QA Mobile Capture (39GB)"
    return 0
}

# ============================================================================
# Main Execution
# ============================================================================
main() {
    log "$SEPARATOR_LINE"
    log "GCS Dataset Upload Script Started"
    log "Bucket: $GCS_BUCKET"
    log "Dry Run: $DRY_RUN"
    log "Tier Filter: ${TIER_FILTER:-all}"
    log "$SEPARATOR_LINE"

    # Verify GCS access
    if ! gsutil ls "$GCS_BUCKET" > /dev/null 2>&1; then
        log "ERROR: Cannot access GCS bucket. Check authentication."
        exit 1
    fi

    case "${TIER_FILTER:-all}" in
        1) upload_tier1 ;;
        2) upload_tier2 ;;
        3) upload_tier3 ;;
        all|"")
            upload_tier1
            upload_tier2
            upload_tier3
            ;;
        *)
            log "ERROR: Invalid tier. Use 1, 2, 3, or leave empty for all."
            exit 1
            ;;
    esac

    log "$SEPARATOR_LINE"
    log "Upload Complete!"
    log "Log file: $LOG_FILE"
    log "$SEPARATOR_LINE"
    return 0
}

main "$@"
