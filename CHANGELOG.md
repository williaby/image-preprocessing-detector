# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `image_preprocessing_detector.utils.file_validation` module: stdlib
  magic-byte validation (`validate_file_content`, `detect_file_type`,
  `FileTypeMismatchError`, `MIN_VALIDATION_BYTES`) to block file
  extension spoofing before bytes reach PyMuPDF/OpenCV/PIL (#183)
- `ProcessingResult.pages_truncated` field reporting how many PDF pages
  the API dropped when a document exceeds the page cap (#183)
- `APISettings.max_batch_total_size_mb` (default 500MB) and
  `APISettings.max_pdf_pages_per_request` (default 100) settings (#183)
- `PDFLoader.max_pixels` / `ImageLoader.max_pixels` pixel-dimension-bomb
  guards, plus `PDFTooManyPagesError` and `PDFPageTooLargeError` (#183)

### Security

- `torch.load` calls switched to `weights_only=True` in production
  inference and Modal training to prevent pickle-based RCE
  (CVE-2025-32434 class; mitigation requires the pinned torch>=2.10.0) (#183)
- Streaming, size-capped upload reads with first-chunk magic-byte
  validation on `/process` and `/batch`; cumulative batch size cap (#183)
- Model artifact paths in the Arena inference backends validated against
  path traversal (#183)
- `PDFLoader` now raises `PDFTooManyPagesError` by default when a
  document exceeds `max_pages` (set `allow_truncation=True` to restore
  the previous silent-truncate behavior; the API routes opt in) (#183)
- Pin `actions/github-script` and `astral-sh/setup-uv` to commit SHAs (#183)

### Changed

- **BREAKING**: Project license changed from MIT to CC-BY-SA-4.0.
  Derivatives must be shared under CC-BY-SA-4.0 or compatible license.
  Attribution required. Commercial use permitted.
- Consolidated all license declarations into REUSE.toml with `precedence = "override"`
  (removed ~386 inline SPDX headers from source files)
- Documentation license changed from CC-BY-4.0 to CC-BY-SA-4.0 for consistency

### Added

- New `annotation` package extracted from monolithic `annotate_base_metadata.py`
  - `schemas/` subpackage with enums, immutable layer, enrichment layer, sample aggregate
  - `integrity/` subpackage with full-file hashing and atomic file operations
  - `config/` subpackage with externalized settings and tier definitions
  - `create_orchestrator()` factory function for dependency injection
- Full-file SHA256 hashing in `annotation.integrity.hashing` (P0-1 fix)
- Deterministic sample ID generation via `compute_sample_id()` (P1-3 fix)
- Atomic file operations with `atomic_write()` context manager (P2-2 fix)
- FUNSD annotation type correction (dict, not list) in schemas (P0-4 fix)
- Schema migrations infrastructure with rollback support
- Configuration loading from environment variables and YAML files
- `AnnotationSettings` frozen dataclass for externalized configuration
- Enrichment tier definitions (Tier 0-3) with helper functions
- 108 unit tests for annotation package

### Changed

- **BREAKING**: Sample ID computation now uses full-file SHA256 hash instead of
  partial 64KB hash. This means **ALL existing sample IDs will change** when
  processing the same files. Migration steps:
  1. Re-run annotation pipeline on all datasets to regenerate sample IDs
  2. Update any external references to sample IDs (databases, indexes, etc.)
  3. Optionally maintain a mapping file from old to new IDs during transition
  - **Rationale**: The 64KB partial hash was insufficient for collision detection
    in datasets with similar file headers. Full-file hashing ensures unique
    identification regardless of file structure.
  - **Affected code**: `annotation.integrity.hashing.compute_full_sha256()`
    replaces the previous `_compute_sha256_partial()` function

- Recommended Docker base image runtime updated from Python 3.12 to 3.11 for broader
  compatibility with ML dependencies (PyTorch, ONNX Runtime) and cloud GPU environments;
  the project itself supports Python >=3.10,<3.15 (see pyproject.toml)
- OpenSSF Best Practices badge compliance
- Security policy (SECURITY.md) with vulnerability reporting process
- Comprehensive API reference documentation
- GitHub issue templates for bugs and feature requests
- Detailed contribution guidelines with coding standards

## [0.1.0] - TBD

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
- DECISION_MATRIX for critical decisions tracking (now at docs/project/decision-matrix.md)
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
