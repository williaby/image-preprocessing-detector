---
owner: docs-team
purpose: 'Documentation for Model Card: DocLayout-YOLO.'
schema_type: common
status: draft
tags:
- documentation
title: 'Model Card: DocLayout-YOLO'
---

> ⚠️ **SUPERSEDED** — DocLayout-YOLO has been replaced in Prepare-Doc by `docling-layout-egret-xlarge` (accuracy) and `docling-layout-heron` (speed). This card is retained for reference.

## Model Summary

> DocLayout-YOLO is a YOLO-based document layout detection model trained on DocLayNet (80,863 pages). Provides fast detection of 11 document element types with 70-82% mAP. Used in Prepare-Doc for layout-lite detection to classify page attributes and compute structural complexity scores for OCR routing.

---

## Overview

| Field | Value |
|-------|-------|
| **Model ID** | `DocLayout-YOLO` |
| **Project** | Prepare-Doc |
| **Phase** | Phase 2 - Layout-Lite Detection |
| **Status** | `pretrained` (External) |
| **Priority** | P0 (Critical - Production) |
| **Last Updated** | 2025-12-18 |
| **Schema Version** | 3.0 |

---

## 1. Model Identity

| Field | Value |
|-------|-------|
| **Architecture** | DocLayout-YOLO (YOLOv10-based) |
| **Parameters** | ~3M (nano) to ~67M (xlarge) |
| **Precision** | FP32 |
| **Input Size** | 1024x1024x3 (RGB) |
| **Output** | 11 DocLayNet classes with bounding boxes |
| **Source** | HuggingFace (`juliozhao/DocLayout-YOLO-DocStructBench`) |
| **License** | Apache-2.0 |

### Model Variants

| Variant | Parameters | mAP (%) | FPS (T4) | Latency |
|---------|-----------|---------|----------|---------|
| YOLO10n | ~3M | 70 | 85+ | ~12ms |
| YOLO10s | ~9M | 74 | 60+ | ~17ms |
| YOLO10m | ~21M | 78 | 40+ | ~25ms |
| YOLO10l | ~48M | 80 | 25+ | ~40ms |
| YOLO10x | ~67M | 82 | 15+ | ~67ms |

### 11 DocLayNet Classes

1. **Caption**: Image/table captions
2. **Footnote**: Footnote text
3. **Formula**: Mathematical formulas
4. **List-Item**: Bulleted/numbered list items
5. **Page-Footer**: Page footer content
6. **Page-Header**: Page header content
7. **Picture**: Images and figures
8. **Section-Header**: Section headings
9. **Table**: Table structures
10. **Text**: Body text paragraphs
11. **Title**: Document titles

---

## 2. Purpose & Role

| Field | Value |
|-------|-------|
| **Primary Task** | Document layout detection (11 classes) |
| **Role in Pipeline** | Layout-lite detection for page attributes |
| **Upstream Dependencies** | Text gate detection |
| **Downstream Consumers** | DQS calculator, routing engine |

### Use Cases

- Coarse layout classification for page attribute detection
- Table/figure presence detection (`has_tables`, `has_figures`)
- Formula detection (`has_dense_math`)
- Structural complexity scoring
- OCR routing decision support

### NOT Used For (Unify responsibility)

- Full semantic layout extraction
- Table structure detection (PubTables-1M)
- Reading order prediction (ReadingBank)
- Fine-grained element positioning

---

## 3. Training Details

| Field | Value |
|-------|-------|
| **Dataset** | DocLayNet (IBM) |
| **Dataset Size** | 80,863 document pages |
| **Training** | External (Julio Zhao) |
| **Prepare-Doc Role** | Inference only (no retraining) |

**DocLayNet Domains**:
- Financial reports
- Scientific articles
- Manuals
- Laws & patents
- Government tenders

---

## 4. Performance Metrics

### DocLayNet Test Set (YOLO10m)

**Overall Metrics**:

| Metric | Value |
|--------|-------|
| mAP@0.5:0.95 | 78.0% |
| FPS (T4 GPU) | 40+ |
| Latency | ~25ms/page |

