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

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ➖ | ~12,514 | tier_3_heuristic | Signatures are predominantly upright (0°); contributes negatives for non-canonical orientations only |
| MNV4-H2 | skew_reg | ❌ | 0 | N/A | Isolated signature crops; skew estimation not meaningful at this granularity |
| MNV4-H3 | resolution_quality_reg | 🟡 | ~12,514 | tier_3_heuristic | 256×256px fixed resolution; char-height metric derivable but narrow range |
| SIG-G1-1 | blur_score | 🟡 | ~12,514 | tier_3_heuristic | Stroke clarity varies; blur derivable via Laplacian variance, no ground truth labels |
| SIG-G1-2 | noise_score | 🟡 | ~12,514 | tier_3_heuristic | Background noise affects stroke quality; heuristic derivable, no ground truth |
| SIG-G1-3 | contrast_score | 🟡 | ~12,514 | tier_3_heuristic | Ink-to-background contrast variable; derivable heuristically |
| SIG-G1-4 | skew_score | ❌ | 0 | N/A | Isolated signature crops; skew quality degradation not applicable at this scale |
| SIG-G1-5 | compression_score | ❌ | 0 | N/A | PNG format (lossless); no JPEG compression artifacts present |
| SIG-G1-6 | overall_quality | ❌ | 0 | N/A | No MOS or quality score labels; 100% unreliable in L2 audit |
| SIG-G2-1 | script_cls | ➖ | ~12,514 | tier_1_annotation | 100% Latin script (Latn); useful as Latn class examples only — very narrow sub-type |
| SIG-G3-1 | orientation_cls (post) | ➖ | ~12,514 | tier_3_heuristic | Same as MNV4-H1; predominantly 0° orientation, limited orientation diversity |
| SIG-G3-2 | skew_reg (post) | ❌ | 0 | N/A | Sub-page crops; post-correction narrow skew regression not applicable |
| SIG-G4-1 | handwriting_presence_cls | ✅ | 12,514 | tier_1_annotation | 100% DOMINANT — every image is a pure handwritten signature; strong positive class anchor |
| SIG-G4-2 | handwriting_legibility_cls | 🟡 | ~12,514 | tier_2_model | Signatures are intentionally stylized; legibility varies but NOT_APPLICABLE class is often correct |
| SIG-G4-3 | handwriting_content_type_cls | ✅ | 12,514 | tier_1_annotation | 100% CURSIVE content type (signature = cursive script by definition) |
| SIG-G4-4 | presence_reg | ✅ | 12,514 | derived | 100% handwriting area ratio (1.0); all-handwriting ground truth for presence regression |
| SIG-G4-5 | legibility_reg | 🟡 | ~12,514 | tier_2_model | Legibility varies across signers; model-derived score needed (no direct GT) |
| SIG-G5-1 | capture_method_cls | ✅ | 12,514 | tier_1_annotation | 100% scanner_flatbed (confirmed by L2 aggregates); SCANNER class ground truth |
| SIG-G5-2 | shadow_reg | ❌ | 0 | N/A | Flatbed scanner capture; no shadow artifacts in signature images |
| SIG-G5-3 | warping_reg | ❌ | 0 | N/A | Fixed 256×256px crops; no page warping or distortion present |
| SIG-G5-4 | code_cls | ❌ | 0 | N/A | Signature images contain no programming code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 | ~12,514 | tier_3_heuristic | Fixed 256×256px; char-height-based score derivable but limited resolution range |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 | Latn only (100%); no non-Latin scripts — single-script dataset |
| 2 | Capture method | 🟡 | SCANNER only (scanner_flatbed 100%); no camera, born_digital, or synthetic |
| 3 | Document domain | 🟡 | PER (Personal/Signatures) domain exclusively; very narrow — no general documents |
| 4 | Layout type | ❌ | No structured layout; isolated signature crops without page context |
| 5 | Text density | 🟡 | Sparse — single isolated signature per image; no multi-element pages |
| 6 | Degradation types | 🟡 | Ink quality variation, background noise; no systematic degradation labels in L2 |
| 7 | Resolution/DPI range | ❌ | Fixed 256×256px; no DPI metadata; narrow and non-representative of production scans |
| 8 | Document age | 🟡 | Primarily modern (2023 dataset); some historical signature styles possible but unlabeled |
| 9 | Text scope | 🟡 | Signature scope only; not word/line/page — unique sub-character granularity |
| 10 | Content flags | ✅ | has_handwriting: 100%, has_signature: 100%; clear and reliable flags |
| 11 | Binarization status | 🟡 | 50% grayscale, 50% RGB; no binarized samples explicitly |
| 12 | Artifact types | ❌ | No shadow, warping, watermarks, or folds; clean scanner captures |
| 13 | Color mode | 🟡 | Mixed: 50% grayscale, 50% color (RGB); no binarized mode |
| 14 | Font variety | ❌ | Not applicable — signatures are handwritten, not typeset; no font families |

### 13.3 Corpus Role & Constraints

SignaTR6K is a narrow, high-purity corpus for the handwriting detection group (G4). Its primary role is as a **DOMINANT-class anchor** for `handwriting_presence_cls` (G4-1) and as a definitive **CURSIVE** content-type example for `handwriting_content_type_cls` (G4-3). Every image is a pure handwritten signature, making this one of the few datasets that provides a clean 1.0 ground truth for `presence_reg` (G4-4) without any mixed-content ambiguity.

The dataset is useful for `capture_method_cls` (SIG-G5-1) as a verified SCANNER class contributor, confirmed by L2 aggregates showing 100% scanner_flatbed capture. However, its utility is intentionally limited: signatures are isolated crops rather than full-page documents, so orientation, skew, layout, shadow, warping, and IQA quality heads are not applicable or only marginally useful.

**License constraint**: Academic use only (research, non-commercial). This restricts its inclusion in any commercially deployed training pipeline. All 12,514 samples must be flagged as research-only in the training manifest.

**Benchmark protection**: No reserved benchmark splits — full dataset available for training, but the academic license takes precedence over split usage. Cross-dataset leakage risk is low (unique domain and content type).

**Synthetic cap note**: Not applicable; dataset is entirely real scanned signatures (0% synthetic). No mixing cap constraints apply, though the narrow domain means overrepresentation risk for the CURSIVE class if not balanced against broader cursive handwriting sources (e.g., IAM, Muharaf).
