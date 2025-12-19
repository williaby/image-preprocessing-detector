---
schema_type: common
title: "Model Registry"
description: "Complete inventory of all ML models in Project A with status tracking"
tags:
  - reference
  - machine_learning
  - model_registry
  - inventory
status: published
owner: core-maintainer
version: "2.0.0"
last_updated: "2025-12-18"
---

# Model Registry

Complete inventory of all ML models used in Project A (Preprocessing, IQA & Coarse Layout Gateway).

> **Schema Version**: 2.0 (Taxonomy-Aligned)
>
> **Related Documents**:
>
> - [TEMPLATE.md](TEMPLATE.md) - Standard model card template
> - [detection-taxonomy.md](../reference/detection-taxonomy.md) - Detection categories and priorities
> - [document-type-taxonomy.md](../reference/document-type-taxonomy.md) - Document classification hierarchy

---

## Summary Statistics

| Category | Count | Status |
|----------|-------|--------|
| Production Models | 3 | ✅ Trained/Pretrained |
| Classical Detectors | 3 | ✅ Complete |
| External Pretrained (Backbones) | 2 | ✅ Available |
| DIQA Ensemble (Planned) | 6 | ❌ Not Started |
| Phase 9 Classifiers (Planned) | 4 | ❌ Not Started |
| **Total** | **18** | |

---

## 1. Production Models

Models that are trained and ready for production deployment.

### 1.1 IQA Models (Phase 3)

| Model ID | Architecture | Status | Priority | Phase | Card |
|----------|--------------|--------|----------|-------|------|
| `iqa_resnet50_teacher_v1.0.0` | ResNet-50 + MultiTaskHead | ✅ Trained | P0 | 3 | [Link](production/iqa_resnet50_teacher.md) |
| `iqa_resnet18_student_v1.0.0` | ResNet-18 + MultiTaskHead | ✅ Trained | P0 | 3 | [Link](production/iqa_resnet18_student.md) |

**Performance Summary:**

| Model | Val Loss | mAP | Latency (GPU) | Latency (CPU) |
|-------|----------|-----|---------------|---------------|
| Teacher (ResNet-50) | 0.27 | >0.88 | ≤30ms | N/A (GPU-only) |
| Student (ResNet-18) | 0.14 | >0.85 | ≤10ms | ≤100ms |

### 1.2 Layout Models (Phase 2)

| Model ID | Architecture | Status | Priority | Phase | Card |
|----------|--------------|--------|----------|-------|------|
| `layout_yolov10_doclaynet_v1.0.0` | YOLOv10-doc | ✅ Pretrained | P1 | 2 | [Link](production/layout_yolov10_doclaynet.md) |

**Capabilities:**

- 11 DocLayNet classes: Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title
- Performance: 85+ FPS, 70-80% mAP
- No additional training required

---

## 2. Classical Detectors

Rule-based and heuristic detectors (no ML training required).

| Model ID | Type | Status | Priority | Phase | Card |
|----------|------|--------|----------|-------|------|
| `classical_iqa_ensemble_v1.0.0` | 8-detector ensemble | ✅ Complete | P0 | 1C | [Link](classical/classical_iqa_ensemble.md) |
| `textgate_heuristic_v1.0.0` | Ensemble heuristic | ✅ Complete | P0 | 1 | [Link](classical/textgate_heuristic.md) |
| `pdftype_classifier_v1.0.0` | Rule-based classifier | ✅ Complete | P1 | 2 | [Link](classical/pdftype_classifier.md) |

### Classical IQA Ensemble Components

| Detector | Method | Detection Category | Performance |
|----------|--------|-------------------|-------------|
| Skew | Hough Transform | Geometric Distortion | <5ms |
| Blur | Laplacian Variance | Sharpness | <3ms |
| Contrast | Histogram Analysis | Lighting | <2ms |
| Noise | Noise Estimation | Noise Artifacts | <3ms |
| Illumination | Gradient Analysis | Lighting | <3ms |
| JPEG Blockiness | Block DCT | Compression Artifacts | <5ms |
| Binarization | Otsu Analysis | Document Quality | <2ms |
| Bleed-through | Morphological Ops | Document Quality | <5ms |

