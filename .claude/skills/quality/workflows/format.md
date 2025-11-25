---
argument-hint: [path]
description: Format code using Black for Python, markdownlint for Markdown, and appropriate formatters for other languages.
allowed-tools: Bash(poetry:*, black:*, markdownlint:*), Read
---

# Code Formatting

Auto-format code to match project standards.

## Python (Black)

```bash
# Format specific path
poetry run black path/

# Check without modifying
poetry run black --check path/

# Format with diff
poetry run black --diff path/
```

**Standards**: 88-character line length

## Markdown (markdownlint)

```bash
# Format with auto-fix
markdownlint --fix *.md

# Check only
markdownlint *.md
```

**Standards**: 120-character line length

## YAML (yamllint)

```bash
# Check formatting
yamllint file.yml

# Auto-fix (limited)
yamllint --format parsable file.yml
```

**Standards**: 2-space indentation, 120-character line length

---

*Extracted from quality-format-code command.*
