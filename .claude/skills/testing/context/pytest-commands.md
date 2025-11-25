# Pytest Command Reference

Quick reference for common pytest commands and configurations.

## Essential Commands

### Basic Test Execution

```bash
# Run all tests with coverage
uv run pytest -v --cov=src --cov-report=html --cov-report=term-missing

# Fast dev cycle (skip slow tests)
uv run pytest -m "not slow"

# Specific test categories
uv run pytest tests/unit/          # Unit tests only
uv run pytest tests/integration/   # Integration tests
uv run pytest -m security          # Security tests
uv run pytest -m perf              # Performance tests

# Run specific test
uv run pytest tests/test_module.py::test_function_name

# Run matching pattern
uv run pytest -k "test_user"
```

### Coverage Analysis

```bash
# Coverage with 80% minimum threshold
uv run pytest --cov=src --cov-fail-under=80

# HTML coverage report
uv run pytest --cov=src --cov-report=html

# Coverage with missing lines
uv run pytest --cov=src --cov-report=term-missing

# Branch coverage
uv run pytest --cov=src --cov-branch --cov-report=term-missing
```

### Parallel Execution

```bash
# Install pytest-xdist first
uv add --dev pytest-xdist

# Run tests in parallel
uv run pytest -n auto

# Parallel with coverage
uv run pytest -n auto --cov=src --cov-report=html
```

## Debugging and Analysis

### Test Debugging

```bash
# Drop into debugger on failure
uv run pytest --pdb

# Stop after first failure
uv run pytest -x

# Show print statements
uv run pytest -s

# Show local variables on failure
uv run pytest -l

# Detailed tracebacks
uv run pytest --tb=long
```

### Test Discovery

```bash
# Show collected tests
uv run pytest --collect-only

# Show available fixtures
uv run pytest --fixtures

# Show setup/teardown
uv run pytest --setup-show
```

### Performance Analysis

```bash
# Show slowest 10 tests
uv run pytest --durations=10

# Show slowest tests with times
uv run pytest --durations=0

# Profile test execution
uv run pytest --profile
```

## Test Filtering

### By Marker

```bash
# Specific marker
uv run pytest -m "unit"
uv run pytest -m "integration"
uv run pytest -m "slow"

# Exclude marker
uv run pytest -m "not slow"

# Multiple markers
uv run pytest -m "unit or integration"
uv run pytest -m "unit and not slow"
```

### By Pattern

```bash
# Match test name
uv run pytest -k "test_user"
pytest -k "not test_slow"

# Multiple patterns
uv run pytest -k "test_user or test_admin"
```

### By Path

```bash
# Specific directory
uv run pytest tests/unit/

# Specific file
uv run pytest tests/test_auth.py

# Specific test
uv run pytest tests/test_auth.py::test_login
```

## Output Formats

### Verbosity Control

```bash
# Verbose output
uv run pytest -v

# Quiet output
uv run pytest -q

# Very verbose (show test docstrings)
uv run pytest -vv
```

### Reporting

```bash
# JUnit XML for CI
uv run pytest --junitxml=reports/junit.xml

# JSON report (requires pytest-json-report)
uv run pytest --json-report --json-report-file=report.json

# HTML report (requires pytest-html)
uv run pytest --html=report.html --self-contained-html
```

## Test Result Caching

```bash
# Rerun only failed tests
uv run pytest --lf  # --last-failed

# Run failed first, then all
uv run pytest --ff  # --failed-first

# Clear cache
uv run pytest --cache-clear
```

## Configuration Files

### pyproject.toml Configuration

```toml
[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow tests",
    "security: Security tests",
    "perf: Performance tests",
]
filterwarnings = [
    "error",
    "ignore::UserWarning",
    "ignore::DeprecationWarning",
]
```

### Coverage Configuration

```toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
show_missing = true

[tool.coverage.html]
directory = "htmlcov"
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    uv run pytest \
      --cov=src \
      --cov-report=xml \
      --cov-report=term-missing \
      --junitxml=reports/junit.xml \
      --cov-fail-under=80

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
    fail_ci_if_error: true
```

## Useful Options

### Common Option Combinations

```bash
# Standard test run
uv run pytest -v --cov=src --cov-report=term-missing

# Fast dev cycle
uv run pytest -x -v -m "not slow"

# Detailed failure analysis
uv run pytest -vv --tb=long -l

# CI test run
uv run pytest --cov=src --cov-fail-under=80 --junitxml=junit.xml

# Debug specific test
uv run pytest tests/test_module.py::test_function -s --pdb

# Performance check
uv run pytest --durations=10 -m "not slow"
```

## Test Cleanup

```bash
# Clean test artifacts
rm -rf htmlcov/
rm -rf .pytest_cache/
rm -rf .coverage
rm -rf reports/

# Clean compiled Python
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

---

*For detailed pytest patterns and best practices, see pytest-patterns.md*