**Combined Performance**: <25ms for all 8 detectors

---

## 3. External Pretrained Models (Backbones)

Pre-trained models used as backbones or base models for fine-tuning.

| Model ID | Architecture | Status | Source | Used By | Card |
|----------|--------------|--------|--------|---------|------|
| `resnet50_imagenet1k_v2` | ResNet-50 | ✅ Available | torchvision | iqa_resnet50_teacher, diqa_resnet50_generalist | [Link](external/resnet50_imagenet1k_v2.md) |
| `musiq_koniq10k` | MUSIQ (ViT-based) | ✅ Available | PyIQA | diqa_musiq_sharpness | [Link](external/musiq_koniq10k.md) |

### Model Details

| Model | Parameters | Feature Dim | Pre-training Data | Primary Use |
|-------|------------|-------------|-------------------|-------------|
| ResNet-50 ImageNet1K V2 | 25.6M | 2048 | ImageNet-1K (1.3M images) | CNN backbone |
| MUSIQ KonIQ-10k | ~27M | 384 | KonIQ-10k (10K images) | IQA transformer |

---

## 3.1 DIQA-5000 Benchmarked External IQA Models

PyIQA models evaluated on the DIQA-5000 benchmark (1000 samples, T4 GPU, 2025-12-18).

### Performance Rankings

| Rank | Model ID | Status | PLCC | SRCC | Latency | Card |
|------|----------|--------|------|------|---------|------|
| 🏆 1 | `PyIQA-maniqa` | 🏆 BEST PERFORMER | 0.5628 | 0.5258 | 1845ms | [Link](external/maniqa.md) |
| ⭐⭐ 2 | `PyIQA-liqe` | ⭐⭐ HIGHLY RECOMMENDED | 0.5107 | 0.4031 | 150ms | [Link](external/liqe.md) |
| ⭐ 3 | `PyIQA-hyperiqa` | ⭐ TOP TIER 1 CANDIDATE | 0.3271 | 0.2362 | 152ms | [Link](external/hyperiqa.md) |
| 4 | `PyIQA-dbcnn` | ✅ RECOMMENDED | 0.2880 | 0.2880 | 100ms | [Link](external/dbcnn.md) |
| 5 | `PyIQA-clipiqa` | ⚠️ REQUIRES FINE-TUNING | 0.2397 | 0.1596 | 116ms | [Link](external/clipiqa.md) |
| 6 | `PyIQA-qualiclip` | ⚠️ REQUIRES FINE-TUNING | 0.2216 | 0.1038 | 143ms | [Link](external/qualiclip.md) |
| 7 | `PyIQA-tres` | ❌ NOT RECOMMENDED | 0.1206 | 0.0588 | 700ms | [Link](external/tres.md) |
| 8 | `PyIQA-brisque` | 📊 REFERENCE BASELINE | 0.0928 | -0.0556 | 20ms | [Link](external/brisque.md) |
| 9 | `PyIQA-arniqa` | ❌ NOT RECOMMENDED | -0.0512 | -0.1202 | 111ms | [Link](external/arniqa.md) |
| 10 | `PyIQA-niqe` | 📊 REFERENCE BASELINE | -0.0550 | -0.2074 | 30ms | [Link](external/niqe.md) |
| 11 | `PyIQA-nima` | ❌ NOT RECOMMENDED | -0.1232 | -0.2484 | 50ms | [Link](external/nima.md) |
| 12 | `PyIQA-paq2piq` | ❌ NOT RECOMMENDED | -0.0206 | -0.1953 | 80ms | [Link](external/paq2piq.md) |

### Status Legend

| Status | Meaning | Production Use |
|--------|---------|----------------|
| 🏆 BEST PERFORMER | Highest correlations | Teacher/oracle (high latency) |
| ⭐⭐ HIGHLY RECOMMENDED | Strong correlations, good latency | Fine-tuning priority |
| ⭐ TOP TIER 1 CANDIDATE | Best among efficient models | Fine-tuning candidate |
| ✅ RECOMMENDED | Positive correlations, efficient | Ensemble member |
| ⚠️ REQUIRES FINE-TUNING | Below target, needs adaptation | After fine-tuning |
| ❌ NOT RECOMMENDED | Negative/weak correlations | Not suitable |
| 📊 REFERENCE BASELINE | Classical CV comparison | Reference only |