**Per-Class Performance**:

| Class | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| Caption | 0.82 | 0.79 | 0.80 |
| Footnote | 0.76 | 0.71 | 0.73 |
| Formula | 0.88 | 0.84 | 0.86 |
| List-Item | 0.74 | 0.69 | 0.71 |
| Page-Footer | 0.91 | 0.87 | 0.89 |
| Page-Header | 0.89 | 0.85 | 0.87 |
| Picture | 0.86 | 0.82 | 0.84 |
| Section-Header | 0.79 | 0.75 | 0.77 |
| Table | **0.93** | **0.90** | **0.91** |
| Text | 0.81 | 0.77 | 0.79 |
| Title | 0.85 | 0.81 | 0.83 |

### Prepare-Doc Integration

| Metric | Value |
|--------|-------|
| Integration Tests | 21/21 passing |
| Confidence Threshold | 0.25 |
| NMS IOU Threshold | 0.45 |
| Typical Detections | 5-30 elements/page |

---

## 5. Limitations & Known Issues

### Document Type Limitations

- Optimized for structured documents (scientific papers, reports, forms)
- Lower accuracy on handwritten documents (<60% mAP)
- Performance degrades on heavily degraded scans (<150 DPI)

### Class-Specific Weaknesses

- **List-Item**: Lower recall on nested lists or non-standard bullets
- **Footnote**: May miss inline citations or superscript references
- **Formula**: Struggles with inline math vs. display equations

### Known Failure Modes

1. **Dense Multi-Column Layouts**: May merge adjacent columns
2. **Watermarks/Backgrounds**: False positives on decorative elements
3. **Rotated Pages**: Requires pre-rotation (handled by Phase 1 deskew)
4. **Low-Resolution Input**: <150 DPI causes significant mAP drop

### Prepare-Doc Mitigations

- Pre-flight DPI upscaling to 300 DPI (Phase 1B)
- Deskew correction before layout detection (Phase 1)
- Confidence thresholding at 0.25 (tuned for high recall)
- Fallback to classical methods for pure images (no text detected)

---

## 6. Integration Example

```python
from ultralytics import YOLO
from PIL import Image

# Load pre-trained model (auto-downloads from HuggingFace)
model = YOLO("juliozhao/DocLayout-YOLO-DocStructBench")

# Load 300 DPI page image from Phase 0 ingestion
image_path = "/data/corrected/page_001.png"

# Run inference
results = model.predict(
    source=image_path,
    imgsz=1024,        # Input size
    conf=0.25,         # Confidence threshold
    iou=0.45,          # NMS IOU threshold
    device="cpu",      # "cpu" or "cuda"
    verbose=False
)

# Extract detections
for result in results:
    boxes = result.boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
    classes = result.boxes.cls.cpu().numpy()
    confidences = result.boxes.conf.cpu().numpy()
    class_names = result.names

    # Convert to COCO format [x, y, width, height]
    for box, cls, conf in zip(boxes, classes, confidences):
        x1, y1, x2, y2 = box
        coco_box = [x1, y1, x2 - x1, y2 - y1]
        class_name = class_names[int(cls)]
        print(f"Detected {class_name}: box={coco_box}, conf={conf:.2f}")
```

---

## 7. Files & Artifacts

| File | Location |
|------|----------|
| Model Weights | HuggingFace Hub (auto-download) |
| Integration | `src/image_preprocessing_detector/detection/layout_lite.py` |
| Local Cache | `~/.cache/huggingface/hub/` |

---

## 8. References

- **HuggingFace**: https://huggingface.co/juliozhao/DocLayout-YOLO-DocStructBench
- **GitHub**: https://github.com/opendatalab/DocLayout-YOLO
- **DocLayNet Paper**: "DocLayNet: A Large Human-Annotated Dataset for Document-Layout Analysis" (IBM, 2022)
- **YOLOv10 Paper**: https://arxiv.org/abs/2405.14458

---

## Production Readiness: ✅ PRODUCTION (External pretrained, 21/21 integration tests passing)
