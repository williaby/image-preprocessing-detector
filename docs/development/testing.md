---
schema_type: common
title: "Testing Guide"
description: "Testing strategy, guidelines, and best practices"
tags: [testing, development, documentation, quality]
status: published
owner: "quality-team"
authors:
  - name: "Byron Williams"
purpose: "Document the testing strategy, test organization, and testing best practices."
---

Comprehensive testing guide for the Image Preprocessing Detector project.

## Testing Philosophy

**Goal**: Maintain 80%+ code coverage with high-quality, maintainable tests

**Principles**:
1. **Test behavior, not implementation**
2. **Fast feedback loop** (< 30 seconds for unit tests)
3. **Clear test names** (describe what is being tested)
4. **Isolated tests** (no dependencies between tests)
5. **Automated execution** (CI/CD integration)

## Test Levels

### 1. Unit Tests

**Purpose**: Test individual functions and methods

**Characteristics**:
- Fast (< 1ms per test)
- Isolated (no I/O, no network)
- Focused (single function/method)
- Deterministic (same input → same output)

**Example**:
```python
# tests/unit/test_schema.py
from image_preprocessing_detector.schema import DetectedIssue

def test_detected_issue_validation():
    """Test DetectedIssue validates severity values."""
    issue = DetectedIssue(
        issue_type="blur",
        severity="high",
        confidence=0.92,
    )
    assert issue.severity == "high"
    assert issue.confidence == 0.92
```

**Coverage Target**: 90%+

### 2. Integration Tests

**Purpose**: Test module interactions

**Characteristics**:
- Slower (10-100ms per test)
- Multiple components
- File I/O allowed
- May use test fixtures

**Example**:
```python
# tests/integration/test_pipeline.py
from image_preprocessing_detector.ingestion import load_and_normalize_image
from image_preprocessing_detector.detection import detect_blur

def test_blur_detection_pipeline():
    """Test blur detection on normalized image."""
    image = load_and_normalize_image("tests/fixtures/blurry.jpg")
    is_blurry, variance = detect_blur(image)
    assert is_blurry is True
    assert variance < 100
```

**Coverage Target**: 80%+

### 3. End-to-End Tests

**Purpose**: Test complete workflows

**Characteristics**:
- Slow (1-10s per test)
- Full pipeline
- Real files
- CLI invocation

**Example**:
```python
# tests/e2e/test_cli.py
import subprocess

def test_cli_process_pdf():
    """Test CLI processes PDF successfully."""
    result = subprocess.run([
        "poetry", "run", "imgprep", "process",
        "tests/fixtures/sample.pdf",
        "--output", "result.json",
    ], capture_output=True)

    assert result.returncode == 0
    assert Path("result.json").exists()
```

**Coverage Target**: Critical paths

## Test Organization

### Directory Structure

```
tests/
├── unit/
│   ├── test_schema.py           # Schema validation
│   ├── test_detection.py         # Detection algorithms
│   └── test_correction.py        # Correction operations
├── integration/
│   ├── test_pipeline.py          # Module interactions
│   └── test_io.py                # File I/O operations
├── e2e/
│   └── test_cli.py               # CLI workflows
├── fixtures/
│   ├── sample.pdf                # Test data
│   ├── blurry.jpg
│   └── skewed.png
└── conftest.py                   # Pytest configuration
```

### Test Markers

```python
import pytest

# Unit test
@pytest.mark.unit
def test_function():
    pass

# Integration test
@pytest.mark.integration
def test_integration():
    pass

# Slow test
@pytest.mark.slow
def test_expensive_operation():
    pass
```

**Run specific markers**:
```bash
# Unit tests only
poetry run pytest -m unit

# Exclude slow tests
poetry run pytest -m "not slow"

# Integration tests
poetry run pytest -m integration
```

## Running Tests

### Basic Execution

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific file
poetry run pytest tests/unit/test_schema.py

# Run specific test
poetry run pytest tests/unit/test_schema.py::test_detected_issue_validation

# Verbose output
poetry run pytest -v

# Stop on first failure
poetry run pytest -x
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
poetry run pytest -n auto

# Use 4 workers
poetry run pytest -n 4
```

### Watch Mode

```bash
# Re-run on file changes (requires pytest-watch)
poetry run ptw
```

## Coverage Requirements

### Minimum Coverage

**Enforced**: 80% via `--cov-fail-under=80`

**Current**: 94%+

**Target**: 90%+ for all modules

### Coverage Reports

```bash
# Generate HTML report
poetry run pytest --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html

# Terminal report
poetry run pytest --cov=src --cov-report=term-missing
```

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "*/tests/*",
    "validation/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Writing Good Tests

### 1. Clear Test Names

**Good**:
```python
def test_detect_blur_returns_true_for_blurry_image():
    pass

def test_apply_deskew_rejects_excessive_angle():
    pass
```

**Bad**:
```python
def test_blur():
    pass

