#!/bin/bash
# SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: Apache-2.0

set -e  # Exit on error

echo "Adding benchmark datasets to DVC tracking..."
echo "This will take time for large datasets (27GB + 14GB + 5.3GB + smaller)"
echo ""

# List of datasets to add (in order of size)
datasets=(
    "pubtabnet:14GB"
    "fintabnet:5.3GB"
    "omnidocbench:1.2GB"
    "signatr6k:153MB"
    "wili_2018:129MB"
)

# Function to add dataset to DVC
add_to_dvc() {
    local dataset=$1
    local size=$2

    # Skip if .dvc file already exists
    if [ -f "data/benchmarks/${dataset}.dvc" ]; then
        echo "✓ ${dataset} already tracked (${size})"
        return 0
    fi

    # Check if dataset directory exists
    if [ ! -d "data/benchmarks/${dataset}" ]; then
        echo "⚠ Skipping ${dataset} - directory not found"
        return 0
    fi

    echo "→ Adding ${dataset} (${size})..."
    uv run dvc add "data/benchmarks/${dataset}"
    echo "✓ ${dataset} added successfully"
    echo ""
}

# Add each dataset
for item in "${datasets[@]}"; do
    dataset="${item%%:*}"
    size="${item##*:}"
    add_to_dvc "$dataset" "$size"
done

# Show summary
echo ""
echo "Summary of tracked datasets:"
ls -lh data/benchmarks/*.dvc

echo ""
echo "Next steps:"
echo "1. Commit .dvc files:  git add data/benchmarks/*.dvc && git commit -m 'feat: add Phase 2-3 benchmark datasets to DVC tracking'"
echo "2. Push to DVC cache:  uv run dvc push"
