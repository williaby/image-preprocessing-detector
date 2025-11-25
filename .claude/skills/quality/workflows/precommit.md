---
argument-hint: [--fix]
description: Comprehensive pre-commit validation with formatting, linting, type checking, security scanning, and test execution.
allowed-tools: Bash(poetry:*, black:*, ruff:*, mypy:*, bandit:*, safety:*, pytest:*), Read
---

# Pre-commit Validation

Comprehensive validation before committing code. Runs all quality checks in sequence.

## Validation Checklist

### 1. Code Formatting (Black)
- Check: `uv run black --check src tests`
- Fix: `uv run black src tests`

### 2. Linting (Ruff)
- Check: `uv run ruff check src tests`
- Fix: `uv run ruff check --fix src tests`

### 3. Type Checking (MyPy)
- Check: `uv run mypy src`
- Report type errors with suggested fixes

### 4. Security Scanning (Bandit)
- Check: `uv run bandit -r src`
- Report security issues with severity

### 5. Dependency Security (Safety)
- Check: `uv run safety check`
- Report vulnerable packages

### 6. Test Suite
- Run: `uv run pytest -v --cov=src --cov-report=term-missing --cov-fail-under=80`
- Report failing tests and coverage gaps

### 7. Pre-commit Hooks
- Run: `uv run pre-commit run --all-files`

## Interactive Fix Mode

With `--fix` flag:
1. Auto-apply Black formatting
2. Auto-apply Ruff fixes
3. Suggest type hint additions
4. Propose security fixes
5. Suggest dependency updates

## Success Criteria

All checks pass → Ready to commit

---

*Consolidated from quality-precommit-validate command and validate-precommit skill.*
