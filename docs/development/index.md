---
schema_type: common
title: "Development Documentation"
description: "Developer guide and technical documentation"
tags: [development, contributing, documentation]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Provide comprehensive development documentation for contributors."
---

Welcome to the Image Preprocessing Detector development documentation. This section contains technical guides for contributors and developers working on the project.

## Quick Links

- **[Contributing Guide](contributing.md)** - How to contribute to the project
- **[Licenses](licenses-directory.md)** - License management with REUSE
- **[Mutation Testing](MUTATION_TESTING.md)** - Mutation testing approach
- **[Phase 4 Summary](phase4-implementation-summary.md)** - Phase 4 implementation details
- **[Phase 4 Integration](phase4-integration-guide.md)** - Phase 4 integration guide

## Getting Started with Development

### Prerequisites

- Python 3.11+
- uv for dependency management
- Git with GPG signing configured
- Pre-commit hooks

### Development Setup

```bash
# Clone the repository
git clone https://github.com/williaby/image-preprocessing-detector.git
cd image-preprocessing-detector

# Install dependencies with dev tools
uv sync --extra dev

# Setup pre-commit hooks
uv run pre-commit install

# Verify installation
uv run pytest -v
```

### Development Workflow

1. **Create feature branch**: `git checkout -b feat/your-feature`
2. **Make changes**: Follow code quality standards in CLAUDE.md
3. **Run tests**: `uv run pytest -v`
4. **Run quality checks**: `uv run pre-commit run --all-files`
5. **Commit changes**: Use signed commits with conventional commit messages
6. **Push and PR**: Create pull request for review

## Architecture Overview

### Project Structure

```text
image-preprocessing-detector/
├── src/                      # Source code
│   └── image_preprocessing_detector/
│       ├── schema.py         # Pydantic models
│       ├── ingestion/        # PDF/image loading + DPI upscaling
│       ├── detection/        # IQA (classical + ML) and layout-lite
│       ├── correction/       # Image corrections
│       ├── classification/   # PDF type classification
│       ├── routing/          # DQS and routing logic
│       ├── metrics/          # Document quality scoring
│       ├── output/           # JSON serialization
│       ├── workers/          # Celery task workers
│       └── utils/            # Utilities
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── docs/                     # Documentation
├── configs/                  # Configuration files
└── scripts/                  # Utility scripts
```

See [Architecture Documentation](../architecture/) for detailed system design.

### RAG Pipeline Context

This project is **Project A** in a four-project RAG pipeline:

- **Project A** (This): Preprocessing & IQA
- **Project B**: OCR Orchestration
- **Project C**: Fusion & Trust
- **Project D**: Vector Indexing

See [RAG Pipeline Overview](RAG%20Pipeline/RAG-pipeline-project-overview.md) for the complete architecture.

## Development Standards

### Code Quality Requirements

- **Coverage**: Minimum 80% enforced
- **Type Checking**: BasedPyright strict mode on `src/`
- **Linting**: Ruff format and lint checks
- **Security**: Bandit and Safety scans
- **Pre-commit**: All hooks must pass

### Code Quality Tools

```bash
# Format code
uv run ruff format src tests

# Lint code
uv run ruff check --fix src tests

# Type checking
uv run basedpyright src

# Security scanning
uv run bandit -r src

# Run all checks
uv run pre-commit run --all-files
```

## Project Status

- **Phase 0** (Complete): Project Setup
- **Phase 1** (Complete): MVP with Classical Methods + DPI Upscaling
- **Phase 1C** (Complete): Enhanced Classical IQA (8 detectors)
- **Phase 2** (Complete): Layout-Lite, DQS, Routing
- **Phase 3** (Complete): Teacher-Student ML IQA (ResNet-50/18)
- **Phase 4** (98%): Device Priority & Production Hardening
- **Phase 5** (40%): Testing, Documentation & Deployment
- **Phase 6** (95%): Monitoring & Drift Detection

See [Project Plan](../planning/PROJECT_PLAN.md) for detailed roadmap.

## Architecture Decision Records

All significant architectural decisions are documented in ADRs:

- [ADR Index](../ADRs/README.md) - Complete list of decisions

## Key Technologies

### Core Stack

- **Python 3.11+**: Modern Python with type hints
- **uv**: Dependency management
- **Pydantic v2**: Schema validation
- **PyTorch 2.0+**: ML models (ResNet-50/18 teacher-student)
- **OpenCV 4.8+**: Image processing
- **Modal**: Serverless GPU training

### Development Tools

- **Ruff**: Linting and formatting
- **BasedPyright**: Static type checking (strict mode)
- **Pytest**: Testing framework
- **Pre-commit**: Git hooks
- **GitHub Actions**: CI/CD

## Related Documentation

- [API Reference](../api/index.md) - API documentation
- [Project Plan](../planning/PROJECT_PLAN.md) - Development roadmap
- [Architecture](../architecture/) - System architecture
