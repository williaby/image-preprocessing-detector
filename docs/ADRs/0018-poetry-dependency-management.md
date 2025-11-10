---
schema_type: common
title: "ADR-018: Poetry for Dependency Management"
description: "Use Poetry for deterministic builds and dependency management"
tags: [adr, poetry, dependencies, packaging, tooling]
status: published
owner: "core-maintainer"
authors:
- name: "Byron Williams"
purpose: "Document the decision to use Poetry for Python dependency management and
  packaging."
---


**Status**: Accepted
**Date**: 2025-01-08
**Deciders**: Byron Williams
**Related**:
- [pyproject.toml](../../pyproject.toml)
- [poetry.lock](../../poetry.lock)
- [ADR-001: Consolidate Linting with Ruff](0001-consolidate-linting-with-ruff.md)

## Context

Python projects require dependency management for:
- Deterministic builds (lock files)
- Development vs production dependencies
- Virtual environment management
- Package building and distribution

## Decision

**Use Poetry for all dependency management, packaging, and virtual environment tasks.**

### Key Features

**Lock Files**: `poetry.lock` ensures deterministic builds across environments

**Dependency Groups**:
```toml
[tool.poetry.dependencies]
python = "^3.11"
opencv-python = "^4.8.0"
pydantic = "^2.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^25.9.0"
mypy = "^1.4.0"

[tool.poetry.group.ml.dependencies]
torch = "^2.0.0"
ultralytics = "^8.0.0"
```

**Commands**:
```bash
poetry install               # Install all dependencies
poetry install --with ml     # Install with ML dependencies
poetry add opencv-python     # Add runtime dependency
poetry add --group dev pytest  # Add dev dependency
poetry lock                  # Update lock file
```

## Consequences

### Positive

1. **Deterministic Builds**: Lock file ensures reproducible environments
2. **Dependency Groups**: Separate dev, ml, api dependencies
3. **Unified Tool**: Single tool for dependencies, packaging, and virtual envs
4. **Industry Standard**: Widely adopted in Python community
5. **pyproject.toml**: Modern PEP 518/621 standard

### Negative

1. **Learning Curve**: Developers need to learn Poetry commands
2. **Lock File Conflicts**: Merge conflicts in poetry.lock
3. **Slower Installs**: ~10-20% slower than pip

### Neutral

1. **Replaces**: pip, venv, setuptools, requirements.txt
2. **File Size**: poetry.lock is ~500KB (acceptable)

## Alternatives Considered

### Alternative 1: pip + requirements.txt

**Approach**: Use pip with requirements.txt and requirements-dev.txt

**Advantages**:
- Standard Python tool
- Fast installs
- Simple

**Disadvantages**:
- No lock file (unless using pip-tools)
- No dependency resolution
- Manual virtual env management

**Why Rejected**: No deterministic builds

### Alternative 2: pipenv

**Approach**: Use pipenv for Pipfile + Pipfile.lock

**Advantages**:
- Lock files
- Dependency resolution

**Disadvantages**:
- Slower than Poetry
- Less active development
- Heavier weight

**Why Rejected**: Poetry is faster and more actively maintained

### Alternative 3: conda

**Approach**: Use conda for environment and dependency management

**Advantages**:
- Cross-language dependencies
- Binary packages

**Disadvantages**:
- Heavier weight
- Slower installs
- Not Python-native

**Why Rejected**: Overkill for Python-only project

## Implementation

### Dependency Groups

**Runtime Dependencies** (`dependencies`):
- opencv-python, pillow, numpy, pymupdf
- pydantic, structlog, rich, click

**Development Tools** (`group.dev`):
- pytest, black, ruff, mypy, bandit, safety
- pre-commit hooks

**ML Dependencies** (`group.ml`):
- torch, ultralytics (YOLOv8), onnx, onnxruntime
- albumentations (data augmentation)

**API Dependencies** (`group.api`):
- fastapi, uvicorn, pydantic-settings

### Installation Workflow

**Developer Setup**:
```bash
git clone <repo>
cd image_detection
poetry install --with dev  # Install with dev tools
poetry shell               # Activate virtual environment
```

**Production Deployment**:
```bash
poetry install --only main  # Runtime dependencies only
```

**ML Training**:
```bash
poetry install --with ml  # Add ML dependencies
```

### Lock File Management

**Update Dependencies**:
```bash
poetry update               # Update all dependencies
poetry update opencv-python # Update specific package
poetry lock --no-update     # Regenerate lock without updating
```

**Resolve Conflicts**:
```bash
git checkout --theirs poetry.lock
poetry lock --no-update
```

## Performance

**Installation Times** (fresh install):
- `poetry install`: ~45s
- `poetry install --with dev`: ~60s
- `poetry install --with ml`: ~120s (PyTorch)

**Lock File Generation**: ~5-10s

## References

- [Poetry Documentation](https://python-poetry.org/docs/)
- [PEP 518 - pyproject.toml](https://peps.python.org/pep-0518/)
- [pyproject.toml](../../pyproject.toml)
