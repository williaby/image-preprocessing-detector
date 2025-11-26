---
schema_type: common
title: "Changelog"
description: "Version history and release notes for Image Preprocessing Detector"
tags: [changelog, releases, version_history, documentation]
status: published
owner: "docs-team"
authors:
  - name: "Byron Williams"
purpose: "Document version history, feature additions, bug fixes, and breaking changes for the project."
---

All notable changes to the Image Preprocessing Detector project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- MkDocs documentation site with Material theme
- Comprehensive API documentation using mkdocstrings
- User guides for configuration, IQA, layout detection, and correction
- Development guides for architecture, testing, and code quality
- Pydantic v2 front matter validation for documentation
- JSON-LD metadata injection for SEO
- Tools catalog auto-generation

### Changed

- Migrated existing documentation to new MkDocs structure
- Updated documentation front matter to use discriminated union schema

### In Progress

- CLI tool final integration testing
- Additional correction algorithm optimizations
- Performance benchmarking suite

## [0.1.0] - 2025-11-08

### Phase 0 Complete: Foundation & Scaffolding

**Status**: ✅ Production-ready foundation established

#### Added

**Core Infrastructure**:

- Poetry project setup with Python 3.12 support
- Modular package structure (ingestion, detection, correction, output, utils)
- Dependency management with optional groups (ml, api, dev)
- Structured logging with structlog + rich console output
- Pre-commit hooks (Black, Ruff, MyPy, Bandit, Safety)
- GitHub Actions CI/CD pipeline
- Test suite with 163 tests achieving 94.46% coverage

**JSON Schema (Pydantic v2)**:

- `DetectedIssue`: Image quality issue representation with severity levels
- `DocumentElement`: Document elements with hybrid IQA support
- `PageMetadata`: Per-page metadata with transform history tracking
- `DocumentMetadata`: Complete document metadata with JSON I/O
- COCO-aligned bounding boxes (`[x, y, width, height]`)

**PDF Ingestion**:

- PyMuPDF-based PDF extraction (src/ingestion/pdf_loader.py)
- Multi-format image loading (PNG, JPEG, TIFF)
- DPI standardization to 300 DPI
- Image normalization and validation

**Text Detection Gate**:

- Fast ensemble heuristics (< 10ms per page)
- Stroke width analysis
- Connected component analysis
- Edge density pattern detection

**Classical IQA**:

- Blur detection using Laplacian variance
- Skew detection using Hough transform
- Contrast assessment via histogram analysis
- Configurable detection thresholds

**Correction Pipeline**:

- Deskew correction with affine rotation
- CLAHE contrast enhancement
- Unsharp mask sharpening
- Non-local means denoising
- Guardrails to prevent over-correction

**CLI Tool**:

- Click-based command-line interface
- Single file and batch processing modes
- JSON metadata output
- Dry run mode for detection-only workflows

**Documentation**:

- README with quick start guide
- PROJECT_PLAN (50+ pages)
- ARCHITECTURE_SUMMARY with design rationale
- ARCHITECTURE_CORRECTION (hybrid IQA explanation)
- DECISION_MATRIX for tracking critical decisions
- PHASE_0_COMPLETE summary

#### Architecture Decisions

**Hybrid IQA Approach**:

- **Problem**: Text documents contain embedded images requiring independent quality assessment
- **Solution**: YOLOv8 layout detection (Phase 3) extracts elements → per-element IQA
- **Implementation**: `quality_issues` field in `DocumentElement` schema

**Text Detection Gate**:

- **Problem**: Mixed document types (pure images vs. text documents)
- **Solution**: Fast text detection gate routes to specialized processing branches
- **Performance**: < 10ms routing decision avoids expensive YOLOv8 for pure images

**COCO Format Alignment**:

- **Decision**: Use `[x, y, width, height]` bounding boxes (not `[x1, y1, x2, y2]`)
- **Rationale**: Industry standard for LayoutParser, Detectron2, COCO datasets
- **Impact**: Simplifies downstream integration

**300 DPI Standard**:

- **Decision**: Standardize all pages to 300 DPI
- **Rationale**: Optimal balance for OCR quality and processing speed
- **Validation**: Industry standard for document digitization

#### Quality Metrics

- **Test Coverage**: 94.46% (163 tests passing)
- **Docstring Coverage**: 100% (Google-style docstrings)
- **Code Quality**: Black formatting, Ruff linting, MyPy type checking
- **Security**: Bandit static analysis, Safety dependency scanning

#### Dependencies

**Core**:

- Python >= 3.11, < 3.13
- PyMuPDF >= 1.25.1 (PDF processing)
- Pillow >= 11.0.0 (image I/O)
- opencv-python >= 4.8.0 (computer vision)
- pydantic >= 2.10.4 (schema validation)
- click >= 8.1.0 (CLI framework)
- structlog >= 24.4.0 (structured logging)
- rich >= 13.9.4 (console output)

**ML Group** (Phase 2+):

- torch >= 2.0.0
- torchvision >= 0.15.0
- ultralytics >= 8.0.0 (YOLOv8)
- albumentations >= 1.3.0 (data augmentation)

**API Group** (Phase 4):

- fastapi >= 0.115.14
- uvicorn >= 0.34.0

**Dev Group**:

- pytest >= 8.3.4
- black >= 25.9.0
- ruff >= 0.8.5
- mypy >= 1.14.1
- pre-commit >= 4.0.1
- bandit >= 1.8.0
- safety >= 3.7.0

## [0.0.1] - 2025-10-20

### Initial Project Setup

#### Added

- Repository initialization
- Basic README with project overview
- MIT License
- .gitignore configuration
- Initial project structure planning

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality (backward compatible)
- **PATCH** version: Bug fixes (backward compatible)

### Pre-1.0 Development

Versions 0.x.y are in active development:

- **0.x.0**: Phase completions (0.1.0 = Phase 0, 0.2.0 = Phase 1, etc.)
- **0.x.y**: Patch releases within a phase

### 1.0 Release Criteria

Version 1.0.0 will be released after Phase 4 completion when:

- [ ] All phases 0-4 complete
- [ ] REST API deployed and tested
- [ ] Production monitoring operational
- [ ] Full documentation published
- [ ] Performance targets met
- [ ] Security audit passed

## Migration Guides

### Upgrading to 0.1.0 from 0.0.1

No migration required - this is the first functional release.

### Future Breaking Changes (Planned)

**0.2.0 (Phase 1 → Phase 2)**:

- Classical IQA detectors will be deprecated in favor of ML models
- Detection API will maintain backward compatibility
- Configuration format unchanged

**0.3.0 (Phase 2 → Phase 3)**:

- Layout detection added (text documents only)
- Schema extended with `DocumentElement.quality_issues`
- Hybrid IQA replaces full-page IQA for text documents
- CLI flag changes for layout detection options

**1.0.0 (Phase 4 → Production)**:

- REST API stabilization
- Configuration format freeze
- Long-term support commitment

## Type of Changes

This changelog uses the following categories:

- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Features marked for future removal
- **Removed**: Deleted features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

## Links

- [Roadmap](roadmap.md) - Future development plans
- [Project Plan](../../PROJECT_PLAN.md) - Detailed implementation guide
- [GitHub Releases](https://github.com/williaby/image-preprocessing-detector/releases) - Release downloads
- [Issues](https://github.com/williaby/image-preprocessing-detector/issues) - Bug reports and feature requests

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines on contributing to this project.

---

**Note**: This changelog is automatically updated for each release. For unreleased changes, see the [Unreleased] section at the top of this document.
