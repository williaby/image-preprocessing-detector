---
argument-hint: [--fix]
description: Comprehensive pre-commit validation with formatting, linting, type checking, security scanning, and test execution.
allowed-tools: Bash(poetry:*, black:*, ruff:*, mypy:*, bandit:*, safety:*, pytest:*), Read
---

# Pre-commit Validation

Comprehensive validation before committing code. Runs all quality checks in sequence.

## Validation Checklist

### 1. Code Formatting (Black)
- Check: `poetry run black --check src tests`
- Fix: `poetry run black src tests`

### 2. Linting (Ruff)
- Check: `poetry run ruff check src tests`
- Fix: `poetry run ruff check --fix src tests`

### 3. Type Checking (MyPy)
- Check: `poetry run mypy src`
- Report type errors with suggested fixes

### 4. Security Scanning (Bandit)
- Check: `poetry run bandit -r src`
- Report security issues with severity

### 5. Dependency Security (Safety)
- Check: `poetry run safety check`
- Report vulnerable packages

### 6. Test Suite
- Run: `poetry run pytest -v --cov=src --cov-report=term-missing --cov-fail-under=80`
- Report failing tests and coverage gaps

### 7. Pre-commit Hooks
- Run: `poetry run pre-commit run --all-files`

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
