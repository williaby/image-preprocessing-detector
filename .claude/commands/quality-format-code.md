---
category: quality
complexity: low
estimated_time: "< 5 minutes"
dependencies: []
version: "1.0"
---

# Quality Format Code

Format code files according to project standards: $ARGUMENTS

## Instructions

Format code files based on their type and apply consistent styling:

### Python Code Formatting

```bash
# Format Python files with Black (88 char line length)
poetry run black $ARGUMENTS

# Auto-fix linting issues where possible
poetry run ruff check --fix $ARGUMENTS

# Verify formatting is correct
poetry run black --check $ARGUMENTS
poetry run ruff check $ARGUMENTS
```

### Markdown Formatting

```bash
# Format markdown files (if markdownlint has --fix capability)
markdownlint --fix $ARGUMENTS 2>/dev/null || markdownlint $ARGUMENTS

# Manual formatting guidelines for markdown:
# - Use 120 character line length
# - Use consistent list styles (- for unordered, 1. for ordered)
# - Proper heading hierarchy (no skipping levels)
# - One blank line between sections
```

### YAML Formatting

```bash
# Check YAML formatting
yamllint $ARGUMENTS

# Manual formatting guidelines for YAML:
# - Use 2-space indentation consistently
# - No trailing whitespace
# - 120 character line length
# - Consistent quote style
```

### JSON Formatting

```bash
# Format JSON files with proper indentation
python -c "
import json
import sys
for file in sys.argv[1:]:
    try:
        with open(file, 'r') as f:
            data = json.load(f)
        with open(file, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)
        print(f'✅ Formatted: {file}')
    except Exception as e:
        print(f'❌ Error formatting {file}: {e}')
" $ARGUMENTS
```

### Multi-File Formatting

When processing directories or multiple files:

1. Detect each file type automatically
2. Apply appropriate formatter for each type
3. Report which files were formatted
4. Report any files that couldn't be formatted

## Formatting Standards

**Python**:

- Line length: 88 characters (Black standard)
- Use double quotes for strings
- Trailing commas in multi-line structures
- Import sorting per Ruff rules

**Markdown**:

- Line length: 120 characters
- ATX-style headers (# ## ###)
- Consistent list markers
- Code blocks with language specification

**YAML**:

- 2-space indentation
- No tabs
- Quoted strings when necessary
- Consistent structure

**JSON**:

- 2-space indentation
- Sorted keys
- No trailing commas
- Proper escaping

## Post-Formatting Validation

After formatting, automatically run appropriate linters to verify:

```bash
# Verify Python formatting
poetry run black --check $ARGUMENTS
poetry run ruff check $ARGUMENTS

# Verify Markdown formatting
markdownlint $ARGUMENTS

# Verify YAML formatting
yamllint $ARGUMENTS
```

Report any remaining issues that require manual attention.
