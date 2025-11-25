# Linting Standards

## File-Type Specific Linting Requirements

### Python Files

#### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # Pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "S",    # flake8-bandit
    "C4",   # flake8-comprehensions
    "COM",  # flake8-commas
    "DTZ",  # flake8-datetimez
    "EM",   # flake8-errmsg
    "EXE",  # flake8-executable
    "ISC",  # flake8-implicit-str-concat
    "PIE",  # flake8-pie
    "PT",   # flake8-pytest-style
    "Q",    # flake8-quotes
    "RET",  # flake8-return
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
    "ARG",  # flake8-unused-arguments
    "PTH",  # flake8-use-pathlib
    "ERA",  # eradicate
    "PL",   # Pylint
    "TRY",  # tryceratops
    "FLY",  # flynt
    "PERF", # Perflint
    "RUF",  # Ruff-specific rules
]

ignore = [
    "E501",   # Line too long (handled by Black)
    "S101",   # Use of assert (allowed in tests)
    "PLR0913", # Too many arguments
    "PLR0915", # Too many statements
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101", "ARG001", "PLR2004"]
"__init__.py" = ["F401"]

[tool.ruff.lint.isort]
known-first-party = ["your_package"]
```

#### Black Configuration

```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ["py311"]
include = '\.pyi?$'
exclude = '''
/(
    \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
)/
'''
```

#### Python Linting Commands

```bash
# Format with Black
poetry run black .

# Check formatting
poetry run black --check .

# Lint with Ruff
poetry run ruff check .

# Auto-fix with Ruff
poetry run ruff check --fix .

# Type check with BasedPyright
poetry run basedpyright src
```

### Markdown Files

#### Markdownlint Configuration

```json
{
  "default": true,
  "line_length": {
    "line_length": 120,
    "code_blocks": false,
    "tables": false,
    "headings": false
  },
  "no-hard-tabs": true,
  "whitespace": true,
  "MD013": {
    "line_length": 120,
    "code_blocks": false,
    "tables": false
  },
  "MD033": {
    "allowed_elements": ["br", "sub", "sup", "details", "summary"]
  },
  "MD041": false
}
```

#### Markdown Standards

- **Line Length**: 120 characters maximum
- **Heading Style**: ATX headers (`# Header` not `Header\n======`)
- **List Style**: Consistent dash `-` for unordered lists
- **Code Blocks**: Use triple backticks with language specification
- **Links**: Use reference-style for repeated links

#### Markdown Linting Commands

```bash
# Lint markdown files
markdownlint **/*.md

# Auto-fix where possible
markdownlint --fix **/*.md

# Lint specific files
markdownlint README.md docs/*.md
```

### YAML Files

#### Yamllint Configuration

```yaml
# .yamllint.yml
extends: default

rules:
  line-length:
    max: 120
    level: error

  indentation:
    spaces: 2
    indent-sequences: true
    check-multi-line-strings: false

  comments:
    min-spaces-from-content: 1

  comments-indentation: {}

  empty-lines:
    max: 2
    max-start: 0
    max-end: 1

  key-duplicates: {}

  brackets:
    min-spaces-inside: 0
    max-spaces-inside: 1

  colons:
    max-spaces-before: 0
    min-spaces-after: 1
    max-spaces-after: 1

  commas:
    max-spaces-before: 0
    min-spaces-after: 1
    max-spaces-after: 1

  hyphens:
    max-spaces-after: 1

  truthy:
    allowed-values: ['true', 'false', 'yes', 'no']
```

#### YAML Standards

- **Indentation**: 2 spaces consistently
- **Line Length**: 120 characters maximum
- **Boolean Values**: Use `true/false` or `yes/no`
- **Quotes**: Only when necessary (special characters, etc.)
- **Key Ordering**: Alphabetical where logical

#### YAML Linting Commands

```bash
# Lint YAML files
yamllint **/*.{yml,yaml}

# Lint specific directory
yamllint .github/workflows/

# Strict mode
yamllint -d '{extends: default, rules: {line-length: {max: 120}}}' file.yml
```

### JSON Files

#### JSON Standards

- **Indentation**: 2 spaces
- **Trailing Commas**: Not allowed (invalid JSON)
- **Key Ordering**: Alphabetical where possible
- **String Quotes**: Double quotes only

#### JSON Validation Commands

```bash
# Validate JSON syntax
python -m json.tool file.json > /dev/null

# Format JSON with jq
jq '.' file.json > formatted.json

# Validate all JSON files
find . -name "*.json" -exec python -m json.tool {} \; > /dev/null
```

### Configuration Files

#### EditorConfig

```ini
# .editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 2

[*.py]
indent_size = 4
max_line_length = 88

[*.md]
max_line_length = 120
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

#### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-merge-conflict
      - id: check-added-large-files
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.287
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  # BasedPyright for type checking (faster than MyPy)
  # Note: Run via local hook or CI for better performance
  # - repo: local
  #   hooks:
  #     - id: basedpyright
  #       name: basedpyright
  #       entry: poetry run basedpyright src
  #       language: system
  #       types: [python]

  - repo: https://github.com/igorshubovych/markdownlint-cli
    rev: v0.35.0
    hooks:
      - id: markdownlint
        args: [--fix]

  - repo: https://github.com/adrienverge/yamllint
    rev: v1.32.0
    hooks:
      - id: yamllint
```

## IDE Integration

### VS Code Settings

```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.analysis.typeCheckingMode": "strict",
  "python.linting.lintOnSave": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "markdownlint.config": {
    "MD013": {
      "line_length": 120
    }
  },
  "yaml.format.enable": true,
  "yaml.format.singleQuote": false,
  "yaml.format.bracketSpacing": true
}
```

### PyCharm/IntelliJ Settings

- Enable Black formatter
- Configure Ruff as external tool
- Set line length to 88 for Python, 120 for Markdown
- Enable format on save

## Linting Workflow

### Development Workflow

```bash
# Before making changes
poetry run pre-commit install

# During development
poetry run black .
poetry run ruff check --fix .

# Before committing
poetry run pre-commit run --all-files

# If pre-commit fails, fix issues and retry
git add .
git commit -m "fix: resolve linting issues"
```

### CI/CD Integration

```yaml
# .github/workflows/lint.yml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Lint with Black
        run: poetry run black --check .

      - name: Lint with Ruff
        run: poetry run ruff check .

      - name: Type check with BasedPyright
        run: poetry run basedpyright src

      - name: Lint Markdown
        run: markdownlint **/*.md

      - name: Lint YAML
        run: yamllint **/*.{yml,yaml}
```

## Error Resolution

### Common Python Issues

```bash
# Fix import sorting
poetry run ruff check --fix --select I .

# Fix code style
poetry run black .

# Fix specific rule violations
poetry run ruff check --fix --select F401 .  # Remove unused imports
```

### Common Markdown Issues

```bash
# Fix line length issues
markdownlint --fix MD013 **/*.md

# Fix heading issues
markdownlint --fix MD041 **/*.md
```

### Common YAML Issues

```bash
# Check indentation
yamllint -d '{rules: {indentation: {spaces: 2}}}' file.yml

# Fix line length
# Manual edit required for YAML line length issues
```

## Custom Rules

### Project-Specific Rules

```toml
# pyproject.toml - Custom Ruff rules
[tool.ruff.lint]
# Add project-specific ignores
ignore = [
    "PLR0913",  # Too many arguments (if needed for API compatibility)
    "S603",     # subprocess-popen-shell-true (if shell=True is required)
]

# Per-file ignores for specific patterns
[tool.ruff.lint.per-file-ignores]
"migrations/*" = ["E501"]  # Allow long lines in migrations
"scripts/*" = ["T201"]     # Allow print statements in scripts
```

### Custom Markdownlint Rules

```json
{
  "MD033": {
    "allowed_elements": [
      "br", "sub", "sup", "details", "summary",
      "img", "a", "div", "span"
    ]
  },
  "MD013": {
    "line_length": 120,
    "code_blocks": false,
    "tables": false,
    "headings": {
      "heading_length": 120,
      "code_blocks": false
    }
  }
}
```

## Performance Optimization

### Linting Performance

```bash
# Run linting in parallel
poetry run black . & poetry run ruff check . & wait

# Use file caching
poetry run ruff check --cache-dir .ruff_cache .

# Lint only changed files
git diff --name-only --cached | grep '\.py$' | xargs poetry run ruff check
```

### Pre-commit Optimization

```yaml
# .pre-commit-config.yaml - Optimized hooks
repos:
  - repo: local
    hooks:
      - id: ruff
        name: ruff
        entry: poetry run ruff check --fix
        language: system
        types: [python]
        require_serial: false
```

---

*This file contains comprehensive linting standards for all file types. For linting command references, see `/commands/quality-lint-check.md`.*
