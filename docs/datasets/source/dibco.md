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
