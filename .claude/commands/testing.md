---
category: testing
complexity: medium
estimated_time: "5-15 minutes"
dependencies: ["pytest", "coverage"]
version: "1.0"
---

# Testing Commands

Comprehensive testing commands for running tests, generating coverage reports, and managing test environments.

## Quick Reference

```bash
# Run all tests with coverage
poetry run pytest -v --cov=src --cov-report=html --cov-report=term-missing

# Run specific test categories
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest -m "not slow"

# Generate detailed coverage report
poetry run pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=80
```

## Test Execution

### Basic Test Running

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_module.py

# Run specific test function
poetry run pytest tests/test_module.py::test_function_name

# Run specific test class
poetry run pytest tests/test_module.py::TestClassName

# Run tests matching pattern
poetry run pytest -k "test_user"
```

### Test Categories and Markers

```bash
# Run only unit tests
poetry run pytest tests/unit/

# Run only integration tests
poetry run pytest tests/integration/

# Run tests by marker
poetry run pytest -m "unit"
poetry run pytest -m "integration"
poetry run pytest -m "slow"
poetry run pytest -m "not slow"

# Run multiple markers
poetry run pytest -m "unit or integration"
poetry run pytest -m "unit and not slow"
```

### Parallel Test Execution

```bash
# Install pytest-xdist for parallel execution
poetry add --group dev pytest-xdist

# Run tests in parallel
poetry run pytest -n auto
poetry run pytest -n 4  # Use 4 workers

# Run tests in parallel with coverage
poetry run pytest -n auto --cov=src --cov-report=html
```

## Coverage Analysis

### Coverage Reports

```bash
# Basic coverage
poetry run pytest --cov=src

# Coverage with missing lines
poetry run pytest --cov=src --cov-report=term-missing

# HTML coverage report
poetry run pytest --cov=src --cov-report=html

# XML coverage report (for CI)
poetry run pytest --cov=src --cov-report=xml

# Multiple report formats
poetry run pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml
```

### Coverage Thresholds

```bash
# Fail if coverage below threshold
poetry run pytest --cov=src --cov-fail-under=80

# Branch coverage (more comprehensive)
poetry run pytest --cov=src --cov-branch --cov-report=term-missing

# Coverage for specific modules
poetry run pytest --cov=src.module --cov-report=term-missing
```

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "*/tests/*",
    "*/venv/*",
    "*/__pycache__/*",
    "*/migrations/*",
    "*/settings/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "@abstract",
]
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"
```

## Test Discovery and Organization

### Test Structure

```bash
# Standard test directory structure
tests/
├── unit/                 # Fast, isolated unit tests
├── integration/          # Tests with external dependencies
├── e2e/                 # End-to-end tests
├── fixtures/            # Test data and fixtures
├── conftest.py          # Shared pytest configuration
└── __init__.py
```

### Test Discovery

```bash
# Show collected tests without running
poetry run pytest --collect-only

# Show test discovery pattern
poetry run pytest --collect-only -q

# Collect tests from specific directory
poetry run pytest tests/unit/ --collect-only
```

## Test Output and Reporting

### Output Formats

```bash
# Detailed output
poetry run pytest -v

# Short output
poetry run pytest -q

# No output capture (see print statements)
poetry run pytest -s

# Show local variables on failure
poetry run pytest -l

# Show full diff on assertion failures
poetry run pytest --tb=long
```

### JUnit XML Reports

```bash
# Generate JUnit XML for CI
poetry run pytest --junitxml=reports/junit.xml

# Include properties in XML
poetry run pytest --junitxml=reports/junit.xml --junitxml-properties

# Custom XML report location
poetry run pytest --junitxml=test-results/results.xml
```

### Test Result Caching

```bash
# Run only failed tests from last run
poetry run pytest --lf  # last-failed

# Run failed tests first, then all others
poetry run pytest --ff  # failed-first

# Clear pytest cache
poetry run pytest --cache-clear
```

