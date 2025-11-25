---
category: quality
complexity: medium
estimated_time: "5-15 minutes"
dependencies: []
version: "1.0"
---

# Quality Lint Document

Perform comprehensive document linting and compliance checking with automatic corrections: $ARGUMENTS

## Usage Options

- `file.md` - Lint specific markdown file
- `directory/` - Lint all markdown files in directory
- `--auto-fix` - Apply automatic corrections where safe
- `--check-links` - Validate internal and external links
- `--strict` - Apply stricter validation rules

## Analysis Performed

1. **File Type Detection**: Determine document type and applicable standards
2. **YAML Front Matter Validation**: Check/fix metadata structure
3. **Heading Structure Correction**: Fix heading hierarchy violations
4. **Markdown Linting**: Apply standard markdown formatting rules
5. **Link Validation**: Check internal references and suggest fixes
6. **Content Structure Analysis**: Recommend improvements
7. **Cross-Reference Validation**: Verify consistency

## Document Type Detection

### Documentation Files (README, docs/, guides/)

**Auto-Corrections Applied**:

- Fix heading hierarchy (no skipping levels)
- Apply standard markdown formatting
- Correct list style inconsistencies
- Fix line length violations (120 chars)
- Standardize code block language tags

**Manual Review Flagged**:

- Structural reorganization suggestions
- Missing sections (installation, usage, etc.)
- Broken external links
- Outdated information

### Configuration Files (with YAML front matter)

**Auto-Corrections Applied**:

- Generate/fix YAML front matter structure
- Standardize metadata fields
- Fix heading structure violations
- Apply markdown formatting rules

**Manual Review Flagged**:

- Metadata inconsistencies
- Content scope issues
- Missing cross-references

### Project-Specific Files

**Auto-Corrections Applied**:

- Apply project-specific formatting rules
- Fix common heading issues
- Standardize list formatting

**Manual Review Flagged**:

- Project convention violations
- Content organization suggestions

## Implementation

### 1. File Detection and Analysis

```bash
analyze_document() {
    local file="$1"
    local auto_fix="$2"

    echo "📝 Analyzing document: $file"

    # Detect document type
    local doc_type=$(detect_document_type "$file")
    echo "Document type: $doc_type"

    # Check file exists and is readable
    if [ ! -f "$file" ]; then
        echo "❌ File not found: $file"
        return 1
    fi

    # Basic file validation
    validate_basic_structure "$file" "$auto_fix"
    validate_yaml_frontmatter "$file" "$auto_fix"
    validate_heading_structure "$file" "$auto_fix"
    validate_markdown_formatting "$file" "$auto_fix"
    validate_links "$file"

    # Type-specific validation
    case "$doc_type" in
        "readme") validate_readme_structure "$file" ;;
        "config") validate_config_document "$file" ;;
        "guide") validate_guide_structure "$file" ;;
        *) validate_generic_document "$file" ;;
    esac
}
```

### 2. Document Type Detection

```bash
detect_document_type() {
    local file="$1"
    local filename=$(basename "$file")
    local dirname=$(dirname "$file")

    # Check filename patterns
    case "$filename" in
        README.md|readme.md) echo "readme" ;;
        *config*.md|*Config*.md) echo "config" ;;
        *guide*.md|*Guide*.md|*tutorial*.md) echo "guide" ;;
        *api*.md|*API*.md) echo "api" ;;
        *)
            # Check directory patterns
            case "$dirname" in
                */docs/*|docs) echo "documentation" ;;
                */guides/*|guides) echo "guide" ;;
                *) echo "generic" ;;
            esac
        ;;
    esac
}
```

### 3. YAML Front Matter Validation

```bash
validate_yaml_frontmatter() {
    local file="$1"
    local auto_fix="$2"

    if head -1 "$file" | grep -q "^---$"; then
        echo "✅ YAML front matter detected"

        # Extract and validate YAML
        local yaml_content=$(sed -n '/^---$/,/^---$/p' "$file" | sed '1d;$d')

        # Check required fields (configurable per project)
        if echo "$yaml_content" | grep -q "^title:"; then
            echo "✅ Title field present"
        else
            echo "⚠️  Missing title field"
            if [ "$auto_fix" = "true" ]; then
                add_yaml_title "$file"
            fi
        fi

        # Validate YAML syntax
        if echo "$yaml_content" | python -c "import yaml, sys; yaml.safe_load(sys.stdin)" 2>/dev/null; then
            echo "✅ Valid YAML syntax"
        else
            echo "❌ Invalid YAML syntax - manual fix required"
        fi
    else
        echo "⚠️  No YAML front matter found"
        if [ "$auto_fix" = "true" ]; then
            add_basic_frontmatter "$file"
        fi
    fi
}
```

### 4. Heading Structure Validation

```bash
validate_heading_structure() {
    local file="$1"
    local auto_fix="$2"

    echo "🔍 Checking heading structure..."

    # Extract headings
    local headings=$(grep '^#' "$file")

    # Check for multiple H1s
    local h1_count=$(echo "$headings" | grep -c '^# ' || echo "0")
    if [ "$h1_count" -gt 1 ]; then
        echo "⚠️  Multiple H1 headings found ($h1_count)"
        if [ "$auto_fix" = "true" ]; then
            fix_multiple_h1s "$file"
        fi
    elif [ "$h1_count" -eq 1 ]; then
        echo "✅ Single H1 heading found"
    else
        echo "⚠️  No H1 heading found"
    fi

    # Check for H4+ headings (often indicates over-nesting)
    local deep_headings=$(echo "$headings" | grep '^#### ' | wc -l)
    if [ "$deep_headings" -gt 0 ]; then
        echo "⚠️  Deep headings (H4+) found: $deep_headings"
        echo "   Consider restructuring for better readability"
        if [ "$auto_fix" = "true" ]; then
            suggest_heading_restructure "$file"
        fi
    fi

    # Check for heading level skipping
    check_heading_level_skipping "$file"
}
```

