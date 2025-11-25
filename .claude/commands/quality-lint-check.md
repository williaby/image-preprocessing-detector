---
category: quality
complexity: low
estimated_time: "< 5 minutes"
dependencies: []
version: "1.0"
---

# Quality Lint Check

Run appropriate linter for file: $ARGUMENTS

## Instructions

Detect file type and run the corresponding linter with appropriate configuration:

### File Type Detection and Commands

**Python Files (.py)**:

```bash
# Format and lint Python code
poetry run black --check $ARGUMENTS
poetry run ruff check $ARGUMENTS
poetry run mypy $ARGUMENTS
```

**Markdown Files (.md)**:

```bash
# Lint markdown files
markdownlint $ARGUMENTS
```

**YAML Files (.yml, .yaml)**:

```bash
# Lint YAML files
yamllint $ARGUMENTS
```

**JSON Files (.json)**:

```bash
# Validate JSON syntax
python -m json.tool $ARGUMENTS > /dev/null && echo "✅ Valid JSON" || echo "❌ Invalid JSON"
```

**Multiple Files or Directories**:

- For directories: recursively check all supported file types
- For multiple files: run appropriate linter for each file type
- Provide summary of results across all files

## Validation Rules

**Markdown Requirements**:

- 120 character line length
- Consistent list styles
- Proper heading hierarchy
- No trailing whitespace

**YAML Requirements**:

- 2-space indentation
- 120 character line length
- Valid YAML syntax

**Python Requirements**:

- 88 character line length (Black)
- Comprehensive Ruff rule compliance
- Type checking with MyPy
- Security scanning compliance

## Output Format

For each file, report:

- ✅ PASS: File meets all linting requirements
- ❌ FAIL: File has linting issues (list specific issues)
- ⚠️  WARN: File has warnings but no errors

Provide actionable commands to fix any issues found.
