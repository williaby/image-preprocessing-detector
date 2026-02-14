#### SignaTR6K (Signature Dataset)

> **Quick Stats**: 12,514 signatures | 6,000 unique | Train/Val/Test splits | Signature verification
>
> **License**: Academic | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | SignaTR6K: Signature Transformer Dataset |
| **Version** | 1.0 |
| **Release Date** | 2023 |
| **Maintainer** | Sina Gholamian, Ali Vahdat |
| **Paper** | [Handwritten and Printed Text Segmentation (arXiv:2307.07887)](https://arxiv.org/abs/2307.07887) |
| **License** | Academic (research use) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/signatr6k/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Signatures** | 12,514 |
| **Unique Signatures** | ~6,000 |
| **Training Split** | Pre-defined |
| **Validation Split** | Pre-defined |
| **Test Split** | Pre-defined |
| **File Format** | PNG |
| **Image Dimensions** | Variable |

##### Content Organization

| Folder | Contents |
|--------|----------|
| **train/** | Training signature images |
| **validation/** | Validation signature images |
| **test/** | Test signature images |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned/captured signatures |
| **Baseline Quality** | Variable |
| **Blur Sensitivity** | **HIGH** - Fine stroke details critical |
| **Noise Sensitivity** | HIGH - Background noise affects verification |
| **Stroke Quality** | Variable pen pressure, ink quality |
| **Key Challenge** | Distinguishing genuine vs forged signatures |

##### Training Value

- **Strengths**: Pre-split for training, signature-specific annotations
- **Weaknesses**: Academic license limits commercial use
- **Use Case**: Signature detection, document authentication IQA
- **Complementary Datasets**: NIST SD-19 for general handwriting

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Text segmentation annotation for signature detection |
| **GT Label Coverage** | 100% |

##### Project Usage

- **Path**: `01_base_data/handwriting/signatr6k/`
- **Size**: 142 MB
- **Phase(s)**: Phase 7, Phase 9 (signature detection)
- **Purpose**: Signature quality assessment, detection training
- **Parser**: [`parse_signatr_labels`](../scripts/annotate_base_metadata.py#L1423) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/handwriting/signatr6k/` | ✅ Available | 12,514 PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Docling GPU Extracted** | `metadata_registry/extracted/signatr6k/` | ✅ Available | Docling GPU: 12,514 OCR records + 9,452 layout images, 14,506 annotations, 4 Docling categories |

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 12,514 |
| **File Format** | PNG (100%) |
| **Dimensions** | 256 × 256 px (fixed) |
| **Avg File Size** | 9 KB |
| **Color Space** | Grayscale (50%), RGB (50%) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | PER (Personal/Signatures) |
| **Content Flags** | Handwriting: ✅, Signatures: ✅ |

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 12,514 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 12,514 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |
