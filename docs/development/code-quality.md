---
schema_type: common
title: "Code Quality Standards"
description: "Code quality standards, tools, and enforcement"
tags: [code_quality, development, documentation]
status: published
owner: "quality-team"
authors:
  - name: "Byron Williams"
purpose: "Document code quality standards, tools, and enforcement mechanisms."
---

Code quality standards and tooling for the Image Preprocessing Detector project.

## Quality Standards

**Goal**: Maintain high code quality through automated tools and best practices

**Requirements**:
1. ✅ Black formatting (88 characters)
2. ✅ Ruff linting (no errors)
3. ✅ MyPy type checking (strict on src/)
4. ✅ 80%+ test coverage
5. ✅ 100% docstring coverage
6. ✅ Security scanning (Bandit, Safety)

## Code Formatting

### Black

**Standard**: 88-character line length

**Configuration**:
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ["py312"]
```

**Usage**:
```bash
# Format all code
poetry run black src tests

# Check without modifying
poetry run black --check src tests

# Format specific file
poetry run black src/image_preprocessing_detector/schema.py
```

**Pre-commit Hook**:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 25.9.0
    hooks:
      - id: black
```

## Linting

### Ruff

**Purpose**: Fast Python linter (replaces flake8, isort, etc.)

**Configuration**:
```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py312"
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "ARG",  # flake8-unused-arguments
    "SIM",  # flake8-simplify
]
ignore = [
    "E501",  # line too long (handled by black)
]
```

**Usage**:
```bash
# Lint all code
poetry run ruff check src tests

# Auto-fix issues
poetry run ruff check --fix src tests

# Lint specific file
poetry run ruff check src/image_preprocessing_detector/schema.py
```

**Pre-commit Hook**:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.0.280
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
```

## Type Checking

### MyPy

**Standard**: Strict type checking on src/, relaxed on tests/

**Configuration**:
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
strict_equality = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

**Usage**:
```bash
# Type check source code
poetry run mypy src

# Check specific file
poetry run mypy src/image_preprocessing_detector/schema.py

# Verbose output
poetry run mypy --show-error-codes src
```

**Pre-commit Hook**:
```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.4.0
    hooks:
      - id: mypy
        args: [--strict, src/]
```

## Docstring Standards

### Pydocstyle

**Standard**: Google-style docstrings

**Configuration**:
```toml
# pyproject.toml
[tool.pydocstyle]
convention = "google"
match = "(?!(test_)).*\\.py"
add-ignore = ["D105", "D107"]  # Ignore magic methods
```

**Usage**:
```bash
# Check docstrings
poetry run pydocstyle src/

# Check specific file
poetry run pydocstyle src/image_preprocessing_detector/schema.py
```

**Example Google-style docstring**:
```python
def detect_blur(image: np.ndarray, threshold: float = 100.0) -> tuple[bool, float]:
    """Detect blur in an image using Laplacian variance.

    Args:
        image: Input image as numpy array (H, W, 3).
        threshold: Laplacian variance threshold (default: 100.0).
            Lower values indicate blurrier images.

    Returns:
        Tuple of (is_blurry, variance) where is_blurry is True if
        variance < threshold.

    Raises:
        ValueError: If image is not 3-channel.

    Example:
        >>> import numpy as np
        >>> image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        >>> is_blurry, var = detect_blur(image)
        >>> print(f"Blurry: {is_blurry}, Variance: {var:.2f}")
    """
    # Implementation...
```

### Interrogate

**Standard**: 85%+ docstring coverage

**Configuration**:
```toml
# pyproject.toml
[tool.interrogate]
verbose = 1
fail-under = 85
exclude = ["tests", "docs", "build", "dist", "validation"]
ignore-init-method = true
ignore-init-module = true
color = true
```

**Usage**:
```bash
# Check docstring coverage
poetry run interrogate src/

# Verbose output with details
poetry run interrogate -v src/

# Generate badge
poetry run interrogate --generate-badge docs/
```

**Current Coverage**: 100% ✅

## Security Scanning

### Bandit

**Purpose**: Find common security issues in Python code

**Configuration**:
```toml
# pyproject.toml
[tool.bandit]
exclude_dirs = ["tests", "validation"]
skips = ["B101"]  # Skip assert_used (OK in tests)
```

**Usage**:
```bash
# Scan source code
poetry run bandit -r src/

# Generate report
poetry run bandit -r src/ -f json -o bandit-report.json

# Scan specific file
poetry run bandit src/image_preprocessing_detector/schema.py
```

**Pre-commit Hook**:
```yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, src/]
```

### Safety

**Purpose**: Check for known security vulnerabilities in dependencies

**Usage**:
```bash
# Check dependencies
poetry run safety check

