#!/bin/bash
# Upload Stage 2 training dataset tarballs to GCS

set -e

BUCKET="gs://image_detection_b"
LOCAL_DIR="/mnt/e/image_detection/03_training_datasets/stage2_diqa_ensemble/tarballs"
GCS_DIR="${BUCKET}/training/stage2_diqa_ensemble"

echo "Uploading Stage 2 training dataset tarballs to GCS..."
echo "Source: $LOCAL_DIR"
echo "Destination: $GCS_DIR"
echo ""

# Create GCS directory structure
gsutil -m mkdir -p "${GCS_DIR}" 2>/dev/null || true

# Upload tarballs with progress
echo "1/4 Uploading metadata (3.7K)..."
gsutil -o GSUtil:parallel_composite_upload_threshold=150M \
    cp "${LOCAL_DIR}/stage2_metadata.tar.gz" "${GCS_DIR}/"

echo "2/4 Uploading validation set (1.7G)..."
gsutil -o GSUtil:parallel_composite_upload_threshold=150M \
    cp "${LOCAL_DIR}/stage2_val.tar.gz" "${GCS_DIR}/"

echo "3/4 Uploading test set (3.5G)..."
gsutil -o GSUtil:parallel_composite_upload_threshold=150M \
    cp "${LOCAL_DIR}/stage2_test.tar.gz" "${GCS_DIR}/"

echo "4/4 Uploading training set (13G - this will take time)..."
gsutil -o GSUtil:parallel_composite_upload_threshold=150M \
    cp "${LOCAL_DIR}/stage2_train.tar.gz" "${GCS_DIR}/"

echo ""
echo "Upload complete! Verifying..."
gsutil ls -lh "${GCS_DIR}/"

echo ""
echo "Computing checksums..."
gsutil hash "${GCS_DIR}/stage2_train.tar.gz"
gsutil hash "${GCS_DIR}/stage2_val.tar.gz"
gsutil hash "${GCS_DIR}/stage2_test.tar.gz"

echo ""
echo "Stage 2 dataset ready for Modal training!"
echo "GCS location: ${GCS_DIR}"
