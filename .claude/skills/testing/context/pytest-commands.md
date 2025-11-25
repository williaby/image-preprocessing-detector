# Pytest Command Reference

Quick reference for common pytest commands and configurations.

## Essential Commands

### Basic Test Execution

```bash
# Run all tests with coverage
poetry run pytest -v --cov=src --cov-report=html --cov-report=term-missing

# Fast dev cycle (skip slow tests)
poetry run pytest -m "not slow"

# Specific test categories
poetry run pytest tests/unit/          # Unit tests only
poetry run pytest tests/integration/   # Integration tests
poetry run pytest -m security          # Security tests
poetry run pytest -m perf              # Performance tests

# Run specific test
poetry run pytest tests/test_module.py::test_function_name

# Run matching pattern
poetry run pytest -k "test_user"
```

### Coverage Analysis

```bash
# Coverage with 80% minimum threshold
poetry run pytest --cov=src --cov-fail-under=80

# HTML coverage report
poetry run pytest --cov=src --cov-report=html

# Coverage with missing lines
poetry run pytest --cov=src --cov-report=term-missing

# Branch coverage
poetry run pytest --cov=src --cov-branch --cov-report=term-missing
```

### Parallel Execution

```bash
# Install pytest-xdist first
poetry add --group dev pytest-xdist

# Run tests in parallel
poetry run pytest -n auto

# Parallel with coverage
poetry run pytest -n auto --cov=src --cov-report=html
```

## Debugging and Analysis

### Test Debugging

```bash
# Drop into debugger on failure
poetry run pytest --pdb

# Stop after first failure
poetry run pytest -x

# Show print statements
poetry run pytest -s

# Show local variables on failure
poetry run pytest -l

# Detailed tracebacks
poetry run pytest --tb=long
```

### Test Discovery

```bash
# Show collected tests
poetry run pytest --collect-only

# Show available fixtures
poetry run pytest --fixtures

# Show setup/teardown
poetry run pytest --setup-show
```

### Performance Analysis

```bash
# Show slowest 10 tests
poetry run pytest --durations=10

# Show slowest tests with times
poetry run pytest --durations=0

# Profile test execution
poetry run pytest --profile
```

## Test Filtering

### By Marker

```bash
# Specific marker
poetry run pytest -m "unit"
poetry run pytest -m "integration"
poetry run pytest -m "slow"

# Exclude marker
poetry run pytest -m "not slow"

# Multiple markers
poetry run pytest -m "unit or integration"
poetry run pytest -m "unit and not slow"
```

### By Pattern

```bash
# Match test name
poetry run pytest -k "test_user"
pytest -k "not test_slow"

# Multiple patterns
poetry run pytest -k "test_user or test_admin"
```

### By Path

```bash
# Specific directory
poetry run pytest tests/unit/

# Specific file
poetry run pytest tests/test_auth.py

# Specific test
poetry run pytest tests/test_auth.py::test_login
```

## Output Formats

### Verbosity Control

```bash
# Verbose output
poetry run pytest -v

# Quiet output
poetry run pytest -q

# Very verbose (show test docstrings)
poetry run pytest -vv
```

### Reporting

```bash
# JUnit XML for CI
poetry run pytest --junitxml=reports/junit.xml

# JSON report (requires pytest-json-report)
poetry run pytest --json-report --json-report-file=report.json

# HTML report (requires pytest-html)
poetry run pytest --html=report.html --self-contained-html
```

## Test Result Caching

```bash
# Rerun only failed tests
poetry run pytest --lf  # --last-failed

# Run failed first, then all
poetry run pytest --ff  # --failed-first

# Clear cache
poetry run pytest --cache-clear
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
    poetry run pytest \
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
poetry run pytest -v --cov=src --cov-report=term-missing

# Fast dev cycle
poetry run pytest -x -v -m "not slow"

# Detailed failure analysis
poetry run pytest -vv --tb=long -l

# CI test run
poetry run pytest --cov=src --cov-fail-under=80 --junitxml=junit.xml

# Debug specific test
poetry run pytest tests/test_module.py::test_function -s --pdb

# Performance check
poetry run pytest --durations=10 -m "not slow"
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
