#### RVL-CDIP

> **Quick Stats**: 400,000 images | Real scans | 16 document classes | Authentic degradation
>
> **License**: Academic | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | RVL-CDIP (Ryerson Vision Lab - Complex Document Information Processing) |
| **Version** | 1.0 |
| **Release Date** | 2015 |
| **Maintainer** | Ryerson Vision Lab |
| **Paper** | [Evaluation of Deep Convolutional Nets for Document Image Classification and Retrieval (ICDAR 2015)](https://www.cs.cmu.edu/~aharley/icdar15/) |
| **Download** | [adamharley.com/rvl-cdip](https://adamharley.com/rvl-cdip/) |
| **License** | Academic (via IIT-CDIP/Legacy Tobacco) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/rvl_cdip/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | TIFF (original), JPEG (local conversion) | 400,000 grayscale document images |
| **Annotations** | TXT | Class labels in format: `path/to/image.tif category_id` |
| **Metadata** | None | No per-image metadata files |
| **Supplementary** | None | Minimal documentation |

##### 2.2 Dataset Split Locations

**Split Organization Pattern**: `by_file_list` (official) / `single_dir_with_manifest` (local subset)

**Official Distribution**:

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `images/` | `labels/train.txt` | 320,000 | ⚠️ Official only |
| **Validation** | `images/` | `labels/val.txt` | 40,000 | ⚠️ Official only |
| **Test** | `images/` | `labels/test.txt` | 40,000 | ⚠️ Official only |
| **Total** | `images/` | `labels/*.txt` | 400,000 | ⚠️ Official only |

**Local Subset** (4% sample):

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Unknown** | `01_base_data/documents/rvl_cdip/images/` | Filename-based only | 16,000 | ✅ Available |

> **Notes**:
>
> - Official dataset uses 3 label files (`train.txt`, `val.txt`, `test.txt`) defining split membership
> - Local subset (16K) has no split labels - all images in single directory
> - Filenames encode class only: `rvl_{class}_{number}.jpg`
> - Split membership for local subset is [NEEDS_PROFILING]

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Document Class** | TXT (numeric ID 0-15) | Image-level | Single class label per document |

> **Note**: No bounding boxes, OCR text, or region-level annotations in source dataset.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | Website README | License, citation, download links |
| **Image-level** | Filename only | Class encoded in filename: `rvl_{class}_{number}` |

> **Note**: Minimal metadata. No resolution, DPI, source document, or temporal metadata.

##### 2.5 Annotation Schema Details

**Format**: Plain text label files

```text
# Example label file format (train.txt, val.txt, test.txt)
path/to/image/rvl_advertisement_0000.tif 4
path/to/image/rvl_letter_0001.tif 0
path/to/image/rvl_form_0002.tif 1
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_path` | str | Yes | Relative path from dataset root |
| `category_id` | int | Yes | Integer 0-15 mapping to class name |

**Class ID Mapping**:

- 0: letter, 1: form, 2: email, 3: handwritten, 4: advertisement
- 5: scientific report, 6: scientific publication, 7: specification, 8: file folder
- 9: news article, 10: budget, 11: invoice, 12: presentation
- 13: questionnaire, 14: resume, 15: memo

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Document class (filename) | `document_class` (str) | High | Parser implemented |
| ✅ Document class ID (filename) | `document_class_id` (int) | High | Parser implemented |
| ⚠️ Split membership | - | Medium | Not in local subset |
| ✅ OCR text | `annotations/rvl-cdip/ocr/ocr_batch_*.jsonl` | Medium | Docling OCR extracted (15,903/16,000 = 99%) |
| ❌ Layout annotations | - | Low | Not in source (can derive) |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available in source

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | 16-class document classification annotation |
| **GT Label Coverage** | 100% |

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.
> **Note**: Local subset (16K) does not have split labels. Official dataset (400K) has train/val/test splits.

**Official Dataset** (400K total):

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 320,000 | 0 | 0% | ⚠️ Not in local subset |
| **Validation** | 40,000 | 0 | 0% | ⚠️ Not in local subset |
| **Test** | 40,000 | 0 | 0% | ⚠️ Not in local subset |
| **Total** | 400,000 | 0 | 0% | ⚠️ Official only |

**Local Subset** (16K - 4% sample):

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Unknown** | 16,000 (estimated) | 16,000 | 100% | ✅ Complete |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Not in local subset - Split exists in official dataset but not processed locally

> **Implementation Note**: Local subset is 4% of full dataset (16K/400K). Split membership not preserved
> in local copy - all images in single directory. For training, recommend implementing stratified
> cross-validation since split labels unavailable.

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 400,000 (official) / 16,000 (local subset) |
| **Training Split** | 320,000 (80%) - official only |
| **Validation Split** | 40,000 (10%) - official only |
| **Test Split** | 40,000 (10%) - official only |
| **Images per Class** | 25,000 (balanced) - official |
| **Max Dimension** | ≤1000 pixels |
| **File Format** | TIFF (grayscale) - official / JPEG (RGB) - local |
| **Download Size** | 37 GB (official full dataset) |

#### 5. Content Composition

##### 5.1 Class/Category Distribution

**Official Dataset** (400K total) - Perfectly Balanced:

| Class ID | Class Name | Count | Percentage |
|----------|------------|-------|------------|
| 0 | letter | 25,000 | 6.25% |
| 1 | form | 25,000 | 6.25% |
| 2 | email | 25,000 | 6.25% |
| 3 | handwritten | 25,000 | 6.25% |
| 4 | advertisement | 25,000 | 6.25% |
| 5 | scientific_report | 25,000 | 6.25% |
| 6 | scientific_publication | 25,000 | 6.25% |
| 7 | specification | 25,000 | 6.25% |
| 8 | file_folder | 25,000 | 6.25% |
| 9 | news_article | 25,000 | 6.25% |
| 10 | budget | 25,000 | 6.25% |
| 11 | invoice | 25,000 | 6.25% |
| 12 | presentation | 25,000 | 6.25% |
| 13 | questionnaire | 25,000 | 6.25% |
| 14 | resume | 25,000 | 6.25% |
| 15 | memo | 25,000 | 6.25% |
| **Total** | | **400,000** | **100%** |

**Local Subset** (16K - 4% sample) - [NEEDS_PROFILING]:

> **Note**: Class distribution of local 16K subset not yet profiled. Recommend running class count
> analysis to verify if stratified sampling was used (1,000 per class) or if distribution differs.

**Source**: [Official] Website (adamharley.com/rvl-cdip)

##### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | **Real scanned documents** (1990s-2000s scans) |
| **Baseline Quality** | Variable (authentic degradation) |
| **Blur Sensitivity** | Variable - depends on original scan quality |
| **Noise Sensitivity** | **HIGH** - Real scanner noise present |
| **Skew Sensitivity** | **HIGH** - Real scanning skew artifacts |
| **Degradation Types** | Yellowing, staining, bleed-through, scan lines |
| **Key Value** | **Ground truth for real-world degradation patterns** |

##### Data Provenance

| Aspect | Details |
|--------|---------|
| **Origin** | IIT-CDIP Test Collection 1.0 |
| **Source** | Legacy Tobacco Document Library |
| **Historical Context** | Scanned documents from tobacco litigation (1990s-2000s era) |
| **Authenticity** | Real-world degradation patterns from archival scanning |

##### Training Value

- **Strengths**: Real degradation, diverse document types, perfectly balanced classes (25K each)
- **Weaknesses**: Lower resolution (max 1000px), grayscale only, dated scanning technology
- **Unique Features**: **Only large-scale real-scan document dataset** with 16-class classification
- **Benchmark Suitability**: **HIGH** - ICDAR 2015 standard for document classification

##### 6.5 Benchmark Results

> **Purpose**: Document published model performance on this dataset for baseline comparison.

**Status**: [NEEDS_VERIFICATION] - ICDAR 2015 paper results not yet extracted

| Model/Method | Task | Metric | Score | Reference |
|--------------|------|--------|-------|-----------|
| CNN Baseline | 16-class Classification | Accuracy | [TBD] | [Harley et al. ICDAR 2015](https://www.cs.cmu.edu/~aharley/icdar15/) |

**Known Leaderboards**:

- [Papers With Code - RVL-CDIP](https://paperswithcode.com/dataset/rvl-cdip)

> **TODO**: Extract baseline CNN accuracy from ICDAR 2015 paper full text or arXiv.
> Paper title: "Evaluation of Deep Convolutional Nets for Document Image Classification and Retrieval"

#### 3. Project Usage

- **Path**: `01_base_data/documents/rvl_cdip/`
- **Phase(s)**: Phase 7 training, IQA calibration
- **Purpose**: Real degradation pattern training, baseline quality assessment
- **Subset Used**: 16,000 images (sample for diversity)
- **Parser**: ✅ `parse_rvl_cdip_labels` (extracts document class from 16-folder structure)

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/documents/rvl_cdip/` | ✅ Available | 16,000 JPEG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | `annotations/rvl-cdip/ocr/ocr_batch_*.jsonl` | ✅ Available | 16,000 records (100%), Docling OCR |
| **Layout Extracted** | `annotations/rvl-cdip/layout/layout_batch_*.json` | ✅ Available | 15,733 records (98%), DocLayout-YOLO |

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 16,000 (4% subset) |
| **File Format** | JPEG (100%) |
| **Dimensions** | 596-1477 × 1000 px (avg: 766 × 1000) |
| **Avg File Size** | 176 KB |
| **Color Space** | RGB |
| **Capture Method** | Scanner (ADF) |
| **Domain** | ADM (Administrative) |

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Filename Dependency**: Class labels encoded in filename only (`rvl_{class}_{number}.jpg`)
- **No Bounding Boxes**: Classification-only dataset - no region annotations
- **Split Labels Missing Locally**: Local 16K subset has no split membership metadata
- **Perfectly Balanced**: Official dataset has exactly 25,000 samples per class (rare property)

##### 10.2 Implementation Notes

- **Format Conversion**: Original TIFF (.tif) grayscale converted to JPEG (.jpg) RGB locally
  - Conversion date: Unknown
  - Quality impact: Minimal (high JPEG quality assumed)
  - Original dimensions preserved (<= 1000px max dimension)

- **Subset Selection**: Local 16K subset = 4% of full 400K dataset
  - Selection method: [NEEDS_PROFILING] (random? stratified? specific split?)
  - Class distribution: [NEEDS_PROFILING] (verify if balanced)

- **Parser Implementation**: Class extracted via regex on filename
  - Pattern: `rvl_{class}_{number}.jpg`
  - Right-split to handle multi-word classes (e.g., `scientific_publication`)

##### 10.3 External Resources

- **Official Website**: <https://adamharley.com/rvl-cdip/>
- **HuggingFace**: Available via Datasets Library (recommended for full dataset access)
- **Download**:
  - Full dataset: `rvl-cdip.tar.gz` (37 GB)
  - Labels only: `labels_only.tar.gz` (6.1 MB)
- **Papers With Code**: <https://paperswithcode.com/dataset/rvl-cdip>

#### 9. References

```bibtex
@inproceedings{harley2015icdar,
  title={Evaluation of Deep Convolutional Nets for Document Image Classification and Retrieval},
  author={Harley, Adam W and Ufkes, Alex and Derpanis, Konstantinos G},
  booktitle={ICDAR},
  year={2015}
}
```

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: B (87.2/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 93.2 | 25% |  |
| Field Validity | 92.7 | 25% |  |
| Doc Completeness | 63.6 | 15% | Below threshold |
| Defect Rate | 97.4 | 15% |  |
| Cross-Source Agreement | 80.4 | 10% |  |
| VLM Accuracy | 85.0 | 10% |  |
| **Overall** | **87.2** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 2 defects (1 deferred, 1 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | layout_detections | LOW | OPEN | 267/16000 images have no Docling layout detections (missing from batch extractio |
| D02 | text_has_content | MEDIUM | DEFERRED | No text transcription labels available for any sample |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 85.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/rvl-cdip/](../../scripts/audit/results/rvl-cdip/)

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 16,000 | **Avg Min Confidence**: 0.533

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 3,274 | 20.5% |
| active_learning | 6,901 | 43.1% |
| unreliable | 5,825 | 36.4% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `layout_detections` | 74.2% | 0.576 |
| 2 | `text_quality` | 25.8% | 0.672 |
