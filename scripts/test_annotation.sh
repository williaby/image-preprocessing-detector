#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
#
# Test script for annotation module with proper coverage thresholds
#
# Usage:
#   ./scripts/test_annotation.sh              # Run annotation tests with coverage
#   ./scripts/test_annotation.sh --no-cov     # Run without coverage
#   ./scripts/test_annotation.sh -v           # Verbose output

set -euo pipefail

# Default options
COVERAGE=true
VERBOSE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-cov)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--no-cov] [-v]"
            exit 1
            ;;
    esac
done

# Base pytest command
PYTEST_CMD="uv run pytest tests/unit/annotation/ tests/e2e/annotation/"

# Add verbose flag if requested
if [[ -n "$VERBOSE" ]]; then
    PYTEST_CMD="$PYTEST_CMD $VERBOSE"
fi

# Add coverage options if enabled
if [[ "$COVERAGE" == "true" ]]; then
    # Override default coverage settings from pyproject.toml
    # By specifying a new --cov path, we override the default --cov from config
    # But we need to override --cov-fail-under as well
    PYTEST_CMD="$PYTEST_CMD \
        --override-ini=addopts= \
        --cov=src/image_preprocessing_detector/annotation \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-report=xml \
        --cov-fail-under=80"

    echo "Running annotation tests with coverage (80% threshold)..."
else
    PYTEST_CMD="$PYTEST_CMD --no-cov"
    echo "Running annotation tests without coverage..."
fi

# Run tests
$PYTEST_CMD

# Print summary
if [[ "$COVERAGE" == "true" ]]; then
    echo ""
    echo "✅ Annotation tests passed with >80% coverage"
    echo "📊 Coverage report: htmlcov/index.html"
fi
