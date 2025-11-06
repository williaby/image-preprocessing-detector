# Image Preprocessing Detector

[![CI/CD Pipeline](https://github.com/williaby/image-preprocessing-detector/workflows/CI/badge.svg)](https://github.com/williaby/image-preprocessing-detector/actions)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/williaby/image-preprocessing-detector/badge)](https://securityscorecards.dev/viewer/?uri=github.com/williaby/image-preprocessing-detector)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Intelligent image preprocessing detection system for RAG applications.** Automatically analyzes documents (PDFs, images) and detects required preprocessing steps before vector database ingestion.

## Features

- **Multi-Stage Pipeline Architecture**: Text detection gate routes documents to specialized processing paths
- **Hybrid IQA**: Classical CV + ML for image quality assessment (noise, blur, skew, contrast, orientation)
- **Document Element Detection**: YOLOv8-based detection of tables, images, handwriting, formulas
- **Quality Assessment per Element**: IQA on embedded images within text documents
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

See [ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md) for detailed architecture and [PROJECT_PLAN.md](PROJECT_PLAN.md) for complete implementation plan.

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
git clone https://github.com/username/image-preprocessing-detector.git
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
├── ARCHITECTURE_SUMMARY.md        # Architecture quick reference
└── DECISION_MATRIX.md             # Critical decisions tracking
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

## Documentation

- **[PROJECT_PLAN.md](PROJECT_PLAN.md)**: Complete 50+ page implementation plan with phased roadmap
- **[ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)**: Quick reference for architecture and design decisions
- **[DECISION_MATRIX.md](DECISION_MATRIX.md)**: Critical decisions tracking and stakeholder requirements
- **[ARCHITECTURE_CORRECTION.md](ARCHITECTURE_CORRECTION.md)**: Hybrid IQA approach for embedded images

## Roadmap

### Phase 1: MVP with Classical Methods (Weeks 4-7)
- PDF ingestion and text detection gate
- Classical IQA detectors (skew, blur, contrast)
- Correction pipeline with guardrails
- JSON output generation

### Phase 2: ML for Image Quality (Weeks 8-11)
- IQA dataset generation (50k synthetic + real images)
- Train MobileNetV3/EfficientNet multi-label classifier
- ONNX optimization for CPU inference
- Integration with classical methods

### Phase 3: ML for Document Layout (Weeks 12-16)
- Document element dataset (PubLayNet + custom)
- Train YOLOv8n/s for layout detection
- Active learning for rare classes
- INT8 quantization for production

### Phase 4: Production Hardening (Weeks 17-20)
- FastAPI service with Docker
- Performance optimization (batching, quantization)
- Monitoring and telemetry
- Comprehensive testing (80%+ coverage)

### Phase 5: Continuous Improvement (Ongoing)
- Drift detection and alerting
- Active learning pipeline
- Quarterly retraining and recalibration

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| IQA mAP | > 0.88 | Multi-label classification |
| Layout mAP@.50 | > 0.82 | Object detection |
| JSON Accuracy | > 0.85 | End-to-end pipeline |
| Latency (GPU) | < 150ms/page | With T4 GPU |
| Throughput | > 6 pages/sec | Per GPU worker |
| Test Coverage | > 80% | Unit + integration |

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

```bibtex
@software{image_preprocessing_detector,
  title = {Image Preprocessing Detector for RAG Applications},
  author = {Byron Williams},
  year = {2025},
  version = {0.1.0},
  url = {https://github.com/username/image-preprocessing-detector}
}
```

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
