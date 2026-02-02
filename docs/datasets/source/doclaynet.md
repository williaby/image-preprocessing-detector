#### DocLayNet

> **Quick Stats**: 80,863 pages | Mixed domains | 11 layout classes | Expert-annotated
>
> **License**: CDLA-Permissive-1.0 | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | DocLayNet: A Large Human-Annotated Dataset for Document-Layout Segmentation |
| **Version** | 1.0 |
| **Release Date** | 2022 |
| **Maintainer** | IBM Research (DS4SD) |
| **Paper** | [DocLayNet (KDD 2022)](https://arxiv.org/abs/2206.01062) |
| **Repository** | [GitHub: DS4SD/DocLayNet](https://github.com/DS4SD/DocLayNet) |
| **HuggingFace** | [ds4sd/DocLayNet](https://huggingface.co/datasets/ds4sd/DocLayNet) |
| **License** | CDLA-Permissive-1.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/doclaynet/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Pages** | 80,863 unique pages |
| **Training Split** | 69,375 (85.8%) |
| **Validation Split** | 6,489 (8.0%) |
| **Test Split** | 4,999 (6.2%) |
| **Image Dimensions** | 1025 × 1025 pixels (resized) |
| **File Format** | PNG (images), PDF (originals) |
| **Annotation Format** | COCO format (bboxes + polygons) |
| **Total Size** | 28 GiB (core) + 7.5 GiB (extras) |

##### Document Categories (6)

| Category | Description |
|----------|-------------|
| Financial Reports | Annual reports, earnings statements |
| Scientific Articles | Research papers, journals |
| Laws & Regulations | Legal documents, statutes |
| Government Tenders | Procurement documents |
| Manuals | Technical documentation |
| Patents | Patent applications, grants |

##### Layout Classes (11)

1. **Caption** - Figure/table captions
2. **Footnote** - Page footnotes
3. **Formula** - Mathematical equations
4. **List-item** - Bulleted/numbered items
5. **Page-footer** - Page numbers, footers
6. **Page-header** - Headers, titles
7. **Picture** - Images, diagrams
8. **Section-header** - Section titles
9. **Table** - Tabular content
10. **Text** - Body text paragraphs
11. **Title** - Document titles

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Born-digital (professionally typeset) |
| **Annotation Quality** | **HIGH** - Expert human annotation, redundant labeling |
| **Blur Sensitivity** | MEDIUM - Variable element sizes |
| **Layout Complexity** | **HIGH** - Multi-column, mixed content types |
| **Skew Sensitivity** | LOW - Born-digital, no rotation |
| **Key Challenge** | Complex mixed layouts, variable density regions |

##### Benchmark Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Inter-Annotator Gap** | ~10% | Models fall behind human agreement by ~10% mAP |
| **vs. PubLayNet** | More robust | DocLayNet-trained models generalize better |
| **vs. DocBank** | More robust | Better on challenging, diverse layouts |

*DocLayNet-trained models are the "preferred choice for general-purpose document-layout analysis"*

##### Annotation Quality

- **Double/Triple Annotated**: Subset of pages for inter-annotator agreement measurement
- **Crowdsourced**: By well-trained expert annotators
- **Format**: COCO-style with bounding boxes + polygon segmentation

##### Training Value

- **Strengths**: Expert annotations, diverse domains (6 categories), industry-standard COCO format
- **Weaknesses**: Born-digital only, resized images may lose detail
- **Unique Features**: Polygon segmentation, font metadata in JSON extras, redundant annotation subset
- **Benchmark Suitability**: **HIGH** - KDD 2022 benchmark for layout detection

##### Project Usage

- **Path**: `01_base_data/documents/doclaynet/`
- **Phase(s)**: Phase 2 (Layout-lite), Phase 7 training
- **Purpose**: Layout-aware IQA training, element detection
- **Parser**: [`parse_doclaynet_labels`](../scripts/annotate_base_metadata.py#L1296) | ✅ Complete

##### Text Labels

DocLayNet includes per-document JSON files with text content extracted from the original PDFs:

| Attribute | Value |
|-----------|-------|
| **Location** | `ground_truth/json/` (81,471 files) |
| **Format** | JSON with `cells` array |
| **Fields** | `text`, `bbox`, `font` (color, name, size) |

**Sample structure**:

```json
{"metadata": {...}, "cells": [{"bbox": [97.4, 70.4, 18.9, 9.5], "text": "The", "font": {...}}, ...]}
```

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 81,471 |
| **File Format** | PNG (100%) |
| **Dimensions** | 1025 × 1025 px (fixed) |
| **Avg File Size** | 412 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | Mixed (FIN, SCI, GOV, TECH) |

##### References

```bibtex
@inproceedings{doclaynet2022,
  title={DocLayNet: A Large Human-Annotated Dataset for Document-Layout Segmentation},
  author={Pfitzmann, Birgit and others},
  booktitle={KDD},
  year={2022},
  doi={10.1145/3534678.3539043}
}
```

---