### 5. Markdown Formatting Validation

```bash
validate_markdown_formatting() {
    local file="$1"
    local auto_fix="$2"

    echo "🔍 Checking markdown formatting..."

    # Use markdownlint if available
    if command -v markdownlint &> /dev/null; then
        if [ "$auto_fix" = "true" ]; then
            markdownlint --fix "$file" 2>/dev/null && echo "✅ Markdown formatting fixes applied"
        fi

        # Check remaining issues
        local issues=$(markdownlint "$file" 2>&1 | wc -l)
        if [ "$issues" -eq 0 ]; then
            echo "✅ Markdown formatting compliant"
        else
            echo "⚠️  Markdown formatting issues: $issues"
            markdownlint "$file" | head -10
        fi
    else
        echo "⚠️  markdownlint not available - install for better validation"
        basic_markdown_checks "$file" "$auto_fix"
    fi
}
```

### 6. Link Validation

```bash
validate_links() {
    local file="$1"

    echo "🔗 Checking links..."

    # Extract all markdown links
    local links=$(grep -o '\[.*\](.*' "$file" | grep -o '](.*' | sed 's/^](//' | sed 's/).*$//')

    local broken_links=0
    local total_links=0

    for link in $links; do
        total_links=$((total_links + 1))

        if [[ "$link" =~ ^https?:// ]]; then
            # External link - would need network check
            echo "🌐 External link: $link (network check needed)"
        elif [[ "$link" =~ ^mailto: ]]; then
            # Email link
            echo "📧 Email link: $link"
        else
            # Internal link
            if [ -f "$link" ] || [ -d "$link" ]; then
                echo "✅ Valid internal link: $link"
            else
                echo "❌ Broken internal link: $link"
                broken_links=$((broken_links + 1))
                suggest_link_fix "$link" "$file"
            fi
        fi
    done

    echo "📊 Link summary: $total_links total, $broken_links broken"
}
```

### 7. Automated Fixes

```bash
add_basic_frontmatter() {
    local file="$1"
    local title=$(basename "$file" .md | sed 's/-/ /g' | sed 's/\b\w/\U&/g')

    # Create temporary file with front matter
    {
        echo "---"
        echo "title: $title"
        echo "version: 1.0"
        echo "status: draft"
        echo "---"
        echo ""
        cat "$file"
    } > "$file.tmp" && mv "$file.tmp" "$file"

    echo "✅ Added basic YAML front matter"
}

fix_multiple_h1s() {
    local file="$1"

    # Convert all H1s except the first to H2s
    awk '
    /^# / {
        if (h1_found) {
            sub(/^# /, "## ")
        } else {
            h1_found = 1
        }
    }
    { print }
    ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"

    echo "✅ Fixed multiple H1 headings"
}

basic_markdown_checks() {
    local file="$1"
    local auto_fix="$2"

    # Check line length
    local long_lines=$(awk 'length > 120 { count++ } END { print count+0 }' "$file")
    if [ "$long_lines" -gt 0 ]; then
        echo "⚠️  Long lines found: $long_lines (>120 chars)"
    fi

    # Check for trailing whitespace
    if grep -q '[[:space:]]$' "$file"; then
        echo "⚠️  Trailing whitespace found"
        if [ "$auto_fix" = "true" ]; then
            sed -i 's/[[:space:]]*$//' "$file"
            echo "✅ Removed trailing whitespace"
        fi
    fi

    # Check for consistent list markers
    local dash_lists=$(grep -c '^[[:space:]]*-[[:space:]]' "$file" || echo "0")
    local star_lists=$(grep -c '^[[:space:]]*\*[[:space:]]' "$file" || echo "0")
    if [ "$dash_lists" -gt 0 ] && [ "$star_lists" -gt 0 ]; then
        echo "⚠️  Mixed list markers (- and *) - consider standardizing"
    fi
}
```

## Final Report

```bash
generate_document_report() {
    local file="$1"
    local fixes_applied="$2"
    local issues_found="$3"

    echo ""
    echo "=================== DOCUMENT LINT REPORT ==================="
    echo "File: $file"
    echo "Auto-fixes applied: $fixes_applied"
    echo "Issues requiring attention: $issues_found"
    echo ""

    if [ "$issues_found" -eq 0 ]; then
        echo "✅ DOCUMENT READY: All checks passed"
    elif [ "$issues_found" -le 3 ]; then
        echo "⚠️  MINOR ISSUES: Document mostly compliant"
    else
        echo "⚠️  MAJOR ISSUES: Document needs attention"
    fi

    echo "==========================================================="
}
```

## Examples

```bash
# Lint single document with auto-fix
/universal:quality-lint-document README.md --auto-fix

# Lint all documents in directory
/universal:quality-lint-document docs/ --check-links

# Strict validation
/universal:quality-lint-document guide.md --strict

# Check links only
/universal:quality-lint-document documentation/ --check-links
```

## Integration with Workflow

```bash
# Complete documentation quality workflow
/universal:quality-lint-document docs/          # Lint documentation
/universal:meta-fix-links docs/                 # Fix broken links
/universal:quality-precommit-validate docs/     # Final validation
```

---

*This command provides universal document linting that adapts to different documentation styles while maintaining quality and consistency.*
