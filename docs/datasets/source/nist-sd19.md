---
dataset_id: nist-sd19
version: "1.0"
license: Academic
commercial_use: false
iqa_profiles:
  - scanner
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

#### NIST Special Database 19 (SD-19)

> **Quick Stats**: 810,000+ characters | 3,600 writers | Full pages + isolated chars | Ground truth
>
> **License**: Public Domain | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | NIST Special Database 19: Handprinted Forms and Characters |
| **Version** | 2nd Edition (Final) |
| **Release Date** | September 2016 |
| **Maintainer** | NIST |
| **Website** | [NIST SRD 19](https://www.nist.gov/srd/nist-special-database-19) |
| **License** | Public Domain |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/nist_sd19/` |
| **Documentation Status** | Complete |

##### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Characters** | 810,000+ |
| **Writers** | 3,600 |
| **Full Page Forms** | 3,669 (HSF pages) |
| **Resolution** | 300 DPI |
| **File Format** | PCT (Pict format) |
| **Derived Dataset** | EMNIST (28x28 normalized) |

##### Content Organization

| Archive | Contents |
|---------|----------|
| by_class.zip | Images grouped by character |
| by_field.zip | Images by form field |
| by_write.zip | Images by writer |
| hsf_page.zip | Complete handwritten forms |
| by_merge.zip | Merged compilation |

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Scanned handwritten forms |
| **Baseline Quality** | Variable (real handwriting quality) |
| **Blur Sensitivity** | HIGH - Fine stroke details |
| **Stroke Quality** | Variable (3,600 different writers) |
| **Key Value** | Ground truth for handwriting quality |

##### Benchmark Performance (EMNIST Derived)

| Task | Accuracy | Model |
|------|----------|-------|
| **Digits** | **99.89%** | CNN (10-fold) |
| **Letters** | 93.78% | Optimized classifier |
| **Full Database** | 88.12% | CNN |
| **Digits** | 99.19% | CNN |
| **Letters** | 92.42% | CNN |

*EMNIST (28×28 normalized) is derived from NIST SD-19 and widely used as OCR benchmark*

##### Training Value

- **Strengths**: Massive scale (810K characters), verified ground truth, writer diversity (3,600 writers)
- **Weaknesses**: Older format (PCT), requires conversion to modern formats
- **Derived Works**: **EMNIST** - standard handwriting recognition benchmark

##### Project Usage

- **Path**: `01_base_data/handwriting/nist_sd19_pages/`
- **Purpose**: Full-page handwriting IQA, stroke quality assessment
- **Parser**: [`parse_nist_sd19_labels`](../scripts/annotate_base_metadata.py#L1985) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/handwriting/nist-sd19/` | ✅ Available | 3,669 PNG files |
| **Text/GT** | Native annotations | ⚠️ Partial | Binary (.hsf): Character-level ground truth from filename/directory structure |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

##### Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | NIST standard collection |
| **Quality Assurance** | NIST handwriting collection protocol |
| **GT Label Coverage** | 100% |

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 3,669 (HSF pages) |
| **File Format** | PNG (100%) |
| **Dimensions** | 2560 × 3300 px (fixed) |
| **Avg File Size** | 95 KB |
| **Color Space** | Binary (1-bit) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | PER (Personal/Handwriting) |
| **Content Flags** | Handwriting: ✅ 100% |

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (91.7/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 88.3 | 18% |  |
| Field Validity | 96.3 | 18% |  |
| Doc Completeness | 45.5 | 6% | Below threshold |
| Defect Rate | 90.0 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **91.7** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 2 defects (2 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| SD19-D01 | layout_detections | HIGH | OPEN |  |
| SD19-D02 | text_has_content | MEDIUM | OPEN |  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/nist-sd19/](../../scripts/audit/results/nist-sd19/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 3,669 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 3,669 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | 🟡 Secondary | ~3,669 | tier_1_annotation | Full-page HSF scans are upright; augment with rotations to create 4-class labels |
| MNV4-H2 | skew_reg | 🟡 Secondary | ~3,669 | tier_3_heuristic | No native skew labels; classical detector can estimate skew on scanned pages |
| MNV4-H3 | resolution_quality_reg | 🟡 Secondary | ~3,669 | tier_2_model | 300 DPI scans; char-height pipeline can assign resolution quality scores |
| SIG-G1-1 | blur_score | 🟡 Secondary | ~3,669 | tier_3_heuristic | Laplacian variance derivable; handwriting strokes are blur-sensitive |
| SIG-G1-2 | noise_score | 🟡 Secondary | ~3,669 | tier_3_heuristic | Binary scan noise estimable via heuristic; limited grayscale detail |
| SIG-G1-3 | contrast_score | ➖ Negatives only | ~3,669 | tier_3_heuristic | Binary 1-bit images; contrast is effectively binary — useful as low-contrast negative class |
| SIG-G1-4 | skew_score | 🟡 Secondary | ~3,669 | tier_3_heuristic | Page-level skew quality degradation derivable from classical skew detector output |
| SIG-G1-5 | compression_score | ❌ Not applicable | 0 | N/A | PNG lossless format; no JPEG compression artifacts present |
| SIG-G1-6 | overall_quality | 🟡 Secondary | ~3,669 | tier_2_model | VLM/heuristic scoring possible; writer variability provides useful quality spread |
| SIG-G2-1 | script_cls | ✅ Primary | 3,669 | tier_0_exact | Latin (Latn) script, 100%; digits + uppercase/lowercase letters; strong Latn contributor |
| SIG-G3-1 | orientation_cls (post) | 🟡 Secondary | ~3,669 | tier_1_annotation | Same as MNV4-H1 — augmented rotation labels usable post-correction |
| SIG-G3-2 | skew_reg (post) | 🟡 Secondary | ~1,000 | tier_3_heuristic | Narrow ±2° residual filter applied to skew-estimated subset |
| SIG-G4-1 | handwriting_presence_cls | ✅ Primary | 3,669 | tier_0_exact | 100% has_handwriting; all HSF full pages are handwritten forms — DOMINANT class |
| SIG-G4-2 | handwriting_legibility_cls | ✅ Primary | 3,669 | tier_1_annotation | 3,600 writers creates natural legibility spread; ground truth strokes enable annotation |
| SIG-G4-3 | handwriting_content_type_cls | ✅ Primary | 3,669 | tier_0_exact | PRINTED handwriting (isolated characters + block letters); not cursive — clear PRINTED label |
| SIG-G4-4 | presence_reg | ✅ Primary | 3,669 | tier_0_exact | 100% handwritten pages; presence_reg = 1.0 for all — useful DOMINANT anchor |
| SIG-G4-5 | legibility_reg | 🟡 Secondary | 3,669 | tier_2_model | Writer quality varies across 3,600 writers; legibility score derivable via VLM or model |
| SIG-G5-1 | capture_method_cls | ✅ Primary | 3,669 | tier_0_exact | 100% scanner_flatbed; strong SCANNER class contributor |
| SIG-G5-2 | shadow_reg | ❌ Not applicable | 0 | N/A | Flatbed scans; no shadow artifacts present |
| SIG-G5-3 | warping_reg | ❌ Not applicable | 0 | N/A | Flatbed scans; no page warping present |
| SIG-G5-4 | code_cls | ❌ Not applicable | 0 | N/A | Handwritten characters only; no source code content |
| SIG-G5-5 | resolution_quality_reg | 🟡 Secondary | ~3,669 | tier_2_model | 300 DPI fixed; scores clusterable around optimal tier; adds SCANNER-origin examples |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | 🟡 Partial | Latin (Latn) only — 100% of 3,669 samples; no multi-script coverage |
| 2 | Capture method | ✅ Well-covered | scanner_flatbed 100% (3,669 samples); strong single-method anchor |
| 3 | Document domain | 🟡 Partial | GOV (government/personal forms) 100%; narrow domain — handwriting forms only |
| 4 | Layout type | 🟡 Partial | Forms layout (structured fields + handwritten entries); no multi-column or free-form pages |
| 5 | Text density | 🟡 Partial | Moderate-to-dense handwriting; isolated characters + full-page form fills |
| 6 | Degradation types | ❌ Not present | Binary flatbed scans; no blur/noise/compression variation documented in L2 metadata |
| 7 | Resolution/DPI range | 🟡 Partial | Fixed 300 DPI (2560×3300 px); no DPI range variation |
| 8 | Document age | 🟡 Partial | Collected pre-2016 (2nd edition 2016, original ~1990s); aged documents, not historical |
| 9 | Text scope | 🟡 Partial | Page-level (HSF full forms); also contains isolated character archives (by_class, by_field) |
| 10 | Content flags | 🟡 Partial | has_handwriting 100%; no tables, figures, formulas, or code |
| 11 | Binarization status | ✅ Well-covered | Binary (1-bit) — 100%; provides strong binarized document examples |
| 12 | Artifact types | ❌ Not present | Flatbed scans; no shadows, warping, watermarks, or folds documented |
| 13 | Color mode | 🟡 Partial | Monochrome (binary 1-bit) only; no grayscale or color variants |
| 14 | Font variety | ❌ Not present | Handwritten only (3,600 writers); no printed fonts — writer-style variety instead |

### 13.3 Corpus Role & Constraints

NIST SD-19 is a **primary contributor for handwriting heads (SIG-G4)** and a **strong Latin script anchor (SIG-G2-1)**. Its 3,669 full-page HSF scanned forms with 100% handwriting presence make it an ideal DOMINANT-class anchor for `handwriting_presence_cls` and `presence_reg`. The 3,600 writer pool provides natural legibility variation suitable for `handwriting_legibility_cls` and `legibility_reg` with model-derived or human annotation scoring. For `handwriting_content_type_cls`, the isolated-character and block-letter content maps cleanly to the PRINTED class. The dataset is public domain with no license restrictions and no benchmark-reserved splits.

The 810K+ character images (via by_class/by_field archives) are character-scope rather than page-scope and may supplement character-level handwriting tasks, but the primary training value for the multi-task pipeline lies in the 3,669 page-level HSF images. The binary 1-bit format limits IQA head utility (contrast, compression heads not applicable), and the fixed 300 DPI / flatbed capture means this dataset does not contribute diversity across resolution range, shadow, or warping dimensions. Orientation and skew labels must be synthetically derived via rotation augmentation and classical estimation respectively.
