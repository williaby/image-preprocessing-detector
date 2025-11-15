# Image Preprocessing Detector

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
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

---

## What Does This Do?

**Prepares scanned documents and images for AI processing.** This tool automatically detects quality issues (blurriness, skew, poor contrast, noise) in PDFs and images, then identifies which preprocessing steps are needed to improve accuracy before feeding documents to AI systems.

**Problem it solves**: Scanned documents and images often have quality issues that hurt AI accuracy. This tool detects those issues automatically, so you know exactly what corrections to apply before processing documents with AI/machine learning systems.

---

**Intelligent image preprocessing detection system for RAG applications.** Automatically analyzes documents (PDFs, images) and detects required preprocessing steps before vector database ingestion.

## Features

- **Multi-Stage Pipeline Architecture**: Text detection gate routes documents to specialized processing paths
- **Hybrid IQA**: Classical CV + ML for image quality assessment (30+ detection categories)
  - Noise, blur, skew, contrast, orientation, perspective distortion
  - Low resolution detection with automatic DPI upscaling (Phase 1B)
  - 3-dimension quality assessment: overall, sharpness, color fidelity (Phase 2)
- **Document Element Detection**: YOLOv8-based detection of tables, images, handwriting, formulas, margin annotations
- **Unified Document Restoration** (Phase 3+): DocRes model for 5 preprocessing tasks
  - Dewarping, de-shadowing, deblurring, binarization, contrast enhancement
  - Dynamic task-specific prompts for runtime task selection
- **Table Structure Extraction** (Phase 3): PubTables-1M dataset for cell-level structure recognition
- **Reading Order Prediction** (Phase 4-5): Logical sequence prediction for complex layouts
- **Quality Assessment per Element**: IQA on embedded images within text documents
- **Comprehensive Benchmarking**: Registry-based evaluation across 9+ datasets with smoke tests and full validation
- **Structured JSON Output**: COCO-aligned metadata with confidence scores and transform history
- **Production-Ready**: Optimized for 50-150ms latency, 6+ pages/sec throughput per GPU worker

## Architecture Overview

```
PDF/Image Input
    ↓
[Ingestion & Standardization]
    ↓
[Text Detection Gate]
    ↓              ↓
[NO TEXT]      [TEXT DETECTED]
    ↓              ↓
Classical CV   YOLOv8 Layout Detection
+ ML (IQA)     + Hybrid IQA on Images
    ↓              ↓
[Corrections & JSON Output]
```

See [ARCHITECTURE_SUMMARY.md](docs/architecture/ARCHITECTURE_SUMMARY.md) for detailed architecture and [PROJECT_PLAN.md](docs/planning/PROJECT_PLAN.md) for complete implementation plan.

## Project Status

**Phase 0: Foundation & Scaffolding** (IN PROGRESS)

- [x] Project structure with Poetry (Python 3.12)
- [x] JSON schema with Pydantic v2 validation
- [x] Structured logging (structlog + rich)
- [x] Pre-commit hooks (Black, Ruff, MyPy, Bandit)
- [x] CI/CD pipeline (GitHub Actions)
- [ ] Evaluation framework
- [ ] Ground-truth test set (500 pages)

**Next**: Phase 1 - MVP with Classical Methods (Week 4-7)

## Quick Start

### Prerequisites

- Python 3.12+
- Poetry 1.7+
- (Optional) GPU with CUDA for ML models (Phase 2+)

### Installation

```bash
# Clone repository
git clone https://github.com/williaby/image-preprocessing-detector.git
cd image-preprocessing-detector

# Install with Poetry
poetry install

# Install with dev dependencies
poetry install --with dev

# Install with ML dependencies (Phase 2+)
poetry install --with dev,ml
```

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
```

### CLI Usage (Phase 1+)

```bash
# Process single file
poetry run imgprep process input.pdf --output result.json

# Batch processing
poetry run imgprep batch input_dir/ --output-dir results/

# With quality threshold tuning
poetry run imgprep process input.pdf --blur-threshold 0.85 --skew-threshold 0.90
```

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
```

### Project Structure

```
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
```

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
```

## Reporting Issues

### Bug Reports

Found a bug? Please report it via GitHub Issues:

1. **Check existing issues**: https://github.com/williaby/image-preprocessing-detector/issues
2. **Create new issue**: https://github.com/williaby/image-preprocessing-detector/issues/new
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
- **[PROJECT_PLAN.md](docs/planning/PROJECT_PLAN.md)**: Complete 114-page implementation plan with phased roadmap (Phases 1-5)
- **[ARCHITECTURE_SUMMARY.md](docs/architecture/ARCHITECTURE_SUMMARY.md)**: Quick reference for architecture and design decisions
- **[ARCHITECTURE_CORRECTION.md](docs/architecture/ARCHITECTURE_CORRECTION.md)**: Hybrid IQA approach for embedded images
- **[DETECTION_TAXONOMY.md](docs/DETECTION_TAXONOMY.md)**: Complete taxonomy of 30+ detection categories with priority levels
- **[DOCUMENT_TYPE_COVERAGE_MATRIX.md](docs/DOCUMENT_TYPE_COVERAGE_MATRIX.md)**: Document type support matrix across phases

### Technical Guides
- **[docs/ADRs/](docs/ADRs/)**: Architecture Decision Records
  - [ADR-031: Comprehensive Benchmarking Framework](docs/ADRs/0031-comprehensive-benchmarking-framework.md)
  - [ADR-032: DocRes Unified Preprocessing](docs/ADRs/0032-docres-unified-preprocessing.md)
  - [ADR-029: Three-Tier Dataset Strategy](docs/ADRs/0029-phase2-dataset-selection-strategy.md)
- **[docs/PUBLIC_DATASET_COVERAGE.md](docs/PUBLIC_DATASET_COVERAGE.md)**: Public dataset coverage analysis across phases
- **[docs/infrastructure/HF_SPACES_VS_COLAB_PRO.md](docs/infrastructure/HF_SPACES_VS_COLAB_PRO.md)**: Training platform cost comparison
- **[docs/TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md)**: Comprehensive testing approach with 80%+ coverage

### Development
- **[docs/project/decision-matrix.md](docs/project/decision-matrix.md)**: Critical decisions tracking and stakeholder requirements
- **[docs/WTD-Runbook.md](docs/WTD-Runbook.md)**: What The Diff integration guide for automated PR summaries
- **[docs/api-reference.md](docs/api-reference.md)**: API and CLI reference documentation
- **[SECURITY.md](SECURITY.md)**: Security policy and vulnerability reporting

### Research & References
- **[docs/references/CITATIONS.md](docs/references/CITATIONS.md)**: Complete dataset and paper citations
- **[docs/research/image_reference_sets.md](docs/research/image_reference_sets.md)**: Validation framework for pre-conversion document analysis

## Roadmap

### Phase 1: MVP with Classical Methods (Weeks 4-7) ✅
- PDF ingestion and text detection gate
- Classical IQA detectors (skew, blur, contrast)
- Correction pipeline with guardrails
- JSON output generation

### Phase 1B: DPI Detection & Upscaling (Weeks 7-8) 🚧
- Automatic DPI detection and analysis
- Multi-algorithm upscaling (5 OpenCV algorithms)
- Pre-flight analysis orchestration
- Graceful fallback and safety guardrails

### Phase 2: ML for Image Quality (Weeks 8-12) - Extended +1 Week
**Training Platform**: Modal serverless GPU (free tier: $30/month credits)
- IQA dataset generation (50k synthetic + real images)
- Train MobileNetV3/EfficientNet multi-label classifier
- **3-dimension quality assessment**: Overall, sharpness, color fidelity (FR-2.3)
- **Domain-Generalized Quality Assessment (DGQA)**: Synthetic-to-real calibration
- ONNX optimization for CPU inference
- Integration with classical methods (ensemble voting)
- **Cost**: ~$3 (T4 GPU @ $0.59/hr, ~5 hours) - **Covered by $30/month free tier**

### Phase 3: ML for Document Layout & Unified Preprocessing (Weeks 12-20) - Extended +3 Weeks
**Training Platform**: Modal serverless GPU (free tier: $30/month credits)
- Document element dataset (PubLayNet + DocLayNet + custom)
- Train YOLOv8n/s for layout detection (no session timeouts - trains to completion)
- **NEW: DocRes Unified Preprocessing** - 5 tasks in one model (dewarping, de-shadowing, deblurring, binarization, contrast)
- **NEW: DLAFormer Research** - Unified layout analysis (dual-track with YOLOv8)
- **NEW: Table Structure Extraction** - PubTables-1M for cell-level recognition (FR-4.11)
- Active learning for rare classes (handwriting, formulas)
- INT8 quantization for production
- **Cost**: ~$55-88 (A10 GPU @ $1.10/hr, 50-80 hours) - **Partially covered by free tier** (~$30 credits, $25-58 out-of-pocket)

### Phase 4: Production Hardening (Weeks 21-24)
- FastAPI service with Docker
- Performance optimization (batching, quantization)
- Monitoring and telemetry
- Comprehensive testing (80%+ coverage)
- **Reading Order Prediction** (optional): Logical sequence prediction for complex layouts

### Phase 5: Continuous Improvement (Weeks 25+)
- Phase 5A: Operational Foundation (Weeks 21-24)
- Phase 5B: Intelligence & Automation (Weeks 25-32)
- Phase 5C: Optimization & Scale (Weeks 33-40)
- Phase 5D: Ongoing Operations (Week 41+)
- Drift detection and alerting
- Active learning pipeline
- Quarterly retraining and recalibration

## Performance Targets

| Metric | Target | Phase | Notes |
|--------|--------|-------|-------|
| IQA mAP | > 0.88 | Phase 2 | Multi-label classification |
| IQA ECE | < 0.05 | Phase 2 | Well-calibrated confidence scores |
| Layout mAP@.50 | > 0.82 | Phase 3 | YOLOv8 object detection |
| Table Structure TEDS | > 0.85 | Phase 3 | PubTables-1M benchmark |
| Dewarping ED@10 | > 0.90 | Phase 3 | AnyPhotoDoc 6300 benchmark |
| Reading Order Accuracy | > 0.85 | Phase 4-5 | Optional: ReadingBank benchmark |
| JSON Accuracy | > 0.85 | Phase 3 | End-to-end pipeline |
| Latency (GPU) | < 150ms/page | Phase 3 | With T4 GPU |
| Latency (CPU) | < 500ms/page | Phase 3 | ONNX INT8 quantized |
| Throughput | > 6 pages/sec | Phase 3 | Per GPU worker |
| Test Coverage | > 80% | All Phases | Unit + integration |

**Benchmark Datasets**:
- **IQA**: DIQA-5000 (document-specific), LIVE/CSIQ (fallback)
- **Layout Detection**: DocLayNet, PubLayNet, OmniDocBench
- **Table Structure**: PubTables-1M, FinTabNet
- **Preprocessing**: AnyPhotoDoc 6300 (dewarping), SynDocDS (shadow removal)
- **Reading Order**: ReadingBank, OHR-Bench (optional Phase 4-5)

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

MIT License - see [LICENSE](LICENSE) for details.

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
```

### Datasets Used

This project uses the following datasets:

- **DocLayNet** (Pfitzmann et al., 2022) - Document layout analysis validation
  [![License](https://img.shields.io/badge/License-CDLA--Permissive--2.0-blue.svg)](https://github.com/DS4SD/DocLayNet)

- **Genalog** (Microsoft, 2021) - Synthetic document degradation
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/microsoft/genalog)

Full citations and dataset attributions available in [CITATIONS.md](docs/references/CITATIONS.md).

## Acknowledgments

Architecture designed with multi-model consensus analysis:
- **Gemini 2.5 Pro**: Pipeline design and phased roadmap
- **GPT-5**: Risk assessment and optimization strategies

## Support

- **Issues**: [GitHub Issues](https://github.com/username/image-preprocessing-detector/issues)
- **Discussions**: [GitHub Discussions](https://github.com/username/image-preprocessing-detector/discussions)
- **Email**: byronawilliams@gmail.com

---

**Status**: Phase 0 (Foundation) - Week 2-3 of 24-week development timeline
