# Project A - Document Preprocessing & IQA Gateway

**Part of the Four-Project RAG Document Pipeline**

## Security & Quality

[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/11445/badge)](https://www.bestpractices.dev/en/projects/11445)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/williaby/image-preprocessing-detector/badge)](https://securityscorecards.dev/viewer/?uri=github.com/williaby/image-preprocessing-detector)
[![codecov](https://codecov.io/gh/williaby/image-preprocessing-detector/graph/badge.svg?token=eS2YJZ5BzM)](https://codecov.io/gh/williaby/image-preprocessing-detector)
[![REUSE Compliance](https://github.com/williaby/image-preprocessing-detector/workflows/REUSE%20Compliance/badge.svg)](https://github.com/williaby/image-preprocessing-detector/actions/workflows/reuse.yml)

## CI/CD Status

[![CI Pipeline](https://github.com/williaby/image-preprocessing-detector/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/williaby/image-preprocessing-detector/actions/workflows/ci.yml?query=branch%3Amain)
[![Security Analysis](https://github.com/williaby/image-preprocessing-detector/actions/workflows/security-analysis.yml/badge.svg?branch=main)](https://github.com/williaby/image-preprocessing-detector/actions/workflows/security-analysis.yml?query=branch%3Amain)
[![Documentation](https://github.com/williaby/image-preprocessing-detector/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/williaby/image-preprocessing-detector/actions/workflows/docs.yml?query=branch%3Amain)
[![ClusterFuzzLite](https://github.com/williaby/image-preprocessing-detector/actions/workflows/cifuzzy.yml/badge.svg?branch=main)](https://github.com/williaby/image-preprocessing-detector/actions/workflows/cifuzzy.yml?query=branch%3Amain)
[![SBOM & Security Scan](https://github.com/williaby/image-preprocessing-detector/actions/workflows/sbom.yml/badge.svg?branch=main)](https://github.com/williaby/image-preprocessing-detector/actions/workflows/sbom.yml?query=branch%3Amain)

## Project Info

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY-SA 4.0](https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

---

## What Does This Do?

**Project A** is the **front door** for the four-project RAG document pipeline. It prepares raw documents (PDFs, images) for intelligent OCR processing by:

1. **Assessing Quality**: Classical + ML-based image quality assessment (IQA)
2. **Applying Corrections**: Deskew, denoise, enhance (with safety guardrails)
3. **Calculating DQS**: Document Quality Score for routing decisions
4. **Classifying Layout**: Coarse page-level attributes (not full semantic layout)
5. **Routing Recommendations**: Tells Project B which OCR strategy to use

**Four-Project RAG Pipeline**:

```text
Project A (This) → Project B (OCR) → Project C (Fusion) → Project D (Vector Search)
Preprocessing      Layout & Reading   Multi-Engine        Embeddings &
& IQA Gateway      Order Detection    Fusion & Trust      Retrieval
```text

**Problem it solves**: Poor-quality scans break OCR. Project A detects and fixes quality issues, then provides routing intelligence so downstream projects can optimize processing strategies.

## Features

- **Multi-Stage Pipeline Architecture**: Text detection gate routes documents to specialized processing paths
- **Teacher-Student ML IQA** (Phase 2):
  - ResNet-50 teacher for difficult/high-risk documents
  - ResNet-18 student for fast production inference
  - Selective teacher inference based on uncertainty and discrepancy
  - Device-priority execution: Local GPU → CPU → Modal GPU
- **Classical IQA** (Phase 4): Traditional computer vision quality assessment
  - Blur (Laplacian), noise (wavelet), skew (Hough), lighting, JPEG blockiness
  - Student vs classical discrepancy detection for teacher escalation
- **DPI Upscaling** (Phase 4): Automatic resolution normalization
  - 5 OpenCV algorithms (lanczos, bicubic, inter_linear, inter_cubic, inter_area)
  - Automatic detection and upscaling for documents <300 DPI
  - Proven technology from data_ingestor project
- **Layout-Lite Detection** (Phase 6): Coarse page-level attributes
  - Page types: single/multi/three_column/complex
  - Attributes: has_tables, has_figures, has_dense_math, has_handwriting
  - Page quality: fuzzy_scan, watermark, colorful_background
  - **NOT full semantic layout** (Project B responsibility)
- **Document Quality Score** (Phase 8): Holistic quality assessment
  - Degradation score (0-1) from IQA metrics
  - Structural complexity score (0-1) from layout-lite
  - Pre-OCR risk scoring
- **OCR Routing Recommendations** (Phase 8): Intelligent strategy selection
  - 4 routing strategies: ocr_fast, ocr_advanced, vision_simple, vision_structured
  - Based on DQS, PDF type (image_only/born_digital/hybrid), and complexity
- **PDF Type Classification** (Phase 8): Automatic document categorization
- **Structured JSON Output**: DocumentMetadata.json with routing metadata + corrected images
- **Production-Ready**: <150ms/page latency (GPU), <400ms/page (CPU), ≥6 pages/sec throughput

## Architecture Overview

### Four-Project RAG Pipeline

```text
┌───────────────────────────────────────────────────────────────────┐
│                    RAG DOCUMENT PIPELINE                           │
└───────────────────────────────────────────────────────────────────┘

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

### Project A Internal Pipeline

```text
PDF/Image Input → DPI Upscaling → Ingestion → PDF Type Classification → Text Gate
                                                                             ↓
                                                           ┌─────────────────┴─────────────────┐
                                                           ↓                                   ↓
                                                       [NO TEXT]                          [TEXT DETECTED]
                                                           ↓                                   ↓
                                                    Classical IQA                      Layout-Lite Classifier
                                                           +                                   +
                                                    ML IQA (Student)                   ML IQA (Student/Teacher)
                                                           ↓                                   ↓
                                                        Corrections ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                                                           ↓
                                                    DQS Calculation
                                                           ↓
                                                  Routing Recommendation
                                                           ↓
                                                    JSON Output + Images
                                                           ↓
                                                    HANDOFF TO PROJECT B
```text

See [docs/development/RAG Pipeline/RAG-pipeline-project-overview.md](docs/development/RAG Pipeline/RAG-pipeline-project-overview.md) for complete architecture and [docs/planning/MASTER_PROJECT_PLAN.md](docs/planning/MASTER_PROJECT_PLAN.md) for detailed implementation plan.

## Project Status

**Phase 0: Project Setup** (Week 0-1) - **COMPLETE** ✅

- [x] Project structure with Poetry (Python 3.12)
- [x] JSON schema with Pydantic v2 validation
- [x] Structured logging (structlog + rich)
- [x] Pre-commit hooks (Ruff format, Ruff lint, MyPy, Bandit)
- [x] CI/CD pipeline (GitHub Actions)
- [x] Modal workspace setup
- [ ] GPU/CPU device probing utilities
- [ ] Configuration system (YAML) with teacher fallback settings

**Next**: Phase 2 - ResNet Teacher & Student ML IQA (Week 2-4)

## Quick Start

### Prerequisites

- Python 3.12+
- Poetry 1.7+
- (Optional) GPU with CUDA for ML models (Phase 2+)

### Installation

```bash
# Clone repository
# Note: clone into image_detection/ (not the default image-preprocessing-detector/)
# The GitHub repo name is kept as-is per the project's no-rename policy; image_detection
# is the canonical local folder, matching the Python module path convention.
git clone https://github.com/williaby/image-preprocessing-detector.git image_detection
cd image_detection

# Install with Poetry
poetry install

# Install with dev dependencies
poetry install --with dev

# Install with ML dependencies (Phase 2+)
poetry install --with dev,ml
```text

### Usage

```python
from image_preprocessing_detector import DocumentMetadata
from image_preprocessing_detector.utils import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO", json_logs=False)
logger = get_logger(__name__)

# Process document (Phase 1+ implementation)
# from image_preprocessing_detector.pipeline import process_document
# metadata = process_document("document.pdf")
# metadata.to_json_file("output.json")

# Validate JSON schema
metadata = DocumentMetadata.from_json_file("output.json")
logger.info("Processed document", pages=metadata.num_pages)
```text

### CLI Usage (Phase 1+)

```bash
# Process single file
poetry run imgprep process input.pdf --output result.json

# Batch processing
poetry run imgprep batch input_dir/ --output-dir results/

# With quality threshold tuning
poetry run imgprep process input.pdf --blur-threshold 0.85 --skew-threshold 0.90
```text

## Development

### Setup Development Environment

```bash
# Install all dependencies including dev tools
poetry install --with dev

# Setup pre-commit hooks
poetry run pre-commit install

# Run tests
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=src/image_preprocessing_detector --cov-report=html

# Lint code
poetry run black src tests
poetry run ruff check --fix src tests
poetry run mypy src
```text

### Project Structure

```text
image_detection/
├── src/
│   └── image_preprocessing_detector/
│       ├── __init__.py
│       ├── schema.py              # JSON schema (Pydantic models)
│       ├── ingestion/             # PDF/image loading (Phase 1)
│       ├── detection/             # Detection modules (Phase 1-3)
│       ├── correction/            # Image corrections (Phase 1)
│       ├── output/                # JSON generation (Phase 1)
│       └── utils/                 # Logging, telemetry
├── tests/
│   ├── unit/                      # Unit tests
│   └── integration/               # Integration tests
├── scripts/                       # Training & evaluation scripts (Phase 2-3)
├── configs/                       # Model configurations
├── data/                          # Datasets (managed by DVC)
├── models/                        # Trained models
├── docs/                          # Documentation
├── pyproject.toml                 # Dependencies & tool config
├── README.md                      # This file
├── PROJECT_PLAN.md                # Complete implementation plan
└── ARCHITECTURE_SUMMARY.md        # Architecture quick reference
```text

## ML Model Training (Phase 2+)

### IQA Training with Modal

Train ML models for Image Quality Assessment using Modal's serverless GPU platform:

```bash
# Install Modal CLI
poetry add modal && poetry install

# Authenticate with Modal
poetry run modal token new

# Setup GCS credentials (one-time)
./scripts/modal_helpers.sh setup-gcs-secret /path/to/gcp-service-account-key.json

# Test GPU access
./scripts/modal_helpers.sh test-gpu

# Start Phase 2 IQA training (T4 GPU, ~3-6 hours)
./scripts/modal_helpers.sh train-phase2

# Monitor training at: https://modal.com/apps
```text

**Training Cost**: ~$3 for 5 hours on T4 GPU - covered by Modal's $30/month free tier!

See [PHASE2_QUICKSTART.md](docs/PHASE2_QUICKSTART.md) for complete training guide.

**Note**: This trains IQA models only (Project A scope). Layout detection (YOLOv8) is handled by Project B (ocr-orchestrator) per RAG Pipeline architecture.

## Testing

```bash
# Run all tests
poetry run pytest -v

# Run specific test categories
poetry run pytest -v -m unit          # Unit tests only
poetry run pytest -v -m integration   # Integration tests only
poetry run pytest -v -m "not slow"    # Exclude slow tests

# Run with coverage requirements
poetry run pytest --cov=src --cov-fail-under=80

# Run tests in parallel
poetry run pytest -n auto
```text

## Reporting Issues

### Bug Reports

Found a bug? Please report it via GitHub Issues:

1. **Check existing issues**: <https://github.com/williaby/image-preprocessing-detector/issues>
2. **Create new issue**: <https://github.com/williaby/image-preprocessing-detector/issues/new>
3. **Include**:
   - Python version and OS
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs

### Feature Requests

Have an idea? We welcome enhancement proposals via GitHub Issues. Please describe:

- Use case and motivation
- Proposed solution (if any)
- Alternatives considered

### Security Vulnerabilities

**Please do not report security vulnerabilities through public issues.**

See [SECURITY.md](SECURITY.md) for responsible disclosure process.

## Versioning

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: Backwards-compatible functionality additions
- **PATCH** version: Backwards-compatible bug fixes

Current version: **0.1.0** (pre-release, API may change)

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Documentation

### Core Documentation

- **[MASTER_PROJECT_PLAN.md](docs/planning/MASTER_PROJECT_PLAN.md)**: Consolidated implementation plan with phased roadmap and current status
- **[DATASET_METHODOLOGY.md](docs/DATASET_METHODOLOGY.md)**: IQA training dataset methodology with reproducibility instructions and validation criteria
- **[ARCHITECTURE_SUMMARY.md](docs/architecture/ARCHITECTURE_SUMMARY.md)**: Quick reference for architecture and design decisions
- **[ARCHITECTURE_CORRECTION.md](docs/architecture/ARCHITECTURE_CORRECTION.md)**: Hybrid IQA approach for embedded images
- **[DETECTION_TAXONOMY.md](docs/DETECTION_TAXONOMY.md)**: Complete taxonomy of 30+ detection categories with priority levels
- **[DOCUMENT_TYPE_COVERAGE_MATRIX.md](docs/DOCUMENT_TYPE_COVERAGE_MATRIX.md)**: Document type support matrix across phases

### Architecture Diagrams

- **[docs/architecture/diagrams/](docs/architecture/diagrams/)**: Centralized PlantUML diagram repository
  - [PROJECT_A_ARCHITECTURE_OVERVIEW.puml](docs/architecture/diagrams/PROJECT_A_ARCHITECTURE_OVERVIEW.puml): Complete system architecture
  - [PROJECT_A_WORKFLOW_HIERARCHY.puml](docs/architecture/diagrams/PROJECT_A_WORKFLOW_HIERARCHY.puml): Workstream data flow
  - [INDEX.md](docs/architecture/diagrams/INDEX.md): Diagram-to-source traceability matrix
  - [STYLE_GUIDE.md](docs/architecture/diagrams/STYLE_GUIDE.md): Diagram styling standards
- **[AUDIT.md](docs/architecture/AUDIT.md)**: Diagram gap analysis and recommendations
- **[docs/datasets/README.md](docs/datasets/README.md)**: Dataset documentation navigation guide (51 datasets, modular structure)

### Technical Guides

- **[docs/ADRs/](docs/ADRs/)**: Architecture Decision Records
  - [ADR-031: Comprehensive Benchmarking Framework](docs/ADRs/0031-comprehensive-benchmarking-framework.md)
  - [ADR-032: DocRes Unified Preprocessing](docs/ADRs/0032-docres-unified-preprocessing.md)
  - [ADR-029: Three-Tier Dataset Strategy](docs/ADRs/0029-phase2-dataset-selection-strategy.md)
- **[docs/MODEL_STORAGE.md](docs/MODEL_STORAGE.md)**: Model artifact storage, versioning, and promotion workflow (GCS + HF Hub)
- **[docs/PUBLIC_DATASET_COVERAGE.md](docs/PUBLIC_DATASET_COVERAGE.md)**: Public dataset coverage analysis across phases
- **[docs/infrastructure/HF_SPACES_VS_COLAB_PRO.md](docs/infrastructure/HF_SPACES_VS_COLAB_PRO.md)**: Training platform cost comparison
- **[docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md)**: Comprehensive testing approach with 80%+ coverage

### Development

- **[docs/project/decision-matrix.md](docs/project/decision-matrix.md)**: Critical decisions tracking and stakeholder requirements
- **[docs/WTD-Runbook.md](docs/WTD-Runbook.md)**: What The Diff integration guide for automated PR summaries
- **[docs/api-reference.md](docs/api-reference.md)**: API and CLI reference documentation
- **[SECURITY.md](SECURITY.md)**: Security policy and vulnerability reporting

### Research & References

- **[docs/reference/CITATIONS.md](docs/reference/CITATIONS.md)**: Complete dataset and paper citations
- **[docs/research/image_reference_sets.md](docs/research/image_reference_sets.md)**: Validation framework for pre-conversion document analysis

## Roadmap

**NEW PHASE STRUCTURE** (aligned with RAG Pipeline architecture):

### Phase 0: Project Setup (Week 0-1) ✅ **COMPLETE**

- Project skeleton with Poetry, Modal workspace setup
- GPU/CPU device probing utilities
- Configuration system (YAML) with teacher fallback settings
- Logging/telemetry scaffolding

### Phase 2: ResNet Teacher & Student ML IQA (Week 2-4) 🚧 **PLANNED**

**Training Platform**: Modal serverless GPU (free tier: $30/month credits)

- Multi-head ResNet-50 teacher architecture
- Knowledge distillation to ResNet-18 student
- Validation on OHR-Bench (document-specific IQA)
- Export to ONNX + TorchScript
- Model registry integration (local + Modal)
- Selective teacher inference triggers (uncertainty, discrepancy, risk)
- Device priority execution (Local GPU → CPU → Modal GPU)
- **Cost**: ~$5-10 (Modal GPU training) - **Covered by $30/month free tier**

### Phase 4: Classical IQA + DPI Upscaling (Week 5-6) 🚧 **PLANNED**

- Laplacian blur, wavelet noise, Hough skew
- Lighting metrics, JPEG blockiness detection
- Student vs classical discrepancy threshold tuning
- **DPI upscaling integration** (5 OpenCV algorithms)
- Proven technology from data_ingestor project
- Source: `/home/byron/dev/data_ingestor/src/data_ingestor/utils/`

### Phase 6: Layout-Lite Detection (Week 6-8) 🚧 **PLANNED**

- YOLOv8-nano for coarse page attributes (text/table/figure blocks)
- Handwriting presence classifier
- Structural complexity scorer
- OmniDocBench-style page attributes
- **NOT full DocLayNet-style semantic layout** (Project B responsibility)

### Phase 8: DQS & Routing (Week 9) 🚧 **PLANNED**

- Document Quality Score calculation (degradation + complexity)
- PDF type classification (image_only/born_digital/hybrid)
- Pre-OCR risk scoring
- Routing recommendation logic (4 strategies)
- JSON schema output with complete routing metadata

### Phase 10: Validation, Reporting, Documentation (Week 10) 🚧 **PLANNED**

- End-to-end pipeline benchmarking
- Teacher vs student performance analysis
- Stress testing (large batches, cost tracking)
- Documentation updates, PlantUML diagrams

**REMOVED PHASES** (out of Project A scope):

- ~~Phase 1/1B (old numbering)~~ → Absorbed into Phases 0 and 4
- ~~Table Structure Extraction (PubTables-1M)~~ → Project B responsibility
- ~~Reading Order Prediction (ReadingBank)~~ → Project B responsibility
- ~~Full DocLayNet-style layout detection~~ → Project B responsibility
- ~~DocRes Unified Preprocessing (dewarping, etc.)~~ → Out of scope
- ~~DLAFormer Research~~ → Project B responsibility

## Performance Targets

**ML IQA (Phase 2)**:

| Metric | Target | Notes |
|--------|--------|-------|
| Student (ResNet-18) CPU | ≤40ms/page (target), ≤100ms (acceptable) | Production default |
| Student (ResNet-18) GPU | ≤10ms/page (target), ≤25ms (acceptable) | Local GPU preferred |
| Teacher (ResNet-50) GPU | ≤30ms/page | Flagged pages only |
| IQA mAP | > 0.88 | Multi-label classification on OHR-Bench |

**End-to-End Pipeline (Phase 10)**:

| Metric | Target | Notes |
|--------|--------|-------|
| Latency (GPU) | <150ms/page | Full pipeline with GPU |
| Latency (CPU) | <500ms/page | Full pipeline CPU-only |
| Throughput (GPU) | ≥6 pages/sec/worker | With T4 GPU |
| Throughput (CPU) | ≥2 pages/sec/worker | CPU-only mode |
| Test Coverage | >80% | Unit + integration |

**Benchmark Datasets**:

- **IQA**: OHR-Bench (document-specific), DIQA-5000 (fallback)
- **Layout-Lite**: OmniDocBench (page attributes)

**REMOVED METRICS** (out of Project A scope):

- ~~Layout mAP@.50~~ → Project B (full layout detection)
- ~~Table Structure TEDS~~ → Project B (table structure extraction)
- ~~Dewarping ED@10~~ → Out of scope (DocRes removed)
- ~~Reading Order Accuracy~~ → Project B (reading order prediction)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for comprehensive contribution guidelines, development workflow, and code quality standards.

### Code Quality Standards

- **Formatting**: Black (88 chars)
- **Linting**: Ruff (comprehensive rules)
- **Type Checking**: MyPy (strict mode)
- **Testing**: Pytest with 80%+ coverage
- **Security**: Bandit + dependency scanning
- **Commits**: Conventional Commits, GPG-signed

### Pre-commit Checks

All commits must pass:

- Black formatting
- Ruff linting
- MyPy type checking (src/ only)
- Bandit security scanning
- YAML/Markdown linting

## License

CC-BY-SA-4.0 - see [LICENSE](LICENSE) for details.

## Citation

If you use this software in your research, please cite:

```bibtex
@software{image_preprocessing_detector,
  title = {Image Preprocessing Detector for RAG Applications},
  author = {Byron Williams},
  year = {2025},
  version = {0.1.0},
  url = {https://github.com/williaby/image-preprocessing-detector}
}
```text

### Datasets Used

This project uses the following datasets:

- **DocLayNet** (Pfitzmann et al., 2022) - Document layout analysis validation
  [![License](https://img.shields.io/badge/License-CDLA--Permissive--2.0-blue.svg)](https://github.com/DS4SD/DocLayNet)

- **Genalog** (Microsoft, 2021) - Synthetic document degradation
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/microsoft/genalog)

Full citations and dataset attributions available in [CITATIONS.md](docs/reference/CITATIONS.md).

## Acknowledgments

Architecture designed with multi-model consensus analysis:

- **Gemini 2.5 Pro**: Pipeline design and phased roadmap
- **GPT-5**: Risk assessment and optimization strategies

## Support

- **Issues**: [GitHub Issues](https://github.com/username/image-preprocessing-detector/issues)
- **Discussions**: [GitHub Discussions](https://github.com/username/image-preprocessing-detector/discussions)
- **Email**: <byronawilliams@gmail.com>

---

**Status**: Phase 0 (Foundation) - Week 2-3 of 24-week development timeline
