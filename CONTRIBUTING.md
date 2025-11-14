# Contributing to Image Preprocessing Detector

Thank you for your interest in contributing to the Image Preprocessing Detector! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Quality Standards](#code-quality-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Convention](#commit-convention)
- [Pull Request Process](#pull-request-process)
- [Security](#security)

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to byronawilliams@gmail.com.

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Poetry 1.7+ for dependency management
- Git with GPG signing configured
- (Optional) GPU with CUDA for ML model development (Phase 2+)

### Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/williaby/image-preprocessing-detector.git
cd image-preprocessing-detector

# Install dependencies with Poetry
poetry install --with dev

# Setup pre-commit hooks (REQUIRED)
poetry run pre-commit install

# Verify installation
poetry run pytest -v
poetry run black --check src tests
poetry run ruff check src tests
poetry run mypy src
```

### Project Structure

```
image_detection/
├── src/image_preprocessing_detector/  # Main package
│   ├── ingestion/                     # PDF/image loading
│   ├── detection/                     # IQA and layout detection
│   ├── correction/                    # Image corrections
│   ├── output/                        # JSON generation
│   └── utils/                         # Logging and utilities
├── tests/                             # Test suite
│   ├── unit/                          # Unit tests
│   └── integration/                   # Integration tests
├── docs/                              # Documentation
├── scripts/                           # Training and evaluation scripts
└── configs/                           # Model configurations
```

## Development Workflow

### 1. Create a Feature Branch

```bash
# Create and checkout a new branch
git checkout -b feature/your-feature-name

# For bug fixes
git checkout -b fix/issue-description

# For documentation
git checkout -b docs/documentation-update
```

### Branch Naming Convention

- `feature/` - New features or enhancements
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or improvements
- `chore/` - Maintenance tasks

### 2. Make Your Changes

- Write clean, readable code following [PEP 8](https://peps.python.org/pep-0008/)
- Add type hints to all functions and methods
- Update documentation for API changes
- Add tests for new functionality
- Ensure all tests pass locally

### 3. Run Quality Checks

Before committing, ensure all quality checks pass:

```bash
# Format code
poetry run black src tests

# Lint code
poetry run ruff check --fix src tests

# Type checking
poetry run mypy src

# Run tests with coverage
poetry run pytest --cov=src --cov-report=term-missing

# Run all pre-commit hooks manually
poetry run pre-commit run --all-files
```

## Code Quality Standards

All contributions MUST meet these requirements:

### Formatting

- **Tool**: Black (88 character line length)
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Sorted with isort (integrated into Black)
- **Quotes**: Double quotes for strings
- **Verification**: `poetry run black src tests`

### Linting

- **Tool**: Ruff with project configuration
- **Rules**: Comprehensive rule set (see `pyproject.toml`)
- **Auto-fix**: `poetry run ruff check --fix src tests`
- **Verification**: `poetry run ruff check src tests`

### Type Checking

- **Tool**: MyPy strict mode for `src/`
- **Coverage**: All public functions must have type hints
- **Verification**: `poetry run mypy src`

### Security

- **Tool**: Bandit security scanner
- **Scope**: All production code in `src/`
- **Verification**: `poetry run bandit -r src`

### Pre-Commit Hooks

Run before EVERY commit (automatically enforced):

```bash
poetry run pre-commit run --all-files
```

See `pyproject.toml` for complete configuration.

### Type Hints

All functions must include type hints:

```python
from pathlib import Path
from typing import Optional

def process_image(
    image_path: Path,
    output_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Process an image and return metadata.

    Args:
        image_path: Path to the input image
        output_dir: Optional output directory for processed files

    Returns:
        Dictionary containing image metadata and quality scores

    Raises:
        FileNotFoundError: If image_path does not exist
        ValueError: If image format is not supported
    """
    pass
```

### Documentation

- **Docstrings**: Use Google-style docstrings for all public APIs
- **Comments**: Explain *why*, not *what* (code should be self-documenting)
- **README Updates**: Update README.md for significant feature additions
- **Architecture Docs**: Update ARCHITECTURE_SUMMARY.md for architectural changes

### Security

- **No Hardcoded Secrets**: Use environment variables or secure vaults
- **Input Validation**: Validate all user inputs and file paths
- **Path Sanitization**: Use `pathlib.Path.resolve()` to prevent directory traversal
- **Dependency Security**: Run `poetry run safety check` before submitting PRs

## Testing Requirements

### Testing Policy

All new functionality MUST include corresponding tests:

- **Unit tests**: Required for all new functions/classes
- **Integration tests**: Required for new modules/workflows
- **Coverage**: Must maintain ≥80% overall coverage
- **Test types**: Use pytest markers (`@pytest.mark.unit`, `@pytest.mark.integration`)

### Test Guidelines

- Test both success and failure cases
- Test edge cases and boundary conditions
- Use descriptive test names: `test_<function>_<scenario>_<expected>`
- Include docstrings explaining test purpose
- Use fixtures for common setup

### Minimum Coverage

- **Overall Coverage**: 80% minimum (enforced by CI)
- **New Code**: 90% coverage for new features
- **Critical Paths**: 100% coverage for security-sensitive code

### Test Categories

```bash
# Run all tests
poetry run pytest -v

# Run only unit tests
poetry run pytest -v -m unit

# Run only integration tests
poetry run pytest -v -m integration

# Run tests with coverage report
poetry run pytest --cov=src --cov-report=html
# Open htmlcov/index.html to view coverage report

# Run specific test file
poetry run pytest tests/unit/test_schema.py -v
```

### Writing Tests

```python
import pytest
from pathlib import Path
from image_preprocessing_detector.schema import DocumentMetadata

def test_document_metadata_validation():
    """Test DocumentMetadata validates required fields."""
    with pytest.raises(ValueError):
        DocumentMetadata(num_pages=-1)  # Should raise validation error

def test_document_metadata_json_roundtrip(tmp_path: Path):
    """Test DocumentMetadata JSON serialization/deserialization."""
    metadata = DocumentMetadata(num_pages=5, source_file="test.pdf")

    # Write to JSON
    json_path = tmp_path / "metadata.json"
    metadata.to_json_file(json_path)

    # Read from JSON
    loaded = DocumentMetadata.from_json_file(json_path)

    assert loaded.num_pages == metadata.num_pages
    assert loaded.source_file == metadata.source_file
```

### Test Organization

- **Unit Tests**: Test individual functions/classes in isolation
- **Integration Tests**: Test component interactions
- **Fixtures**: Use pytest fixtures for common test data
- **Markers**: Use pytest markers to categorize tests (`@pytest.mark.unit`, `@pytest.mark.slow`)

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic changes)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes
- `build`: Build system or dependency changes

### Examples

```bash
# Feature addition
feat(detection): add blur detection using Laplacian variance

Implements blur detection for image quality assessment using
OpenCV's Laplacian operator. Includes confidence scoring and
threshold-based classification.

Refs: #42

# Bug fix
fix(ingestion): handle corrupted PDF files gracefully

Previously, corrupted PDFs caused uncaught exceptions. Now we
validate PDF structure and return clear error messages.

Fixes: #56

# Breaking change
feat(schema)!: change bounding box format to COCO alignment

BREAKING CHANGE: Bounding boxes now use [x, y, width, height]
format instead of [x1, y1, x2, y2] for LayoutParser compatibility.

Migration guide available in docs/migration/v0.2.0.md
```

### Commit Signing

All commits must be GPG-signed:

```bash
# Configure Git signing
git config --global user.signingkey YOUR_GPG_KEY_ID
git config --global commit.gpgsign true

# Verify signing is enabled
git config --get commit.gpgsign  # Should output: true
```

## Pull Request Process

### Before Submitting

- [ ] Branch is up-to-date with `main`
- [ ] All tests pass locally
- [ ] Code coverage meets minimum requirements (80%)
- [ ] Pre-commit hooks pass
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (for significant changes)
- [ ] Commits follow conventional commit format
- [ ] Commits are GPG-signed

### Submitting a Pull Request

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub with:
   - **Clear title**: Following conventional commit format
   - **Description**: What changes were made and why
   - **Issue reference**: `Fixes #123` or `Refs #456`
   - **Testing notes**: How reviewers can test the changes
   - **Screenshots**: For UI or visual changes
   - **Breaking changes**: Clearly documented

3. **Wait for CI checks**:
   - All GitHub Actions workflows must pass
   - CodeQL security analysis must pass
   - Test coverage must meet requirements

4. **Address review feedback**:
   - Respond to all reviewer comments
   - Push additional commits to the same branch
   - Request re-review when ready

5. **Squash and merge**:
   - Maintainers will squash commits before merging
   - Ensure final commit message follows conventional commits

### PR Review Criteria

Reviewers will check:

- **Code Quality**: Follows style guide and best practices
- **Tests**: Adequate test coverage and meaningful tests
- **Documentation**: Clear docstrings and updated docs
- **Security**: No security vulnerabilities introduced
- **Performance**: No performance regressions
- **Compatibility**: Maintains backward compatibility (or documents breaking changes)

## Issue Guidelines

### Issue Response Policy

We aim to:

- **Acknowledge bug reports** typically within 7-14 days
- **Respond to enhancement requests** typically within 14-21 days
- **Triage severity** typically within 14 days of report
- **Provide status updates** on open issues

**Note**: As a single-maintainer project, these timeframes are goals and may vary depending on workload and availability. All issues will be acknowledged and triaged as promptly as possible, but responses may occasionally take longer during busy periods.

### Reporting Bugs

Use the bug report template and include:

- **Description**: Clear description of the bug
- **Reproduction Steps**: Minimal steps to reproduce
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: Python version, OS, package versions
- **Logs**: Relevant error messages or stack traces

### Requesting Features

Use the feature request template and include:

- **Use Case**: Why is this feature needed?
- **Proposed Solution**: How should it work?
- **Alternatives**: Other approaches considered
- **Additional Context**: Screenshots, mockups, or examples

## Development Phases

The project is developed in phases (see [PROJECT_PLAN.md](docs/planning/PROJECT_PLAN.md)):

- **Phase 0** (Weeks 1-3): Foundation & Scaffolding ✅ **COMPLETE**
- **Phase 1** (Weeks 4-7): MVP with Classical Methods 🔄 **IN PROGRESS**
- **Phase 2** (Weeks 8-11): ML for Image Quality
- **Phase 3** (Weeks 12-16): ML for Document Layout
- **Phase 4** (Weeks 17-20): Production Hardening
- **Phase 5** (Ongoing): Continuous Improvement

When contributing, consider which phase your contribution aligns with.

## Questions?

- **General Questions**: Open a [GitHub Discussion](https://github.com/williaby/image-preprocessing-detector/discussions)
- **Bug Reports**: Open a [GitHub Issue](https://github.com/williaby/image-preprocessing-detector/issues)
- **Security Issues**: See [SECURITY.md](SECURITY.md)
- **Email**: byronawilliams@gmail.com

## Recognition

Contributors are recognized in:

- Repository contributors page
- Release notes for significant contributions
- Project documentation

Thank you for contributing to Image Preprocessing Detector! 🎉
