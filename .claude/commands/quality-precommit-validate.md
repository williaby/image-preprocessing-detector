---
category: quality
complexity: high
estimated_time: "10-20 minutes"
dependencies: []
version: "1.0"
---

# Quality Precommit Validate

Perform comprehensive pre-commit validation and compliance checking with automatic corrections for all file types: $ARGUMENTS

## Usage Options

- `staged` - Validate only staged files (default)
- `all` - Validate all files in repository
- `path/to/files` - Validate specific files or directories
- `--auto-fix` - Apply automatic corrections where safe

## Analysis Performed

1. **File Type Detection**: Determine applicable validators based on file extension
2. **Hook-by-Hook Validation**: Check compliance with standard development practices
3. **Safe Auto-Corrections**: Apply formatting and safe fixes automatically
4. **Security Issue Detection**: Flag critical issues requiring manual review
5. **Cross-File Impact Analysis**: Identify changes that might affect other files
6. **Git Environment Validation**: Verify GPG/SSH keys for signed commits
7. **Commit Message Readiness**: Suggest proper conventional commit format
8. **Compliance Scoring**: Provide comprehensive before/after assessment

## Pre-commit Hook Coverage

### Universal Hooks (All Files)

**Auto-Corrections Applied**:

- **trailing-whitespace**: Remove trailing whitespace from all lines
- **end-of-file-fixer**: Ensure files end with newline
- **mixed-line-ending**: Standardize line endings to LF
- **fix-byte-order-marker**: Remove byte order markers

**Manual Review Flagged**:

- **check-added-large-files**: Files over 1MB (suggest alternatives)
- **detect-private-key**: Private key detection (security critical)
- **check-case-conflict**: Flag case conflicts
- **check-merge-conflict**: Detect merge conflict markers

### File-Type Specific Hooks

#### Python Files (.py)

**Auto-Corrections Applied**:

- **black**: Code formatting (88 character line length)
- **ruff --fix**: Auto-fixable linting violations
- **debug-statements**: Remove debug imports and statements

**Manual Review Flagged**:

- **mypy**: Type checking errors
- **bandit**: Security vulnerabilities
- **ruff**: Non-auto-fixable linting issues

#### Markdown Files (.md)

**Auto-Corrections Applied**:

- **markdownlint**: Apply auto-fixes for formatting
- Line length, heading spacing, list formatting

**Manual Review Flagged**:

- Content structure violations requiring human judgment

#### YAML Files (.yml, .yaml)

**Auto-Corrections Applied**:

- **yamllint**: Indentation, line length, syntax corrections

**Manual Review Flagged**:

- Complex configuration issues

#### JSON/TOML/XML Files

**Auto-Corrections Applied**:

- **syntax validation**: Fix syntax and formatting
- **structure validation**: Basic structural fixes

**Manual Review Flagged**:

- Complex structural issues requiring content understanding

## Implementation Strategy

### 1. Environment Validation

```bash
# Check required tools are available
if command -v git &> /dev/null; then
    echo "✅ Git available"
else
    echo "❌ Git not found - install Git first"
    exit 1
fi

# Validate GPG/SSH keys for signed commits
gpg --list-secret-keys > /dev/null 2>&1 && echo "✅ GPG key available" || echo "⚠️  No GPG key found"
ssh-add -l > /dev/null 2>&1 && echo "✅ SSH key loaded" || echo "⚠️  No SSH key loaded"
```

### 2. File Detection and Processing

```bash
# Determine files to check
if [ "$1" = "staged" ] || [ -z "$1" ]; then
    files=$(git diff --cached --name-only)
elif [ "$1" = "all" ]; then
    files=$(git ls-files)
else
    files="$@"
fi

# Process each file by type
for file in $files; do
    case "$file" in
        *.py) validate_python_file "$file" ;;
        *.md) validate_markdown_file "$file" ;;
        *.yml|*.yaml) validate_yaml_file "$file" ;;
        *.json) validate_json_file "$file" ;;
        *) validate_universal_rules "$file" ;;
    esac
done
```

### 3. Python File Validation

```bash
validate_python_file() {
    local file="$1"
    echo "🐍 Validating Python file: $file"

    # Auto-corrections
    if command -v black &> /dev/null; then
        black "$file" && echo "✅ Black formatting applied"
    fi

    if command -v ruff &> /dev/null; then
        ruff check --fix "$file" && echo "✅ Ruff auto-fixes applied"
    fi

    # Manual review items
    if command -v mypy &> /dev/null; then
        mypy "$file" || echo "⚠️  MyPy issues found - manual review needed"
    fi

    if command -v bandit &> /dev/null; then
        bandit "$file" || echo "⚠️  Security issues found - manual review needed"
    fi
}
```

