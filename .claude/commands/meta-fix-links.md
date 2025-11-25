---
category: meta
complexity: medium
estimated_time: "10-15 minutes"
dependencies: []
version: "1.0"
---

# Meta Fix Links

Analyze and fix broken internal links in documentation files with intelligent path resolution: $ARGUMENTS

## Usage Options

- `file.md` - Fix links in specific markdown file
- `directory/` - Fix links in all markdown files in directory
- `--dry-run` - Show fixes without applying them
- `--fuzzy-match` - Use fuzzy matching for suggestions

## Analysis Performed

1. **Link Detection**: Find all internal links (relative, absolute, anchor)
2. **Path Validation**: Check if target files and directories exist
3. **Anchor Validation**: Verify heading targets exist in documents
4. **Fuzzy Matching**: Suggest similar filenames for broken links
5. **Path Correction**: Calculate correct relative paths
6. **Content Preservation**: Maintain document flow and context

## Link Types Supported

### Internal File Links

- **Relative**: `[text](./file.md)`, `[text](../dir/file.md)`
- **Absolute**: `[text](/docs/file.md)`
- **Cross-directory**: `[text](../../other/file.md)`

### Anchor Links

- **Same file**: `[text](#heading-name)`
- **Other files**: `[text](./other.md#section)`
- **Cross-references**: `[text](/docs/guide.md#installation)`

### Common Patterns

- Documentation cross-references
- Project structure navigation
- Table of contents links
- Cross-document citations

## Implementation Strategy

### 1. Link Extraction and Analysis

```bash
extract_links() {
    local file="$1"
    echo "🔍 Extracting links from: $(basename "$file")"

    # Find all markdown links
    grep -n '\[.*\](.*' "$file" | while read -r line_num content; do
        # Extract link components
        link_text=$(echo "$content" | sed -n 's/.*\[\([^]]*\)\].*/\1/p')
        link_target=$(echo "$content" | sed -n 's/.*](\([^)]*\)).*/\1/p')

        echo "Line $line_num: [$link_text]($link_target)"
        validate_link "$file" "$link_target" "$line_num"
    done
}

validate_link() {
    local source_file="$1"
    local target="$2"
    local line_num="$3"
    local source_dir=$(dirname "$source_file")

    # Skip external links
    if [[ "$target" =~ ^https?:// ]]; then
        echo "  ✅ External link (not validated)"
        return
    fi

    # Handle anchor-only links
    if [[ "$target" =~ ^# ]]; then
        validate_anchor "$source_file" "$target"
        return
    fi

    # Handle file+anchor links
    if [[ "$target" =~ (.*)#(.*) ]]; then
        local file_part="${BASH_REMATCH[1]}"
        local anchor_part="${BASH_REMATCH[2]}"

        validate_file_link "$source_dir" "$file_part" "$line_num"
        validate_anchor_in_file "$source_dir/$file_part" "#$anchor_part"
        return
    fi

    # Handle file-only links
    validate_file_link "$source_dir" "$target" "$line_num"
}
```

### 2. File Link Validation

```bash
validate_file_link() {
    local source_dir="$1"
    local target="$2"
    local line_num="$3"

    # Calculate absolute path
    local target_path
    if [[ "$target" =~ ^/ ]]; then
        # Absolute path from repo root
        target_path="$(git rev-parse --show-toplevel)$target"
    else
        # Relative path
        target_path="$(cd "$source_dir" && realpath "$target" 2>/dev/null)"
    fi

    if [[ -f "$target_path" ]]; then
        echo "  ✅ Valid file link"
    elif [[ -d "$target_path" ]]; then
        echo "  ✅ Valid directory link"
    else
        echo "  ❌ Broken link: $target"
        suggest_file_fix "$source_dir" "$target" "$line_num"
    fi
}

suggest_file_fix() {
    local source_dir="$1"
    local broken_target="$2"
    local line_num="$3"

    echo "    🔍 Searching for similar files..."

    # Extract just the filename
    local filename=$(basename "$broken_target")
    local dirname=$(dirname "$broken_target")

    # Search for similar filenames using fuzzy matching
    local repo_root=$(git rev-parse --show-toplevel)
    local suggestions=$(find "$repo_root" -name "*.md" -type f | grep -i "$filename" | head -3)

    if [ -n "$suggestions" ]; then
        echo "    💡 Possible matches:"
        echo "$suggestions" | while read -r suggestion; do
            # Calculate relative path from source to suggestion
            local rel_path=$(realpath --relative-to="$source_dir" "$suggestion")
            echo "      - $rel_path"
        done
    fi

    # Check for common naming patterns
    check_common_patterns "$source_dir" "$broken_target"
}
```