### Key Findings

**Top Performers:**

- **MANIQA** (🏆): Best overall (PLCC 0.56) but extreme latency (1.8s) - use as teacher
- **LIQE** (⭐⭐): Second best (PLCC 0.51), best error metrics, 150ms - primary candidate
- **HyperIQA** (⭐): Best Tier 1 (PLCC 0.33), 152ms - efficient fine-tuning candidate

**Negative Correlations (Domain Mismatch):**

- ARNIQA, NIMA, PAQ2PIQ, NIQE show negative correlations
- Natural image IQA models fail on document domain
- Demonstrates need for document-specific training

---

## 4. Planned Models - DIQA Ensemble

Document Image Quality Assessment pseudo-labeling ensemble (from DIQA-5000 specification).

### 4.1 Track A: Traditional IQA Models

| Model ID | Architecture | Status | Priority | Role | Card |
|----------|--------------|--------|----------|------|------|
| `diqa_resnet50_generalist_v1.0.0` | ResNet-50 + MultiTaskHead | ❌ Planned | P1 | Anchor (generalist) | [Link](planned/diqa/diqa_resnet50_generalist.md) |
| `diqa_musiq_sharpness_v1.0.0` | MUSIQ (ViT-based) | ❌ Planned | P1 | Sharpness specialist | [Link](planned/diqa/diqa_musiq_sharpness.md) |
| `diqa_qualiclip_color_v1.0.0` | QualiCLIP | ❌ Planned | P2 | Color specialist | [Link](planned/diqa/diqa_qualiclip_color.md) |

### 4.2 Track B: Vision-Language Models

| Model ID | Architecture | Status | Priority | Role | Card |
|----------|--------------|--------|----------|------|------|
| `diqa_qwen3vl_generalist_v1.0.0` | Qwen2.5-VL-3B | ❌ Planned | P1 | Anchor (generalist) | [Link](planned/diqa/diqa_qwen3vl_generalist.md) |
| `diqa_internvl3_overall_v1.0.0` | InternVL3-1B | ❌ Planned | P2 | Overall specialist | [Link](planned/diqa/diqa_internvl3_overall.md) |

### 4.3 Ensemble Fusion

| Model ID | Architecture | Status | Priority | Role | Card |
|----------|--------------|--------|----------|------|------|
| `diqa_stacker_ensemble_v1.0.0` | Gradient Boosting | ❌ Planned | P1 | Meta-learner | [Link](planned/diqa/diqa_stacker_ensemble.md) |

**DIQA Ensemble Architecture:**

```text
Track A (IQA)                    Track B (VLM)
─────────────                    ─────────────
ResNet-50 (anchor)               Qwen2.5-VL-3B (anchor)
MUSIQ (sharpness)                InternVL3-1B (overall)
QualiCLIP (color)
         ↓                              ↓
         └──────────┬──────────────────┘
                    ↓
            [Stacker Ensemble]
                    ↓
            Final Pseudo-Labels
```

---

## 5. Planned Models - Phase 9 Classifiers

Element-specific classifiers for detailed document analysis.

| Model ID | Architecture | Status | Priority | Target | Card |
|----------|--------------|--------|----------|--------|------|
| `classify_resnet18_table_v1.0.0` | ResNet-18 | ❌ Planned | P2 | Table type | [Link](planned/phase9/classify_resnet18_table.md) |
| `classify_resnet18_handwriting_v1.0.0` | ResNet-18 | ❌ Planned | P2 | Handwriting | [Link](planned/phase9/classify_resnet18_handwriting.md) |
| `classify_resnet18_formula_v1.0.0` | ResNet-18 | ❌ Planned | P3 | Math formulas | [Link](planned/phase9/classify_resnet18_formula.md) |
| `classify_mobilenetv3_parasitic_v1.0.0` | MobileNetV3-Small | ❌ Planned | P3 | Parasitic elements | [Link](planned/phase9/classify_mobilenetv3_parasitic.md) |

