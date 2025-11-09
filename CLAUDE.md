# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Project Context**: Extends global CLAUDE.md standards from `~/.claude/CLAUDE.md`. Only project-specific configurations documented below.

## Claude Code Supervisor Role (CRITICAL)

**Claude Code acts as the SUPERVISOR for all development tasks and MUST:**

1. **Always Use TodoWrite Tool**: Create and maintain TODO lists for ALL tasks to track progress
2. **Assign Tasks to Agents**: Each TODO item should be assigned to a specialized agent via Zen MCP Server
3. **Review Agent Work**: Validate all agent outputs before proceeding to next steps
4. **Use Temporary Reference Files**: Create `.tmp-` prefixed files in `tmp_cleanup/` folder to store detailed context that might be lost during compaction
5. **Maintain Continuity**: Use reference files to preserve TODO details across conversation compactions

### Agent Assignment Patterns

```bash
# Always assign TODO items to appropriate agents:
- Security tasks → Security Agent (via mcp__zen-core__secaudit)
- Code reviews → Code Review Agent (via mcp__zen-core__codereview)
- Testing → Test Engineer Agent (via mcp__zen-core__testgen)
- Documentation → Documentation Agent (via mcp__zen-core__docgen)
- Debugging → Debug Agent (via mcp__zen-core__debug)
- Analysis → Analysis Agent (via mcp__zen-core__analyze)
- Refactoring → Refactor Agent (via mcp__zen-core__refactor)
```

### Temporary Reference Files (Anti-Compaction Strategy)

**ALWAYS create temporary reference files when:**
- TODO list contains >5 items
- Complex implementation details need preservation
- Multi-step workflows span multiple conversation turns
- Agent assignments and progress need tracking

**Naming Convention**: `tmp_cleanup/.tmp-{task-type}-{timestamp}.md` (e.g., `tmp_cleanup/.tmp-iqa-implementation-20250205.md`)

### Supervisor Workflow Patterns (MANDATORY)

**Every development task MUST follow this pattern:**

1. **Create TODO List**: Use TodoWrite tool to break down the task into specific, actionable items
2. **Agent Assignment**: Assign each TODO item to the most appropriate specialized agent
3. **Progress Tracking**: Mark items as in_progress when assigned, completed when validated
4. **Reference File Creation**: For complex tasks, create `.tmp-` reference files immediately
5. **Agent Output Validation**: Review all agent work before marking items complete

**For complex tasks requiring multiple agents:**

1. **Sequential Dependencies**: Use TodoWrite to show dependencies between tasks
2. **Parallel Execution**: Assign independent tasks to multiple agents simultaneously
3. **Integration Points**: Create specific TODO items for integrating agent outputs
4. **Quality Gates**: Assign review tasks to appropriate agents after implementation

## Project Overview

**Image Preprocessing Detector** - Intelligent detection system for RAG applications that analyzes documents (PDFs, images) and identifies required preprocessing steps before vector database ingestion.

**Key Innovation**: Multi-stage pipeline with **text detection gate** that routes documents to specialized processing paths:
- **No-text path**: Classical CV + ML IQA (skew, blur, contrast, noise)
- **Text-detected path**: YOLOv8 layout detection + hybrid IQA on embedded images

**Current Phase**: Phase 0 (Foundation) → Phase 1 (MVP with Classical Methods)

## Development Philosophy (MANDATORY)

**Security First** → **Quality Standards** → **Documentation** → **Testing** → **Collaboration**

### Core Principles

1. **Security First**: Always validate keys, encrypt secrets, scan dependencies
2. **Reuse First**: Check existing repositories for solutions before building new code
3. **Configure, Don't Build**: Prefer configuration and orchestration over custom implementation
4. **Quality Standards**: Maintain consistent code quality across all projects
5. **Documentation**: Keep documentation current and well-formatted
6. **Testing**: Maintain high test coverage and run tests before commits
7. **Collaboration**: Use consistent Git workflows and clear commit messages

## Naming Conventions (MANDATORY COMPLIANCE)

