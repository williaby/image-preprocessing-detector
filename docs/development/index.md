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
- **[Architecture](architecture.md)** - System architecture and design
- **[Testing](testing.md)** - Testing strategy and guidelines
- **[Code Quality](code-quality.md)** - Code quality standards and tools
- **[Licenses](licenses-directory.md)** - License management with REUSE

## Getting Started with Development

### Prerequisites

- Python 3.11+
- Poetry for dependency management
- Git with GPG signing configured
- Pre-commit hooks

### Development Setup

```bash
# Clone the repository
git clone https://github.com/williaby/image-preprocessing-detector.git
cd image-preprocessing-detector

# Install dependencies with dev tools
poetry install --with dev

# Setup pre-commit hooks
poetry run pre-commit install

# Verify installation
poetry run pytest -v
```

### Development Workflow

1. **Create feature branch**: `git checkout -b feature/your-feature`
2. **Make changes**: Follow code quality standards
3. **Run tests**: `poetry run pytest -v`
4. **Run quality checks**: `poetry run pre-commit run --all-files`
5. **Commit changes**: Use signed commits with conventional commit messages
6. **Push and PR**: Create pull request for review

## Architecture Overview

### Project Structure

```
image-preprocessing-detector/
├── src/                      # Source code
│   └── image_preprocessing_detector/
│       ├── schema.py         # Pydantic models
│       ├── ingestion/        # PDF/image loading
│       ├── detection/        # IQA and layout detection
│       ├── correction/       # Image corrections
│       ├── routing/          # DQS and routing logic
│       ├── output/           # JSON serialization
│       └── utils/            # Utilities
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── docs/                     # Documentation
├── configs/                  # Configuration files
└── scripts/                  # Utility scripts
```

See [Architecture Documentation](architecture.md) for detailed system design.

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
- **Type Checking**: MyPy strict mode on `src/`
- **Linting**: Ruff format and lint checks
- **Security**: Bandit and Safety scans
- **Pre-commit**: All hooks must pass

### Code Quality Tools

```bash
# Format code
poetry run ruff format src tests

# Lint code
poetry run ruff check --fix src tests

# Type checking
poetry run mypy src

# Security scanning
poetry run bandit -r src
poetry run safety check

# Run all checks
poetry run pre-commit run --all-files
```

See [Code Quality Guide](code-quality.md) for complete details.

### Testing Standards

```bash
# Run all tests
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test categories
poetry run pytest -m unit           # Unit tests only
poetry run pytest -m integration    # Integration tests
poetry run pytest -m "not slow"     # Exclude slow tests

# Run parallel
poetry run pytest -n auto
```

See [Testing Guide](testing.md) for testing strategy.

## Phase-Based Development

The project follows a phased development approach:

- **Phase 0** (Complete): Project Setup
- **Phase 2** (Planned): Teacher-Student ML IQA
- **Phase 4** (Planned): Classical IQA + DPI Upscaling
- **Phase 6** (Planned): Layout-Lite Detection
- **Phase 8** (Planned): DQS & Routing
- **Phase 10** (Planned): Validation & Documentation

See [Project Plan](RAG%20Pipeline/project-a-project-plan.md) for detailed roadmap.

## Architecture Decision Records

All significant architectural decisions are documented in ADRs:

- [ADR Index](../ADRs/README.md) - Complete list of decisions
- [ADR-001: Ruff Linting](../ADRs/0001-consolidate-linting-with-ruff.md)
- [ADR-029: Project A Scope](../ADRs/0029-project-a-scope-boundaries.md)
- [ADR-034: ResNet18 IQA](../ADRs/0034-resnet18-phase2-iqa.md)

When making significant decisions, create a new ADR following the established format.

## Key Technologies

### Core Stack

- **Python 3.11+**: Modern Python with type hints
- **Poetry**: Dependency management
- **Pydantic v2**: Schema validation
- **PyTorch 2.0+**: ML models
- **OpenCV 4.8+**: Image processing
- **Modal**: Serverless GPU training

### Development Tools

- **Ruff**: Linting and formatting
- **MyPy**: Static type checking
- **Pytest**: Testing framework
- **Pre-commit**: Git hooks
- **MkDocs**: Documentation
- **GitHub Actions**: CI/CD

## Contributing

We welcome contributions! Please see:

- [Contributing Guide](contributing.md) - Detailed contribution guidelines
- [Code of Conduct](https://github.com/williaby/image-preprocessing-detector/blob/main/CODE_OF_CONDUCT.md)
- [GitHub Issues](https://github.com/williaby/image-preprocessing-detector/issues)

### Contribution Areas

- **Bug Fixes**: Report and fix bugs
- **Features**: Implement new features from roadmap
- **Documentation**: Improve docs and examples
- **Testing**: Add test coverage
- **Performance**: Optimize critical paths

## Security

Security is a top priority:

- **No secrets in code**: Use environment variables
- **Encrypted .env**: GPG-encrypted configuration
- **Signed commits**: GPG signature required
- **Dependency scanning**: Automated vulnerability checks
- **Fuzzing**: ClusterFuzzLite integration

See [Security Guide](../security/codeql-python-scanning-guide.md).

## Performance Guidelines

### Performance Targets

**ML IQA (Phase 2)**:
- Student (ResNet-18) CPU: ≤40ms/page
- Student (ResNet-18) GPU: ≤10ms/page
- Teacher (ResNet-50) GPU: ≤30ms/page

**End-to-End (Phase 10)**:
- GPU: <150ms/page
- CPU: <500ms/page

### Optimization Tips

1. **Use GPU when available**: Significant speedup for ML inference
2. **Batch processing**: Process multiple pages together
3. **ONNX Runtime**: Use optimized ONNX models for production
4. **Profile first**: Use `cProfile` to identify bottlenecks

## Documentation

### Writing Documentation

- Use Markdown with front matter
- Follow schema_type conventions
- Include code examples
- Link to related docs
- Test with `mkdocs serve`

### Building Docs

```bash
# Serve locally
mkdocs serve

# Build static site
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy
```

## Useful Resources

### Internal Documentation

- [Repository Structure](../REPOSITORY_STRUCTURE.md)
- [Dataset Locations](../DATASET_LOCATIONS.md)
- [Model Storage](../MODEL_STORAGE.md)
- [Testing Strategy](../TESTING_STRATEGY.md)
- [Phase 2 Quickstart](../PHASE2_QUICKSTART.md)

### External Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [Modal Documentation](https://modal.com/docs)

## Support

- **GitHub Issues**: [Report issues](https://github.com/williaby/image-preprocessing-detector/issues)
- **Discussions**: [Ask questions](https://github.com/williaby/image-preprocessing-detector/discussions)
- **Email**: For security issues only

## Related Documentation

- [User Guide](../guides/index.md) - User-focused documentation
- [API Reference](../api/index.md) - API documentation
- [Project Plan](RAG%20Pipeline/project-a-project-plan.md) - Development roadmap