**Target Classes:**

| Classifier | Classes |
|------------|---------|
| Table Type | simple, complex, nested, borderless |
| Handwriting | none, annotations, full_handwritten, signatures |
| Formula | inline_math, display_math, chemical, none |
| Parasitic | watermark, stamp, redaction, highlight, sticky_note |

---

## 6. Detection Category Coverage

Mapping models to detection taxonomy categories (from [detection-taxonomy.md](../reference/detection-taxonomy.md)).

### 6.1 Coverage Matrix

| Detection Category | Classical | ML IQA | Layout | DIQA | Phase 9 |
|--------------------|-----------|--------|--------|------|---------|
| **Geometric Distortion** | | | | | |
| Skew | ✅ | ✅ | | ✅ | |
| Rotation | ✅ | ✅ | | ✅ | |
| Perspective | | ✅ | | ✅ | |
| **Sharpness** | | | | | |
| Blur (motion/focus) | ✅ | ✅ | | ✅ | |
| Low resolution | | ✅ | | ✅ | |
| **Lighting** | | | | | |
| Contrast | ✅ | ✅ | | ✅ | |
| Illumination | ✅ | ✅ | | ✅ | |
| Shadows | | ✅ | | ✅ | |
| **Noise** | | | | | |
| Sensor noise | ✅ | ✅ | | ✅ | |
| Compression artifacts | ✅ | ✅ | | ✅ | |
| **Document Quality** | | | | | |
| Binarization issues | ✅ | | | | |
| Bleed-through | ✅ | | | | |
| **Layout Elements** | | | | | |
| Tables | | | ✅ | | ✅ |
| Figures | | | ✅ | | |
| Formulas | | | ✅ | | ✅ |
| Handwriting | | | | | ✅ |
| **Parasitic Elements** | | | | | |
| Watermarks | | | | | ✅ |
| Stamps | | | | | ✅ |

### 6.2 Priority Distribution

| Priority | Count | Models |
|----------|-------|--------|
| P0 (Critical) | 4 | IQA Teacher, IQA Student, Classical Ensemble, Text Gate |
| P1 (High) | 5 | Layout, DIQA ResNet, DIQA MUSIQ, DIQA Qwen, DIQA Stacker |
| P2 (Medium) | 4 | PDF Classifier, DIQA QualiCLIP, DIQA InternVL, Table/Handwriting |
| P3 (Low) | 3 | Formula, Parasitic classifiers |

---

## 7. Model Dependencies

### 7.1 Dependency Graph

```text
┌─────────────────────────────────────────────────────────────┐
│                    INPUT DOCUMENTS                          │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
              ┌───────────────────────┐
              │   PDF Type Classifier │ (P2)
              └───────────┬───────────┘
                          ↓
              ┌───────────────────────┐
              │      Text Gate        │ (P0)
              └───────────┬───────────┘
                          ↓
         ┌────────────────┴────────────────┐
         ↓                                 ↓
┌─────────────────┐              ┌─────────────────┐
│ Classical IQA   │ (P0)         │  Layout-Lite    │ (P1)
│ (8 detectors)   │              │  (YOLOv10-doc)  │
└────────┬────────┘              └────────┬────────┘
         │                                │
         └────────────┬───────────────────┘
                      ↓
         ┌────────────────────────┐
         │   ML IQA (Student)     │ (P0)
         └────────────┬───────────┘
                      ↓
         ┌────────────────────────┐
         │   ML IQA (Teacher)     │ (P0) [selective]
         └────────────┬───────────┘
                      ↓
         ┌────────────────────────┐
         │    DQS Calculator      │
         │    Routing Engine      │
         └────────────────────────┘
```

### 7.2 Execution Order

| Order | Model | Condition |
|-------|-------|-----------|
| 1 | PDF Type Classifier | Always |
| 2 | Text Gate | Always |
| 3 | Classical IQA | No text detected |
| 3 | Layout-Lite | Text detected |
| 4 | ML IQA Student | Always |
| 5 | ML IQA Teacher | High uncertainty OR discrepancy |

