# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- OpenSSF Best Practices badge compliance
- Security policy (SECURITY.md) with vulnerability reporting process
- Comprehensive API reference documentation
- GitHub issue templates for bugs and feature requests
- Detailed contribution guidelines with coding standards

## [0.1.0] - 2025-11-07

### Added
- Initial project structure with Poetry package management
- Pydantic v2 JSON schema (DetectedIssue, DocumentElement, PageMetadata, DocumentMetadata)
- COCO-aligned bounding boxes for LayoutParser integration
- Hybrid IQA approach with per-element quality assessment
- Text detection gate for document routing
- Structured logging with structlog and rich console output
- Pre-commit hooks (Black, Ruff, MyPy, Bandit, Safety)
- Comprehensive test suite (163 tests, 94.46% coverage)
- GitHub Actions CI/CD pipeline with quality gates
- CLI tool foundation (`imgprep` command)
- MIT License
- Python 3.12 support

### Documentation
- README with project overview and quick start
- CONTRIBUTING guidelines with development workflow
- PROJECT_PLAN with 50+ page implementation roadmap
- ARCHITECTURE_SUMMARY with design decisions
- DECISION_MATRIX for critical decisions tracking
- ARCHITECTURE_CORRECTION documenting hybrid IQA rationale

### Infrastructure
- Poetry dependency management with lock file
- pytest test framework with coverage reporting
- GitHub issue tracking
- Automated dependency security scanning (Safety, Bandit)
- Code quality enforcement (Black, Ruff, MyPy)
- CI/CD pipeline with multiple quality gates

### Security
- Bandit security linting
- Safety dependency vulnerability scanning
- Pre-commit hooks for security validation
- No leaked credentials verification

[Unreleased]: https://github.com/williaby/image-preprocessing-detector/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/williaby/image-preprocessing-detector/releases/tag/v0.1.0
