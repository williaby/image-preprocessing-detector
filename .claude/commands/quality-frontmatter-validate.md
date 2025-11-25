---
category: quality
complexity: medium
estimated_time: "5-10 minutes"
dependencies: []
version: "1.0"
---

# Quality Frontmatter Validate

Validate and fix YAML front matter in documentation files with intelligent content analysis: $ARGUMENTS

## Usage Options

- `file.md` - Validate specific markdown file
- `directory/` - Validate all markdown files in directory
- `--auto-fix` - Apply automatic corrections
- `--strict` - Apply stricter validation rules

## Analysis Performed

1. **Front Matter Detection**: Check for YAML front matter presence and syntax
2. **File Type Classification**: Determine applicable validation rules
3. **Field Validation**: Verify required fields and formats
4. **Content Consistency**: Match metadata with document content
5. **Schema Compliance**: Ensure format follows project standards
6. **Intelligent Corrections**: Generate proper metadata from content

## File Type Detection and Rules

### Knowledge Files (knowledge/ directory)

**Required YAML Structure**:

```yaml
---
title: [String - must match H1 heading exactly]
version: [X.Y or X.Y.Z semantic version]
status: [draft|in-review|published]
agent_id: [snake_case - MUST match folder name exactly]
tags: [Array of lowercase strings, use underscores for spaces]
purpose: [Single sentence ending with period]
---
```

### Documentation Files (docs/ directory)

**Required YAML Structure**:

```yaml
---
title: [String - must match H1 heading exactly]
version: [X.Y or X.Y.Z semantic version]
status: [draft|in-review|published]
component: [Architecture|Planning|Process|Guide|Reference]
tags: [Array of lowercase strings, use underscores for spaces]
source: [String - reference to originating document]
purpose: [Single sentence ending with period]
---
```

### General Files (other locations)

**Basic YAML Structure**:

```yaml
---
title: [String - must match H1 heading]
version: [X.Y or X.Y.Z semantic version]
status: [draft|in-review|published]
tags: [Array of lowercase strings]
purpose: [Single sentence ending with period]
---
```

## Validation Implementation

### 1. File Type Detection

```bash
detect_file_type() {
    local file_path="$1"
    local dir_path=$(dirname "$file_path")

    if [[ "$dir_path" =~ /knowledge/ ]]; then
        echo "knowledge"
    elif [[ "$dir_path" =~ /docs/ ]]; then
        echo "documentation"
    else
        echo "general"
    fi
}

extract_agent_id_from_path() {
    local file_path="$1"

    # Extract agent_id from knowledge/{agent_id}/file.md pattern
    if [[ "$file_path" =~ knowledge/([^/]+)/ ]]; then
        echo "${BASH_REMATCH[1]}"
    fi
}
```

### 2. YAML Front Matter Extraction

```bash
extract_frontmatter() {
    local file="$1"

    if head -1 "$file" | grep -q "^---$"; then
        # Extract content between first two --- lines
        sed -n '/^---$/,/^---$/p' "$file" | sed '1d;$d'
    else
        echo ""
    fi
}

extract_h1_title() {
    local file="$1"

    # Find first H1 heading and extract title
    grep -m 1 "^# " "$file" | sed 's/^# *//' | sed 's/ *$//'
}

parse_yaml_field() {
    local yaml_content="$1"
    local field_name="$2"

    echo "$yaml_content" | grep "^$field_name:" | sed "s/^$field_name: *//" | sed 's/^["'\'']//' | sed 's/["'\'']$//'
}
```

### 3. Field Validation Functions

```bash
validate_title_consistency() {
    local yaml_title="$1"
    local h1_title="$2"

    if [[ "$yaml_title" == "$h1_title" ]]; then
        echo "✅ Title matches H1 heading"
        return 0
    else
        echo "❌ Title mismatch: YAML='$yaml_title', H1='$h1_title'"
        return 1
    fi
}

validate_agent_id_consistency() {
    local yaml_agent_id="$1"
    local path_agent_id="$2"

    if [[ "$yaml_agent_id" == "$path_agent_id" ]]; then
        echo "✅ Agent ID matches directory"
        return 0
    else
        echo "❌ Agent ID mismatch: YAML='$yaml_agent_id', Path='$path_agent_id'"
        return 1
    fi
}

validate_version_format() {
    local version="$1"

    if [[ "$version" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]; then
        echo "✅ Valid semantic version format"
        return 0
    else
        echo "❌ Invalid version format: '$version' (should be X.Y or X.Y.Z)"
        return 1
    fi
}

validate_status_value() {
    local status="$1"

    case "$status" in
        "draft"|"in-review"|"published")
            echo "✅ Valid status value"
            return 0
            ;;
        *)
            echo "❌ Invalid status: '$status' (should be draft, in-review, or published)"
            return 1
            ;;
    esac
}

validate_tags_format() {
    local tags="$1"
    local issues=()

    # Parse array format
    local tag_list=$(echo "$tags" | sed "s/\[//" | sed "s/\]//" | sed "s/',*/' /g" | sed "s/'//g")

    for tag in $tag_list; do
        # Check for uppercase letters
        if [[ "$tag" =~ [A-Z] ]]; then
            issues+=("Tag '$tag' contains uppercase (should be lowercase)")
        fi

        # Check for spaces
        if [[ "$tag" =~ [[:space:]] ]]; then
            issues+=("Tag '$tag' contains spaces (use underscores)")
        fi

        # Check for camelCase
        if [[ "$tag" =~ [a-z][A-Z] ]]; then
            issues+=("Tag '$tag' appears to be camelCase (use underscores)")
        fi
    done

    if [[ ${#issues[@]} -eq 0 ]]; then
        echo "✅ Valid tag format"
        return 0
    else
        for issue in "${issues[@]}"; do
            echo "❌ $issue"
        done
        return 1
    fi
}

validate_purpose_format() {
    local purpose="$1"

    # Check if it's a single sentence ending with period
    if [[ "$purpose" =~ \.$ ]] && [[ $(echo "$purpose" | grep -o '\.' | wc -l) -eq 1 ]]; then
        echo "✅ Valid purpose format"
        return 0
    else
        echo "❌ Purpose should be single sentence ending with period"
        return 1
    fi
}
```

### 4. Auto-Generation Functions

```bash
generate_missing_frontmatter() {
    local file_path="$1"
    local file_type="$2"

    local h1_title=$(extract_h1_title "$file_path")
    local agent_id=$(extract_agent_id_from_path "$file_path")
    local filename=$(basename "$file_path" .md)

    # Generate title from H1 or filename
    local title="${h1_title:-$(echo "$filename" | sed 's/-/ /g' | sed 's/\b\w/\U&/g')}"

    # Generate tags from content analysis
    local tags=$(generate_content_tags "$file_path" "$file_type")

    # Generate purpose from content
    local purpose=$(generate_content_purpose "$file_path" "$file_type")

    case "$file_type" in
        "knowledge")
            cat << EOF
---
title: $title
version: 1.0
status: draft
agent_id: $agent_id
tags: $tags
purpose: $purpose
---
EOF
            ;;
        "documentation")
            local component=$(classify_doc_component "$file_path")
            cat << EOF
---
title: $title
version: 1.0
status: draft
component: $component
tags: $tags
source: "Project Documentation"
purpose: $purpose
---
EOF
            ;;
        *)
            cat << EOF
---
title: $title
version: 1.0
status: draft
tags: $tags
purpose: $purpose
---
EOF
            ;;
    esac
}

generate_content_tags() {
    local file_path="$1"
    local file_type="$2"

    # Analyze content for relevant keywords
    local content=$(cat "$file_path")
    local tags=()

    # Common technical terms
    if echo "$content" | grep -qi "api\|endpoint\|rest"; then
        tags+=("api")
    fi
    if echo "$content" | grep -qi "auth\|login\|security"; then
        tags+=("authentication")
    fi
    if echo "$content" | grep -qi "config\|setting\|environment"; then
        tags+=("configuration")
    fi
    if echo "$content" | grep -qi "deploy\|build\|ci\|cd"; then
        tags+=("deployment")
    fi
    if echo "$content" | grep -qi "test\|spec\|mock"; then
        tags+=("testing")
    fi

    # File-type specific tags
    case "$file_type" in
        "knowledge")
            tags+=("knowledge_base")
            ;;
        "documentation")
            tags+=("documentation")
            ;;
    esac

    # Format as YAML array
    if [[ ${#tags[@]} -gt 0 ]]; then
        printf "['%s']" "$(IFS="', '"; echo "${tags[*]}")"
    else
        echo "['general']"
    fi
}

generate_content_purpose() {
    local file_path="$1"
    local file_type="$2"

    # Extract first paragraph or section for purpose
    local first_para=$(sed -n '/^## /,$p' "$file_path" | head -n 10 | grep -v '^#' | grep -v '^$' | head -n 1)

    if [[ -n "$first_para" ]]; then
        # Truncate and ensure period ending
        local purpose=$(echo "$first_para" | cut -c 1-80 | sed 's/[^.]*$//')
        if [[ ! "$purpose" =~ \.$ ]]; then
            purpose="${purpose}."
        fi
        echo "$purpose"
    else
        # Generic purpose based on file type
        case "$file_type" in
            "knowledge")
                echo "To provide essential knowledge and guidance for development workflows."
                ;;
            "documentation")
                echo "To document project processes and provide developer guidance."
                ;;
            *)
                echo "To provide information and guidance on the covered topic."
                ;;
        esac
    fi
}

classify_doc_component() {
    local file_path="$1"
    local content=$(cat "$file_path" | tr '[:upper:]' '[:lower:]')

    if echo "$content" | grep -q "architecture\|design\|system"; then
        echo "Architecture"
    elif echo "$content" | grep -q "plan\|strategy\|roadmap"; then
        echo "Planning"
    elif echo "$content" | grep -q "process\|workflow\|procedure"; then
        echo "Process"
    elif echo "$content" | grep -q "guide\|tutorial\|how.to"; then
        echo "Guide"
    else
        echo "Reference"
    fi
}
```