**Core Components:**
- **Module Names**: snake_case (e.g., `iqa_classical`, `text_gate`)
- **Classes**: PascalCase (e.g., `DocumentMetadata`, `DetectedIssue`)
- **Functions**: snake_case (e.g., `detect_skew`, `apply_correction`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_DPI`, `MIN_CONFIDENCE`)

**Code & Files:**
- **Python Files**: snake_case.py
- **Test Files**: test_*.py
- **Git Branches**: kebab-case with prefixes (e.g., `feature/add-layout-detection`, `fix/skew-threshold`)

## Common Commands

### Development Workflow

```bash
# Install dependencies (includes dev tools)
poetry install --with dev

# Install with ML dependencies (Phase 2+)
poetry install --with dev,ml

# Setup pre-commit hooks (required before first commit)
poetry run pre-commit install

# Run CLI tool
poetry run imgprep --help
poetry run imgprep process input.pdf --output result.json
```

### Testing

```bash
# Run all tests with coverage (80% minimum enforced)
poetry run pytest -v

# Run specific test categories
poetry run pytest -v -m unit               # Unit tests only
poetry run pytest -v -m integration        # Integration tests only
poetry run pytest -v -m "not slow"         # Exclude slow tests

# Run single test file
poetry run pytest tests/unit/test_schema.py -v

# Run single test function
poetry run pytest tests/unit/test_schema.py::test_detected_issue_validation -v

# Run with coverage report
poetry run pytest --cov=src --cov-report=html --cov-report=term-missing

# Run tests in parallel (faster for large suites)
poetry run pytest -n auto
```

### Code Quality

```bash
# Format code (required before commit)
poetry run black src tests

# Lint and auto-fix
poetry run ruff check --fix src tests

# Type checking (strict on src/, relaxed on tests/)
poetry run mypy src

# Run all pre-commit hooks manually
poetry run pre-commit run --all-files

# Security scanning
poetry run bandit -r src
poetry run safety check
```

### Validation Scripts

```bash
# Run standalone validation scripts (not part of test suite)
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH poetry run python validation/validate_*.py
```

### Security Requirements (MANDATORY)

```bash
# Key validation (MUST pass before development)
gpg --list-secret-keys  # Must show GPG key for .env encryption
ssh-add -l              # Must show SSH key for signed commits
git config --get user.signingkey  # Must be configured for signed commits

# Security scanning
poetry run bandit -r src                    # Python security analysis
poetry run safety check                     # Dependency vulnerability check
```

## Architecture - Big Picture

### Pipeline Flow (Text Detection Fork with DPI Upscaling)

The system uses a **text detection gate** to route documents to specialized processing, with **automatic DPI upscaling** (Phase 1B) for low-resolution inputs:

```
PDF/Image Input
    ↓
[Pre-flight Analysis] (src/ingestion/) - DPI detection & upscaling (Phase 1B)
    ↓ (Auto-upscale if < 300 DPI)
[Ingestion] (src/ingestion/) - Standardize to 300 DPI images
    ↓
[Text Gate] (src/detection/text_gate.py) - Fast ensemble heuristics
    ↓              ↓
[NO TEXT]      [TEXT DETECTED]
    ↓              ↓
Classical IQA  YOLOv8 Layout → Extract elements → Per-element IQA
    ↓              ↓
[Correction] (src/correction/) - Deskew, CLAHE, sharpening, denoising
    ↓              ↓
[JSON Output] (src/output/) - COCO-aligned metadata
```

**Phase 1B: DPI Upscaling (NEW)**
- **Technology**: Proven implementation from data_ingestor project (Phase 1C)
- **DPI Detection**: PyMuPDF-based automatic resolution analysis
- **Upscaling Trigger**: Documents below 300 DPI are automatically upscaled
- **Algorithm Options**: 5 OpenCV algorithms (lanczos, bicubic, inter_linear, inter_cubic, inter_area)
- **Performance**: 310-360ms processing time, <2GB memory usage, page-by-page processing
- **Quality**: 100% test success rate, 100% DPI improvement (e.g., 150→300 DPI)
- **Safety**: Graceful fallback to original on errors, high-res documents correctly skipped
- **Configuration**: 5 settings (enable_pdf_upscaling, pdf_min_dpi, pdf_target_dpi, pdf_upscale_algorithm, pdf_preserve_original_on_error)

**Critical Design Decision**: Hybrid IQA approach required because:
- Text documents contain embedded images (tables, figures, photos)
- Each embedded image needs independent quality assessment
- Layout detection (YOLOv8) identifies elements → IQA runs per-element
- See [ARCHITECTURE_CORRECTION.md](ARCHITECTURE_CORRECTION.md) for detailed rationale

**Why Text Detection Gate?**
- **Problem**: Mixed document types require different processing strategies
- **Solution**: Fast text detection gate (< 10ms) routes to appropriate branch, avoiding expensive YOLOv8 inference for pure images

### Module Responsibilities

**[schema.py](src/image_preprocessing_detector/schema.py)**
- Pydantic v2 models for JSON I/O
- `DetectedIssue`, `DocumentElement`, `PageMetadata`, `DocumentMetadata`
- COCO-aligned bounding boxes (`[x, y, width, height]`) for LayoutParser integration
- **Hybrid IQA**: `quality_issues` field in `DocumentElement` for per-element assessment

**[ingestion/](src/image_preprocessing_detector/ingestion/)** (Phase 1 + Phase 1B)
- **Phase 1B: DPI Upscaling**
  - [pdf_resolution.py](src/image_preprocessing_detector/ingestion/pdf_resolution.py): DPI detection and analysis
  - [pdf_upscaler.py](src/image_preprocessing_detector/ingestion/pdf_upscaler.py): OpenCV-based upscaling (5 algorithms)
  - [pdf_analyzer.py](src/image_preprocessing_detector/ingestion/pdf_analyzer.py): Pre-flight analysis orchestration
- **Phase 1: Basic Ingestion**
  - PDF → standardized images (300 DPI)
  - Image normalization and validation
  - Multi-format support (PDF, PNG, JPEG, TIFF)

**[detection/](src/image_preprocessing_detector/detection/)** (Phase 1-3)
- [text_gate.py](src/image_preprocessing_detector/detection/text_gate.py): Fast text presence detection (ensemble: stroke density, connected components, edge density)
- [iqa_classical.py](src/image_preprocessing_detector/detection/iqa_classical.py): Classical CV detectors (Hough transform skew, Laplacian blur, histogram contrast)
- (Phase 2+): ML-based IQA (MobileNetV3/EfficientNet)
- (Phase 3): YOLOv8 layout detection (tables, images, handwriting, formulas)

**[correction/](src/image_preprocessing_detector/correction/)** (Phase 1)
- OpenCV-based corrections with guardrails
- Deskew, CLAHE enhancement, sharpening, denoising
- Transform history tracking for audit trail

**[output/](src/image_preprocessing_detector/output/)** (Phase 1)
- JSON generation with COCO alignment
- Confidence scores, bounding boxes, transform history
- Integration with downstream processors (LayoutParser, Tesseract, Marker, Docling)

**[utils/](src/image_preprocessing_detector/utils/)**
- Structured logging: `structlog` + `rich` console output
- Telemetry and monitoring hooks (Phase 4)

### Data Flow Pattern

1. **Pre-flight Analysis** (Phase 1B): DPI detection → automatic upscaling if <300 DPI
2. **Ingestion**: PyMuPDF extracts PDF pages → Pillow/OpenCV standardizes to 300 DPI
3. **Text Gate**: Fast heuristics (< 10ms) → route to appropriate branch
4. **Detection Branch**:
   - No-text: Classical IQA on full page
   - Text: YOLOv8 layout → extract elements → IQA per-element
5. **Correction**: Apply OpenCV transforms with confidence-based thresholds
6. **Output**: Serialize to JSON with COCO-aligned metadata (includes upscaling metadata)

## Project-Specific Standards

### Coverage Requirements

- **Minimum**: 80% enforced via `--cov-fail-under=80`
- **MyPy**: Strict mode on `src/`, relaxed on `tests/`
- **Pre-commit**: All hooks must pass before commit (Black, Ruff, MyPy, Bandit)

### Performance Targets (Phase 3+)

| Metric | Target | Notes |
|--------|--------|-------|
| IQA mAP | > 0.88 | Multi-label classification |
| Layout mAP@.50 | > 0.82 | Object detection |
| Latency (GPU) | < 150ms/page | With T4 GPU |
| Throughput | > 6 pages/sec | Per GPU worker |

### JSON Schema (COCO Alignment)

**Critical**: Bounding boxes must use COCO format `[x, y, width, height]` (not `[x1, y1, x2, y2]`) for LayoutParser compatibility.

See [schema.py](src/image_preprocessing_detector/schema.py) for complete Pydantic v2 models.

### Phased Development

- **Phase 0** (Weeks 1-3): Foundation & scaffolding (COMPLETE)
- **Phase 1** (Weeks 4-7): MVP with classical methods (IN PROGRESS)
- **Phase 1B** (Weeks 7-8): DPI detection & upscaling (PLANNED - before Phase 2)
- **Phase 2** (Weeks 8-11): ML for image quality
- **Phase 3** (Weeks 12-16): ML for document layout
- **Phase 4** (Weeks 17-20): Production hardening
- **Phase 5** (Ongoing): Continuous improvement

**Phase 1B Integration Notes:**
- Implements proven upscaling technology from data_ingestor project (Phase 1C)
- Required for consistent 300 DPI input to downstream ML models
- Source code available: `/home/byron/dev/data_ingestor/src/data_ingestor/utils/`
- Handoff documentation: `/home/byron/dev/data_ingestor/docs/PHASE1C_HANDOFF.md`

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for complete 50+ page implementation roadmap.

## CI/CD Pipeline

**GitHub Actions** ([.github/workflows/ci.yml](.github/workflows/ci.yml)):
- Triggers: PRs to main/develop/feature branches, pushes to main/develop
- Jobs: setup-optimized (10min), test (30min), quality-checks (12min), ci-gate
- Coverage reports uploaded to Codecov

**Quality Gates**:
1. All tests pass with 80%+ coverage
2. Black, Ruff, MyPy checks pass
3. Bandit security scan passes
4. Safety dependency scan passes

## Key Technologies

**Classical CV** (Phase 1):
- OpenCV 4.8+: Hough transform, Laplacian, histogram analysis
- PyMuPDF: PDF extraction
- Pillow: Image I/O and preprocessing

**Deep Learning** (Phase 2-3):
- PyTorch 2.0+: Model training
- YOLOv8: Layout detection (tables, images, handwriting, formulas)
- MobileNetV3/EfficientNet: IQA multi-label classification
- ONNX Runtime: Production inference optimization

**Framework**:
- Click: CLI framework
- Pydantic v2: JSON schema and validation
- Structlog + Rich: Structured logging with console output

## Pre-Commit Linting Checklist

Before committing ANY changes, ensure:

- [ ] **TODO Management**: Was TodoWrite used for task tracking?
- [ ] **Agent Assignment**: Were tasks assigned to appropriate specialized agents?
- [ ] **Reference Files**: Were temporary reference files created for complex tasks?
- [ ] **Agent Validation**: Was all agent work reviewed and validated?
- [ ] **Security Keys**: GPG and SSH keys present and validated
- [ ] **Code Quality**: Black formatting, Ruff linting, MyPy type checking passed
- [ ] **Security Scans**: Bandit and Safety checks completed successfully
- [ ] **Test Coverage**: All tests pass with minimum 80% coverage
- [ ] **Configuration**: `.env` file properly configured with encrypted secrets (if applicable)
- [ ] **Git Signing**: Commits are signed (Git signing key configured)
- [ ] **Documentation**: Code changes include relevant documentation updates
- [ ] **File-Specific Linting**: Appropriate linter run for modified file types

## Troubleshooting

### Tests Failing

```bash
# Check coverage threshold
poetry run pytest --cov=src --cov-report=term-missing

# Run specific failing test
poetry run pytest tests/path/to/test.py::test_name -v

# Check pre-commit hooks
poetry run pre-commit run --all-files
```

### Type Errors

```bash
# MyPy strict on src/, relaxed on tests/
poetry run mypy src

# Check specific file
poetry run mypy src/image_preprocessing_detector/schema.py
```

### Import Errors in Validation Scripts

```bash
# Validation scripts need PYTHONPATH set
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH poetry run python validation/script.py
```

### Database Connection Issues

*Not applicable yet - database integration in Phase 4*

### Performance Issues

For Phase 3+ performance troubleshooting:
- Check GPU availability: `nvidia-smi`
- Monitor batch processing: Review logs in `logs/`
- Profile slow operations: Use `cProfile` on specific modules

---

*This configuration extends global CLAUDE.md standards. For detailed specifications on security, testing, and Git workflows, see `~/.claude/CLAUDE.md` and referenced files in `/standards/` directory.*
