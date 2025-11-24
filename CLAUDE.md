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

**Project A - Preprocessing, IQA & Coarse Layout Gateway** - Front door for the four-project RAG document pipeline. Analyzes raw documents (PDFs, images), assesses quality, applies corrections, and provides intelligent routing metadata to downstream OCR processing.

### Four-Project RAG Pipeline Architecture

```
Project A (THIS REPO)     →    Project B          →    Project C         →    Project D
Preprocessing & IQA              OCR Orchestration       Fusion & Trust         Vector Indexing
─────────────────────           ─────────────────       ──────────────         ───────────────
• IQA & Corrections             • Full Layout           • Multi-Engine         • Embeddings
• Text Gate                     • Reading Order           Fusion               • Vector DB
• DQS Calculation               • Table Structure       • Trust Scoring        • Retrieval
• Routing Metadata              • Multi-Engine OCR      • RAG Chunking         • Search

OUTPUT:                         OUTPUT:                 OUTPUT:                OUTPUT:
DocumentMetadata.json           OCRDocument.json        FusedDocument.json     Vector DB Entries
+ Corrected Images
```

**Project A Mission**: Deliver clean, corrected, quality-scored page images with reliable metadata that determines which workflows Project B should use.

**Key Innovation**: Multi-stage pipeline with **text detection gate** that routes documents to specialized processing paths:
- **No-text path**: Classical CV + ML IQA (teacher-student ResNet architecture)
- **Text-detected path**: Layout-lite classification + hybrid IQA on embedded images

**Scope Boundaries**:
- **IN SCOPE**: IQA, corrections, DQS, layout-lite (coarse page attributes), routing recommendations
- **OUT OF SCOPE**: Full layout detection, table structure, reading order (Project B responsibility)

**Current Phase**: Phase 0 (Foundation) → Phase 2 (Teacher-Student ML IQA)

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
poetry run ruff format src tests

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

### Modal & Training (Phase 2+)

**Status**: ✅ Modal setup complete, ready for training runs

**Quick Reference**: [docs/reference/MODAL_QUICK_REFERENCE.md](docs/reference/MODAL_QUICK_REFERENCE.md)

```bash
# Start training (ready to use)
poetry run modal run modal/train_phase2_iqa.py      # Phase 2: ResNet IQA

# Monitor training
poetry run modal app logs image-detection --follow  # Stream logs
open https://modal.com/apps                         # Dashboard

# Cost tracking
poetry run modal profile current                    # Check usage

# Verify setup (optional)
poetry run modal token current                      # Check authentication
poetry run modal secret list | grep gcs-credentials # Check GCS credentials
```

**Key Training Details:**

- **Model Architecture**: ResNet-50 teacher → ResNet-18 student (NOT MobileNetV3/EfficientNet)
- **Dataset**: OHR-Bench via GCS (~18 GB)
- **GPU**: T4 (16GB) or A10 (24GB)
- **Duration**: 12-24 hours (continuous, no session timeouts)
- **Cost**: ~$7-14 or $0 with $30/month free tier

**Quick Reference includes**: Complete training workflow, monitoring, debugging, cost management, troubleshooting

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

### OSV Scanner (Optional - Local Development)

OpenSSF Scorecard uses osv-scanner for vulnerability detection. Install locally to test osv-scanner.toml exceptions before pushing:

```bash
# Install osv-scanner (requires Go 1.21+)
go install github.com/google/osv-scanner/cmd/osv-scanner@latest

# Verify installation
osv-scanner --version

# Run scan (automatically respects osv-scanner.toml exceptions)
osv-scanner --lockfile=poetry.lock

# Expected output: 0 vulnerabilities (all false positives documented in osv-scanner.toml)

# Scan with detailed output
osv-scanner --lockfile=poetry.lock --format=json --output=osv-local-results.json
```

**Key Features:**
- **Automatic Exception Handling**: Reads `osv-scanner.toml` from repository root
- **Multi-Ecosystem**: Supports Python, npm, Go, Rust (vs. Safety Python-only)
- **OSV Database**: Same database used by OpenSSF Scorecard and Google
- **CI Integration**: Runs automatically in `security-analysis.yml` workflow

**When to Run Locally:**
- After updating dependencies (`poetry add/update`)
- Before creating PR with dependency changes
- To verify `osv-scanner.toml` exceptions work correctly
- When OpenSSF Scorecard reports new vulnerabilities

**Not Required**: CI runs osv-scanner automatically on all PRs and scheduled runs.

**Alternative (without Go)**: Use GitHub Actions logs from `security-analysis.yml` → `OSV Vulnerability Scanner` job to review scan results.

## Architecture - Big Picture

### Pipeline Flow (Project A Only)

The system uses a **text detection gate** to route documents to specialized processing, with **automatic DPI upscaling** (Phase 4) for low-resolution inputs:

