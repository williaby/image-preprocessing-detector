# tools/

**Purpose**: Development tools for code quality, documentation generation, and validation.

## What Goes Here

**✅ Belongs in tools/**:

- Code quality tools (linting, formatting)
- Documentation generation scripts
- Front matter validation
- REUSE compliance tools
- Catalog generation utilities

**❌ Does NOT belong here** (and where it should go instead):

- **Dataset/GCS utilities** → `scripts/` (operational utilities)
- **Training code** → `src/` or `notebooks/` (model training)
- **Testing code** → `tests/` (unit/integration tests)
- **Build tools** → `noxfile.py`, `pyproject.toml` (build configuration)

## Current Tools

### Front Matter Validation

**Files**: `validate_front_matter.py`, `frontmatter_contract/`

**Purpose**: Validates YAML front matter in markdown files (docs, ADRs) using Pydantic models

**Usage**:

```bash
# Validate all markdown files in docs/
poetry run python tools/validate_front_matter.py docs

# Auto-fix common issues (tags normalization, punctuation)
poetry run python tools/validate_front_matter.py docs --fix

# Output JSON for CI integration
poetry run python tools/validate_front_matter.py docs --emit-json
```

**Validates**:

- YAML syntax correctness
- Required fields present (title, status, owner, purpose)
- Field types match Pydantic schema
- Enum values are valid (status, category, component)
- Tags are snake_case and in allow-list
- Owners are in allow-list
- Purpose ends with terminal punctuation
- No redundant H1 headings in body (title renders automatically)

**Autofix Capabilities**:

- Normalize tags to snake_case (replace hyphens/spaces, lowercase)
- Add terminal punctuation to purpose field

**Schema Types**:

- `common`: General documentation pages (default)
- `script`: Tool/script documentation pages
- `knowledge`: Knowledge base entries
- `planning`: Planning and strategy documents

**Integration**: Pre-commit hook (`.pre-commit-config.yaml`)

### Tools Catalog Generation

**File**: `gen_tools_catalog.py`

**Purpose**: Generates catalog of script documentation pages for MkDocs

**Usage**:

```bash
# Runs automatically during MkDocs build via gen-files plugin
mkdocs build

# Generated page: docs/tools/index.md
```

**Features**:

- Scans all markdown files with `schema_type: script`
- Organizes by category (validation, data, build, docs, release, misc)
- Includes usage examples and descriptions
- Auto-updates during documentation build

**Integration**: MkDocs build process (`mkdocs-gen-files` plugin)

### Front Matter Contract

**Directory**: `frontmatter_contract/`

**Purpose**: Pydantic models for front matter validation

**Files**:

- `models.py`: Pydantic v2 models with discriminated union
- `__init__.py`: Package exports

**Models**:

- `CommonFM`: Base schema for general documentation
- `ScriptSpecFM`: Extended schema for script/tool docs
- `KnowledgeFM`: Extended schema for knowledge base entries
- `PlanningFM`: Extended schema for planning documents
- `DiscriminatedFM`: Discriminated union type

**Dependencies**: `pydantic>=2.0`, `ruamel.yaml`, `python-frontmatter`

## Distinction from Other Folders

### vs. scripts/

- **tools/**: Development and quality assurance tools
- **scripts/**: Operational utilities for datasets, training, deployment

### vs. tests/

- **tools/**: Development-time validation and generation
- **tests/**: Runtime test execution (pytest)

### vs. monitoring/

- **tools/**: Development tools (pre-deployment)
- **monitoring/**: Runtime monitoring (post-deployment, Phase 4+)

## Pre-Commit Integration

Tools are integrated into pre-commit hooks (`.pre-commit-config.yaml`):

```yaml
- repo: local
  hooks:
    - id: validate-front-matter
      name: Validate Front Matter
      entry: poetry run python tools/validate_front_matter.py
      language: system
      pass_filenames: false
```

## Adding New Tools

When creating a new development tool:

1. **Location**: Add to `tools/` directory
2. **Naming**: Use descriptive names (`validate_*.py`, `gen_*.py`)
3. **Documentation**: Add docstring and README section
4. **Pre-Commit**: Consider adding to `.pre-commit-config.yaml`
5. **Dependencies**: Declare in `pyproject.toml` under `[tool.poetry.group.dev.dependencies]`

## Example Tool Structure

```python
#!/usr/bin/env python3
"""
Validate YAML front matter in markdown documentation.

Usage:
    python tools/validate_front_matter.py [--path docs/]

Exit codes:
    0: All files valid
    1: Validation errors found
"""

import argparse
import sys
from pathlib import Path

def validate_file(file_path: Path) -> bool:
    """Validate single markdown file."""
    # Implementation here
    pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default="docs/")
    args = parser.parse_args()

    # Run validation
    errors = []
    for md_file in args.path.rglob("*.md"):
        if not validate_file(md_file):
            errors.append(md_file)

    # Report results
    if errors:
        print(f"Validation failed: {len(errors)} files have errors")
        return 1
    else:
        print("All files valid")
        return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Best Practices

1. **Standalone**: Tools should be self-contained with minimal dependencies
2. **CLI Interface**: Provide command-line arguments for flexibility
3. **Exit Codes**: Return 0 for success, non-zero for errors
4. **Documentation**: Clear usage instructions and examples
5. **Testing**: Tools should have their own tests in `tests/tools/`
