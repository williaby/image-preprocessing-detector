---
schema_type: common
title: "Architecture Documentation"
description: "System architecture, design decisions, and technical specifications"
tags: [architecture, development, documentation]
status: published
owner: "core-maintainer"
authors:
  - name: "Byron Williams"
purpose: "Document the system architecture, design decisions, and technical rationale."
---

Comprehensive architecture documentation for the Image Preprocessing Detector system.

## System Architecture

See the complete architecture documentation in [ARCHITECTURE_SUMMARY.md](../../ARCHITECTURE_SUMMARY.md).

## Key Design Decisions

### 1. Text Detection Gate

**Decision**: Route documents through fast text detection before processing

**Rationale**:
- Mixed document types require different strategies
- YOLOv8 layout detection expensive for pure images
- Fast heuristics (< 10ms) provide efficient routing

**Trade-offs**:
- Occasional misclassification vs. 10-50× speedup
- Simple ensemble vs. deep learning accuracy

**See**: [Text Gate Implementation](../../src/image_preprocessing_detector/detection/text_gate.py)

### 2. Hybrid IQA Approach

**Decision**: Per-element quality assessment for embedded images

**Problem**: Text documents contain embedded images (tables, figures) needing independent quality assessment

**Solution**:
1. Detect document layout (YOLOv8)
2. Extract each element region
3. Run IQA on element
4. Store per-element quality issues

**Rationale**:
- Accurate quality assessment for complex documents
- Targeted corrections per element
- Preserves high-quality regions

**See**: [Architecture Correction](../../ARCHITECTURE_CORRECTION.md)

### 3. COCO Bounding Box Format

**Decision**: Use COCO format `[x, y, width, height]`

**Rationale**:
- Industry standard for object detection
- Compatible with LayoutParser, Detectron2, YOLO
- Simplifies downstream integration

**Alternative**: Corner format `[x1, y1, x2, y2]` (rejected for incompatibility)

**See**: [Schema API](../api/schema.md)

### 4. 300 DPI Standardization

**Decision**: Normalize all inputs to 300 DPI

**Rationale**:
- Industry standard for document scanning
- Sufficient for OCR and layout detection
- Balances quality and computational cost

**Trade-offs**:
- May upsample low-resolution images
- May downsample high-resolution scans
- Consistent processing pipeline

### 5. Pydantic v2 for Schema

**Decision**: Use Pydantic v2 for JSON schema validation

**Rationale**:
- Type safety and validation
- JSON serialization built-in
- Discriminated unions for flexibility
- Industry standard for Python APIs

**See**: [Schema Module](../../src/image_preprocessing_detector/schema.py)

### 6. Phased Development Approach

**Decision**: Incremental delivery in 5 phases

**Rationale**:
- Reduce risk with MVP (Phase 1)
- Validate assumptions early
- Iterative improvement
- Clear milestones

**Phases**:
- Phase 0: Foundation (Complete)
- Phase 1: Classical methods (Current)
- Phase 2: ML IQA
- Phase 3: ML layout
- Phase 4: Production
- Phase 5: Continuous improvement

**See**: [Project Plan](../../PROJECT_PLAN.md)

## Module Architecture

### Ingestion Module

**Purpose**: Load and standardize documents

**Design**:
- PyMuPDF for PDF extraction
- Pillow for image I/O
- OpenCV for preprocessing
- 300 DPI normalization

**Files**:
- [pdf_loader.py](../../src/image_preprocessing_detector/ingestion/pdf_loader.py)
- [image_loader.py](../../src/image_preprocessing_detector/ingestion/image_loader.py)

### Detection Module

**Purpose**: Assess quality and detect layout

**Design**:
- Text gate for routing
- Classical IQA (Phase 1)
- ML IQA (Phase 2)
- YOLOv8 layout (Phase 3)

**Files**:
- [text_gate.py](../../src/image_preprocessing_detector/detection/text_gate.py)
- [iqa_classical.py](../../src/image_preprocessing_detector/detection/iqa_classical.py)

### Correction Module

**Purpose**: Apply preprocessing with guardrails

**Design**:
- OpenCV-based operations
- Validation before/after
- Transform history tracking

**Files**:
- [corrections.py](../../src/image_preprocessing_detector/correction/corrections.py)

### Output Module

**Purpose**: Generate JSON metadata

**Design**:
- Pydantic serialization
- COCO-aligned format
- Audit trail preservation

**Files**:
- [json_generator.py](../../src/image_preprocessing_detector/output/json_generator.py)

### Schema Module

**Purpose**: Define data models

**Design**:
- Pydantic v2 models
- Discriminated unions
- Validation rules

**Files**:
- [schema.py](../../src/image_preprocessing_detector/schema.py)

