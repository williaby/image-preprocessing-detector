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

##### Project Usage

- **Path**: `01_base_data/handwriting/signatr6k/`
- **Size**: 142 MB
- **Phase(s)**: Phase 7, Phase 9 (signature detection)
- **Purpose**: Signature quality assessment, detection training
- **Parser**: [`parse_signatr_labels`](../scripts/annotate_base_metadata.py#L1423) | ✅ Complete

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
