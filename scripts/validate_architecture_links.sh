#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 Byron Williams
# SPDX-License-Identifier: MIT

set -euo pipefail

# Validate cross-level references in architecture documentation
# Checks for broken links between Level 0, Level 1, and Level 2 docs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_DIR="${PROJECT_ROOT}/docs/architecture/diagrams"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
total_links=0
broken_links=0
valid_links=0

echo "🔗 Validating Architecture Documentation Cross-References..."
echo "Documentation Root: ${DOCS_DIR}"
echo ""

# Function to extract markdown links from a file
# Returns: link_text|link_target (one per line)
extract_links() {
    local file=$1
    # Match [text](path) - capturing both text and path
    grep -oP '\[([^\]]+)\]\(([^)]+)\)' "$file" 2>/dev/null | \
        sed 's/\[\(.*\)\](\(.*\))/\1|\2/' || true
}

# Function to resolve relative path from source file
resolve_path() {
    local source_file=$1
    local link_target=$2
    local source_dir=$(dirname "$source_file")

    # Skip external URLs
    if [[ "$link_target" =~ ^https?:// ]]; then
        echo "EXTERNAL"
        return
    fi

    # Skip anchors-only links
    if [[ "$link_target" =~ ^# ]]; then
        echo "ANCHOR"
        return
    fi

    # Remove anchor from target if present
    local path_only="${link_target%#*}"

    # Resolve relative path
    local resolved=$(cd "$source_dir" && realpath -m "$path_only" 2>/dev/null || echo "INVALID")

    echo "$resolved"
}

# Function to check if file exists
check_file_exists() {
    local file_path=$1

    if [ "$file_path" = "EXTERNAL" ] || [ "$file_path" = "ANCHOR" ] || [ "$file_path" = "INVALID" ]; then
        return 2  # Skip
    fi

    if [ -f "$file_path" ] || [ -d "$file_path" ]; then
        return 0  # Exists
    else
        return 1  # Broken
    fi
}

# Array to store broken links for summary
declare -a BROKEN_LINKS

# Validate links in a file
validate_file_links() {
    local file=$1
    local file_display="${file#$PROJECT_ROOT/}"

    echo -e "${BLUE}Checking: ${file_display}${NC}"

    local file_links=0
    local file_broken=0

    while IFS='|' read -r link_text link_target; do
        [ -z "$link_target" ] && continue

        ((total_links++))
        ((file_links++))

        resolved=$(resolve_path "$file" "$link_target")

        if check_file_exists "$resolved"; then
            status=$?
            if [ $status -eq 0 ]; then
                ((valid_links++))
            elif [ $status -eq 1 ]; then
                ((broken_links++))
                ((file_broken++))
                echo -e "  ${RED}✗ BROKEN: [$link_text]($link_target)${NC}"
                echo -e "    Resolved to: $resolved"
                BROKEN_LINKS+=("${file_display}|${link_text}|${link_target}|${resolved}")
            fi
            # status=2 means skip (external/anchor)
        fi
    done < <(extract_links "$file")

    if [ $file_links -eq 0 ]; then
        echo -e "  ${YELLOW}No links found${NC}"
    elif [ $file_broken -eq 0 ]; then
        echo -e "  ${GREEN}✓ All ${file_links} links valid${NC}"
    else
        echo -e "  ${RED}✗ ${file_broken}/${file_links} links broken${NC}"
    fi

    echo ""
}

# Main validation
echo "=== Level 0 ==="
for file in "$DOCS_DIR"/level-0/*.md; do
    [ -f "$file" ] && validate_file_links "$file"
done

echo "=== Level 1 ==="
for file in "$DOCS_DIR"/level-1/*.md; do
    [ -f "$file" ] && validate_file_links "$file"
done

echo "=== Level 2 ==="
for dir in "$DOCS_DIR"/level-2/*/; do
    for file in "$dir"*.md; do
        [ -f "$file" ] && validate_file_links "$file"
    done
done

echo "=== Deprecated ==="
for dir in "$DOCS_DIR"/deprecated/*/; do
    for file in "$dir"*.md; do
        [ -f "$file" ] && validate_file_links "$file"
    done
done

echo "=== Root Architecture Docs ==="
for file in "$PROJECT_ROOT"/docs/architecture/*.md; do
    [ -f "$file" ] && validate_file_links "$file"
done

# Summary
echo "========================================="
echo "📊 Validation Summary"
echo "========================================="
echo -e "Total Links Checked: ${BLUE}${total_links}${NC}"
echo -e "Valid Links: ${GREEN}${valid_links}${NC}"
echo -e "Broken Links: ${RED}${broken_links}${NC}"

if [ ${broken_links} -gt 0 ]; then
    echo ""
    echo "❌ FAILED: Found ${broken_links} broken link(s)"
    echo ""
    echo "Broken Links Details:"
    echo "===================="
    printf "%-50s | %-30s | %-40s\n" "Source File" "Link Text" "Target"
    echo "$(printf '=%.0s' {1..125})"
    for broken in "${BROKEN_LINKS[@]}"; do
        IFS='|' read -r source text target resolved <<< "$broken"
        printf "%-50s | %-30s | %-40s\n" "$source" "${text:0:30}" "${target:0:40}"
    done
    echo ""
    exit 1
else
    echo ""
    echo -e "${GREEN}✅ SUCCESS: All architecture documentation links are valid!${NC}"
    exit 0
fi
