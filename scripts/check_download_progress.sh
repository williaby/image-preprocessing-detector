#!/bin/bash
# Monitor dataset download progress
#
# Usage:
#   ./scripts/check_download_progress.sh

set -euo pipefail
IFS=$'\n\t'

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}=== Dataset Download Progress ===${NC}"
echo ""

# Check if download process is running
if pgrep -f "download_phase3_datasets.py" > /dev/null; then
    echo -e "${GREEN}✓ Download process is running${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠ Download process not found (may have completed or failed)${NC}"
    echo ""
fi

# Check latest log file
LATEST_LOG=$(ls -t logs/dataset_download_*.log 2>/dev/null | head -1)
if [ -n "$LATEST_LOG" ]; then
    echo -e "${BLUE}Latest log file:${NC} $LATEST_LOG"
    echo ""
    echo -e "${BLUE}Last 20 lines:${NC}"
    tail -20 "$LATEST_LOG"
    echo ""
else
    echo -e "${YELLOW}No log files found${NC}"
    echo ""
fi

# Check download directory sizes
echo -e "${BLUE}=== Download Directory Sizes ===${NC}"
echo ""

DATASETS=(
    "data/benchmarks/ohr-bench|OHR-Bench|10 GB"
    "data/training/layout/docsynth300k|DocSynth-300K|113 GB"
    "data/training/tables/pubtables1m|PubTables-1M|25 GB"
    "data/training/specialized/handwriting/iam|IAM Handwriting|266 MB"
)

for dataset in "${DATASETS[@]}"; do
    IFS='|' read -r path name expected_size <<< "$dataset"
    full_path="${PROJECT_ROOT}/${path}"

    if [ -d "$full_path" ]; then
        current_size=$(du -sh "$full_path" 2>/dev/null | cut -f1 || echo "0")
        file_count=$(find "$full_path" -type f 2>/dev/null | wc -l)
        echo -e "${GREEN}✓${NC} ${name}: ${current_size} / ${expected_size} (${file_count} files)"
    else
        echo -e "${YELLOW}⚠${NC} ${name}: Not started (expected ${expected_size})"
    fi
done

echo ""
echo -e "${BLUE}=== Commands ===${NC}"
echo ""
echo "Monitor live progress:"
echo "  tail -f \$(ls -t logs/dataset_download_*.log | head -1)"
echo ""
echo "Check process:"
echo "  ps aux | grep download_phase3_datasets"
echo ""
echo "Kill process (if needed):"
echo "  pkill -f download_phase3_datasets.py"
