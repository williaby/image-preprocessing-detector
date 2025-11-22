#!/bin/bash
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT

#
# Complete Dataset Workflow: Generation → DVC → GCS → Training Setup
#
# This script automates the entire workflow for creating the 100K IQA dataset.
#
# Duration: 8-12 hours (generation) + 30-90 minutes (upload)
# Prerequisites: GCS credentials configured, poetry install --with ml
#

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "100K IQA DATASET - COMPLETE WORKFLOW"
echo "================================================================================"
echo ""
echo "This script will:"
echo "  1. Generate 100K IQA training dataset (~8-12 hours)"
echo "  2. Validate distribution across 13 dimensions"
echo "  3. Initialize DVC and configure GCS remote"
echo "  4. Upload dataset to GCS (~30-90 minutes)"
echo "  5. Commit DVC metadata to Git"
echo "  6. Update training configuration"
echo ""
echo -e "${YELLOW}WARNING: This will take 9-13 hours total and use ~45GB disk space.${NC}"
echo ""

ACCEPT_PATTERN='^(yes|y|Y|YES)$'
read -p "Proceed with full workflow? (yes/no): " response
if [[ ! "$response" =~ $ACCEPT_PATTERN ]]; then
    echo "Aborted."
    exit 0
fi

# Step 1: Generate Dataset
echo ""
echo -e "${GREEN}[1/6] Generating 100K IQA Dataset...${NC}"
echo "Duration: ~8-12 hours"
echo "Output: data/training/iqa_phase2_100k/"
echo ""

if ! poetry run python scripts/generate_100k_iqa_dataset.py; then
    echo -e "${RED}Error: Dataset generation failed${NC}" >&2
    exit 1
fi

# Step 2: Validate Distribution
echo ""
echo -e "${GREEN}[2/6] Validating Dataset Distribution...${NC}"
echo ""

# Check metadata exists
if [ ! -f "data/training/iqa_phase2_100k/metadata.json" ]; then
    echo -e "${RED}Error: metadata.json not found${NC}"
    exit 1
fi

# Print distribution summary
echo "Distribution Summary:"
cat data/training/iqa_phase2_100k/metadata.json | jq '.actual_distributions' || echo "jq not installed, skipping validation"

# Step 3: Initialize DVC
echo ""
echo -e "${GREEN}[3/6] Initializing DVC...${NC}"
echo ""

# Check if DVC already initialized
if [ ! -d ".dvc" ]; then
    echo "Initializing DVC..."
    dvc init

    # Configure GCS remote
    dvc remote add -d gcs gs://image_detection_b/image-preprocessing-detector/datasets
    dvc remote modify gcs credentialpath .gcp/service-account.json

    # Commit DVC config
    git add .dvc/config .dvc/.gitignore
    git commit -m "chore: initialize DVC with GCS remote" || echo "DVC config already committed"
else
    echo "DVC already initialized."
fi

# Step 4: Add Dataset to DVC
echo ""
echo -e "${GREEN}[4/6] Adding Dataset to DVC...${NC}"
echo ""

if ! dvc add data/training/iqa_phase2_100k; then
    echo -e "${RED}Error: DVC add failed${NC}" >&2
    exit 1
fi

# Step 5: Upload to GCS
echo ""
echo -e "${GREEN}[5/6] Uploading to GCS...${NC}"
echo "Duration: ~30-90 minutes"
echo "Destination: gs://image_detection_b/image-preprocessing-detector/datasets/iqa_phase2_100k/"
echo ""

if ! dvc push data/training/iqa_phase2_100k; then
    echo -e "${RED}Error: DVC push failed${NC}" >&2
    exit 1
fi

# Verify upload
echo ""
echo "Verifying upload..."
gsutil du -sh gs://image_detection_b/image-preprocessing-detector/datasets/iqa_phase2_100k/ || echo "Verification failed"

# Step 6: Commit DVC Metadata
echo ""
echo -e "${GREEN}[6/6] Committing DVC Metadata...${NC}"
echo ""

git add data/training/iqa_phase2_100k.dvc
git add data/training/.gitignore
git commit -m "feat(dataset): add 100K IQA training dataset with 13-dimensional distribution

- 100,000 samples with balanced defect types and severity
- Multi-dimensional distribution: color mode, orientation, DPI, JPEG quality
- Source: DIQA-5000, TableBank, PubTabNet, DocLayNet, IAM, FUNSD
- Tracked with DVC, uploaded to GCS
- Size: ~45 GB
"

# Final Summary
echo ""
echo "================================================================================"
echo -e "${GREEN}WORKFLOW COMPLETE!${NC}"
echo "================================================================================"
echo ""
echo "Dataset Location (local): data/training/iqa_phase2_100k/"
echo "Dataset Location (GCS):   gs://image_detection_b/.../iqa_phase2_100k/"
echo "DVC Metadata:             data/training/iqa_phase2_100k.dvc"
echo ""
echo "Next Steps:"
echo "  1. Push Git commit: git push origin <branch>"
echo "  2. Update training config: configs/modal_phase2_iqa.yaml"
echo "  3. Run training: poetry run modal run modal/train_phase2_iqa.py"
echo ""
echo "To download dataset in Modal/Colab:"
echo "  dvc pull data/training/iqa_phase2_100k"
echo ""
echo -e "${GREEN}Ready for model training!${NC}"
echo ""