### 4. Markdown File Validation

```bash
validate_markdown_file() {
    local file="$1"
    echo "📝 Validating Markdown file: $file"

    # Auto-corrections
    if command -v markdownlint &> /dev/null; then
        markdownlint --fix "$file" 2>/dev/null && echo "✅ Markdown formatting applied"
        markdownlint "$file" || echo "⚠️  Markdown issues found - manual review needed"
    fi

    # Check for broken links (basic)
    grep -n "](.*)" "$file" | while read -r line; do
        if echo "$line" | grep -q "](http"; then
            continue  # External links - would need network check
        fi
        local link=$(echo "$line" | sed -n 's/.*](\([^)]*\)).*/\1/p')
        if [ -n "$link" ] && [ ! -f "$link" ] && [ ! -d "$link" ]; then
            echo "⚠️  Broken link found: $link"
        fi
    done
}
```

### 5. Universal Rules Validation

```bash
validate_universal_rules() {
    local file="$1"
    echo "🔍 Validating universal rules for: $file"

    # Remove trailing whitespace
    sed -i 's/[[:space:]]*$//' "$file" && echo "✅ Trailing whitespace removed"

    # Ensure file ends with newline
    if [ -s "$file" ] && [ "$(tail -c1 "$file" | wc -l)" -eq 0 ]; then
        echo >> "$file" && echo "✅ End-of-file newline added"
    fi

    # Check for private keys
    if grep -q "PRIVATE KEY" "$file"; then
        echo "❌ CRITICAL: Private key detected in $file"
    fi

    # Check file size
    local size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
    if [ "$size" -gt 1048576 ]; then
        echo "⚠️  Large file detected ($(($size/1024))KB): Consider alternatives"
    fi
}
```

## Commit Message Validation

```bash
validate_commit_message() {
    if [ -n "$(git diff --cached --name-only)" ]; then
        echo "📝 Suggested commit message format:"
        echo "   type(scope): description"
        echo ""
        echo "   Types: feat, fix, docs, style, refactor, test, chore, ci, perf"
        echo "   Example: feat(auth): add user login validation"
        echo "   Example: fix(api): resolve timeout issue in user service"
    fi
}
```

## Final Report

```bash
generate_final_report() {
    echo ""
    echo "================== PRE-COMMIT VALIDATION REPORT =================="
    echo "Files processed: $files_processed"
    echo "Auto-corrections applied: $auto_fixes_applied"
    echo "Manual review items: $manual_review_count"
    echo "Critical issues: $critical_issues"
    echo ""

    if [ "$critical_issues" -gt 0 ]; then
        echo "❌ COMMIT BLOCKED: Critical issues must be resolved"
        echo "   Review security alerts and fix before committing"
    elif [ "$manual_review_count" -gt 0 ]; then
        echo "⚠️  COMMIT CAUTION: Manual review recommended"
        echo "   Review warnings and consider fixes before committing"
    else
        echo "✅ COMMIT READY: All validations passed"
        echo "   Safe to commit with confidence"
    fi

    echo "=================================================================="
}
```

## Configuration Options

### Project-Specific Settings

Create `.precommit-config.yaml` in project root:

```yaml
# Universal pre-commit validation settings
universal_precommit:
  auto_fix: true
  security_scan: true
  coverage_threshold: 80
  exclude_patterns:
    - "*.log"
    - "build/*"
    - "dist/*"

  file_type_configs:
    python:
      line_length: 88
      type_checking: true
    markdown:
      line_length: 120
      strict_headers: true
    yaml:
      indent_spaces: 2
      line_length: 120
```

### Tool Requirements

The command automatically detects and uses available tools:

- **Required**: git
- **Recommended**: black, ruff, mypy, markdownlint, yamllint
- **Optional**: bandit, safety

## Examples

```bash
# Validate staged files before commit
/universal:quality-precommit-validate

# Validate all files with auto-fix
/universal:quality-precommit-validate all --auto-fix

# Validate specific directory
/universal:quality-precommit-validate src/

# Validate specific files
/universal:quality-precommit-validate README.md src/main.py
```

## Integration with Development Workflow

This command complements existing quality commands:

```bash
# Complete quality workflow
/universal:security-validate-env        # Ensure keys are configured
/universal:quality-format-code src/     # Format code
/universal:quality-precommit-validate   # Comprehensive validation
/universal:workflow-git-helpers pr-ready # Check PR readiness
```

---

*This command provides universal pre-commit validation that adapts to any project structure while maintaining high quality standards.*
