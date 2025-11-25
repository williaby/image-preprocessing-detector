# Python Development Standards

## Code Quality Requirements

### Line Length and Formatting

- **Maximum Line Length**: 88 characters (Black default)
- **Formatter**: Black (mandatory for all Python files)
- **Import Sorting**: Use Black's import handling or compatible isort configuration

### Code Style Standards

- **Indentation**: 4 spaces (never tabs)
- **String Quotes**: Consistent quote style (Black will normalize)
- **Trailing Commas**: Required in multi-line structures
- **Function/Class Spacing**: 2 blank lines between top-level definitions

## Linting and Analysis

### Ruff Configuration

- **Rules**: Comprehensive rule set including:
  - `E` (pycodestyle errors)
  - `F` (Pyflakes)
  - `I` (isort)
  - `N` (pep8-naming)
  - `UP` (pyupgrade)
  - `B` (flake8-bugbear)
  - `S` (flake8-bandit security)
  - `C4` (flake8-comprehensions)

### Essential Commands

```bash
# Format code
poetry run black .

# Auto-fix linting issues
poetry run ruff check --fix .

# Check for remaining issues
poetry run ruff check .

# Verify formatting is correct
poetry run black --check .
```

## Type Checking

### BasedPyright Requirements

- **Type Hints**: Required for all public functions and methods
- **Configuration**: Use `pyproject.toml` for BasedPyright settings under `[tool.basedpyright]`
- **Strictness**: Use `typeCheckingMode = "strict"` for new projects
- **Coverage**: Target 100% type annotation coverage
- **Strict Inference**: Enable `strictListInference`, `strictDictionaryInference`, `strictSetInference`

> **Note**: BasedPyright is a stricter fork of Pyright, providing 3-5x faster type checking than MyPy with enhanced type inference.

### Type Annotation Standards

```python
# Function signatures
def process_data(input_data: list[str], limit: int = 100) -> dict[str, Any]:
    """Process data with proper type hints."""
    pass

# Class definitions
class DataProcessor:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def process(self, data: list[str]) -> ProcessResult:
        """Process data and return results."""
        pass
```

### Essential Commands

```bash
# Type check entire project
poetry run basedpyright src

# Type check specific files
poetry run basedpyright src/module.py

# For UV-based projects
uv run basedpyright src
```

## Testing Standards

### Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Branch Coverage**: Required (not just line coverage)
- **Missing Coverage Reports**: Must identify uncovered areas

### Test Organization

```
tests/
├── unit/           # Unit tests (fast, isolated)
├── integration/    # Integration tests (slower, with dependencies)
├── e2e/           # End-to-end tests (full system)
└── fixtures/      # Test data and fixtures
```

### Test Naming Conventions

```python
def test_should_return_valid_result_when_given_valid_input():
    """Test function with descriptive name following pattern."""
    pass

class TestDataProcessor:
    """Test class for DataProcessor."""

    def test_should_process_data_correctly(self):
        """Test method with descriptive name."""
        pass
```

### Essential Commands

```bash
# Run all tests with coverage
poetry run pytest -v --cov=src --cov-report=html --cov-report=term-missing

# Run specific test categories
poetry run pytest tests/unit/
poetry run pytest tests/integration/

# Run tests with specific markers
poetry run pytest -m "slow"
poetry run pytest -m "not integration"
```

## Dependency Management

### Poetry Configuration

- **Dependency Specification**: Use semantic versioning constraints
- **Development Dependencies**: Separate from production dependencies
- **Lock File**: Always commit `poetry.lock`

### Version Constraints

```toml
[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.28.0"
pydantic = "^2.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^23.0.0"
ruff = "^0.1.0"
basedpyright = "^1.28.0"
```

### Essential Commands

```bash
# Install dependencies
poetry install

# Add new dependency
poetry add package-name

# Add development dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Show dependency tree
poetry show --tree
```

## Project Structure

### Standard Layout

```
project/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── main.py
│       └── modules/
├── tests/
├── docs/
├── pyproject.toml
├── README.md
└── .env.example
```

### Configuration Files

- **pyproject.toml**: Primary configuration for all tools
- **py.typed**: Mark package as typed
- **.env.example**: Template for environment variables

## Security Requirements

### Code Security

- **Bandit Scanning**: Required for all security-sensitive code
- **Dependency Scanning**: Use Safety to check for vulnerabilities
- **Secret Detection**: No hardcoded secrets or API keys

### Essential Commands

```bash
# Security scanning
poetry run bandit -r src

# Dependency vulnerability check
poetry run safety check

# Check for secrets (if pre-commit configured)
poetry run pre-commit run detect-private-key --all-files
```

## Performance Guidelines

### Best Practices

- **Lazy Loading**: Use generators and lazy evaluation where appropriate
- **Memory Efficiency**: Avoid loading large datasets into memory unnecessarily
- **Async/Await**: Use for I/O-bound operations
- **Caching**: Implement appropriate caching strategies

### Profiling

```bash
# Profile with cProfile
python -m cProfile -s cumulative script.py

# Memory profiling
pip install memory_profiler
python -m memory_profiler script.py
```

## Environment Setup

### Python Version

- **Minimum**: Python 3.11+
- **Recommended**: Latest stable Python version
- **Virtual Environment**: Always use Poetry or similar

### IDE Configuration

- **VS Code**: Recommended extensions and settings
- **PyCharm**: Configuration for Black, Ruff, MyPy integration
- **Editor Config**: Consistent formatting across editors

---

*This file contains comprehensive Python development standards. For command references, see `/commands/quality.md` and `/commands/testing.md`.*
