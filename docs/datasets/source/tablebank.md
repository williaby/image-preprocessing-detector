#### TableBank

> **Quick Stats**: 278,582 images | Born-digital | High contrast | Blur-sensitive | Grid lines
>
> **License**: Apache-2.0 | **Commercial Use**: Research only

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | TableBank: A Benchmark Dataset for Table Detection and Recognition |
| **Version** | 1.0 |
| **Release Date** | 2019-03-05 (arXiv) |
| **Maintainer** | Microsoft Research Asia |
| **Paper** | [TableBank: Table Benchmark for Image-based Table Detection and Recognition (LREC 2020)](https://arxiv.org/abs/1903.01949) |
| **Repository** | [GitHub: doc-analysis/TableBank](https://github.com/doc-analysis/TableBank) |
| **HuggingFace** | [liminghao1630/TableBank](https://huggingface.co/datasets/liminghao1630/TableBank) |
| **License** | Apache-2.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/tablebank/` |
| **Documentation Status** | Complete |

##### Source Data Inventory

###### Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Document page images with table regions |
| **Annotations** | JSON (COCO) | Table detection bounding boxes |
| **Metadata** | README | Documentation and citation info |

###### Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train (LaTeX)** | `Detection/images/` | `Detection/annotations/tablebank_latex_train.json` | 187,199 | ✅ |
| **Train (Word)** | `Detection/images/` | `Detection/annotations/tablebank_word_train.json` | 73,383 | ✅ |
| **Validation (LaTeX)** | `Detection/images/` | `Detection/annotations/tablebank_latex_val.json` | 7,265 | ✅ |
| **Validation (Word)** | `Detection/images/` | `Detection/annotations/tablebank_word_val.json` | 2,735 | ✅ |
| **Test (LaTeX)** | `Detection/images/` | `Detection/annotations/tablebank_latex_test.json` | 5,719 | ✅ |
| **Test (Word)** | `Detection/images/` | `Detection/annotations/tablebank_word_test.json` | 2,281 | ✅ |

**Split Organization Pattern**: `by_file_list` (LaTeX and Word samples in same image directory, split by annotation file)

> **Notes**: [Official]
>
> - All images stored in single `Detection/images/` directory
> - Splits defined by separate annotation JSON files (6 total: 3 splits × 2 sources)
> - LaTeX subset: arXiv papers (rendered table regions)
> - Word subset: MSRA NLC academic documents (extracted table regions)

###### Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Bounding Boxes** | COCO JSON | Region (table-level) | Single class "table" detection boxes [x,y,w,h] |
| **Text Transcriptions** | N/A | N/A | Not provided - detection only |
| **Table Structure** | N/A | N/A | Not in Detection task (separate Recognition dataset) |

###### Annotation Schema Details

**Format**: Standard COCO format

```json
{
  "images": [{"id": int, "file_name": str, "width": int, "height": int}],
  "annotations": [{"id": int, "image_id": int, "category_id": 1, "bbox": [x,y,w,h]}],
  "categories": [{"id": 1, "name": "table"}]
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image_id` | int | Yes | Links annotation to image |
| `bbox` | list[4] | Yes | COCO format [x,y,w,h] |
| `category_id` | int | Yes | Always 1 (table class) |
| `file_name` | str | Yes | Relative path to image |

###### Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Table bounding boxes | `layout_detections.bbox` | High | COCO format, direct mapping |
| ✅ Image metadata | `image_metadata` | High | Dimensions from annotation |
| ✅ LaTeX vs Word source | `provenance.subset` | Medium | Derivable from annotation file |
| ✅ Split information | `provenance.split` | High | train/val/test from filename |
| ❌ Text transcriptions | - | Low | Not provided in Detection task |
| ❌ Table structure | - | Low | Separate Recognition dataset |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

###### Ground Truth Provenance

| Field | Value |
|-------|-------|
| **Annotation Method** | Automatic Extraction |
| **Provenance Tier** | Tier 0 (Exact - programmatic extraction from Word/LaTeX source) |
| **Quality Assurance** | Automatic extraction from Word/LaTeX documents |
| **GT Label Coverage** | 100% (all 278K images with table bounding boxes) |

##### Dataset Statistics

###### Split Coverage

> **CRITICAL**: Layer 2 metadata not yet generated for TableBank. Counts below are from source annotations [Official].

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 260,582 | N/A | N/A | ⚠️ Pending Layer 2 annotation |
| **Validation** | 10,000 | N/A | N/A | ⚠️ Pending Layer 2 annotation |
| **Test** | 8,000 | N/A | N/A | ⚠️ Pending Layer 2 annotation |
| **Total** | 278,582 | N/A | N/A | ⚠️ Pending Layer 2 annotation |

**Split Status Legend**:

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2 OR Layer 2 not yet generated
- ❌ Missing - Split not included in Layer 2 metadata

> **Action Required**: Run Layer 2 annotation pipeline on TableBank to populate metadata and verify 100% coverage.

###### Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images (Detection)** | 278,582 [Official] |
| **Total Images (Structure)** | 145,463 [Official] |
| **Training Split** | 260,582 (93.5%) [Official] |
| **Validation Split** | 10,000 (3.6%) [Official] |
| **Test Split** | 8,000 (2.9%) [Official] |
| **Image Dimensions** | Variable (document page size) |
| **File Format** | JPG |
| **Annotation Format** | COCO-style JSON |

###### Text Statistics

**Text Statistics**: ❌ Not Available

> TableBank provides table detection bounding boxes only. Text transcription is NOT included in the dataset annotations. The Detection task focuses on table region localization, while the separate Recognition task dataset includes table structure annotations (rows/columns/cells) but not text content. OCR extraction would be required to obtain text for IQA text-based metrics.

##### Composition by Source

| Source | Detection Train | Detection Val | Detection Test | Total |
|--------|-----------------|---------------|----------------|-------|
| **LaTeX** | 187,199 | 7,265 | 5,719 | 200,183 |
| **Word** | 73,383 | 2,735 | 2,281 | 78,399 |
| **Combined** | 260,582 | 10,000 | 8,000 | 278,582 |

##### IQA Profile

###### Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Born-digital (LaTeX rendering + Word extraction) [Official] |
| **Capture Device** | N/A (programmatic generation) [Official] |
| **Original Quality** | High - no scanning artifacts [Official] |
| **Compression** | JPEG (quality varies by source) [Inferred] |
| **Known Artifacts** | Minor JPEG blocking on some samples [Inferred] |

###### Degradation Sensitivity

| IQA Metric | Sensitivity | Notes |
|------------|-------------|-------|
| **Blur** | HIGH | Grid lines and cell borders extremely sensitive [Inferred] |
| **Noise** | MEDIUM | High contrast masks moderate noise [Inferred] |
| **Skew** | HIGH | Cell alignment degrades rapidly with rotation [Inferred] |
| **Contrast** | LOW | Already high contrast (black on white) [Inferred] |
| **Compression** | HIGH | JPEG artifacts destroy thin cell borders [Inferred] |

###### Document Feature Characteristics

| Feature | Presence | IQA Implications |
|---------|----------|------------------|
| **Grid Lines** | Pervasive | Primary blur detection target [Inferred] |
| **Small Text** | Common | 8-14pt fonts sensitive to blur [Inferred] |
| **Mathematical Notation** | Common in LaTeX | Subscripts/superscripts fragile [Inferred] |
| **Color Usage** | Minimal | Grayscale processing sufficient [Inferred] |
| **Font Diversity** | Low | Standard academic fonts [Inferred] |

###### Training & Benchmark Value

| Aspect | Assessment |
|--------|------------|
| **Training Value** | HIGH - Large volume (278K), clean ground truth for table quality [Official] |
| **Unique Characteristics** | Grid line sharpness, cell boundary detection [Inferred] |
| **Complementary Datasets** | Combine with PubTabNet (structure), FinTabNet (financial) [Inferred] |
| **Benchmark Suitability** | MEDIUM - Born-digital only, lacks real scan artifacts [Inferred] |
| **Known Limitations** | No handwritten content, limited degradation variety [Inferred] |

**Baseline Quality Metrics**: [NEEDS_PROFILING] - Requires empirical analysis on 1000-sample subset

##### Benchmark Performance

| Task | Model | Dataset | F1 Score |
|------|-------|---------|----------|
| **Detection** | Faster R-CNN (ResNeXt) | LaTeX | **0.9815** |
| **Detection** | Faster R-CNN (ResNeXt) | Word+LaTeX | 0.9559 |
| **Structure** | Image-to-Text | Word+LaTeX→Word | BLEU-4: 69.93 |
| **Structure** | Image-to-Text | Word+LaTeX→LaTeX | BLEU-4: 77.94 |
| **Structure** | Image-to-Text | Word+LaTeX→Combined | BLEU-4: 74.54 |

*Training: 4× V100 GPUs, batch size 20 (detection) / 24 (structure)*

##### Training Value

- **Strengths**: Large volume, clean ground truth, table structure annotations, strong baseline F1 scores
- **Weaknesses**: Born-digital only (no real scan artifacts), limited domain diversity
- **Complementary Datasets**: Combine with PubTabNet for scientific tables, FinTabNet for financial
- **Benchmark Suitability**: MEDIUM - lacks real-world degradation variety

##### Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Phase 7 training |
| **Purpose** | Training augmentation source for table-focused IQA |
| **Local Path** | `01_base_data/tables/tablebank/` |
| **Subset Used** | Full Detection dataset (278,582 images) |
| **Preprocessing** | None required - images ready for use |

###### Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`TableBankParser`](../../src/image_preprocessing_detector/annotation/parsers/layout/tablebank.py) |
| **Parser Status** | ✅ Complete |
| **Layer 1 Fields** | `raw_labels["tablebank_annotations"]` (COCO format), `language_code="en"`, `script_name="Latin"` |
| **Layer 2 Auto-Derived** | `has_table=True`, `iso15924_script="Latn"`, `language_confidence=0.95` |
| **Config Entry** | `DATASET_CONFIGS["tablebank"]` in annotation config |

**Parser vs Layer 2 Schema Audit Matrix**:

| Source Field | Layer 2 Target | Parser Handles? | Priority | Notes |
|--------------|----------------|-----------------|----------|-------|
| COCO bbox [x,y,w,h] | `layout_detections[].bbox` | ⚠️ Via raw_labels | High | In raw_labels, needs Layer 2 mapping |
| category="table" | `layout_detections[].class_name` | ⚠️ Indirect | High | In raw_labels, needs explicit mapping |
| category="table" | `content_flags.has_table` | ❌ No | Medium | Derivable from annotations |
| category_id | `layout_detections[].class_id` | ❌ No | Low | Not critical for single-class |
| image_id | `provenance.source_id` | ❌ No | Low | For traceability |
| file_name | `provenance.original_filename` | ❌ No | Low | For audit trail |
| Dataset config | `capture_method.method` | ❌ No | High | Should set "born_digital" |
| Dataset provenance | `language.language_code` | ✅ Yes | High | "en" correctly set |
| Dataset provenance | `language.script_code` | ✅ Yes | High | "Latn" correctly set |
| Dataset config | `domain.level1` | ❌ No | Medium | Should set "SCI" (scientific) |
| LaTeX vs Word | `provenance.subset` | ❌ No | Low | For analysis purposes |
| Split (train/val/test) | `provenance.split` | ❌ No | High | CRITICAL for training |

**Current Parser Coverage**:

- ✅ **Language/Script Metadata**: Correctly extracted (en/Latin/Latn with 95% confidence)
- ⚠️ **Layout Detections**: In raw_labels but not Layer 2 `layout_detections[]` array
- ❌ **Missing High Priority**: capture_method, domain, provenance.split
- ❌ **Missing Medium Priority**: has_table content flag derivation

**Recommended Parser Enhancements**:

1. Populate `provenance.split` from annotation filename (train/val/test)
2. Set `capture_method.method = "born_digital"`
3. Set `domain.level1 = "SCI"` (scientific publications)
4. Derive `content_flags.has_table = True` from annotations
5. Map raw_labels to Layer 2 `layout_detections[]` structure

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/tables/tablebank/` | ✅ Available | 260,025 PNG files |
| **Text/GT** | - | ❌ Not provided | No ground truth text in source dataset |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In progress - Currently being processed/extracted
- ⚠️ Partial - Some data available, incomplete

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 260,025 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 499-842 × 595-1152 px (avg: 623 × 799) |
| **Avg File Size** | 69 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | SCI (Scientific) |
| **Content Flags** | Tables: ✅ 100% |

##### Known Issues & Limitations

- **Quality Bias**: Born-digital only; doesn't represent scanned document quality [Inferred]
- **Domain Bias**: Heavy scientific/academic focus; limited document variety [Inferred]
- **Annotation Gaps**: Table structure annotations exist in separate Recognition dataset, not in Detection task [Official]
- **Class Imbalance**: 70% LaTeX vs 30% Word creates rendering style bias [Official]
- **Resolution Variance**: Wide dimension range requires normalization for training [Inferred]
- **No Text Content**: Text transcription not provided; OCR extraction would be required [Official]
- **Split Information Missing**: Parser does not currently populate `provenance.split` field [Empirically Derived]

##### Dataset-Specific Notes

###### Annotation Caveats

- **Detection Only**: TableBank Detection task provides table region bounding boxes only. Table structure annotations (rows/columns/cells) are available separately in the Recognition task subset, but NOT included in the Detection task. [Official]
- **No Text Content**: Text transcription is not provided in either Detection or Recognition tasks. OCR would be required to extract text for IQA text-based metrics. [Official]
- **Single Class**: All annotations use category_id=1 for "table" class. No sub-categorization of table types. [Official]

###### Implementation Notes

- **Multi-Path Support**: Parser checks multiple potential annotation paths (TableBank/Detection/annotations/, Detection/annotations/, annotations/) to handle different dataset organizations. [Empirically Derived]
- **Module-Level Caching**: COCO annotations are cached at module level to avoid redundant file I/O when processing multiple images from same split. [Empirically Derived]
- **Filename Matching**: Images matched to annotations via filename field in COCO JSON. All images stored in single directory regardless of split or source (LaTeX/Word). [Official]

###### External Resources

- **GitHub Repository**: [doc-analysis/TableBank](https://github.com/doc-analysis/TableBank) - Official dataset repository with download instructions [Official]
- **HuggingFace Dataset**: [liminghao1630/TableBank](https://huggingface.co/datasets/liminghao1630/TableBank) - HuggingFace Datasets integration [Official]
- **GCS Bucket**: `gs://image_detection_b/image-preprocessing-detector/datasets/tablebank/` - Project-internal storage [Project-specific]

##### References

```bibtex
@inproceedings{li2020tablebank,
  title={TableBank: Table Benchmark for Image-based Table Detection and Recognition},
  author={Li, Minghao and Cui, Lei and Huang, Shaohan and Wei, Furu and Zhou, Ming and Li, Zhoujun},
  booktitle={Proceedings of LREC},
  year={2020}
}
```

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: B (88.5/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 93.3 | 28% |  |
| Field Validity | 96.3 | 28% |  |
| Doc Completeness | 63.6 | 17% | Below threshold |
| Defect Rate | 98.0 | 17% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 80.0 | 11% |  |
| **Overall** | **88.5** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 1 defects (1 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| TB-D01 | text_has_content | MEDIUM | OPEN |  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 80.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/tablebank/](../../scripts/audit/results/tablebank/)

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 260,025 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 260,025 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |
