#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 Byron Williams
# SPDX-License-Identifier: MIT

set -euo pipefail

# Extract Lines of Code (LOC) counts for each workstream and output as JSON
# Used by CI to keep documentation LOC counts accurate
#
# Usage:
#   ./extract_workstream_loc.sh                    # Standard LOC extraction
#   ./extract_workstream_loc.sh --validate-tables <workstream>  # Validate Level 2 traceability tables
#   ./extract_workstream_loc.sh --validate-swimlane <workstream>  # Validate Level 3 swimlane annotations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_FILE="${PROJECT_ROOT}/docs/architecture/workstream_loc_counts.json"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
MODE="extract"  # extract, validate-tables, validate-swimlane
WORKSTREAM=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --validate-tables)
            MODE="validate-tables"
            WORKSTREAM="$2"
            shift 2
            ;;
        --validate-swimlane)
            MODE="validate-swimlane"
            WORKSTREAM="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  (no args)                           Extract LOC counts to JSON"
            echo "  --validate-tables <workstream>      Validate Level 2 traceability table"
            echo "  --validate-swimlane <workstream>    Validate Level 3 swimlane annotations"
            echo "  --help, -h                          Show this help"
            echo ""
            echo "Available workstreams:"
            echo "  monitoring_drift, production_runtime, model_training,"
            echo "  data_preparation, pseudo_labeling, model_arena,"
            echo "  labeling_benchmarking, synthetic_generation"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [[ "$MODE" = "extract" ]]; then
    echo "📊 Extracting Workstream LOC Counts..."
    echo "Project Root: ${PROJECT_ROOT}"
    echo ""
elif [[ "$MODE" = "validate-tables" ]]; then
    echo "🔍 Validating Level 2 Traceability Table: ${WORKSTREAM}"
    echo "Project Root: ${PROJECT_ROOT}"
    echo ""
elif [[ "$MODE" = "validate-swimlane" ]]; then
    echo "🔍 Validating Level 3 Swimlane Diagram: ${WORKSTREAM}"
    echo "Project Root: ${PROJECT_ROOT}"
    echo ""
fi

# Function to count LOC in a directory (excluding comments, blanks, tests)
count_loc() {
    local dir="$1"
    local total=0

    if [[ -d "$dir" ]]; then
        # Count Python files only, excluding __pycache__, tests, and .pyc files
        total=$(find "$dir" -name "*.py" \
            -not -path "*/tests/*" \
            -not -path "*/__pycache__/*" \
            -not -path "*/.pytest_cache/*" \
            -not -name "test_*.py" \
            -not -name "*_test.py" \
            -type f \
            -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
    fi

    echo "$total"
    return 0
}

# Function to count LOC in a single file
count_file_loc() {
    local file_path="$1"
    wc -l "$file_path" 2>/dev/null | awk '{print $1}' || echo "0"
}

# Define workstream source directories
declare -A WORKSTREAMS=(
    ["production_runtime"]="src/image_preprocessing_detector/ingestion src/image_preprocessing_detector/classification src/image_preprocessing_detector/detection src/image_preprocessing_detector/correction src/image_preprocessing_detector/metrics src/image_preprocessing_detector/routing src/image_preprocessing_detector/output src/image_preprocessing_detector/utils/device_orchestrator.py src/image_preprocessing_detector/utils/device_probe.py src/image_preprocessing_detector/workers"
    ["model_training"]="modal/train_phase2_iqa.py modal/train_student_distillation.py modal/export_onnx.py modal/export_phase7_onnx.py src/image_preprocessing_detector/training src/image_preprocessing_detector/models"
    ["data_preparation"]="scripts/annotate_base_metadata.py scripts/build_training_labels.py scripts/download_all_datasets.py scripts/download_iqa_datasets.py scripts/download_phase3_datasets.py scripts/download_table_datasets.py scripts/download_omnidocbench.py scripts/validate_datasets.py"
    ["pseudo_labeling"]="src/image_preprocessing_detector/labeling/ensemble modal/generate_pseudo_labels.py modal/arena_benchmark.py scripts/run_model_benchmark.py"
    ["labeling_benchmarking"]="modal/labeling_models src/image_preprocessing_detector/labeling/models"
    ["model_arena"]="src/image_preprocessing_detector/labeling/arena"
    ["monitoring_drift"]="src/image_preprocessing_detector/drift monitoring"
    ["synthetic_generation"]="src/image_preprocessing_detector/augmentation benchmarks/adapters/synthetic_iqa_adapter.py"
)

# Initialize JSON output
echo "{" > "$OUTPUT_FILE"
echo '  "generated_at": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",' >> "$OUTPUT_FILE"
echo '  "git_sha": "'$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")'",' >> "$OUTPUT_FILE"
echo '  "workstreams": {' >> "$OUTPUT_FILE"

first=true

# Extract LOC for each workstream
for workstream in "${!WORKSTREAMS[@]}"; do
    echo -e "${YELLOW}Processing: ${workstream}${NC}"

    total_loc=0
    dirs="${WORKSTREAMS[$workstream]}"

    # Sum LOC across all directories/files for this workstream
    for path in $dirs; do
        full_path="${PROJECT_ROOT}/${path}"
        if [[ -e "$full_path" ]]; then
            if [[ -d "$full_path" ]]; then
                loc=$(count_loc "$full_path")
            else
                # Single file
                loc=$(count_file_loc "$full_path")
            fi
            total_loc=$((total_loc + loc))
            echo "  - ${path}: ${loc} lines"
        else
            echo -e "  ${RED}Warning: Path not found: ${path}${NC}"
        fi
    done

    echo -e "${GREEN}  Total: ${total_loc} lines${NC}"
    echo ""

    # Add to JSON (handle comma for all but last entry)
    if [[ "$first" = true ]]; then
        first=false
    else
        echo "," >> "$OUTPUT_FILE"
    fi

    echo -n "    \"${workstream}\": {" >> "$OUTPUT_FILE"
    echo -n "\"loc\": ${total_loc}, \"status\": \"active\"}" >> "$OUTPUT_FILE"
done

# Close JSON
echo "" >> "$OUTPUT_FILE"
echo "  }" >> "$OUTPUT_FILE"
echo "}" >> "$OUTPUT_FILE"

echo -e "${GREEN}✅ LOC extraction complete!${NC}"
echo "Output written to: ${OUTPUT_FILE}"
echo ""

# Display summary
echo "📊 Summary:"
cat "$OUTPUT_FILE" | python3 -m json.tool 2>/dev/null || cat "$OUTPUT_FILE"
echo ""

# Extract key metrics for Level 1 update
if [[ "$MODE" = "extract" ]]; then
    echo "📝 Suggested Level 1 updates:"
    echo ""
    python3 << 'EOF'
import json
import sys

try:
    with open("docs/architecture/workstream_loc_counts.json") as f:
        data = json.load(f)

    workstreams = data.get("workstreams", {})

    # Map internal names to display names
    name_map = {
        "production_runtime": "Production Runtime",
        "model_training": "Production Model Training",
        "data_preparation": "Data Preparation",
        "pseudo_labeling": "Pseudo-Labeling",
        "labeling_benchmarking": "Labeling & Benchmarking Models",
        "model_arena": "Model Arena & Benchmarking",
        "monitoring_drift": "Monitoring & Drift Detection",
        "synthetic_generation": "Synthetic Data Generation"
    }

    for key, name in name_map.items():
        if key in workstreams:
            loc = workstreams[key]["loc"]
            # Round to nearest hundred for readability
            rounded = round(loc / 100) * 100
            if rounded >= 1000:
                formatted = f"~{rounded:,}"
            else:
                formatted = f"{rounded}+"
            print(f"| **{name}** | {formatted} |")
        else:
            print(f"| **{name}** | NOT FOUND |", file=sys.stderr)

except Exception as e:
    print(f"Error processing JSON: {e}", file=sys.stderr)
    sys.exit(1)
EOF
fi

# ============================================================================
# VALIDATION MODE: --validate-tables
# ============================================================================
if [[ "$MODE" = "validate-tables" ]]; then
    # Map workstream names to Level 2 index.md paths
    declare -A LEVEL2_DOCS=(
        ["monitoring_drift"]="docs/architecture/diagrams/level-2/monitoring-drift/index.md"
        ["production_runtime"]="docs/architecture/diagrams/level-2/production-runtime/index.md"
        ["model_training"]="docs/architecture/diagrams/level-2/model-training/index.md"
        ["data_preparation"]="docs/architecture/diagrams/level-2/data-preparation/index.md"
        ["pseudo_labeling"]="docs/architecture/diagrams/level-2/pseudo-labeling/index.md"
        ["model_arena"]="docs/architecture/diagrams/level-2/model-arena/index.md"
        ["synthetic_generation"]="docs/architecture/diagrams/level-2/synthetic-generation/index.md"
    )

    if [[ -z "${LEVEL2_DOCS[$WORKSTREAM]:-}" ]]; then
        echo -e "${RED}❌ Unknown workstream: ${WORKSTREAM}${NC}"
        exit 1
    fi

    level2_doc="${PROJECT_ROOT}/${LEVEL2_DOCS[$WORKSTREAM]}"

    if [[ ! -f "$level2_doc" ]]; then
        echo -e "${RED}❌ Level 2 doc not found: ${level2_doc}${NC}"
        exit 1
    fi

    echo -e "${BLUE}📄 Extracting LOC from traceability table...${NC}"

    # Extract LOC from "Workstream Total" line in traceability table
    table_total=$(grep -i "Workstream Total" "$level2_doc" | grep -oP '\d{1,3}(,\d{3})*' | head -1 | tr -d ',')

    if [[ -z "$table_total" ]]; then
        echo -e "${RED}❌ Could not find 'Workstream Total' in traceability table${NC}"
        echo -e "${YELLOW}Hint: Ensure the table has a line like:**Workstream Total**: 5,353 lines ✅${NC}"
        exit 1
    fi

    echo -e "${GREEN}  Table Total: ${table_total} lines${NC}"

    # Compute actual LOC from source files
    echo ""
    echo -e "${BLUE}📊 Computing actual LOC from source files...${NC}"

    total_loc=0
    dirs="${WORKSTREAMS[$WORKSTREAM]}"

    for path in $dirs; do
        full_path="${PROJECT_ROOT}/${path}"
        if [[ -e "$full_path" ]]; then
            if [[ -d "$full_path" ]]; then
                loc=$(count_loc "$full_path")
            else
                loc=$(count_file_loc "$full_path")
            fi
            total_loc=$((total_loc + loc))
            echo "  - ${path}: ${loc} lines"
        fi
    done

    echo -e "${GREEN}  Actual Total: ${total_loc} lines${NC}"
    echo ""

    # Compare totals
    diff=$((table_total - total_loc))
    abs_diff=${diff#-}  # Absolute value
    percent_diff=$(awk "BEGIN {printf \"%.2f\", ($abs_diff / $total_loc) * 100}")

    echo -e "${BLUE}📈 Validation Results:${NC}"
    echo "  Table Total:  ${table_total} lines"
    echo "  Actual Total: ${total_loc} lines"
    echo "  Difference:   ${diff} lines (${percent_diff}%)"
    echo ""

    if [[ "$abs_diff" -eq 0 ]]; then
        echo -e "${GREEN}✅ PERFECT MATCH - Table is accurate!${NC}"
        exit 0
    elif [[ "$abs_diff" -le 50 ]] && [[ "$(echo "$percent_diff < 2" | bc -l)" -eq 1 ]]; then
        echo -e "${YELLOW}⚠️  MINOR VARIANCE - Within acceptable range (±2%)${NC}"
        echo -e "${YELLOW}   Consider updating table if variance grows${NC}"
        exit 0
    else
        echo -e "${RED}❌ SIGNIFICANT VARIANCE - Table needs update!${NC}"
        echo -e "${RED}   Difference exceeds 2% threshold${NC}"
        echo ""
        echo "Suggested action:"
        echo "  Update 'Workstream Total' in ${level2_doc}"
        echo "  from ${table_total} to ${total_loc}"
        exit 1
    fi
fi

# ============================================================================
# VALIDATION MODE: --validate-swimlane
# ============================================================================
if [[ "$MODE" = "validate-swimlane" ]]; then
    # Map workstream names to Level 3 swimlane paths
    declare -A SWIMLANES=(
        ["monitoring_drift"]="docs/architecture/diagrams/level-3/monitoring-drift/monitoring-drift-swimlane.puml"
        ["production_runtime"]="docs/architecture/diagrams/level-3/production-runtime/production-runtime-swimlane.puml"
        ["model_training"]="docs/architecture/diagrams/level-3/model-training/model-training-swimlane.puml"
        ["data_preparation"]="docs/architecture/diagrams/level-3/data-preparation/data-preparation-swimlane.puml"
    )

    if [[ -z "${SWIMLANES[$WORKSTREAM]:-}" ]]; then
        echo -e "${RED}❌ No swimlane diagram found for: ${WORKSTREAM}${NC}"
        echo -e "${YELLOW}Available swimlanes: ${!SWIMLANES[*]}${NC}"
        exit 1
    fi

    swimlane_file="${PROJECT_ROOT}/${SWIMLANES[$WORKSTREAM]}"

    if [[ ! -f "$swimlane_file" ]]; then
        echo -e "${RED}❌ Swimlane file not found: ${swimlane_file}${NC}"
        exit 1
    fi

    echo -e "${BLUE}📄 Extracting LOC from swimlane annotations...${NC}"

    # Extract LOC annotations from swimlane (format: "XXX lines" or "(XXX lines)")
    swimlane_total=$(grep -oP '\((\d{1,3}(,\d{3})*) lines?\)' "$swimlane_file" | \
        grep -oP '\d{1,3}(,\d{3})*' | \
        tr -d ',' | \
        awk '{sum += $1} END {print sum}')

    if [[ -z "$swimlane_total" ]] || [[ "$swimlane_total" -eq 0 ]]; then
        echo -e "${RED}❌ Could not find LOC annotations in swimlane${NC}"
        echo -e "${YELLOW}Hint: Ensure annotations use format: 'filename.py (XXX lines)'${NC}"
        exit 1
    fi

    echo -e "${GREEN}  Swimlane Total: ${swimlane_total} lines${NC}"

    # Extract total from legend (format: "Total LOC**: 5,348")
    legend_total=$(grep -i "Total LOC" "$swimlane_file" | grep -oP '\d{1,3}(,\d{3})*' | head -1 | tr -d ',')

    if [[ -n "$legend_total" ]]; then
        echo -e "${GREEN}  Legend Total:   ${legend_total} lines${NC}"

        if [[ "$swimlane_total" -ne "$legend_total" ]]; then
            echo -e "${YELLOW}⚠️  Warning: Annotation sum (${swimlane_total}) != Legend total (${legend_total})${NC}"
        fi
    fi

    # Compute actual LOC from source files
    echo ""
    echo -e "${BLUE}📊 Computing actual LOC from source files...${NC}"

    total_loc=0
    dirs="${WORKSTREAMS[$WORKSTREAM]}"

    for path in $dirs; do
        full_path="${PROJECT_ROOT}/${path}"
        if [[ -e "$full_path" ]]; then
            if [[ -d "$full_path" ]]; then
                loc=$(count_loc "$full_path")
            else
                loc=$(count_file_loc "$full_path")
            fi
            total_loc=$((total_loc + loc))
            echo "  - ${path}: ${loc} lines"
        fi
    done

    echo -e "${GREEN}  Actual Total: ${total_loc} lines${NC}"
    echo ""

    # Compare totals
    diff=$((swimlane_total - total_loc))
    abs_diff=${diff#-}
    percent_diff=$(awk "BEGIN {printf \"%.2f\", ($abs_diff / $total_loc) * 100}")

    echo -e "${BLUE}📈 Validation Results:${NC}"
    echo "  Swimlane Total: ${swimlane_total} lines"
    echo "  Actual Total:   ${total_loc} lines"
    echo "  Difference:     ${diff} lines (${percent_diff}%)"
    echo ""

    if [[ "$abs_diff" -eq 0 ]]; then
        echo -e "${GREEN}✅ PERFECT MATCH - Swimlane annotations are accurate!${NC}"
        exit 0
    elif [[ "$abs_diff" -le 50 ]] && [[ "$(echo "$percent_diff < 2" | bc -l)" -eq 1 ]]; then
        echo -e "${YELLOW}⚠️  MINOR VARIANCE - Within acceptable range (±2%)${NC}"
        echo -e "${YELLOW}   Consider updating annotations if variance grows${NC}"
        exit 0
    else
        echo -e "${RED}❌ SIGNIFICANT VARIANCE - Swimlane needs update!${NC}"
        echo -e "${RED}   Difference exceeds 2% threshold${NC}"
        echo ""
        echo "Suggested action:"
        echo "  Review and update LOC annotations in ${swimlane_file}"
        echo "  Update legend total from ${legend_total:-N/A} to ${total_loc}"
        exit 1
    fi
fi