## Data Flow

```
Input → Ingestion → Text Gate → Detection → Correction → Output
  │         │           │            │           │          │
  │         ▼           ▼            ▼           ▼          ▼
  │      300 DPI    Route Path    Quality    Transform   JSON
  │      Image      Decision      Issues     History    Metadata
  └──────────────────────────────────────────────────────┘
```

## Technology Stack

### Core Dependencies

| Technology | Purpose | Version |
|------------|---------|---------|
| **Python** | Language | 3.11+ |
| **PyMuPDF** | PDF extraction | 1.23+ |
| **Pillow** | Image I/O | 10.0+ |
| **OpenCV** | Computer vision | 4.8+ |
| **NumPy** | Array operations | 1.24+ |
| **Pydantic** | Schema validation | 2.0+ |

### Development Tools

| Tool | Purpose | Version |
|------|---------|---------|
| **Poetry** | Dependency management | 2.0+ |
| **Black** | Code formatting | 25.9+ |
| **Ruff** | Linting | Latest |
| **MyPy** | Type checking | 1.4+ |
| **Pytest** | Testing | 7.4+ |

### ML Dependencies (Phase 2+)

| Technology | Purpose | Version |
|------------|---------|---------|
| **PyTorch** | Deep learning | 2.0+ |
| **YOLOv8** | Object detection | 8.0+ |
| **ONNX** | Model optimization | 1.15+ |
| **Albumentations** | Augmentation | 1.3+ |

## Performance Considerations

### Latency Targets

| Component | Phase 1 (CPU) | Phase 3 (GPU) |
|-----------|--------------|---------------|
| **Ingestion** | ~1s/page | ~1s/page |
| **Text Gate** | < 10ms | < 10ms |
| **Classical IQA** | ~170ms | ~170ms |
| **ML IQA** | N/A | < 50ms |
| **Layout Detection** | N/A | < 50ms |
| **Correction** | ~500ms | ~500ms |
| **Total** | ~2s/page | ~700ms/page |

### Throughput Targets

| Configuration | Pages/Second |
|--------------|--------------|
| **CPU (Phase 1)** | 0.5 |
| **GPU (Phase 3)** | 6+ |
| **GPU Batch** | 20+ |

### Memory Usage

| Component | Memory per Page |
|-----------|----------------|
| **Input Image** | ~25MB (300 DPI, A4) |
| **Processing** | ~50MB (temporary) |
| **ML Models** | ~100MB (loaded once) |

## Security Considerations

### Input Validation

- File size limits (default: 100MB)
- Format validation (PDF, PNG, JPEG, TIFF)
- Malformed file detection
- Resource limits (memory, CPU time)

### Dependency Scanning

- Safety: Vulnerability scanning
- Bandit: Security linting
- CodeQL: Static analysis
- Dependabot: Automated updates

**See**: [Security Documentation](../security/)

## Testing Strategy

### Test Levels

1. **Unit Tests**: Individual functions
2. **Integration Tests**: Module interactions
3. **End-to-End Tests**: Full pipeline
4. **Performance Tests**: Latency and throughput

### Coverage Requirements

- Minimum: 80% (enforced)
- Current: 94%+ (Phase 0)
- Target: 90%+ (all phases)

**See**: [Testing Guide](testing.md)

## Deployment Architecture (Phase 4)

### API Deployment

- FastAPI application
- Uvicorn ASGI server
- Docker containerization
- Kubernetes orchestration

### Scaling Strategy

- Horizontal scaling (multiple workers)
- GPU acceleration (NVIDIA T4+)
- Batch processing optimization
- Queue-based processing (Celery)

## Future Enhancements

### Phase 2

- ML-based IQA (MobileNetV3/EfficientNet)
- Multi-label classification
- GPU acceleration

### Phase 3

- YOLOv8 layout detection
- Hybrid IQA integration
- COCO dataset fine-tuning

### Phase 4

- REST API (FastAPI)
- Batch processing API
- Monitoring and telemetry
- Performance optimization

### Phase 5

- Continuous model improvement
- New feature development
- Performance tuning

## References

- [ARCHITECTURE_SUMMARY.md](../../ARCHITECTURE_SUMMARY.md) - Complete architecture
- [ARCHITECTURE_CORRECTION.md](../../ARCHITECTURE_CORRECTION.md) - Hybrid IQA rationale
- [PROJECT_PLAN.md](../../PROJECT_PLAN.md) - Detailed roadmap
- [DECISION_MATRIX.md](../../DECISION_MATRIX.md) - Decision tracking

## See Also

- [Testing Guide](testing.md) - Testing strategy
- [Code Quality](code-quality.md) - Quality standards
- [Contributing](contributing.md) - Development workflow
