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

**Project A - Preprocessing, IQA & Coarse Layout Gateway** - Front door for the four-project RAG document pipeline. Analyzes raw documents (PDFs, images), assesses quality, applies corrections, and provides intelligent routing metadata to downstream OCR processing.

### Four-Project RAG Pipeline Architecture

```text
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
```text

**Project A Mission**: Deliver clean, corrected, quality-scored page images with reliable metadata that determines which workflows Project B should use.

**Key Innovation**: Multi-stage pipeline with **text detection gate** that routes documents to specialized processing paths:

- **No-text path**: Classical CV + ML IQA (teacher-student ResNet architecture)
- **Text-detected path**: Layout-lite classification + hybrid IQA on embedded images

**Scope Boundaries**:

- **IN SCOPE**: IQA, corrections, DQS, layout-lite (coarse page attributes), routing recommendations
- **OUT OF SCOPE**: Full layout detection, table structure, reading order (Project B responsibility)

**Current Phase**: Phases 0-3, 6 ✅ COMPLETE, Phase 4 (Device Priority) ✅ 98% COMPLETE

> **Note**: This CLAUDE.md provides high-level project overview. For detailed phase breakdown,
> sprint plans, and current status, see [docs/planning/PROJECT_PLAN.md](docs/planning/PROJECT_PLAN.md).
>
> **Last synchronized**: 2025-02-05

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

## Draft PR Workflow (MANDATORY FOR COST OPTIMIZATION)

**ALWAYS create PRs as draft first**, then mark ready for review after validation.

### Why Draft PRs?

Draft PRs skip expensive workflows (saves $0.50-1.00 per PR cycle):

- Python compatibility matrix (12 jobs → 1 job)
- ClusterFuzzLite fuzzing (30 min → skipped)
- Mutation testing (60 min → skipped)
- SonarCloud analysis (10 min → skipped)
- Container security scans (12 min → skipped)

**Essential checks still run**: Linting, tests, security scans, REUSE, SBOM, requirement locks

### Standard PR Workflow

1. **Create as draft** (automatic during development):

   ```bash
   # Claude creates all PRs as draft by default
   gh pr create --draft --title "feat: add new feature"
   ```

2. **Validate locally before each push**:

   ```bash
   ./scripts/validate-before-push.sh && git push
   ```

3. **Draft PR runs fast essential checks** (~5-8 workflows, ~15 minutes):

   - CI (linting, tests, type checking)
   - Security essentials (Bandit, Safety)
   - REUSE compliance
   - SBOM generation
   - Requirements lock validation

4. **Verify draft PR passes** essential checks:

   ```bash
   gh pr checks  # Should show ~5-8 checks passing
   ```

5. **Mark ready for review** when development complete:

   ```bash
   gh pr ready <pr-number>
   ```

6. **Full CI suite runs** (~15 workflows, comprehensive validation)

### Claude PR Creation Pattern

When Claude creates a PR, it MUST follow this pattern:

```bash
# Step 1: Local validation (catch issues before push)
./scripts/validate-before-push.sh

# Step 2: Create PR as DRAFT
gh pr create --draft \
  --title "feat: descriptive title" \
  --body "$(cat PR_DESCRIPTION.md)"

# Step 3: Verify essential checks pass
echo "⏳ Waiting for draft PR checks..."
gh pr checks --watch

# Step 4: Mark ready when checks pass
echo "✅ Draft PR checks passed. Mark ready for review when development complete:"
echo "   gh pr ready <pr-number>"
```

### Cost Comparison

**Old Workflow** (no draft PRs):

- Every push: 15 workflows × 7 min = 105 min
- 3 pushes per PR: 315 minutes ($2.52)

**New Workflow** (with draft PRs):

- Draft push 1: 6 workflows × 5 min = 30 min
- Draft push 2: 6 workflows × 5 min = 30 min
- Mark ready: 15 workflows × 5 min = 75 min
- **Total**: 135 minutes ($1.08)

**Savings**: 180 minutes ($1.44) per PR = 57% reduction

### Exception: Critical Hotfixes

For critical production issues, skip draft PR and run full validation immediately:

```bash
gh pr create --title "fix: critical security patch" \
  --body "Fixes CVE-YYYY-XXXXX"
  # No --draft flag
```

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
- See [docs/planning/PROJECT_PLAN.md](docs/planning/PROJECT_PLAN.md)

**Phase 2: Layout-Lite & DQS & Routing** ✅ COMPLETE

- **Layout-Lite Detection**: Coarse page attributes (layout_type, has_tables, has_figures, has_dense_math, has_handwriting)
- **Page attributes**: fuzzy_scan, watermark, colorful_background
- **Structural complexity score**: 0-1 metric for routing decisions
- **Classes**: All 11 DocLayNet classes (Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title)
- **Model**: YOLOv10-doc (specifically trained on DocLayNet dataset)
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
- [iqa_classical.py](src/image_preprocessing_detector/detection/iqa_classical.py): Classical CV detectors (Phase 1C: 8 detectors - Hough skew, Laplacian blur, histogram contrast, noise, illumination, JPEG blockiness, binarization, bleed-through)
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

**Current Status**: Phases 0-3, 6 ✅ COMPLETE | Phases 4, 5, 8 ⚠️ PARTIAL | Phases 7, 9 ❌ NOT STARTED

> **Detailed Planning**: See [docs/planning/PROJECT_PLAN.md](docs/planning/PROJECT_PLAN.md) for complete sprint breakdown and current status.

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
  - Layout-lite detection (11 DocLayNet classes, YOLOv10-doc)
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
  - Docker/K8s manifests ✅
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
- 8 classical IQA detectors: skew, blur, contrast, noise, illumination, JPEG blockiness, binarization, bleed-through

**Deep Learning** (Phase 2, 3):

- PyTorch 2.0+: Model training and knowledge distillation
- **ResNet-50/ResNet-18**: Teacher-student ML IQA (NOT MobileNetV3/EfficientNet)
  - Teacher: val_loss=0.27 (50 epochs)
  - Student: val_loss=0.14 (30 epochs)
- **YOLOv10-doc**: Layout detection (document-optimized for DocLayNet)
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
