### dibco (Document Image Binarization Competition)

> **Quick Stats**: 343 images (212 train + 131 competition test) | 2009-2019 competitions | Extreme degradation test
>
> **License**: Academic | **Commercial Use**: Research only

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Document Image Binarization Competition |
| **Version** | 2009-2019 (11 editions) |
| **Release Date** | 2009-2019 (annual at ICDAR/ICFHR) |
| **Maintainer** | ICDAR/ICFHR Organizing Committee |
| **Paper** | [DIBCO 2019](https://ieeexplore.ieee.org/document/8977995) |
| **Repository** | [vc.ee.duth.gr/dibco2019](https://vc.ee.duth.gr/dibco2019/) |
| **License** | Academic (research use only) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/dibco/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | BMP / PNG / TIFF / JPEG | Historical document images with degradations |
| **Ground Truth** | BMP / PNG / TIFF | Binary binarization masks (pixel-perfect) |
| **Metadata** | Directory structure | Year, document type (handwritten/printed) encoded in folder names |
| **Supplementary** | TXT / PDF | Competition guidelines, evaluation scripts |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `{year}/DIBCO{year}_Test_images-{type}/` | `{year}/DIBCO{year}-GT-Test-images_{type}/` | 212 | ✅ |
| **Competition Test** | Various years (2009-2019) | Paired GT directories | 131 | ✅ RESERVED |

**Split Organization Pattern**: `by_folder` (organized by competition year, then document type)

> **Notes**:
>
> - Competition years: 2009, 2010, 2011, 2012, 2013, 2014, 2016, 2017, 2018, 2019
> - Document types: `handwritten` or `printed`
> - GT directory naming inconsistent: uses underscores (`_handwritten`) vs input hyphens (`-handwritten`)
> - Competition test sets (131 images) are RESERVED for benchmark evaluation only

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Segmentation Masks** | BMP / PNG / TIFF | Pixel-level | Binary binarization ground truth (0=background, 255=foreground) |
| **Competition Year** | Directory name | Image-level | Encoded in folder structure (e.g., `2013/`) |
| **Document Type** | Directory name | Image-level | Handwritten vs printed (encoded in folder structure) |

> **Note**: DIBCO provides binary ground truth masks for binarization evaluation, not traditional bounding box or text annotations.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Competition websites | Evaluation metrics, competition results, papers |
| **Image-level** | Filename / Directory | Year, document type, test/GT designation |
| **Annotation-level** | N/A | No per-annotation metadata (pixel masks only) |

##### 2.5 Annotation Schema Details

> **Format**: Directory structure-based, not annotation files

```text
# Directory structure schema
DIBCO/
  {year}/                                    # Competition year (2009-2019)
    DIBCO{year}_Test_images-handwritten/    # Input images (handwritten)
      H01.png
      H02.bmp
    DIBCO{year}_Test_images-printed/        # Input images (printed)
      P01.bmp
      P02.png
    DIBCO{year}-GT-Test-images_handwritten/ # Ground truth (note underscore)
      H01_GT.png
      H02_GT.bmp
    DIBCO{year}-GT-Test-images_printed/
      P01_GT.bmp
      P02_GT.png

# Naming conventions:
# - Input folders use hyphens: "-handwritten", "-printed"
# - GT folders use underscores: "_handwritten", "_printed"
# - GT files add "_GT" suffix before extension
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `year` | int | Yes | Extracted from directory name (e.g., `2013`) |
| `document_type` | str | Yes | "handwritten" or "printed" from folder name |
| `is_ground_truth` | bool | Yes | Detected from "GT" in folder/filename |
| `ground_truth_path` | str | Conditional | Paired GT image path if available |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Competition year | `dibco_year` | High | Extracted from directory structure |
| ✅ Document type | `document_type` | High | Handwritten vs printed |
| ✅ GT availability | `has_ground_truth` | High | Paired binary masks |
| ✅ GT path | `ground_truth_path` | Medium | For evaluation pipeline |
| ⚠️ Degradation types | - | Low | Could infer from year/competition focus |
| ❌ Quality scores | - | N/A | Not provided (binarization benchmark) |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | Competition organizers |
| **Quality Assurance** | DIBCO competition binarization ground truth masks |
| **GT Label Coverage** | 100% |

#### Dataset Statistics

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 212 | 212 | 100% | ✅ Complete |
| **Competition Test** | 131 | 0 | 0% | ⚠️ RESERVED (benchmark only) |
| **Total** | 343 | 212 | 62% | ⚠️ Partial (test excluded by design) |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ⚠️ RESERVED - Competition test sets excluded from Layer 2 by design
- ❌ Missing - Split not included in Layer 2 metadata

> **Note**: Competition test sets (131 images) are intentionally excluded from Layer 2 processing
> to preserve benchmark integrity. Only the 212 train split images are processed.

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 343 (212 train + 131 competition test) |
| **Training Split** | 212 (62%) |
| **Test Split** | 131 (38%) - RESERVED for competition benchmarking |
| **Years Covered** | 2009, 2010, 2011, 2012, 2013, 2014, 2016, 2017, 2018, 2019 |
| **Ground Truth** | Pixel-perfect binarization masks |

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Historical documents |
| **Degradation Types** | Bleed-through, staining, fading, uneven illumination |
| **Key Value** | Extreme degradation edge cases, binarization quality |

#### Training Value

- **Strengths**: Gold-standard binarization benchmark, extreme degradation cases (bleed-through, fading, staining), well-established evaluation metrics
- **Weaknesses**: Small size (131 images), evaluation-only design, limited diversity
- **Critical**: **NEVER train on this dataset - benchmark only**

#### Benchmark Performance (Binarization Quality)

| Competition | Best F-Measure | Best Method | Metrics |
|-------------|---------------|-------------|---------|
| **DIBCO 2019** | 95.8% | Deep learning ensemble | F-M, p-FM, PSNR, NRM, MPM, DRD |
| **DIBCO 2017** | 92.7% | CNN-based | F-M, p-FM, PSNR, DRD |
| **DIBCO 2016** | 91.5% | Adaptive thresholding | F-M, PSNR, NRM |
| **H-DIBCO 2018** | 90.6% | Deep learning | Handwritten subset metrics |

**Evaluation Metrics**:

- **F-Measure (F-M)**: Harmonic mean of precision/recall (primary metric)
- **pseudo-F-Measure (p-FM)**: Weighted distance-based F-measure
- **PSNR**: Peak Signal-to-Noise Ratio (image quality)
- **DRD**: Distance Reciprocal Distortion
- **NRM**: Negative Rate Metric
- **MPM**: Misclassification Penalty Metric

*Competition details: 2019 had 20 test images (Set A: machine-printed, Set B: papyri documents)*

#### Project Usage

- **Path**: `02_benchmark_only/dibco/`
- **Phase(s)**: Benchmark evaluation
- **Purpose**: Extreme degradation edge cases, binarization quality
- **Parser**: [`parse_dibco_labels`](../scripts/annotate_base_metadata.py#L1124) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/dibco/` | ✅ Available | 212 PNG/BMP files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | `metadata_registry/extracted/dibco/ocr_batch_0.jsonl` | ✅ Extracted | Docling OCR, 127 records, 106 (83.5%) with text content |
| **Layout Extracted** | `metadata_registry/extracted/dibco/layout_batch_0.json` | ✅ Extracted | Docling layout annotations, 4 categories (list_item, picture, section_header, text) |

#### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 212 |
| **File Formats** | BMP (69%), PNG (19%), TIFF (9%), JPEG (3%) |
| **Dimensions** | 351-4161 × 259-2206 px (avg: 1551 × 719) |
| **Avg File Size** | 2,036 KB |
| **Color Space** | RGB (64%), Binary (36%) |
| **Capture Method** | Scanner (Flatbed) |
| **Domain** | Historical Documents |

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (87.6/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 91.2 | 20% |  |
| Field Validity | 92.6 | 20% |  |
| Doc Completeness | 54.5 | 7% | Below threshold |
| Defect Rate | - | - | Excluded (no data) |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **87.6** | | **Grade B** |

###### 11.2 Key Defects

No defect catalog available for this dataset.

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 80.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/dibco/](../../scripts/audit/results/dibco/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 212 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 212 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |

---

## 13. Training Head Coverage

> **Purpose**: Documents how this dataset contributes to the 22 training heads across
> MobileNetV4-Conv-S (pre-correction) and SigLIP 2 NAFlex (multi-task) models.

### 13.1 Head Contribution Summary

> **CRITICAL**: DIBCO is a **benchmark-only** dataset. Competition test sets (131 images) are
> RESERVED and must NEVER be used for training. The 212 train-split images are technically
> processable but the dataset is designated evaluation-only by the project. All training heads
> are marked accordingly — use only for evaluation/validation pipelines.

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
| ------- | --------- | ------------ | ------------ | ---------- | ----- |
| MNV4-H1 | orientation_cls | ❌ Not applicable | - | - | Benchmark only; no orientation labels provided |
| MNV4-H2 | skew_reg | ❌ Not applicable | - | - | Benchmark only; no skew angle labels |
| MNV4-H3 | resolution_quality_reg | ❌ Not applicable | - | - | Benchmark only; resolution varies but no RQ labels |
| SIG-G1-1 | blur_score | ❌ Not applicable | - | - | Benchmark only; degradation present but no IQA scores |
| SIG-G1-2 | noise_score | ❌ Not applicable | - | - | Benchmark only; historical noise present but unlabeled for training |
| SIG-G1-3 | contrast_score | ❌ Not applicable | - | - | Benchmark only; contrast variance from fading/staining present but unlabeled |
| SIG-G1-4 | skew_score | ❌ Not applicable | - | - | Benchmark only |
| SIG-G1-5 | compression_score | ❌ Not applicable | - | - | Benchmark only |
| SIG-G1-6 | overall_quality | ❌ Not applicable | - | - | Benchmark only; binarization GT ≠ IQA MOS |
| SIG-G2-1 | script_cls | ❌ Not applicable | - | - | Benchmark only; 100% Latin (Latn) but reserved for evaluation |
| SIG-G3-1 | orientation_cls (post) | ❌ Not applicable | - | - | Benchmark only |
| SIG-G3-2 | skew_reg (post) | ❌ Not applicable | - | - | Benchmark only |
| SIG-G4-1 | handwriting_presence_cls | ❌ Not applicable | - | - | Benchmark only; 100% has_handwriting per L2 but reserved — do not use for training |
| SIG-G4-2 | handwriting_legibility_cls | ❌ Not applicable | - | - | Benchmark only |
| SIG-G4-3 | handwriting_content_type_cls | ❌ Not applicable | - | - | Benchmark only |
| SIG-G4-4 | presence_reg | ❌ Not applicable | - | - | Benchmark only |
| SIG-G4-5 | legibility_reg | ❌ Not applicable | - | - | Benchmark only |
| SIG-G5-1 | capture_method_cls | ❌ Not applicable | - | - | Benchmark only; 100% scanner_flatbed per L2 but reserved |
| SIG-G5-2 | shadow_reg | ❌ Not applicable | - | - | Benchmark only |
| SIG-G5-3 | warping_reg | ❌ Not applicable | - | - | Benchmark only |
| SIG-G5-4 | code_cls | ❌ Not applicable | - | - | Benchmark only |
| SIG-G5-5 | resolution_quality_reg (SigLIP) | ❌ Not applicable | - | - | Benchmark only |

**Contribution legend**: ✅ Primary | 🟡 Secondary | ➖ Negatives only | ❌ Not applicable

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
| - | --------- | -------- | ------- |
| 1 | Script families | 🟡 Partial | 100% Latin (Latn/en) per L2 aggregates; historical European manuscripts only |
| 2 | Capture method | 🟡 Partial | 100% scanner_flatbed per L2; relevant for binarization evaluation context only |
| 3 | Document domain | ❌ Not present | 100% GOV (historical documents) per L2; no domain diversity |
| 4 | Layout type | ❌ Not present | No layout annotations; mix of handwritten and printed pages |
| 5 | Text density | ❌ Not present | No text density labels; full-page historical documents |
| 6 | Degradation types | ✅ Well-covered | Bleed-through, staining, fading, uneven illumination — extreme historical degradation cases across 11 competition years |
| 7 | Resolution/DPI range | 🟡 Partial | 351–4161 × 259–2206 px (avg 1551 × 719); variable across years; no DPI metadata |
| 8 | Document age | ✅ Well-covered | Historical documents spanning centuries; maximum age diversity for binarization challenge |
| 9 | Text scope | ❌ Not present | No text scope labels; text_scope=document (full-page) per L2 |
| 10 | Content flags | 🟡 Partial | has_handwriting 100% per L2 (includes both handwritten and printed competition subsets) |
| 11 | Binarization status | ✅ Well-covered | Binary GT masks provided (pixel-perfect); 36% of images are binary per L2 color space |
| 12 | Artifact types | ✅ Well-covered | Staining, foxing, bleed-through, fading, uneven illumination — comprehensive historical degradation coverage |
| 13 | Color mode | 🟡 Partial | RGB 64% + Binary 36% per L2; no grayscale-only examples |
| 14 | Font variety | ✅ Well-covered | Wide variety of historical scripts and handwriting styles across 2009–2019 competitions |

**Coverage legend**: ✅ Well-covered | 🟡 Partial | ❌ Not present

### 13.3 Corpus Role & Constraints

DIBCO is designated as a **benchmark-only** dataset for this project — the competition test sets (131 images) are permanently reserved for evaluation, and the project policy is to never train on any DIBCO split to preserve benchmark validity for measuring binarization and degradation-handling quality. The dataset's unique value lies in its gold-standard pixel-level binarization ground truth and extreme historical degradation cases (bleed-through, staining, fading) that serve as held-out stress tests for the IQA pipeline's contrast, noise, and artifact-handling capabilities. Any future relaxation of benchmark-only status would require explicit project approval, as contaminating this evaluation set would invalidate years of competition-comparable metrics.