### 3. Anchor Link Validation

```bash
validate_anchor() {
    local file="$1"
    local anchor="$2"

    # Remove # prefix
    local heading_name=${anchor#"#"}

    # Convert anchor format to heading format
    local expected_heading=$(echo "$heading_name" | sed 's/-/ /g' | tr '[:upper:]' '[:lower:]')

    # Check if heading exists in file
    if grep -qi "^#.*$expected_heading" "$file"; then
        echo "  ✅ Valid anchor link"
    else
        echo "  ❌ Broken anchor: $anchor"
        suggest_anchor_fix "$file" "$heading_name"
    fi
}

suggest_anchor_fix() {
    local file="$1"
    local broken_anchor="$2"

    echo "    🔍 Available headings in file:"
    grep '^#' "$file" | head -5 | while read -r heading; do
        # Convert heading to anchor format
        local anchor_format=$(echo "$heading" | sed 's/^#* *//' | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g')
        echo "      #$anchor_format"
    done
}

validate_anchor_in_file() {
    local target_file="$1"
    local anchor="$2"

    if [[ -f "$target_file" ]]; then
        validate_anchor "$target_file" "$anchor"
    else
        echo "  ❌ Cannot validate anchor in missing file"
    fi
}
```

### 4. Intelligent Path Correction

```bash
fix_broken_links() {
    local file="$1"
    local auto_fix="$2"

    echo "🔧 Fixing broken links in: $(basename "$file")"

    # Create backup
    cp "$file" "$file.backup"

    local fixes_applied=0
    local temp_file=$(mktemp)
    cp "$file" "$temp_file"

    # Process each broken link
    while IFS= read -r link_info; do
        if [[ "$link_info" =~ "❌ Broken link:" ]]; then
            local broken_link=$(echo "$link_info" | sed 's/.*❌ Broken link: //')
            local suggested_fix=$(get_best_suggestion "$file" "$broken_link")

            if [[ -n "$suggested_fix" ]] && [[ "$auto_fix" == "true" ]]; then
                # Apply the fix
                sed -i "s|]($broken_link)|]($suggested_fix)|g" "$temp_file"
                echo "    ✅ Fixed: $broken_link → $suggested_fix"
                fixes_applied=$((fixes_applied + 1))
            fi
        fi
    done < <(extract_and_validate_links "$file")

    if [[ "$fixes_applied" -gt 0 ]] && [[ "$auto_fix" == "true" ]]; then
        mv "$temp_file" "$file"
        echo "✅ Applied $fixes_applied fixes to $file"
    else
        rm "$temp_file"
        echo "📋 Found issues but no auto-fixes applied"
    fi

    rm -f "$file.backup"
}
```

### 5. Common Pattern Recognition

