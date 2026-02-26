# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Project Context**: Extends global CLAUDE.md standards from `~/.claude/CLAUDE.md`. Only project-specific configurations documented below.

## Template Feedback Tracking (CRITICAL)

This project uses the `cookiecutter-python-template` for standards alignment.
All template-related issues MUST be documented for upstream fixes.

**Location**: `template_feedback/`
**Naming Convention**: `MMDDYYYY_template_feedback.md`

### When to Create Feedback

- CI failures caused by template-managed files
- Missing features in generated files
- Configuration mismatches between template and project
- Formatting/linting issues in template output
- Tools or patterns that should be added to the template

### .claude/ Directory

This project includes a comprehensive `.claude/` directory with:

- **21 Agents**: Specialized agents for code review, security, testing, etc.
- **13 Commands**: Custom slash commands for quality, security, and testing
- **9 Skills**: Reusable skills for git, PR preparation, and project planning
- **Standards**: Development standards reference documents

See [.claude/README.md](.claude/README.md) for full documentation.

**Source**: [https://github.com/ByronWilliamsCPA/.claude](https://github.com/ByronWilliamsCPA/.claude)

### Architecture Documentation System

This project uses a **4-level architecture documentation hierarchy** with automated validation and traceability:

- **Level 0**: Multi-project RAG pipeline context (6 projects)
- **Level 1**: Project A architecture (8 workstreams overview)
- **Level 2**: Workstream details ("Level 2.5" standard with code examples)
- **Level 3**: Module implementation (state machines, detailed swimlanes with LOC annotations)

**📖 Complete Maintenance Guide**: [docs/architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md](docs/architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md)

**Key Resources**:

- [LEVEL_2_DOCUMENTATION_TEMPLATE.md](docs/architecture/LEVEL_2_DOCUMENTATION_TEMPLATE.md) - "Level 2.5" standard
- [FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md](docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md) - 1,292 files mapped
- [scripts/extract_workstream_loc.sh](scripts/extract_workstream_loc.sh) - Automated LOC counting
- [scripts/validate_architecture_links.sh](scripts/validate_architecture_links.sh) - Link validation

**When to Update Architecture Docs**: See maintenance guide for trigger events and step-by-step procedures

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
```text

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

**Project A - Preprocessing, IQA & Coarse Layout Gateway** - Front door for the four-project RAG document pipeline. Accepts raw documents in any condition, assesses quality along multiple dimensions, applies geometric and quality corrections, and delivers `DocumentMetadata.json` + corrected images to Project B.

> **Full system narrative**: [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md)
> — explains what the system does, how the two-model pipeline works, and why the design is sound.
>
> **Current roadmap and status**: [docs/planning/MASTER_PROJECT_PLAN.md](docs/planning/MASTER_PROJECT_PLAN.md)
> — consolidated plan replacing PROJECT_PLAN.md and PHASE_10_11_RESTRUCTURED_PLAN.md.
>
> **Last synchronized**: 2026-02-21

### Six-Service RAG Pipeline Architecture

```text
Ingest            →  Prepare-Doc / Prepare-Audio  →  Unify  →  Chunk  →  App Embedding
(foundry-ingest)     (foundry-prepare-doc)            (foundry-unify)  (foundry-chunk)  (per-app)
──────────────────   (foundry-prepare-audio)          ───────────────  ───────────────  ─────────
• Web UI upload      Document track: IQA, corrections,   Multi-engine OCR    Trust scoring
• File routing         layout, routing metadata           Docling DOM         RAG chunking
• Job status         Audio track: FFmpeg + Deepgram,    unification
• Cloud Workflows      diarization, TranscriptMetadata

OUTPUT:              DocumentMetadata.json               OCRDocument.json    RAGChunkSet.json
                     + Corrected Images                                      (each app embeds
                     TranscriptMetadata.json                                  per its own needs)
```text

**Prepare-Doc Mission**: Deliver clean, corrected, quality-scored page images with reliable metadata that determines which workflows Unify should use.

**Current Architecture** (two-model pipeline):

- **MobileNetV4-Conv-S** (~3ms GPU): Pre-correction gate — orientation, skew, resolution
- **SigLIP 2 NAFlex** (~50ms GPU): Multi-task teacher — 16 heads across IQA, Script, Orientation, Handwriting, Page Attributes
- **docling-layout** (egret-large / heron): Layout detection (replaced YOLOv10-doc)
- **Classical IQA layer**: 9 detectors (blur, noise, contrast, JPEG blockiness, illumination, binarization, bleed-through, skew, JPEG quality factor)

**Scope Boundaries**:

- **IN SCOPE**: IQA, corrections, DQS, script/orientation/handwriting detection, routing recommendations
- **OUT OF SCOPE**: Full layout detection, table structure, reading order (Unify's responsibility)

**Current Status**: Phases 0–6 ✅ COMPLETE | Streams 1–4C ✅ COMPLETE | Dataset assembly ⚠️ IN PROGRESS | Training ❌ PENDING

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

## Security-First Development (CRITICAL)

Claude MUST adopt a security-first approach in all development:

### 1. Proactive Security Suggestions

When working on this project, always suggest appropriate security measures:
- **Dependencies**: Vulnerability scanning (safety, osv-scanner)
- **Image Processing**: Input validation, sanitization, DoS protection (large images)
- **PDF Handling**: Path traversal prevention, memory limits, malicious PDF detection
- **APIs**: Authentication, rate limiting, input validation
- **Data**: Encryption at rest and in transit, access controls

### 2. Never Bypass Security Issues

- **ALL security findings** from scanners (Semgrep, Bandit, Safety, OSV) must be addressed
- False positives must be documented with inline comments explaining WHY
- Use baseline files (`osv-scanner.toml`) only for unavoidable exceptions with justification

### 3. Code Quality Standards

- Treat linting warnings as errors to fix, not ignore
- Address ALL type checker warnings (BasedPyright strict mode)
- Don't accumulate technical debt by deferring quality issues

### 4. Default to Strictest Settings

- Security scanners: fail on HIGH/CRITICAL by default (configured)
- Type checking: strict mode on `src/` (already configured)
- Linting: no ignored rules without documented reason

## Project Planning Documents

> **Planning Documents**: This project uses planning documents for complex features

**Location**: `docs/development/RAG Pipeline/`
- [project-a-project-plan.md](docs/development/RAG%20Pipeline/project-a-project-plan.md) - Phased implementation plan
- Phase tracking with detailed implementation steps
- Architecture decisions documented inline

### Quick Start

```bash
# Review current phase implementation
cat "docs/development/RAG Pipeline/project-a-project-plan.md" | grep "Phase.*:"

# Start new phase implementation
/plan implement Phase X from project-a-project-plan.md
```

## Third-Party Integrations

### CodeRabbit (AI Code Reviews)

Configuration: `.coderabbit.yaml`

**Commands**:

```bash
@coderabbitai summary      # Get high-level PR summary
@coderabbitai review       # Request re-review after changes
@coderabbitai resolve      # Mark conversation resolved
```

**Features**:

- Automatic PR reviews on all pull requests
- Line-by-line code suggestions
- Security vulnerability detection
- Test coverage analysis

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
uv sync --extra dev

# Install with ML dependencies (Phase 2+)
uv sync --extra dev --extra ml

# Setup pre-commit hooks (required before first commit)
uv run pre-commit install

# Run CLI tool
uv run imgprep --help
uv run imgprep process input.pdf --output result.json
```text

### Testing

```bash
# Run all tests with coverage (80% minimum enforced)
uv run pytest -v

# Run specific test categories
uv run pytest -v -m unit               # Unit tests only
uv run pytest -v -m integration        # Integration tests only
uv run pytest -v -m "not slow"         # Exclude slow tests

# Run single test file
uv run pytest tests/unit/test_schema.py -v

# Run single test function
uv run pytest tests/unit/test_schema.py::test_detected_issue_validation -v

# Run with coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# Run tests in parallel (faster for large suites)
uv run pytest -n auto
```text

### Code Quality

```bash
# Format code (required before commit)
uv run ruff format src tests

# Lint and auto-fix
uv run ruff check --fix src tests

# Type checking - BasedPyright (strict on src/, 3-5x faster than MyPy)
uv run basedpyright src

# Legacy type checking (MyPy - kept for reference)
# uv run mypy src

# Dead code detection
uv run vulture src/ --min-confidence 80

# Run all pre-commit hooks manually
uv run pre-commit run --all-files

# Security scanning
uv run bandit -r src
uv run safety check
```text

### Validation Scripts

```bash
# Run standalone validation scripts (not part of test suite)
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH uv run python validation/validate_*.py
```text

### Modal & Training (Phase 2+)

**Status**: ✅ Modal setup complete, ready for training runs

**Quick Reference**: [docs/reference/MODAL_QUICK_REFERENCE.md](docs/reference/MODAL_QUICK_REFERENCE.md)

```bash
# Start training (ready to use)
uv run modal run modal/train_phase2_iqa.py      # Phase 2: ResNet IQA

# Monitor training
uv run modal app logs image-detection --follow  # Stream logs
open https://modal.com/apps                     # Dashboard

# Cost tracking
uv run modal profile current                    # Check usage

# Verify setup (optional)
uv run modal token current                      # Check authentication
uv run modal secret list | grep gcs-credentials # Check GCS credentials
```text

**Key Training Details:**

- **Model Architecture**: ResNet-50 teacher → ResNet-18 student (NOT MobileNetV3/EfficientNet)
- **Dataset**: OHR-Bench via GCS (~18 GB)
- **GPU**: T4 (16GB) or A10 (24GB)
- **Duration**: 12-24 hours (continuous, no session timeouts)
- **Cost**: ~$7-14 or $0 with $30/month free tier

**Quick Reference includes**: Complete training workflow, monitoring, debugging, cost management, troubleshooting

### Celery Workers (Phase 4 - Week 17)

**Status**: ✅ Worker pool implementation complete

**Prerequisites**:
- Redis server (broker + result backend)
- Python dependencies: `uv sync --extra workers`

```bash
# Install worker dependencies
uv sync --extra dev --extra workers

# Start Redis (via Docker - recommended)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or use local Redis
# macOS: brew install redis && brew services start redis
# Ubuntu: sudo apt install redis-server && sudo systemctl start redis

# Verify Redis connection
redis-cli ping  # Should return PONG

# Start Celery worker (default queue)
celery -A image_preprocessing_detector.workers worker -l info

# Start GPU worker (IQA inference)
celery -A image_preprocessing_detector.workers worker -l info -Q gpu -c 2

# Start batch worker
celery -A image_preprocessing_detector.workers worker -l info -Q batch

# Monitor with Flower (optional)
celery -A image_preprocessing_detector.workers flower --port=5555
```text

**Environment Variables**:
- `CELERY_BROKER_URL`: Redis broker URL (default: `redis://localhost:6379/0`)
- `CELERY_RESULT_BACKEND`: Redis result backend (default: `redis://localhost:6379/1`)

**Queue Configuration**:
- `default`: Standard document processing
- `gpu`: IQA analysis (GPU-optimized, priority queue)
- `batch`: Batch document processing (high timeout)

### Security Requirements (MANDATORY)

```bash
# Key validation (MUST pass before development)
gpg --list-secret-keys  # Must show GPG key for .env encryption
ssh-add -l              # Must show SSH key for signed commits
git config --get user.signingkey  # Must be configured for signed commits

# Security scanning
uv run bandit -r src                        # Python security analysis
uv run safety check                         # Dependency vulnerability check
```text

### OSV Scanner (Optional - Local Development)

OpenSSF Scorecard uses osv-scanner for vulnerability detection. Install locally to test osv-scanner.toml exceptions before pushing:

```bash
# Install osv-scanner (requires Go 1.21+)
go install github.com/google/osv-scanner/cmd/osv-scanner@latest

# Verify installation
osv-scanner --version

# Run scan (automatically respects osv-scanner.toml exceptions)
osv-scanner --lockfile=uv.lock

# Expected output: 0 vulnerabilities (all false positives documented in osv-scanner.toml)

# Scan with detailed output
osv-scanner --lockfile=uv.lock --format=json --output=osv-local-results.json
```text

**Key Features:**

- **Automatic Exception Handling**: Reads `osv-scanner.toml` from repository root
- **Multi-Ecosystem**: Supports Python, npm, Go, Rust (vs. Safety Python-only)
- **OSV Database**: Same database used by OpenSSF Scorecard and Google
- **CI Integration**: Runs automatically in `security-analysis.yml` workflow

**When to Run Locally:**

- After updating dependencies (`uv add/uv sync`)
- Before creating PR with dependency changes
- To verify `osv-scanner.toml` exceptions work correctly
- When OpenSSF Scorecard reports new vulnerabilities

**Not Required**: CI runs osv-scanner automatically on all PRs and scheduled runs.

**Alternative (without Go)**: Use GitHub Actions logs from `security-analysis.yml` → `OSV Vulnerability Scanner` job to review scan results.

## Architecture - Big Picture

### Pipeline Flow (Project A Only)

The system uses a **text detection gate** to route documents to specialized processing, with **automatic DPI upscaling** (Phase 1B) for low-resolution inputs:

```text
PDF/Image Input
    ↓
[Pre-flight Analysis] (src/ingestion/) - DPI detection & upscaling (Phase 1B)
    ↓ (Auto-upscale if < 300 DPI)
[Ingestion] (src/ingestion/) - Standardize to 300 DPI images
    ↓
[PDF Type Classification] - image_only/born_digital/hybrid (Phase 2)
    ↓
[Text Gate] (src/detection/text_gate.py) - Fast ensemble heuristics (Phase 1)
    ↓              ↓
[NO TEXT]      [TEXT DETECTED]
    ↓              ↓
Classical IQA  Layout-Lite Classifier → Coarse page attributes (Phase 2)
(Phase 1C)         ↓
    ↓              ↓
ML IQA         ML IQA (Teacher-Student ResNet, Phase 3)
(Student)      (Student + selective Teacher)
    ↓              ↓
[Correction] (src/correction/) - Deskew, CLAHE, sharpening, denoising (Phase 1)
    ↓              ↓
[DQS Calculation] (Phase 2) - Degradation + Structural Complexity scores
    ↓              ↓
[Routing Recommendation] (Phase 2) - ocr_fast/advanced, vision_simple/structured
    ↓              ↓
[JSON Output] (src/output/) - DocumentMetadata.json + corrected images
    ↓
HANDOFF TO PROJECT B (OCR Orchestration)
```text

**Phase 1B: DPI Upscaling** ✅ COMPLETE

- **Technology**: PyMuPDF-based DPI detection with OpenCV upscaling
- **DPI Detection**: Automatic resolution analysis (100% accuracy)
- **Upscaling Trigger**: Documents below 300 DPI are automatically upscaled
- **Algorithm Options**: 5 OpenCV algorithms (lanczos, bicubic, inter_linear, inter_cubic, inter_area)
- **Performance**: 310-360ms processing time, <2GB memory usage, page-by-page processing
- **Quality**: 100% test success rate, 100% DPI improvement (e.g., 150→300 DPI)
- **Safety**: Graceful fallback to original on errors, high-res documents correctly skipped
- **Configuration**: 5 settings (enable_pdf_upscaling, pdf_min_dpi, pdf_target_dpi, pdf_upscale_algorithm, pdf_preserve_original_on_error)
- **Tests**: 61 tests (38 unit + 23 integration), 100% passing

**Phase 3: Teacher-Student ML IQA** ✅ COMPLETE

- **Student Model** (ResNet-18): Default production inference, val_loss=0.14
- **Teacher Model** (ResNet-50): High-capacity model for difficult cases, val_loss=0.27
- **Selective Teacher Inference**: Triggered by uncertainty, discrepancy, or document risk
- **Device Priority**: Local GPU → Local CPU → Modal GPU
- **Exports**: ONNX + TorchScript, model registry integration
- **Training**: 50 epochs (teacher), 30 epochs (student) on OHR-Bench dataset
- See [docs/planning/MASTER_PROJECT_PLAN.md](docs/planning/MASTER_PROJECT_PLAN.md)

**Phase 2: Layout-Lite & DQS & Routing** ✅ COMPLETE

- **Layout-Lite Detection**: Coarse page attributes (layout_type, has_tables, has_figures, has_dense_math, has_handwriting)
- **Page attributes**: fuzzy_scan, watermark, colorful_background
- **Structural complexity score**: 0-1 metric for routing decisions
- **Classes**: All 11 DocLayNet classes (Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title)
- **Model**: docling-layout-egret-xlarge (accuracy) / docling-layout-heron (speed)
- **Document Quality Score**: Aggregates degradation (IQA) + structural complexity (layout-lite)
- **Pre-OCR Risk**: Single 0-1 score combining quality and layout signals
- **Routing Recommendations**: 4 strategies based on DQS, pdf_type, and complexity
- **Tests**: 21/21 integration tests passing, 100% PDF classification accuracy
- **NOT DocLayNet-style full semantic layout** (that's Project B)

**Why Text Detection Gate?**

- **Problem**: Mixed document types require different processing strategies
- **Solution**: Fast text detection gate (< 10ms) routes to appropriate branch, avoiding expensive layout inference for pure images

### Module Responsibilities

**[schema.py](src/image_preprocessing_detector/schema.py)**

- Pydantic v2 models for JSON I/O
- `DetectedIssue`, `DocumentElement`, `PageMetadata`, `DocumentMetadata`
- COCO-aligned bounding boxes (`[x, y, width, height]`) for LayoutParser integration
- **Hybrid IQA**: `quality_issues` field in `DocumentElement` for per-element assessment

**[ingestion/](src/image_preprocessing_detector/ingestion/)** (Phase 0, 1B)

- **Phase 1B: DPI Upscaling** ✅ COMPLETE
  - [pdf_resolution.py](src/image_preprocessing_detector/ingestion/pdf_resolution.py): DPI detection and analysis
  - [pdf_upscaler.py](src/image_preprocessing_detector/ingestion/pdf_upscaler.py): OpenCV-based upscaling (5 algorithms)
  - [pdf_analyzer.py](src/image_preprocessing_detector/ingestion/pdf_analyzer.py): Pre-flight analysis orchestration
- **Phase 0: Basic Ingestion** ✅ COMPLETE
  - PDF → standardized images (300 DPI)
  - Image normalization and validation
  - Multi-format support (PDF, PNG, JPEG, TIFF)

**[detection/](src/image_preprocessing_detector/detection/)** (Phase 1, 1C, 2, 3)

- [text_gate.py](src/image_preprocessing_detector/detection/text_gate.py): Fast text presence detection (Phase 1: ensemble stroke density, connected components, edge density)
- [iqa_classical.py](src/image_preprocessing_detector/detection/iqa_classical.py): Classical CV detectors (Phase 1C: 9 detectors - Hough skew, Laplacian blur, histogram contrast, noise, illumination, JPEG blockiness, binarization, bleed-through, JPEG quality factor)
- [iqa_ml.py](src/image_preprocessing_detector/detection/iqa_ml.py): Teacher-student ML IQA (Phase 3: ResNet-50 teacher, ResNet-18 student, selective inference)
- [layout_lite.py](src/image_preprocessing_detector/detection/layout_lite.py): Coarse layout classification (Phase 2: page attributes, complexity scoring, 11 DocLayNet classes)

**[classification/](src/image_preprocessing_detector/classification/)** (Phase 2)

- [pdf_type_classifier.py](src/image_preprocessing_detector/classification/pdf_type_classifier.py): PDF type classification (image_only/born_digital/hybrid)

**[correction/](src/image_preprocessing_detector/correction/)** (Phase 1)

- OpenCV-based corrections with guardrails ✅ COMPLETE
- Deskew, CLAHE enhancement, sharpening, denoising
- Transform history tracking for audit trail
- 8 correction classes, 41 tests passing

**[routing/](src/image_preprocessing_detector/routing/)** (Phase 2)

- [recommendation_engine.py](src/image_preprocessing_detector/routing/recommendation_engine.py): OCR routing logic (4 strategies)

**[metrics/](src/image_preprocessing_detector/metrics/)** (Phase 2)

- [dqs_calculator.py](src/image_preprocessing_detector/metrics/dqs_calculator.py): Document Quality Score calculation (degradation + complexity, weight calibration)

**[output/](src/image_preprocessing_detector/output/)** (Phase 0,8)

- JSON generation with updated schema including routing metadata
- DocumentMetadata.json with pdf_type, DQS, pre_ocr_risk, ocr_routing_recommendation
- Corrected image output to filesystem for Project B handoff

**[utils/](src/image_preprocessing_detector/utils/)**

- Structured logging: `structlog` + `rich` console output
- Device probing utilities (GPU/CPU/Modal) - Phase 0
- Telemetry and monitoring hooks (Phase 10)

### Data Flow Pattern

1. **Pre-flight Analysis** (Phase 1B): DPI detection → automatic upscaling if <300 DPI
2. **Ingestion** (Phase 0): PyMuPDF extracts PDF pages → Pillow/OpenCV standardizes to 300 DPI
3. **PDF Type Classification** (Phase 2): Classify as image_only/born_digital/hybrid
4. **Text Gate** (Phase 1): Fast heuristics (< 10ms) → route to appropriate branch
5. **Detection Branch**:
   - No-text: Classical IQA (Phase 1C) + Student ML IQA (Phase 3)
   - Text: Layout-lite classification (Phase 2) + Student ML IQA (Phase 3) + selective Teacher inference
6. **Correction** (Phase 1): Apply OpenCV transforms with confidence-based thresholds
7. **DQS & Routing** (Phase 2): Calculate quality scores + generate routing recommendations
8. **Output** (Phase 2): Serialize DocumentMetadata.json + write corrected images → handoff to Project B

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

**Current Status**: Phases 0–6 ✅ COMPLETE | Streams 1–4C ✅ COMPLETE | Dataset assembly ⚠️ IN PROGRESS | SigLIP 2 training ❌ PENDING

> **Detailed Planning**: See [docs/planning/MASTER_PROJECT_PLAN.md](docs/planning/MASTER_PROJECT_PLAN.md) for current status, dependency tiers, and remaining work.

#### Completed Phases ✅

- **Phase 0** (Week 0-1): Foundation & Scaffolding - ✅ **100% COMPLETE**
  - Project skeleton, Modal workspace, GPU/CPU device probing
  - Configuration system with teacher fallback settings
  - Logging/telemetry scaffolding

- **Phase 1** (Weeks 2-5): MVP with Classical Methods - ✅ **100% COMPLETE**
  - 3 basic IQA detectors (skew, blur, contrast)
  - Text detection gate (ensemble heuristics)
  - Correction pipeline (deskew, CLAHE) with guardrails
  - CLI tool, output generation

- **Phase 1B** (Week 6): PDF Resolution & DPI Upscaling - ✅ **100% COMPLETE**
  - PyMuPDF DPI detection (100% accuracy)
  - 5 OpenCV upscaling algorithms
  - Pre-flight analysis orchestrator
  - 61 tests (38 unit + 23 integration), 100% passing

- **Phase 1C** (Weeks 6-7): Enhanced Classical IQA Detectors - ✅ **100% COMPLETE**
  - 5 additional detectors (noise, illumination, JPEG blockiness, binarization, bleed-through)
  - Discrepancy threshold framework
  - DQS weight calibration
  - 99 tests, 100% passing, <25ms combined performance

- **Phase 2** (Weeks 7-9): Core Components & Schema Alignment - ✅ **100% COMPLETE**
  - PDF type classification (image_only/born_digital/hybrid)
  - Layout-lite detection (11 DocLayNet classes, docling-layout-egret-xlarge / docling-layout-heron)
  - DQS calculator (degradation + complexity)
  - Pre-OCR risk scoring
  - Routing engine (4 strategies)
  - All 26 sprints, 21/21 integration tests passing

- **Phase 3** (Weeks 10-14): Teacher-Student ML IQA - ✅ **100% COMPLETE**
  - ResNet-50 teacher (50 epochs, val_loss=0.27)
  - ResNet-18 student (30 epochs, val_loss=0.14)
  - Knowledge distillation, selective teacher inference
  - ONNX + TorchScript exports, model registry integration
  - Training on OHR-Bench dataset via Modal

- **Phase 6** (Ongoing): Monitoring, Drift Detection & Continuous Improvement - ✅ **95% COMPLETE**
  - 7500+ lines: drift detection, alerting, active learning
  - Pipeline integration, retraining automation
  - Privacy review workflow
  - Prometheus metrics, Grafana dashboards

#### In-Progress Phases ⚠️

- **Phase 4** (Weeks 15-17): Device-Priority Execution & Production Hardening - ✅ **98% COMPLETE**
  - Device capability probing ✅
  - Device orchestration with policy enforcement ✅
  - Device priority rules (Local GPU → Modal GPU → BLOCK CPU) ✅
  - Modal GPU integration with circuit breaker ✅
  - Budget enforcement (3 levels: doc/batch/monthly) ✅
  - Prometheus metrics and structured logging ✅
  - Batch inference integrated into iqa_ml.py ✅
  - Tensor caching active in batch processing hot path ✅
  - Uncertainty/discrepancy gates wired to DeviceOrchestrator ✅
  - DeviceOrchestrator integrated into Celery tasks ✅
  - Performance regression gates in CI workflow ✅
  - 156+ tests passing (98+ unit, 20 integration, 38 e2e) ✅
  - Only remaining: Async I/O (deferred to Phase 5)

- **Phase 5** (Weeks 18-20): Testing, Documentation & Deployment - ⚠️ **40% COMPLETE**
  - FastAPI framework ✅
  - Docker deployment ✅
  - E2E test suite ✅
  - Actual API endpoint implementations (pending)
  - Load testing, deployment automation (pending)

- **Phase 8**: DQS Calibration with Real OCR Data - ⚠️ **60% COMPLETE**
  - Core DQS components integrated in Phase 2 ✅
  - Calibration with real OCR feedback data (pending)

#### Future Phases ❌

- **Phase 7**: ML IQA Model Optimization - ❌ **NOT STARTED**
  - Continuous label retraining from harvested samples
  - Fine-tuning on production data

- **Phase 9**: Element Classification Models - ❌ **NOT STARTED**
  - Table/figure classifiers
  - Handwriting detection refinement

**Out of Scope** (Project B responsibility):
- Full semantic layout detection (DocLayNet-style)
- Table structure extraction (PubTables-1M)
- Reading order prediction (ReadingBank)

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

**Classical CV** (Phase 1, 1B, 1C):

- OpenCV 4.8+: Hough transform, Laplacian, histogram analysis, DPI upscaling
- PyMuPDF: PDF extraction and DPI detection
- Pillow: Image I/O and preprocessing
- 9 classical IQA detectors: skew, blur, contrast, noise, illumination, JPEG blockiness, binarization, bleed-through, JPEG quality factor (DCT coefficient analysis)

**Deep Learning** (Phase 2, 3):

- PyTorch 2.0+: Model training and knowledge distillation
- **ResNet-50/ResNet-18**: Teacher-student ML IQA (NOT MobileNetV3/EfficientNet)
  - Teacher: val_loss=0.27 (50 epochs)
  - Student: val_loss=0.14 (30 epochs)
- **docling-layout-egret-xlarge / docling-layout-heron**: Layout detection (document-optimized for DocLayNet)
  - **Pre-trained models available (no additional training required)**
  - 11 DocLayNet classes (Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title)
  - Performance: 85+ FPS, 70-80% mAP
- ONNX Runtime: Production inference optimization
- Modal: Serverless GPU training platform

**Routing & Quality** (Phase 2):

- Document Quality Score (DQS): Degradation + complexity metrics
- PDF type classification: image_only/born_digital/hybrid detection
- OCR routing recommendations: 4-strategy decision logic
- Pre-OCR risk scoring

**Framework**:

- Click: CLI framework
- Pydantic v2: JSON schema and validation
- Structlog + Rich: Structured logging with console output

**OUT OF SCOPE** (Project B):

- Table structure extraction (PubTables-1M)
- Reading order prediction (ReadingBank)
- Full semantic layout detection (DocLayNet)

## Dataset Inventory

> **Token Optimized**: Modular documentation structure for efficient LLM context usage
> **Total Datasets**: 51 (41 training-ready, 8 in progress, 1 blocked, 1 text corpus)
> **Expected Token Savings**: 70-85% for typical dataset queries
> **Layer 2 Metadata**: 20/51 datasets with aggregated statistics
> **New Structure**: Individual dataset files in `docs/datasets/source/` + task-based indices

### Documentation Tiers

**Tier 1 - Quick Reference** (START HERE): [docs/datasets/DATASET_QUICK_REFERENCE.md](docs/datasets/DATASET_QUICK_REFERENCE.md)
- **Purpose**: Training task selection, quick stats
- **Use For**: "Which datasets for IQA training?", "How many layout detection images?"
- **Size**: ~800 lines, ~8K tokens
- **Enhanced**: Includes capture method, domain, and content flags from Layer 2 metadata aggregates
- **Contains**:
  - Datasets grouped by training purpose (IQA, Layout, Text Detection, etc.)
  - Metadata-enriched tables with capture method (📄 🖨️ 📱 🎨 icons)
  - Label type index (COCO boxes, quality scores, OCR text, scripts)
  - Training recipes by phase with metadata coverage indicators (⭐⭐⭐/⭐⭐/⭐)
  - Critical filters (benchmark-reserved, license restrictions)

**Tier 1b - Ground Truth Summary**: [docs/datasets/GROUND_TRUTH_SUMMARY.md](docs/datasets/GROUND_TRUTH_SUMMARY.md)
- **Purpose**: Ground truth label provenance and annotation methodology
- **Use For**: "How was dataset X annotated?", "Which datasets have human GT labels?"
- **Size**: ~250 lines, ~6K tokens
- **Contains**:
  - Annotation method legend (Human, Crowdsourced, Synthetic, Automatic, Paired GT, Mixed)
  - Ground truth labels grouped by training task
  - Full dataset index with provenance tiers
  - Annotation quality indicators (IAA metrics where available)

**Tier 2 - Processing Status**: [docs/datasets/DATASET_PROCESSING_STATUS.md](docs/datasets/DATASET_PROCESSING_STATUS.md)
- **Purpose**: Current conversion/extraction status tracking
- **Use For**: "Is ohr-bench ready?", "What's blocking cocotext?"
- **Size**: ~500 lines, ~5K tokens
- **Contains**:
  - Format conversion status (✅ Training-Ready, 🔄 In Progress, ❌ Blocked, 📚 Text Corpus)
  - Label extraction progress
  - Blockers, priorities, and ETAs
  - Storage requirements

**Tier 3 - Naming Standard**: [docs/datasets/DATASET_NAMING_STANDARD.md](docs/datasets/DATASET_NAMING_STANDARD.md)
- **Purpose**: Canonical names and alias resolution
- **Use For**: "Is nist_db2 same as nist-sd2?", "What's the canonical name?"
- **Size**: ~600 lines, ~6K tokens
- **Contains**:
  - Canonical name registry (all 51 datasets)
  - Alias mappings (resolves underscore vs hyphen confusion)
  - Migration guide with scripts
  - Naming conventions

**Tier 4 - Individual Dataset Files** (TARGETED LOOKUP): [docs/datasets/source/](docs/datasets/source/)
- **Purpose**: Per-dataset deep technical documentation (51 individual files)
- **Use For**: Specific dataset details (licenses, IQA sensitivity, citations)
- **Size**: ~100-500 lines per dataset, ~500-2K tokens each
- **Contains**: Complete dataset documentation (all 10 template sections per dataset)
- **Access**: Alphabetical - `source/{canonical-name}.md` (e.g., `source/tablebank.md`)
- **Navigation**: See [docs/datasets/README.md](docs/datasets/README.md)

**Tier 5 - Task Indices** (TRAINING RECIPES): [docs/datasets/indices/](docs/datasets/indices/)
- **Purpose**: Curated dataset lists by training task (7 task-specific indices)
- **Tasks**: [IQA](docs/datasets/indices/IQA.md), [Layout](docs/datasets/indices/LAYOUT.md), [Tables](docs/datasets/indices/TABLES.md), [Text Detection](docs/datasets/indices/TEXT_DETECTION.md), [Handwriting](docs/datasets/indices/HANDWRITING.md), [Scripts](docs/datasets/indices/SCRIPTS.md), [Benchmarks](docs/datasets/indices/BENCHMARKS.md)
- **Use For**: "All layout detection datasets", "Which datasets for IQA training?"
- **Size**: ~100-300 lines per index, ~1-3K tokens each

### Usage Guidelines for Claude Code

**Decision Flow**:
1. **Training task selection or quick stats?** → Read Tier 1 (Quick Reference)
2. **Which datasets for specific task?** → Read Tier 5 (Task Indices like IQA.md, LAYOUT.md)
3. **Current state, blockers, or conversion status?** → Read Tier 2 (Processing Status)
4. **Naming confusion or aliases?** → Read Tier 3 (Naming Standard)
5. **Deep technical details for ONE dataset?** → Read Tier 4 (Individual source file)
6. **Ground truth provenance or annotation method?** → Read Tier 1b (Ground Truth Summary)

**Token Efficiency**:

| Query Type | Files Read | Token Cost | Savings vs Old Catalog |
|------------|------------|------------|-------------------------|
| "Datasets for IQA training?" | Tier 5 (IQA.md) | 2K | 96% |
| "All layout datasets?" | Tier 5 (LAYOUT.md) | 3K | 93% |
| "Is ohr-bench ready?" | Tier 1 + 2 | 13K | 71% |
| "Is nist_db2 same as nist-sd2?" | Tier 3 only | 6K | 87% |
| "TableBank blur sensitivity?" | Tier 4 (source/tablebank.md) | 1-2K | 96% |

**Critical Rules**:
- ✅ **Always start with Tier 1** (Quick Reference) for dataset questions
- ✅ **Use Tier 5** (Task Indices) for training task selection (most efficient)
- ✅ **Use Tier 2** (Processing Status) for current state queries
- ✅ **Use Tier 3** (Naming Standard) for name resolution
- ✅ **Use Tier 4** (Individual files) for specific dataset deep dives (replaces old monolithic catalog)

### Layer 2 Metadata Aggregation

**Purpose**: Surface dataset characteristics from Layer 2 enrichment metadata

**Current Coverage**: 20/46 datasets with aggregated statistics
- ⭐⭐⭐ **Good metadata**: 4 datasets (capture + domain + content flags)
- ⭐⭐ **Partial metadata**: 6 datasets (capture + domain)
- ⭐ **Minimal metadata**: 10 datasets (domain only)
- **No metadata yet**: 26 datasets (pending Layer 2 enrichment)

**Aggregation Script**: [scripts/aggregate_layer2_metadata.py](scripts/aggregate_layer2_metadata.py)
- Processes Layer 2 enrichment JSON files from `/mnt/e/image_detection/metadata_registry/json/`
- Computes capture method, domain, quality, degradation, script, and content statistics
- Outputs to `metadata_registry/aggregates/{dataset}_stats.json`

**Usage**:
```bash
# Aggregate all datasets
python scripts/aggregate_layer2_metadata.py \
    --layer2-dir /mnt/e/image_detection/metadata_registry/json \
    --output-dir metadata_registry/aggregates \
    --verbose

# Aggregate single dataset
python scripts/aggregate_layer2_metadata.py --dataset tablebank --verbose
```

**Enhanced Quick Reference**: Training tables now include:

- 📷 **Capture Method**: Icons showing born-digital (📄), scanner (🖨️), camera (📱), synthetic (🎨)
- 🏛️ **Domain**: TAX, FIN, SCI, EDU, etc. (or UNK if not yet classified)
- ⭐ **Metadata Coverage**: Indicates enrichment completeness (⭐⭐⭐ good, ⭐⭐ partial, ⭐ minimal)

**Related Documentation**:

- [Level 2 Architecture](docs/architecture/diagrams/level-2/data-preparation/index.md#layer-2-metadata-aggregation) - Technical details

**Key Datasets**:

- **IQA Training**: ohr-bench (8.5K), diqa-5000 (5.5K), realdae (1.2K) *(iqa_phase7_165k EXCLUDED — dataset flawed; see docs/datasets/reviews/BATCH_1_IQA_SUMMARY.md §5)*
- **Layout Detection**: doclaynet (81K), pubtabnet (568K), tablebank (278K), fintabnet (97K)
- **Script Detection**: synth-multiscript-v3 (190K GCS-actual, generator bug — v2/250K DELETED), mdiw13 (290K), mlt19 (20K)
- **Text Detection**: cocotext (64K), mlt19 (20K), cc-ocr (6.5K)

## Training Dataset Inventory

> **Token Optimized**: Two-tier documentation structure for training datasets
> **Location**: `E:\image_detection\03_training_datasets\`
> **Total Training Images**: 140K ready (orientation 50K + skew 90K) + 190K GCS-complete (synth-multiscript-v3 — generator bug stopped at 190K)

### Documentation Tiers

**Tier 1 - Quick Reference** (START HERE): [docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md](docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md)

- **Purpose**: Training dataset selection, quick stats
- **Use For**: "Which training dataset for orientation?", "Script detection dataset?"
- **Size**: ~200 lines, ~2K tokens

**Tier 2 - Full Catalog**: [docs/datasets/TRAINING_DATASET_CATALOG.md](docs/datasets/TRAINING_DATASET_CATALOG.md)

- **Purpose**: Comprehensive training dataset documentation
- **Use For**: Deep technical details, generation provenance, label schemas
- **Size**: ~800 lines, ~8K tokens

**Template**: [docs/datasets/TRAINING_DATASET_TEMPLATE.md](docs/datasets/TRAINING_DATASET_TEMPLATE.md)

- **Purpose**: Template for documenting new training datasets

### Training Datasets Summary

| Dataset | Purpose | Images | Status | Design Spec |
|---------|---------|--------|--------|-------------|
| orientation | Orientation Detection | 50,000 | ✅ Ready | [MOBILECLIP2_S4_S0_DATASET_DESIGN.md](docs/planning/MOBILECLIP2_S4_S0_DATASET_DESIGN.md) |
| synth-multiscript-v3 | Script Detection | 190,485 (GCS-actual, generator bug — treat as complete) | ⚠️ Partial | [training/synth-multiscript-v3.md](docs/datasets/training/synth-multiscript-v3.md) |

### Usage Guidelines for Claude Code

**Decision Flow**:

1. **Training dataset selection?** → Read Quick Reference
2. **Deep technical details?** → Read Full Catalog
3. **Creating new dataset?** → Use Template

**Key Difference from Source Datasets**:

- Training datasets are **assembled/generated** from source datasets
- Have **generation provenance** (scripts, configs, timestamps)
- May use **soft labels** or **pseudo-labels** (not just ground truth)
- Are **purpose-built** for specific ML training tasks

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
uv run pytest --cov=src --cov-report=term-missing

# Run specific failing test
uv run pytest tests/path/to/test.py::test_name -v

# Check pre-commit hooks
uv run pre-commit run --all-files
```text

### Type Errors

```bash
# BasedPyright strict on src/, relaxed on tests/
uv run basedpyright src

# Check specific file
uv run basedpyright src/image_preprocessing_detector/schema.py
```text

### Import Errors in Validation Scripts

```bash
# Validation scripts need PYTHONPATH set
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH uv run python validation/script.py
```text

### Database Connection Issues

*Not applicable yet - database integration in Phase 4*

### Performance Issues

For Phase 3+ performance troubleshooting:

- Check GPU availability: `nvidia-smi`
- Monitor batch processing: Review logs in `logs/`
- Profile slow operations: Use `cProfile` on specific modules

---

*This configuration extends global CLAUDE.md standards. For detailed specifications on security, testing, and Git workflows, see `~/.claude/CLAUDE.md` and referenced files in `/standards/` directory.*