# Check with detailed output
poetry run safety check --full-report

# Generate JSON report
poetry run safety check --json
```

**CI Integration**:
```yaml
# .github/workflows/security.yml
- name: Run Safety check
  run: poetry run safety check
```

## Pre-commit Hooks

### Setup

```bash
# Install pre-commit
poetry install

# Install git hooks
poetry run pre-commit install

# Run manually on all files
poetry run pre-commit run --all-files
```

### Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 25.9.0
    hooks:
      - id: black

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.0.280
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.4.0
    hooks:
      - id: mypy
        args: [src/]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: [-r, src/]
```

### Skipping Hooks

```bash
# Skip all hooks
git commit --no-verify

# Skip specific hook
SKIP=mypy git commit -m "message"
```

## CI/CD Quality Gates

### GitHub Actions

All quality checks run on every PR:

```yaml
# .github/workflows/ci.yml
jobs:
  quality-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: poetry install
      - name: Black
        run: poetry run black --check src tests
      - name: Ruff
        run: poetry run ruff check src tests
      - name: MyPy
        run: poetry run mypy src
      - name: Bandit
        run: poetry run bandit -r src/
```

### Required Checks

All must pass before merge:
1. ✅ Black formatting
2. ✅ Ruff linting
3. ✅ MyPy type checking
4. ✅ Bandit security scan
5. ✅ Pytest (80%+ coverage)

## Code Review Checklist

### For Authors

Before requesting review:
- [ ] All tests pass locally
- [ ] Coverage ≥ 80%
- [ ] Pre-commit hooks pass
- [ ] Code formatted with Black
- [ ] Type hints added
- [ ] Docstrings complete (Google style)
- [ ] Security scan passes
- [ ] No TODO comments (convert to issues)

### For Reviewers

Review checklist:
- [ ] Code follows project standards
- [ ] Tests are comprehensive
- [ ] Docstrings are clear and complete
- [ ] No security issues
- [ ] Performance considerations addressed
- [ ] Error handling appropriate
- [ ] Type hints accurate

## Best Practices

### 1. Type Hints

**Always use type hints**:
```python
# Good
def detect_blur(image: np.ndarray, threshold: float = 100.0) -> tuple[bool, float]:
    pass

# Bad
def detect_blur(image, threshold=100.0):
    pass
```

### 2. Docstrings

**Document all public functions**:
```python
# Good
def detect_skew(image: np.ndarray) -> tuple[float, float]:
    """Detect skew angle using Hough transform.

    Args:
        image: Input image.

    Returns:
        Tuple of (angle, confidence).
    """
    pass

# Bad
def detect_skew(image):
    pass  # No docstring
```

### 3. Imports

**Organize imports**:
```python
# Standard library
import os
from pathlib import Path

# Third-party
import numpy as np
from PIL import Image

# Local
from image_preprocessing_detector.schema import DetectedIssue
```

### 4. Error Handling

**Use specific exceptions**:
```python
# Good
if not image_path.exists():
    raise FileNotFoundError(f"Image not found: {image_path}")

# Bad
if not image_path.exists():
    raise Exception("File not found")
```

### 5. Constants

**Use UPPER_CASE for constants**:
```python
# Good
DEFAULT_DPI = 300
BLUR_THRESHOLD = 100.0

# Bad
defaultDpi = 300
blur_threshold = 100.0
```

## Tools Summary

| Tool | Purpose | Command |
|------|---------|---------|
| **Black** | Formatting | `poetry run black src tests` |
| **Ruff** | Linting | `poetry run ruff check --fix src tests` |
| **MyPy** | Type checking | `poetry run mypy src` |
| **Pydocstyle** | Docstring style | `poetry run pydocstyle src` |
| **Interrogate** | Docstring coverage | `poetry run interrogate src` |
| **Bandit** | Security scan | `poetry run bandit -r src` |
| **Safety** | Dependency scan | `poetry run safety check` |
| **Pytest** | Testing | `poetry run pytest` |
| **Pre-commit** | Git hooks | `poetry run pre-commit run --all-files` |

## Troubleshooting

### Black and Ruff Conflicts

If Black and Ruff disagree, Black takes precedence:
```bash
# Run Black first
poetry run black src tests

# Then Ruff
poetry run ruff check --fix src tests
```

### MyPy Import Errors

Install type stubs:
```bash
poetry add --group dev types-Pillow
poetry add --group dev types-requests
```

### Pre-commit Hook Failures

Update hooks:
```bash
poetry run pre-commit autoupdate
poetry run pre-commit run --all-files
```

## See Also

- [Testing Guide](testing.md) - Testing standards
- [Contributing Guide](contributing.md) - Development workflow
- [Architecture](architecture.md) - System design
