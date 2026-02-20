---
argument-hint: [path]
description: Format code using Ruff for Python, markdownlint for Markdown, and appropriate formatters for other languages.
allowed-tools: Bash(uv:*, ruff:*, markdownlint:*), Read
---

# Code Formatting

Auto-format code to match project standards.

## Python (Ruff)

```bash
# Format specific path
uv run ruff format path/

# Check without modifying
uv run ruff format --check path/

# Format with diff
uv run ruff format --diff path/
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
