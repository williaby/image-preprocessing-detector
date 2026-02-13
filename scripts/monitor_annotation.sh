#!/bin/bash
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
#
# Monitor annotation progress for large datasets

# Constant for separator line (avoid duplication)
SEPARATOR_LINE="======================================================================="

echo "$SEPARATOR_LINE"
echo "ANNOTATION PROGRESS MONITOR"
echo "$SEPARATOR_LINE"
echo

# Check running processes
echo "Running Processes:"
echo "-----------------"
ps aux | grep -E "annotate_base_metadata" | grep -v grep | grep -v monitor || echo "  No annotation processes running"
echo

# Check progress file
if [[ -f ".annotate_progress.json" ]]; then
    echo "Progress Status:"
    echo "---------------"
    uv run python scripts/annotate_base_metadata_incremental.py --status 2>&1 | tail -20
    echo
fi

# Check output directory
echo "Output Files:"
echo "------------"
ls -lh /mnt/e/image_detection/metadata_registry/json/*.json 2>/dev/null | wc -l | xargs echo "  Total JSON files:"
echo

# Check for recent output
echo "Recently Updated (last 60 min):"
echo "------------------------------"
find /mnt/e/image_detection/metadata_registry/json -name "*.json" -mmin -60 2>/dev/null | xargs -I {} basename {} | sed 's/_metadata.json//' || echo "  None"
echo

# Show log tail if available
if [[ -f "/tmp/annotation_progress.log" ]]; then
    echo "Recent Log Activity:"
    echo "-------------------"
    tail -10 /tmp/annotation_progress.log | grep -E "Processing:|completed|failed|ERROR" || tail -5 /tmp/annotation_progress.log
fi

echo
echo "$SEPARATOR_LINE"
echo "To watch live progress: tail -f /tmp/annotation_progress.log"
echo "To check specific task: cat /tmp/claude/-home-byron-dev-image-detection/tasks/<task_id>.output"
echo "$SEPARATOR_LINE"