---

## 8. Storage & Versioning

### 8.1 Storage Locations

| Environment | Base Path | Format |
|-------------|-----------|--------|
| GCS (Production) | `gs://image_detection_b/models/` | `.pt`, `.onnx` |
| Local (Development) | `models/` | `.pt`, `.onnx` |
| Modal (Training) | Volume mount | `.pt` |

### 8.2 Naming Convention

```text
{task}_{architecture}_{variant}_v{major}.{minor}.{patch}

Examples:
- iqa_resnet50_teacher_v1.0.0
- diqa_musiq_sharpness_v1.0.0
- classify_resnet18_table_v1.0.0
```

### 8.3 Version Schema

| Component | Increment When |
|-----------|----------------|
| Major | Breaking architecture changes |
| Minor | New capabilities, retraining |
| Patch | Bug fixes, calibration updates |

---

## 9. Governance & Lifecycle

### 9.1 Model Lifecycle States

```text
planned → training → trained → validated → production → deprecated
```

| State | Description | Requirements |
|-------|-------------|--------------|
| Planned | Specification documented | Model card created |
| Training | Active training in progress | Training script ready |
| Trained | Training complete | Metrics recorded |
| Validated | Cross-dataset validation complete | Meets performance targets |
| Production | Deployed and serving | ONNX export, registry entry |
| Deprecated | No longer supported | Successor identified |

### 9.2 Review Cadence

| Model Type | Review Frequency | Responsible |
|------------|------------------|-------------|
| Production (P0) | Monthly | Core Team |
| Production (P1-P2) | Quarterly | Core Team |
| Classical | Semi-annually | Core Team |
| Planned | On implementation | Implementing Team |

### 9.3 Deprecation Policy

1. **Notice Period**: 90 days minimum
2. **Migration Path**: Successor model must be identified
3. **Documentation**: Deprecation reason and migration guide required
4. **Archive**: Model cards moved to `deprecated/` directory

---

## 10. Registry Schema

Python dataclass for programmatic model registry access:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import date

class ModelStatus(Enum):
    PLANNED = "planned"
    TRAINING = "training"
    TRAINED = "trained"
    VALIDATED = "validated"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"

class Priority(Enum):
    P0_CRITICAL = "P0"
    P1_HIGH = "P1"
    P2_MEDIUM = "P2"
    P3_LOW = "P3"

@dataclass
class ModelRegistryEntry:
    model_id: str
    architecture: str
    status: ModelStatus
    priority: Priority
    phase: int
    card_path: str
    val_loss: Optional[float] = None
    map_score: Optional[float] = None
    latency_gpu_ms: Optional[float] = None
    latency_cpu_ms: Optional[float] = None
    gcs_path: Optional[str] = None
    last_updated: Optional[date] = None
```

---

## 11. Quick Reference

### Models by Phase

| Phase | Models |
|-------|--------|
| 1 | Text Gate |
| 1C | Classical IQA Ensemble |
| 2 | PDF Type Classifier, Layout-Lite (YOLOv10) |
| 3 | IQA Teacher (ResNet-50), IQA Student (ResNet-18) |
| DIQA | 6 ensemble models (Track A + B + Stacker) |
| 9 | 4 element classifiers |

### Models by Architecture

| Architecture | Models |
|--------------|--------|
| ResNet-50 | IQA Teacher, DIQA Generalist |
| ResNet-18 | IQA Student, Table/Handwriting/Formula classifiers |
| YOLOv10 | Layout-Lite |
| MUSIQ (ViT) | DIQA Sharpness |
| QualiCLIP | DIQA Color |
| Qwen2.5-VL | DIQA VLM Anchor |
| InternVL3 | DIQA Overall |
| MobileNetV3 | Parasitic Classifier |
| Gradient Boosting | DIQA Stacker |
| Heuristic | Text Gate, Classical IQA, PDF Classifier |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2025-12-18 | Taxonomy-aligned restructure, added DIQA and Phase 9 models |
| 1.0.0 | 2025-02-01 | Initial registry with Phase 1-3 models |
