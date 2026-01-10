#!/bin/bash
# Create tarballs for Stage 2 training dataset

set -e

DATASET_DIR="/mnt/e/image_detection/03_training_datasets/stage2_diqa_ensemble"
cd "$DATASET_DIR"

mkdir -p tarballs

echo "Creating train tarball..."
tar -czf tarballs/stage2_train.tar.gz \
    splits/train.jsonl \
    checksums/train_checksums.sha256 \
    images/diqa-5000/train \
    images/smartdoc-qa/train \
    images/funsd/train \
    images/sroie/train \
    images/tobacco-800/train

echo "Creating val tarball..."
tar -czf tarballs/stage2_val.tar.gz \
    splits/val.jsonl \
    checksums/val_checksums.sha256 \
    images/diqa-5000/val \
    images/smartdoc-qa/val \
    images/funsd/val \
    images/sroie/val \
    images/tobacco-800/val

echo "Creating test tarball..."
tar -czf tarballs/stage2_test.tar.gz \
    splits/test.jsonl \
    checksums/test_checksums.sha256 \
    images/diqa-5000/test \
    images/smartdoc-qa/test \
    images/funsd/test \
    images/sroie/test \
    images/tobacco-800/test

echo "Creating metadata tarball (README + MANIFEST)..."
tar -czf tarballs/stage2_metadata.tar.gz \
    README.md \
    MANIFEST.json

echo "Done! Tarballs created:"
ls -lh tarballs/