## Advanced Testing Features

### Test Fixtures and Data

```bash
# Show available fixtures
poetry run pytest --fixtures

# Show fixture usage
poetry run pytest --fixtures-per-test

# Run with specific fixture scope
poetry run pytest --setup-show
```

### Debugging Tests

```bash
# Drop into debugger on failure
poetry run pytest --pdb

# Drop into debugger on first failure
poetry run pytest -x --pdb

# Use ipdb instead of pdb
poetry add --group dev ipdb
poetry run pytest --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb
```

### Performance Testing

```bash
# Install pytest-benchmark
poetry add --group dev pytest-benchmark

# Run benchmark tests
poetry run pytest --benchmark-only

# Skip benchmark tests
poetry run pytest --benchmark-skip

# Save benchmark results
poetry run pytest --benchmark-save=baseline
poetry run pytest --benchmark-compare=baseline
```

## Continuous Integration

### GitHub Actions Integration

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

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
    fail_ci_if_error: true
```

### Test Matrix

```yaml
strategy:
  matrix:
    python-version: [3.9, 3.10, 3.11]

steps:
  - name: Run tests
    run: poetry run pytest -v --cov=src
```

## Test Environment Management

### Environment Variables

```bash
# Set test environment
export TESTING=true
poetry run pytest

# Use pytest-env plugin
poetry add --group dev pytest-env

# Configure in pyproject.toml
[tool.pytest_env]
TESTING = "true"
DATABASE_URL = "sqlite:///:memory:"
```

### Test Database Setup

```bash
# Run tests with test database
export DATABASE_URL="postgresql://test:test@localhost/test_db"
poetry run pytest

# Use different settings for tests
export DJANGO_SETTINGS_MODULE="myapp.settings.test"
poetry run pytest
```

## Specialized Testing

### Mutation Testing

```bash
# Install mutmut for mutation testing
poetry add --group dev mutmut

# Run mutation testing
poetry run mutmut run
poetry run mutmut results
poetry run mutmut html
```

### Property-Based Testing

```bash
# Install hypothesis
poetry add --group dev hypothesis

# Run property-based tests
poetry run pytest tests/property/

# Generate hypothesis examples
poetry run pytest --hypothesis-show-statistics
```

### Load Testing

```bash
# Install locust for load testing
poetry add --group dev locust

# Run load tests
poetry run locust -f tests/load/locustfile.py
```

## Test Cleanup and Maintenance

### Test Data Cleanup

```bash
# Clean test artifacts
rm -rf htmlcov/
rm -rf .pytest_cache/
rm -rf .coverage
rm -rf reports/

# Clean temporary test files
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

### Test Quality Checks

```bash
# Check test coverage quality
poetry run pytest --cov=src --cov-report=term-missing | grep -E "TOTAL.*[0-9]+%"

# Find slow tests
poetry run pytest --durations=10

# Profile test execution
poetry run pytest --profile
```

## pytest Configuration

### pyproject.toml Configuration

```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "-ra",
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-fail-under=80",
]
testpaths = ["tests"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests",
    "external: Tests requiring external services",
]
filterwarnings = [
    "error",
    "ignore::UserWarning",
    "ignore::DeprecationWarning",
]
```

### Custom Markers

```python
# tests/conftest.py
import pytest

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
```

## Testing Best Practices

### Test Naming Conventions

```python
def test_should_return_true_when_user_is_valid():
    """Test should follow naming convention: test_should_[expected]_when_[condition]."""
    pass

def test_user_creation_with_valid_email():
    """Alternative naming: test_[action]_with_[condition]."""
    pass
```

### Test Organization

```python
class TestUserAuthentication:
    """Group related tests in classes."""

    def test_should_authenticate_with_valid_credentials(self):
        pass

    def test_should_reject_invalid_credentials(self):
        pass
```

---

*This file contains comprehensive testing commands and configurations. For testing standards and requirements, see `/standards/python.md`.*