```
PDF/Image Input
    ↓
[Pre-flight Analysis] (src/ingestion/) - DPI detection & upscaling (Phase 4)
    ↓ (Auto-upscale if < 300 DPI)
[Ingestion] (src/ingestion/) - Standardize to 300 DPI images
    ↓
[PDF Type Classification] - image_only/born_digital/hybrid (Phase 8)
    ↓
[Text Gate] (src/detection/text_gate.py) - Fast ensemble heuristics
    ↓              ↓
[NO TEXT]      [TEXT DETECTED]
    ↓              ↓
Classical IQA  Layout-Lite Classifier → Coarse page attributes
    ↓              ↓
ML IQA         ML IQA (Teacher-Student ResNet)
(Student)      (Student + selective Teacher)
    ↓              ↓
[Correction] (src/correction/) - Deskew, CLAHE, sharpening, denoising
    ↓              ↓
[DQS Calculation] (Phase 8) - Degradation + Structural Complexity scores
    ↓              ↓
[Routing Recommendation] (Phase 8) - ocr_fast/advanced, vision_simple/structured
    ↓              ↓
[JSON Output] (src/output/) - DocumentMetadata.json + corrected images
    ↓
HANDOFF TO PROJECT B (OCR Orchestration)
```

**Phase 4: DPI Upscaling**
- **Technology**: Proven implementation from data_ingestor project (Phase 1C)
- **DPI Detection**: PyMuPDF-based automatic resolution analysis
- **Upscaling Trigger**: Documents below 300 DPI are automatically upscaled
- **Algorithm Options**: 5 OpenCV algorithms (lanczos, bicubic, inter_linear, inter_cubic, inter_area)
- **Performance**: 310-360ms processing time, <2GB memory usage, page-by-page processing
- **Quality**: 100% test success rate, 100% DPI improvement (e.g., 150→300 DPI)
- **Safety**: Graceful fallback to original on errors, high-res documents correctly skipped
- **Configuration**: 5 settings (enable_pdf_upscaling, pdf_min_dpi, pdf_target_dpi, pdf_upscale_algorithm, pdf_preserve_original_on_error)

**Phase 2: Teacher-Student ML IQA**
- **Student Model** (ResNet-18): Default production inference, fast and accurate
- **Teacher Model** (ResNet-50): High-capacity model for difficult/high-risk cases
- **Selective Teacher Inference**: Triggered by uncertainty, discrepancy, or document risk
- **Device Priority**: Local GPU → Local CPU → Modal GPU
- See [docs/development/RAG Pipeline/project-a-project-plan.md](docs/development/RAG Pipeline/project-a-project-plan.md)

