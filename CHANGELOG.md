# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- ClusterFuzzLite continuous fuzzing integration for security testing
- PDF ingestion with PyMuPDF for document processing
- Image loading with Pillow/OpenCV for multi-format support
- Text detection gate using classical CV heuristics (stroke density, connected components, edge density)
- Classical IQA detectors (skew via Hough transform, blur via Laplacian, contrast via histogram analysis)
- JSON schema with Pydantic v2 for structured metadata output
- CLI tool with Click for command-line processing
- Comprehensive test suite (163 tests, 94.46% coverage)
- CI/CD pipeline with GitHub Actions (setup, test, quality checks)
- Pre-commit hooks (Black, Ruff, MyPy, Bandit, Safety)
- OpenSSF Scorecard integration for security metrics

### Security
- Signed commits with SSH for commit verification
- Dependency scanning with Safety for vulnerability detection
- Security policy (SECURITY.md) with 10-day acknowledgment time
- Token permissions scoped to job-level (principle of least privilege)
- GitHub Actions dependencies pinned to SHA hashes
- No known vulnerabilities (OpenSSF Scorecard: 10/10 Vulnerabilities check)

### Changed
- Updated Black from 23.12.1 to 25.9.0 (fixes CVE-2024-21503 ReDoS vulnerability)
- Updated FastAPI from 0.100.1 to >=0.115.0 (fixes PVE-2024-64930 ReDoS vulnerability)

### Fixed
- PDF loader DPI estimation fallback handling
- Logging example to use relative paths instead of /tmp
- Pre-commit MyPy exclusions to skip validation directory

## [0.0.1] - 2025-01-15

### Added
- Initial project scaffolding with Poetry dependency management
- Python 3.12 support
- MIT License
- Basic project structure (ingestion, detection, correction, output, utils modules)
- Structured logging with structlog and rich console output
- Pydantic v2 models for JSON I/O (DetectedIssue, DocumentElement, PageMetadata, DocumentMetadata)

[Unreleased]: https://github.com/williaby/image-preprocessing-detector/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/williaby/image-preprocessing-detector/releases/tag/v0.0.1
