---
argument-hint: [path]
description: Lint code using Ruff for Python with auto-fix capabilities.
allowed-tools: Bash(poetry:*, ruff:*), Read
---

# Code Linting

Lint code and apply automatic fixes.

## Python (Ruff)

```bash
# Check and auto-fix
poetry run ruff check --fix path/

# Check only
poetry run ruff check path/

# Show violations
poetry run ruff check --output-format=full path/
```

## Auto-fixable Issues

Ruff can automatically fix:
- Unused imports
- Import sorting
- Line length issues
- Trailing whitespace
- Many PEP 8 violations

## Manual Review Required

- Type errors → Use MyPy
- Complex refactoring
- Security issues → Use Bandit

---

*Extracted from quality-lint-check command.*
