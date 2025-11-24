#!/usr/bin/env bash
# Run mutation testing on the codebase
#
# This script runs mutmut against the source code to verify test quality.
# Mutation testing introduces small changes (mutations) to the code and
# verifies that tests catch these bugs.
#
# Usage:
#   ./scripts/run_mutation_tests.sh [options]
#
# Options:
#   --fast           Run on a subset of modules for quick feedback
#   --module=NAME    Run on a specific module (e.g., detection, ingestion)
#   --report         Generate HTML report
#   --help           Show this help message
#
# Examples:
#   ./scripts/run_mutation_tests.sh                    # Full run
#   ./scripts/run_mutation_tests.sh --fast             # Quick check
#   ./scripts/run_mutation_tests.sh --module=schema    # Single module
#   ./scripts/run_mutation_tests.sh --report           # With HTML report

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default settings
FAST_MODE=false
MODULE=""
REPORT=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fast)
            FAST_MODE=true
            shift
            ;;
        --module=*)
            MODULE="${1#*=}"
            shift
            ;;
        --report)
            REPORT=true
            shift
            ;;
        --help)
            head -30 "$0" | tail -25
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== Mutation Testing ===${NC}"
echo "Configuration:"
echo "  Fast mode: $FAST_MODE"
echo "  Module: ${MODULE:-all}"
echo "  Report: $REPORT"
echo ""

# Set paths to mutate based on options
PATHS_TO_MUTATE="src/image_preprocessing_detector"

if [[ -n "$MODULE" ]]; then
    PATHS_TO_MUTATE="src/image_preprocessing_detector/${MODULE}"
    if [[ ! -d "$PATHS_TO_MUTATE" ]]; then
        # Check if it's a file
        if [[ -f "src/image_preprocessing_detector/${MODULE}.py" ]]; then
            PATHS_TO_MUTATE="src/image_preprocessing_detector/${MODULE}.py"
        else
            echo -e "${RED}Module not found: $MODULE${NC}"
            echo "Available modules:"
            ls -1 src/image_preprocessing_detector/
            exit 1
        fi
    fi
fi

if [[ "$FAST_MODE" == "true" ]]; then
    # Fast mode: only run on critical, well-tested modules
    echo -e "${YELLOW}Running in fast mode on critical modules...${NC}"
    PATHS_TO_MUTATE="src/image_preprocessing_detector/schema.py"
fi

echo "Paths to mutate: $PATHS_TO_MUTATE"
echo ""

# Clear previous results if running fresh
if [[ ! -f ".mutmut-cache" ]] || [[ "$1" == "--fresh" ]]; then
    echo -e "${YELLOW}Starting fresh mutation run...${NC}"
else
    echo -e "${YELLOW}Continuing from previous run (use --fresh to restart)...${NC}"
fi

# Run mutation testing
echo -e "${GREEN}Starting mutation testing...${NC}"
echo "This may take a while depending on the codebase size."
echo ""

# Run mutmut with specific paths
poetry run mutmut run --paths-to-mutate="$PATHS_TO_MUTATE" || true

# Show results
echo ""
echo -e "${GREEN}=== Mutation Testing Results ===${NC}"
poetry run mutmut results

# Show summary
echo ""
echo -e "${GREEN}=== Summary ===${NC}"
poetry run mutmut show-stats 2>/dev/null || echo "Run 'poetry run mutmut show-stats' for detailed statistics"

# Generate HTML report if requested
if [[ "$REPORT" == "true" ]]; then
    echo ""
    echo -e "${GREEN}Generating HTML report...${NC}"
    poetry run mutmut html
    echo "HTML report generated at: html/index.html"
fi

# Show next steps
echo ""
echo -e "${GREEN}=== Next Steps ===${NC}"
echo "To investigate surviving mutants:"
echo "  poetry run mutmut show <id>    # Show specific mutant"
echo "  poetry run mutmut html          # Generate HTML report"
echo ""
echo "Surviving mutants indicate tests that don't catch bugs."
echo "Consider adding tests to kill these mutants."