def test_deskew_1():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_contrast_enhancement():
    # Arrange: Setup test data
    image = create_low_contrast_image()

    # Act: Execute function
    corrected, info = apply_contrast_enhancement(image)

    # Assert: Verify results
    assert info["success"] is True
    assert corrected.mean() != image.mean()
```

### 3. Use Fixtures

```python
# conftest.py
import pytest
import numpy as np

@pytest.fixture
def sample_image():
    """Create sample image for testing."""
    return np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

# test_detection.py
def test_detect_blur(sample_image):
    """Test blur detection on sample image."""
    is_blurry, variance = detect_blur(sample_image)
    assert isinstance(is_blurry, bool)
```

### 4. Test Edge Cases

```python
def test_deskew_handles_zero_angle():
    """Test deskew with zero angle returns original."""
    corrected, info = apply_deskew(image, angle=0.0)
    assert np.array_equal(corrected, image)

def test_deskew_rejects_excessive_angle():
    """Test deskew rejects angle > 45 degrees."""
    corrected, info = apply_deskew(image, angle=90.0)
    assert info["success"] is False
```

### 5. Use Parameterization

```python
@pytest.mark.parametrize("angle,expected", [
    (0.0, False),    # No skew
    (0.5, True),     # Minimal skew
    (2.0, True),     # Moderate skew
    (45.0, False),   # Excessive skew (rejected)
])
def test_deskew_angles(angle, expected):
    """Test deskew handles various angles."""
    corrected, info = apply_deskew(image, angle)
    assert info["success"] == expected
```

## Test Data Management

### Fixtures Directory

```
tests/fixtures/
├── sample.pdf          # Multi-page PDF
├── blurry.jpg          # Blurry image
├── skewed.png          # Skewed image
├── low_contrast.tiff   # Low contrast image
└── expected/
    └── sample_page1.json  # Expected output
```

### Generating Test Data

```python
# tests/utils/generate_test_data.py
import numpy as np
from PIL import Image

def create_blurry_image(size=(300, 300), blur_kernel=15):
    """Generate blurry test image."""
    image = np.random.randint(0, 256, size + (3,), dtype=np.uint8)
    # Apply blur...
    return image
```

### Version Control

- ✅ **Do commit**: Small test fixtures (< 1MB)
- ❌ **Don't commit**: Large test data (> 1MB)
- ✅ **Do use**: Git LFS for large files
- ✅ **Do document**: Test data generation scripts

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: poetry install
      - run: poetry run pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run manually
poetry run pre-commit run --all-files
```

### Quality Gates

All must pass before merge:
1. ✅ All tests pass
2. ✅ Coverage ≥ 80%
3. ✅ No linting errors
4. ✅ Type checking passes
5. ✅ Security scans pass

## Performance Testing

### Benchmarking

```python
import time

def test_blur_detection_performance(sample_image):
    """Test blur detection completes within 100ms."""
    start = time.time()
    detect_blur(sample_image)
    elapsed = time.time() - start

    assert elapsed < 0.1  # 100ms
```

### Profiling

```bash
# Profile tests
poetry run pytest --profile

# Generate profile report
poetry run pytest --profile-svg
```

## Mocking and Stubbing

### Mocking External Dependencies

```python
from unittest.mock import patch, MagicMock

def test_pdf_loading_with_mock():
    """Test PDF loading with mocked PyMuPDF."""
    with patch('fitz.open') as mock_open:
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 5
        mock_open.return_value = mock_doc

        pages = load_pdf_pages("test.pdf")
        assert len(pages) == 5
```

### Using pytest-mock

```python
def test_with_pytest_mock(mocker):
    """Test using pytest-mock plugin."""
    mock_load = mocker.patch('image_preprocessing_detector.ingestion.load_image')
    mock_load.return_value = np.zeros((100, 100, 3))

    result = process_image("test.jpg")
    assert mock_load.called
```

## Troubleshooting

### Tests Failing Locally

```bash
# Clear pytest cache
rm -rf .pytest_cache

# Clear coverage data
rm -rf .coverage htmlcov/

# Reinstall dependencies
poetry install

# Run with verbose output
poetry run pytest -vv
```

### Coverage Not Meeting Threshold

```bash
# Check uncovered lines
poetry run pytest --cov=src --cov-report=term-missing

# Generate HTML report for detailed view
poetry run pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Slow Tests

```bash
# Profile slow tests
poetry run pytest --durations=10

# Skip slow tests
poetry run pytest -m "not slow"
```

## Best Practices Summary

1. ✅ **Write tests first** (TDD when appropriate)
2. ✅ **Test behavior, not implementation**
3. ✅ **Keep tests simple and focused**
4. ✅ **Use descriptive names**
5. ✅ **Maintain fast feedback loop**
6. ✅ **Aim for 90%+ coverage**
7. ✅ **Run tests before committing**
8. ✅ **Fix failing tests immediately**
9. ✅ **Review test code like production code**
10. ✅ **Keep test data small and versioned**

## See Also

- [Code Quality Guide](code-quality.md) - Quality standards
- [Contributing Guide](contributing.md) - Development workflow
- [CI/CD Documentation](../../.github/workflows/ci.yml) - CI configuration
