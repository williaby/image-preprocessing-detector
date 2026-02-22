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

##### File Format

| Attribute | Value |
|-----------|-------|
| **Image Format** | PNG |
| **Dimensions** | 256 x 256 px (fixed) |
| **Color Space** | Grayscale (50%), RGB (50%) |
| **Avg File Size** | ~9 KB |
| **Total Size** | 142 MB |

##### Label Schema

| Label | Type | Description |
|-------|------|-------------|
| **Signature ID** | Categorical | Unique signer identifier |
| **Split** | Categorical | train / validation / test |

No bounding box or segmentation annotations provided. Classification-only dataset organized by folder structure.

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

##### Known Limitations

- Academic license restricts commercial use
- Fixed 256x256 resolution may not represent production document scans
- No bounding box or segmentation masks provided
- No negative examples (non-signature images) included
- Handwriting quality varies significantly across signers

##### License & Citation

| Attribute | Value |
|-----------|-------|
| **License** | Academic (research use only) |
| **Commercial Use** | Not permitted |
| **Citation** | Gholamian & Vahdat (2023). arXiv:2307.07887 |

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

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (88.0/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 92.8 | 17% |  |
| Field Validity | 96.3 | 17% |  |
| Doc Completeness | 100.0 | 6% |  |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | 46.6 | 17% | Below threshold |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **88.0** | | **Grade B** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 95.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/signatr6k/](../../scripts/audit/results/signatr6k/)

##### Processing Notes

- Parser: `parse_signatr_labels` in `annotate_base_metadata.py`
- Docling GPU extraction complete: 12,514 OCR records + 9,452 layout images
- Layer 2 enrichment applied with standard pipeline
- 100% of samples classified as "unreliable" due to zero-confidence text quality scores

##### Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2023 | Initial dataset release |
| L2 v1 | 2026-02-10 | Layer 2 metadata annotation |
| L2 v2 | 2026-02-14 | Scorecard v2.0 audit |

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 12,514 | **Avg Min Confidence**: 0.000

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