### 5. Auto-Correction Functions

```bash
fix_frontmatter_issues() {
    local file_path="$1"
    local yaml_content="$2"
    local file_type="$3"

    local corrected_yaml="$yaml_content"
    local fixes_applied=()

    # Fix title consistency
    local yaml_title=$(parse_yaml_field "$yaml_content" "title")
    local h1_title=$(extract_h1_title "$file_path")
    if [[ -n "$h1_title" ]] && [[ "$yaml_title" != "$h1_title" ]]; then
        corrected_yaml=$(echo "$corrected_yaml" | sed "s/^title:.*/title: $h1_title/")
        fixes_applied+=("Fixed title to match H1 heading")
    fi

    # Fix agent_id for knowledge files
    if [[ "$file_type" == "knowledge" ]]; then
        local yaml_agent_id=$(parse_yaml_field "$yaml_content" "agent_id")
        local path_agent_id=$(extract_agent_id_from_path "$file_path")
        if [[ -n "$path_agent_id" ]] && [[ "$yaml_agent_id" != "$path_agent_id" ]]; then
            corrected_yaml=$(echo "$corrected_yaml" | sed "s/^agent_id:.*/agent_id: $path_agent_id/")
            fixes_applied+=("Fixed agent_id to match directory")
        fi
    fi

    # Fix tag formatting
    local tags=$(parse_yaml_field "$yaml_content" "tags")
    if [[ -n "$tags" ]]; then
        local fixed_tags=$(fix_tag_format "$tags")
        if [[ "$tags" != "$fixed_tags" ]]; then
            corrected_yaml=$(echo "$corrected_yaml" | sed "s/^tags:.*/tags: $fixed_tags/")
            fixes_applied+=("Fixed tag formatting")
        fi
    fi

    echo "$corrected_yaml"

    # Report fixes
    for fix in "${fixes_applied[@]}"; do
        echo "✅ $fix"
    done
}

fix_tag_format() {
    local tags="$1"

    # Extract tags and fix format
    local tag_list=$(echo "$tags" | sed 's/\[//' | sed 's/\]//' | sed "s/',*/' /g" | sed "s/'//g")
    local fixed_tags=()

    for tag in $tag_list; do
        # Convert to lowercase and replace spaces with underscores
        local fixed_tag=$(echo "$tag" | tr '[:upper:]' '[:lower:]' | sed 's/ /_/g')
        fixed_tags+=("$fixed_tag")
    done

    # Format as YAML array
    printf "['%s']" "$(IFS="', '"; echo "${fixed_tags[*]}")"
}
```

## Report Generation

```bash
generate_frontmatter_report() {
    local file_path="$1"
    local file_type="$2"
    local validation_results="$3"
    local fixes_applied="$4"

    echo ""
    echo "================ FRONTMATTER VALIDATION REPORT ================"
    echo "File: $(basename "$file_path")"
    echo "Type: $file_type"
    echo "Auto-fixes applied: $fixes_applied"
    echo ""

    local issues_count=$(echo "$validation_results" | grep -c "❌" || echo "0")
    local valid_count=$(echo "$validation_results" | grep -c "✅" || echo "0")

    if [[ $issues_count -eq 0 ]]; then
        echo "✅ FRONTMATTER VALID: All checks passed"
    elif [[ $issues_count -le 2 ]]; then
        echo "⚠️  MINOR ISSUES: $issues_count fields need attention"
    else
        echo "❌ MAJOR ISSUES: $issues_count fields require fixes"
    fi

    echo "Valid fields: $valid_count"
    echo "Issues found: $issues_count"
    echo "================================================================"
}
```

## Examples

```bash
# Validate specific file with auto-fix
/universal:quality-frontmatter-validate guide.md --auto-fix

# Validate all files in directory
/universal:quality-frontmatter-validate knowledge/

# Strict validation
/universal:quality-frontmatter-validate docs/ --strict

# Validate without fixes (dry-run)
/universal:quality-frontmatter-validate file.md
```

## Integration with Quality Workflow

```bash
# Complete documentation quality workflow
/universal:quality-frontmatter-validate docs/  # Validate metadata
/universal:quality-lint-document docs/         # Lint content
/universal:meta-fix-links docs/                # Fix broken links
/universal:quality-precommit-validate docs/    # Final validation
```

---

*This command provides universal YAML front matter validation that adapts to different documentation types while maintaining metadata consistency and quality.*