```bash
check_common_patterns() {
    local source_dir="$1"
    local broken_target="$2"

    echo "    🔎 Checking common patterns..."

    # Common file renames
    case "$(basename "$broken_target")" in
        "PROJECT_HUB.md")
            echo "      💡 Try: project_hub.md"
            ;;
        "CONTRIBUTING.md")
            echo "      💡 Try: ../../CONTRIBUTING.md or ../PC_Contributing.md"
            ;;
        "PC_ADR.md")
            echo "      💡 Try: ./ADR.md (if in planning directory)"
            ;;
        "issues")
            echo "      💡 Try: ./pc_milestones_issues.md"
            ;;
        *)
            # Check for case sensitivity issues
            local lowercase_target=$(echo "$broken_target" | tr '[:upper:]' '[:lower:]')
            local uppercase_target=$(echo "$broken_target" | tr '[:lower:]' '[:upper:]')

            if [[ -f "$source_dir/$lowercase_target" ]]; then
                echo "      💡 Case issue: try $lowercase_target"
            elif [[ -f "$source_dir/$uppercase_target" ]]; then
                echo "      💡 Case issue: try $uppercase_target"
            fi
            ;;
    esac
}

get_best_suggestion() {
    local source_file="$1"
    local broken_link="$2"
    local source_dir=$(dirname "$source_file")

    # Implement logic to return the best suggestion
    # This would use fuzzy matching and common patterns
    # to determine the most likely correct path

    local filename=$(basename "$broken_link")
    local repo_root=$(git rev-parse --show-toplevel)

    # Find best match using find and similarity
    local best_match=$(find "$repo_root" -name "*$filename*" -type f | head -1)

    if [[ -n "$best_match" ]]; then
        realpath --relative-to="$source_dir" "$best_match"
    fi
}
```

## Fuzzy Matching Algorithm

```bash
calculate_similarity() {
    local str1="$1"
    local str2="$2"

    # Simple Levenshtein distance approximation
    local len1=${#str1}
    local len2=${#str2}
    local max_len=$((len1 > len2 ? len1 : len2))

    if [[ $max_len -eq 0 ]]; then
        echo "1.0"
        return
    fi

    # Count matching characters (simplified)
    local matches=0
    for ((i=0; i<len1 && i<len2; i++)); do
        if [[ "${str1:$i:1}" == "${str2:$i:1}" ]]; then
            matches=$((matches + 1))
        fi
    done

    # Calculate similarity score using bash arithmetic
    local similarity
    if [[ $max_len -gt 0 ]]; then
        similarity=$((100 * matches / max_len))
    else
        similarity=0
    fi
    echo "$similarity"
}

find_best_matches() {
    local broken_file="$1"
    local source_dir="$2"
    local repo_root=$(git rev-parse --show-toplevel)

    # Find all markdown files
    find "$repo_root" -name "*.md" -type f | while read -r candidate; do
        local candidate_name=$(basename "$candidate")
        local similarity=$(calculate_similarity "$broken_file" "$candidate_name")

        # Only suggest if similarity is above threshold (60%)
        if (( similarity > 60 )); then
            local rel_path=$(realpath --relative-to="$source_dir" "$candidate")
            echo "$similarity:$rel_path"
        fi
    done | sort -nr | head -3 | cut -d: -f2
}
```

## Report Generation

```bash
generate_link_report() {
    local file="$1"
    local total_links="$2"
    local valid_links="$3"
    local broken_links="$4"

    echo ""
    echo "================== LINK VALIDATION REPORT =================="
    echo "File: $(basename "$file")"
    echo "Total links found: $total_links"
    echo "Valid links: $valid_links"
    echo "Broken links: $broken_links"
    echo ""

    if [[ $broken_links -eq 0 ]]; then
        echo "✅ ALL LINKS VALID: No issues found"
    elif [[ $broken_links -le 2 ]]; then
        echo "⚠️  MINOR ISSUES: Few broken links found"
    else
        echo "❌ MAJOR ISSUES: Multiple broken links need attention"
    fi

    echo "=============================================================="
}
```

## Examples

```bash
# Fix links in specific file
/universal:meta-fix-links README.md

# Fix all links in directory
/universal:meta-fix-links docs/

# Dry run to see fixes without applying
/universal:meta-fix-links guide.md --dry-run

# Use fuzzy matching for better suggestions
/universal:meta-fix-links . --fuzzy-match
```

## Integration with Quality Workflow

```bash
# Complete documentation quality workflow
/universal:quality-lint-document docs/       # Lint documents
/universal:meta-fix-links docs/              # Fix broken links
/universal:quality-precommit-validate docs/  # Final validation
```

---

*This command provides universal link validation and fixing that works across different documentation structures while maintaining content integrity.*