**Phase 6: Layout-Lite (NOT Full Layout)**
- **Coarse page attributes only**: layout_type, has_tables, has_figures, has_dense_math, has_handwriting
- **Page attributes**: fuzzy_scan, watermark, colorful_background
- **Structural complexity score**: 0-1 metric for routing decisions
- **NOT DocLayNet-style semantic layout** (that's Project B)

**Phase 8: DQS & Routing**
- **Document Quality Score**: Aggregates degradation (IQA) + structural complexity (layout-lite)
- **Pre-OCR Risk**: Single 0-1 score combining quality and layout signals
- **Routing Recommendations**: 4 strategies based on DQS, pdf_type, and complexity

**Why Text Detection Gate?**
- **Problem**: Mixed document types require different processing strategies
- **Solution**: Fast text detection gate (< 10ms) routes to appropriate branch, avoiding expensive layout inference for pure images

### Module Responsibilities

**[schema.py](src/image_preprocessing_detector/schema.py)**
- Pydantic v2 models for JSON I/O
- `DetectedIssue`, `DocumentElement`, `PageMetadata`, `DocumentMetadata`
- COCO-aligned bounding boxes (`[x, y, width, height]`) for LayoutParser integration
- **Hybrid IQA**: `quality_issues` field in `DocumentElement` for per-element assessment

**[ingestion/](src/image_preprocessing_detector/ingestion/)** (Phase 0,4)
- **Phase 4: DPI Upscaling**
  - [pdf_resolution.py](src/image_preprocessing_detector/ingestion/pdf_resolution.py): DPI detection and analysis
  - [pdf_upscaler.py](src/image_preprocessing_detector/ingestion/pdf_upscaler.py): OpenCV-based upscaling (5 algorithms)
  - [pdf_analyzer.py](src/image_preprocessing_detector/ingestion/pdf_analyzer.py): Pre-flight analysis orchestration
- **Phase 0: Basic Ingestion**
  - PDF → standardized images (300 DPI)
  - Image normalization and validation
  - Multi-format support (PDF, PNG, JPEG, TIFF)

**[detection/](src/image_preprocessing_detector/detection/)** (Phase 2,4,6)
- [text_gate.py](src/image_preprocessing_detector/detection/text_gate.py): Fast text presence detection (ensemble: stroke density, connected components, edge density)
- [iqa_classical.py](src/image_preprocessing_detector/detection/iqa_classical.py): Classical CV detectors (Phase 4: Hough skew, Laplacian blur, histogram contrast, lighting, JPEG blockiness)
- [iqa_ml.py](src/image_preprocessing_detector/detection/iqa_ml.py): Teacher-student ML IQA (Phase 2: ResNet-50 teacher, ResNet-18 student, selective inference)
- [layout_lite.py](src/image_preprocessing_detector/detection/layout_lite.py): Coarse layout classification (Phase 6: page attributes, complexity scoring, NOT full semantic layout)

**[correction/](src/image_preprocessing_detector/correction/)** (Phase 4)
- OpenCV-based corrections with guardrails
- Deskew, CLAHE enhancement, sharpening, denoising
- Transform history tracking for audit trail

**[routing/](src/image_preprocessing_detector/routing/)** (Phase 8)
- [dqs.py](src/image_preprocessing_detector/routing/dqs.py): Document Quality Score calculation (degradation + complexity)
- [pdf_classifier.py](src/image_preprocessing_detector/routing/pdf_classifier.py): PDF type classification (image_only/born_digital/hybrid)
- [recommendation.py](src/image_preprocessing_detector/routing/recommendation.py): OCR routing logic (4 strategies)

**[output/](src/image_preprocessing_detector/output/)** (Phase 0,8)
- JSON generation with updated schema including routing metadata
- DocumentMetadata.json with pdf_type, DQS, pre_ocr_risk, ocr_routing_recommendation
- Corrected image output to filesystem for Project B handoff

**[utils/](src/image_preprocessing_detector/utils/)**
- Structured logging: `structlog` + `rich` console output
- Device probing utilities (GPU/CPU/Modal) - Phase 0
- Telemetry and monitoring hooks (Phase 10)

### Data Flow Pattern

1. **Pre-flight Analysis** (Phase 4): DPI detection → automatic upscaling if <300 DPI
2. **Ingestion** (Phase 0): PyMuPDF extracts PDF pages → Pillow/OpenCV standardizes to 300 DPI
3. **PDF Type Classification** (Phase 8): Classify as image_only/born_digital/hybrid
4. **Text Gate** (Phase 0): Fast heuristics (< 10ms) → route to appropriate branch
5. **Detection Branch**:
   - No-text: Classical IQA (Phase 4) + Student ML IQA (Phase 2)
   - Text: Layout-lite classification (Phase 6) + Student ML IQA (Phase 2) + selective Teacher inference
6. **Correction** (Phase 4): Apply OpenCV transforms with confidence-based thresholds
7. **DQS & Routing** (Phase 8): Calculate quality scores + generate routing recommendations
8. **Output** (Phase 8): Serialize DocumentMetadata.json + write corrected images → handoff to Project B

## Project-Specific Standards

### Coverage Requirements

- **Minimum**: 80% enforced via `--cov-fail-under=80`
- **MyPy**: Strict mode on `src/`, relaxed on `tests/`
- **Pre-commit**: All hooks must pass before commit (Ruff format, Ruff lint, MyPy, Bandit)

### Performance Targets

**ML IQA (Phase 2)**:

| Metric | Target | Notes |
|--------|--------|-------|
| Student (ResNet-18) CPU | ≤40ms/page (target), ≤100ms (acceptable) | Production default |
| Student (ResNet-18) GPU | ≤10ms/page (target), ≤25ms (acceptable) | Local GPU preferred |
| Teacher (ResNet-50) GPU | ≤30ms/page | Flagged pages only |
| IQA mAP | > 0.88 | Multi-label classification on OHR-Bench |

**End-to-End (Phase 10)**:

| Metric | Target | Notes |
|--------|--------|-------|
| Latency (GPU) | <150ms/page | Full pipeline with GPU |
| Latency (CPU) | <500ms/page | Full pipeline CPU-only |
| Throughput (GPU) | ≥6 pages/sec/worker | With T4 GPU |
| Throughput (CPU) | ≥2 pages/sec/worker | CPU-only mode |

### JSON Schema (COCO Alignment)

**Critical**: Bounding boxes must use COCO format `[x, y, width, height]` (not `[x1, y1, x2, y2]`) for LayoutParser compatibility.

See [schema.py](src/image_preprocessing_detector/schema.py) for complete Pydantic v2 models.

### Phased Development

**NEW PHASE STRUCTURE** (aligned with RAG Pipeline architecture):

- **Phase 0** (Week 0-1): Project Setup - **COMPLETE**
  - Project skeleton, Modal workspace, GPU/CPU device probing
  - Configuration system (YAML) with teacher fallback settings
  - Logging/telemetry scaffolding

- **Phase 2** (Week 2-4): ResNet Teacher & Student ML IQA - **PLANNED**
  - Multi-head ResNet-50 teacher architecture
  - Knowledge distillation to ResNet-18 student
  - Validation on OHR-Bench (document-specific IQA)
  - Export to ONNX + TorchScript, model registry integration
  - Cost: ~$5-10 (Modal GPU training)

- **Phase 4** (Week 5-6): Classical IQA + DPI Upscaling - **PLANNED**
  - Laplacian blur, wavelet noise, Hough skew, lighting metrics, JPEG blockiness
  - Student vs classical discrepancy threshold tuning
  - **DPI upscaling integration** (from data_ingestor Phase 1C)
  - Source: `/home/byron/dev/data_ingestor/src/data_ingestor/utils/`

- **Phase 6** (Week 6-8): Layout-Lite Detection - **PLANNED**
  - DocLayout-YOLO or YOLOv8-nano for coarse page attributes (NOT full semantic layout)
  - Model selection: `configs/models/doclayout_yolo.yaml`
  - Handwriting presence classifier, structural complexity scorer
  - OmniDocBench-style page attributes

- **Phase 8** (Week 9): DQS & Routing - **PLANNED**
  - Document Quality Score (degradation + complexity)
  - PDF type classification, pre-OCR risk scoring
  - Routing recommendation logic (4 strategies)
  - JSON schema output with complete routing metadata
  - Device priority execution (Local GPU → CPU → Modal GPU)

- **Phase 10** (Week 10): Validation & Documentation - **PLANNED**
  - End-to-end pipeline benchmarking
  - Teacher vs student performance analysis
  - Stress testing (large batches, cost tracking)
  - Documentation updates, PlantUML diagrams

**REMOVED PHASES** (out of Project A scope):
- ~~Phase 1/1B (old numbering)~~ → Absorbed into Phases 0 and 4
- ~~Table Structure Extraction~~ → Project B responsibility
- ~~Reading Order Prediction~~ → Project B responsibility
- ~~Full DocLayNet-style layout~~ → Project B responsibility

See [docs/development/RAG Pipeline/project-a-project-plan.md](docs/development/RAG Pipeline/project-a-project-plan.md) for complete implementation plan.

## CI/CD Pipeline

**GitHub Actions** ([.github/workflows/ci.yml](.github/workflows/ci.yml)):
- Triggers: PRs to main/develop/feature branches, pushes to main/develop
- Jobs: setup-optimized (10min), test (30min), quality-checks (12min), ci-gate
- Coverage reports uploaded to Codecov

**Quality Gates**:
1. All tests pass with 80%+ coverage
2. Ruff format, Ruff lint, MyPy checks pass
3. Bandit security scan passes
4. Safety dependency scan passes

## Key Technologies

**Classical CV** (Phase 4):
- OpenCV 4.8+: Hough transform, Laplacian, histogram analysis, DPI upscaling
- PyMuPDF: PDF extraction and DPI detection
- Pillow: Image I/O and preprocessing

**Deep Learning** (Phase 2,6):
- PyTorch 2.0+: Model training and knowledge distillation
- **ResNet-50/ResNet-18**: Teacher-student ML IQA (NOT MobileNetV3/EfficientNet)
- **DocLayout-YOLO**: Layout detection (YOLOv10-based, document-optimized)
  - Model selection: `configs/models/doclayout_yolo.yaml`
  - Training: `modal run modal/train_phase3_doclayout_yolo.py`
- ONNX Runtime: Production inference optimization
- Modal: Serverless GPU training platform

**Routing & Quality** (Phase 8):
- Document Quality Score (DQS): Degradation + complexity metrics
- PDF type classification: image_only/born_digital/hybrid detection
- OCR routing recommendations: 4-strategy decision logic

**Framework**:
- Click: CLI framework
- Pydantic v2: JSON schema and validation
- Structlog + Rich: Structured logging with console output

**OUT OF SCOPE** (Project B):
- Table structure extraction (PubTables-1M)
- Reading order prediction (ReadingBank)
- Full semantic layout detection (DocLayNet)

## Pre-Commit Linting Checklist

Before committing ANY changes, ensure:

- [ ] **TODO Management**: Was TodoWrite used for task tracking?
- [ ] **Agent Assignment**: Were tasks assigned to appropriate specialized agents?
- [ ] **Reference Files**: Were temporary reference files created for complex tasks?
- [ ] **Agent Validation**: Was all agent work reviewed and validated?
- [ ] **Security Keys**: GPG and SSH keys present and validated
- [ ] **Code Quality**: Ruff formatting, Ruff linting, MyPy type checking passed
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
