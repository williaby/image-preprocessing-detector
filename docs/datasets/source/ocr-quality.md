#### OCR-Quality

> **Quick Stats**: 1,000 images | Human quality scores (1-4) | Multilingual | OCR evaluation
>
> **License**: CC0 1.0 (Public Domain) | **Commercial Use**: Yes

##### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | OCR-Quality: Document Image Quality for OCR |
| **Version** | 1.0 |
| **Release Date** | 2025 |
| **Maintainer** | Yulong Zhang et al. |
| **Paper** | [OCR-Quality: A Human-Annotated Dataset (arXiv:2510.21774)](https://arxiv.org/abs/2510.21774) |
| **Repository** | [HuggingFace Dataset](https://huggingface.co/datasets/Aslan-mingye/OCR-Quality) |
| **License** | [CC0 1.0 Universal (Public Domain)](https://creativecommons.org/publicdomain/zero/1.0/) |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/ocr_quality/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG (embedded in Parquet) | 300 DPI document page images |
| **Annotations** | Parquet + JSON | Quality scores, OCR text, source metadata |
| **Metadata** | Parquet columns | Image dimensions, source categories |
| **Supplementary** | README (HuggingFace) | Dataset card, usage examples |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | Embedded in Parquet | `OCR-Quality.parquet` | 1,000 | ✅ |
| **Validation** | - | - | 0 | ℹ️ N/A |
| **Test** | - | - | 0 | ℹ️ N/A |

**Split Organization Pattern**: `single_dir_with_manifest` (Parquet-based)

> **Notes**:
>
> - HuggingFace provides single `train` split only
> - No official validation or test splits
> - All 1,000 images available in single Parquet file
> - Images embedded as byte arrays in Parquet (no separate image directory)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Quality Scores** | Parquet (int) | Page | Human-annotated 1-4 scale (1=best - INVERTED) |
| **Text Transcriptions** | Parquet (string) | Page | Full OCR text by Qwen2.5-VL-72B |

> **Note**: No bounding boxes, layout annotations, or degradation labels provided.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | HuggingFace README | License (CC0), citation, usage examples |
| **Image-level** | Parquet columns | Dimensions (width/height), source category |
| **Annotation-level** | Parquet columns | OCR extraction model (Qwen2.5-VL-72B) |
| **Document-level** | `source` column | 30 source categories (textbooks, papers, e-books) |

##### 2.5 Annotation Schema Details

> **Format**: Parquet schema with embedded images and annotations

```python
Parquet Schema (OCR-Quality.parquet):
{
  "index": int,            # Sample ID (0-999)
  "human_score": int,      # Quality score (1-4, 1=best - INVERTED!)
  "ocr_text": string,      # Full page OCR transcription
  "source": string,        # Source category (e.g., "zhishilei", "theeye-pdf")
  "image": bytes,          # PNG image data (300 DPI)
  "image_width": int,      # Width in pixels
  "image_height": int      # Height in pixels
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `index` | int | Yes | Unique sample ID (0-999) |
| `human_score` | int | Yes | 1-4 scale (INVERTED: 1=best, 4=worst) |
| `ocr_text` | string | Yes | Full OCR transcription by Qwen2.5-VL-72B |
| `source` | string | Yes | Document source category (30 categories) |
| `image` | bytes | Yes | Embedded PNG image data |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Quality scores | `quality.overall_score` | High | Requires inversion: (5-score)/4 |
| ✅ OCR text | `text_content.full_text` | High | Full page transcription |
| ✅ Source category | `provenance.source_dataset` | Medium | 30 categories available |
| ✅ Image dimensions | `image_metadata.width/height` | Low | Already in Parquet |
| ❌ Layout boxes | - | N/A | Not provided |
| ❌ Degradation labels | - | N/A | Not provided |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Crowdsourced |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Human quality rating process |
| **GT Label Coverage** | 100% |

#### 4. Dataset Statistics

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 1,000 | [NEEDS_VERIFICATION] | [NEEDS_VERIFICATION] | ⚠️ Verify |
| **Validation** | 0 | 0 | N/A | ℹ️ N/A |
| **Test** | 0 | 0 | N/A | ℹ️ N/A |
| **Total** | 1,000 | [NEEDS_VERIFICATION] | [NEEDS_VERIFICATION] | ⚠️ Verify |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ❌ Missing - Split not included in Layer 2 metadata
- ℹ️ N/A - Split does not exist in source dataset

> **Note**: HuggingFace provides single `train` split only. No official val/test splits.
> Verify Layer 2 metadata includes all 1,000 images.

##### 4.2 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 1,000 |
| **File Format** | PNG |
| **Image Dimensions** | Variable |
| **Annotation Format** | JSON + Parquet |
| **Total Size** | ~1.19 GB |

#### 5. Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Documents, textbooks, scientific papers |
| **Languages** | Chinese (primary), English, multilingual |
| **Sources** | zh-textbook (Chinese textbooks), scientific papers, mixed documents |
| **Quality Levels** | 4 discrete levels (1=best, 4=worst) |

##### 5.2 Class/Category Definitions (Quality Levels)

> **Purpose**: Define the taxonomy of quality levels used in human annotations.
> **Applicability**: IQA datasets with discrete quality categories.

| Quality Level | Score | Description | Sample Count | Percentage |
|---------------|-------|-------------|--------------|------------|
| Excellent | 1 | Near-perfect OCR quality, minimal errors | 507 | 50.7% |
| Good | 2 | Minor OCR errors, high readability | 305 | 30.5% |
| Fair | 3 | Noticeable OCR errors, moderate readability | 84 | 8.4% |
| Poor | 4 | Significant OCR errors, low readability | 104 | 10.4% |

> **CRITICAL NOTE**: This dataset uses an **INVERTED scale** where **1 = best** and **4 = worst**.
> This is opposite from DIQA-5000 (1-5 scale, 5=best) and SmartDoc-QA (OCR accuracy proxy).
>
> **Normalization Formula**:
>
> ```python
> normalized_score = (5 - human_score) / 4.0
> # Result: 1 → 1.0, 2 → 0.75, 3 → 0.5, 4 → 0.25
> ```
>
> **References**:
>
> - Official paper: [arXiv:2510.21774](https://arxiv.org/abs/2510.21774)
> - HuggingFace distribution table: [Aslan-mingye/OCR-Quality](https://huggingface.co/datasets/Aslan-mingye/OCR-Quality)

##### 5.3 Language & Script Coverage

> **Purpose**: Document language and script distribution for multilingual datasets.
> **Applicability**: OCR, script detection, multilingual document datasets.

| Script/Language | ISO Code | Samples | Coverage | Notes |
|-----------------|----------|---------|----------|-------|
| Han (Chinese Simplified) | Hans | ~502 | 50.2% | Primary script, textbooks + e-books |
| Latin (English) | Latn | ~236 | 23.6% | Secondary script, papers + e-books |
| Mixed/Unknown | - | ~262 | 26.2% | [NEEDS_PROFILING] Script detection needed |

**Script Families Present**: Han (CJK), Latin

**Source Category Breakdown**:

| Source Category | Samples | Language | Document Type |
|-----------------|---------|----------|---------------|
| zhishilei (Chinese e-books) | 324 | Chinese | Educational content |
| baiyun (Chinese textbooks) | 178 | Chinese | Academic textbooks |
| theeye-pdf (English e-books) | 142 | English | General e-books |
| escholarship (English papers) | 94 | English | Academic papers |
| Other categories | 262 | Mixed | Various domains |

> **Notes**:
>
> - Language distribution estimated from source categories
> - Exact script detection pending (use `scripts/enrich_language.py`)
> - ISO 15924 codes for scripts, ISO 639-1/3 for languages
> - No script-confusable pairs documented
> - [NEEDS_PROFILING] Run language detection enrichment to confirm distribution

##### 4.3 Text Statistics (if ground truth text available)

> **Source**: [NEEDS_PROFILING] OCR text available in Parquet but statistics not yet computed
> **Availability**: ✅ Available - OCR text in `ocr_text` column (Qwen2.5-VL-72B extractions)

**[NEEDS_PROFILING]** - Run text statistics computation:

```bash
# Compute text statistics from Parquet ocr_text column
uv run python scripts/calculate_text_statistics.py \
    --input /mnt/e/image_detection/01_base_data/ocr_quality/OCR-Quality.parquet \
    --column ocr_text \
    --output docs/datasets/ocr_quality_text_stats.json
```

**Expected Statistics** (once computed):

| Metric | Mean ± Std | Min | Max | Percentiles (25/50/75) |
|--------|------------|-----|-----|------------------------|
| **Character Count** | [TBD] | [TBD] | [TBD] | [TBD] / [TBD] / [TBD] |
| **Word Count** | [TBD] | [TBD] | [TBD] | [TBD] / [TBD] / [TBD] |
| **Sentence Count** | [TBD] | [TBD] | [TBD] | [TBD] / [TBD] / [TBD] |
| **Paragraph Count** | [TBD] | [TBD] | [TBD] | [TBD] / [TBD] / [TBD] |
| **Avg Word Length** | [TBD] | [TBD] | [TBD] | [TBD] / [TBD] / [TBD] |
| **Avg Sentence Length** | [TBD] | [TBD] | [TBD] | [TBD] / [TBD] / [TBD] |

**Text Source**: `dataset_provided` (Qwen2.5-VL-72B extractions)

> **Note**: Text statistics computation requires reading Parquet `ocr_text` column for all 1,000 samples.
> Estimated computation time: ~2 minutes.

#### 6. IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Mixed (scanned + digital) |
| **Baseline Quality** | Variable (intentionally diverse quality levels) |
| **Human Annotations** | **HIGH** - Direct human quality scores |
| **Score Distribution** | 4 discrete levels mapped to IQA |
| **Multilingual** | **YES** - Chinese + English content |
| **Key Value** | Independent human quality validation, OCR correlation |

##### Training Value

- **Strengths**: Human quality scores, multilingual coverage, OCR text ground truth
- **Weaknesses**: Small dataset (1,000 images), inverted scoring scale, unknown license
- **Unique Features**: Only dataset with both human quality scores AND OCR ground truth
- **Cross-Validation**: Use to validate DeQA-Doc predictions (target SRCC > 0.80)

##### Score Conversion

```python
# OCR-Quality uses inverted scale: 1=best, 4=worst
# Convert to standard 0-1 scale (higher=better):
normalized_score = (5 - human_score) / 4
# Result: 1 → 1.0, 2 → 0.75, 3 → 0.5, 4 → 0.25
```

##### Project Usage

- **Path**: `01_base_data/ocr_quality/`
- **Phase(s)**: Stage 1 DeQA-Doc labeling, IQA validation
- **Purpose**: Cross-validate DeQA-Doc predictions against independent human scores
- **Priority**: **HIGH** for unified labeling strategy
- **Parser**: [`parse_ocr_quality_labels`](../scripts/annotate_base_metadata.py#L1192) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/ocr_quality/` | ✅ Available | 1,000 PNG files |
| **Text/GT** | Native annotations | ✅ Available | Parquet: Full page OCR text by Qwen2.5-VL-72B (`ocr_text` field) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In progress - Currently being processed/extracted
- ⚠️ Partial - Some data available, incomplete
- ℹ️ N/A - Not applicable for this dataset

##### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 1,000 |
| **File Format** | PNG (100%) |
| **Dimensions** | 830-9230 × 1063-12313 px (avg: 2194 × 3060) |
| **Avg File Size** | 1,159 KB |
| **Color Space** | RGB |
| **Capture Method** | Unknown |
| **Domain** | General Documents |

#### 9. References

##### Primary Citation

```bibtex
@misc{zhang2025ocrquality,
  title={OCR-Quality: A Human-Annotated Dataset for OCR Readability Assessment},
  author={Zhang, Yulong and others},
  year={2025},
  eprint={2510.21774},
  archivePrefix={arXiv},
  primaryClass={cs.CV},
  url={https://arxiv.org/abs/2510.21774}
}
```

##### Official Resources

- **Paper**: [arXiv:2510.21774](https://arxiv.org/abs/2510.21774) - OCR-Quality: A Human-Annotated Dataset
- **HuggingFace**: [Aslan-mingye/OCR-Quality](https://huggingface.co/datasets/Aslan-mingye/OCR-Quality) - Dataset download
- **License**: [CC0 1.0 Universal (Public Domain)](https://creativecommons.org/publicdomain/zero/1.0/)

##### Related Works

- [DIQA-5000](diqa-5000.md) - Complementary IQA dataset with MOS scores
- [SmartDoc-QA](smartdoc-qa.md) - Mobile capture quality assessment
- [OHR-Bench](ohr-bench.md) - OCR hallucination benchmark

##### Leaderboards

- None available yet (dataset released October 2025)

#### 10. Dataset-Specific Notes

> **Purpose**: Capture unique characteristics, caveats, and implementation details specific to this dataset that don't fit standard template sections. This is a **freeform section** - content varies by dataset.

##### 10.1 Annotation Caveats

**CRITICAL - Inverted Quality Scale**:

- OCR-Quality uses **1 = best quality, 4 = worst quality** (INVERTED)
- This is **opposite** from most IQA datasets:
  - DIQA-5000: 1-5 scale, 5 = best
  - SmartDoc-QA: OCR accuracy (higher = better)
  - OHR-Bench: 0-100 scale, 100 = best
- **Always apply normalization** before training: `(5 - human_score) / 4.0`
- **Risk**: Forgetting to invert will train models to predict the opposite of quality

**OCR Text Source**:

- OCR text extracted by **Qwen2.5-VL-72B** Vision-Language Model
- NOT traditional OCR engines (Tesseract, DocTR, PaddleOCR)
- VLM-based extraction may have different error patterns than traditional OCR
- Quality scores assess OCR **readability**, not VLM transcription accuracy

##### 10.2 Implementation Notes

**Parquet Format Specifics**:

- Images embedded as byte arrays in Parquet (no separate image directory)
- Parser extracts from `image_path` column matching image stem
- Potential issue: `str.contains()` matching could match multiple images (e.g., "doc1" matches "doc1.png" and "doc10.png")
- **Recommendation**: Use exact stem matching instead of substring matching

**Text Truncation**:

- Parser truncates `ocr_text` to 500 characters for storage efficiency
- Full text available in source Parquet for text statistics computation
- Text statistics (char count, word count) not yet computed in Layer 2

##### 10.3 External Resources

**HuggingFace Dataset Card**:

- Comprehensive source category statistics (30 categories)
- Quality score distribution table
- Usage examples in Python (datasets library + pandas)
- Dataset viewer with sample visualization

**OCR Model**:

- Qwen2.5-VL-72B model documentation: [Qwen2.5-VL](https://huggingface.co/Qwen/Qwen2.5-VL-72B)
- VLM approach differs from traditional OCR pipelines

##### 10.4 Custom Metrics

**Quality Tiers** (for stratified sampling):

| Tier | Score Range | Label | Sample Count | Usage |
|------|-------------|-------|--------------|-------|
| Tier 1 | 1 (Excellent) | High Quality | 507 | Positive examples, upper bound calibration |
| Tier 2 | 2 (Good) | Medium-High Quality | 305 | Balanced training examples |
| Tier 3 | 3 (Fair) | Medium-Low Quality | 84 | Degraded examples |
| Tier 4 | 4 (Poor) | Low Quality | 104 | Negative examples, lower bound calibration |

**Stratified Sampling Recommendation**:

- Tier 1+2 (good quality): 812 images (81.2%)
- Tier 3+4 (degraded quality): 188 images (18.8%)
- **Caution**: Class imbalance toward high-quality samples
- Consider oversampling Tier 3+4 for balanced training

> **Notes**:
>
> - Small dataset (1,000 images) - use for validation, not primary training
> - Multilingual coverage (Chinese + English) valuable for multilingual IQA
> - VLM-based OCR text differs from traditional OCR engines
> - Always invert quality scores before training to avoid reversed predictions

---

## 2. Benchmark-Only Datasets (02_benchmark_only/)

**CRITICAL**: These datasets are reserved for model evaluation ONLY. Never use for training to preserve benchmark validity.

| Dataset | Images | Purpose | Ground Truth | License |
|---------|--------|---------|--------------|---------|
| **DIQA-5000** | 5,500 | IQA calibration | Human MOS scores (3-dim) | Research |
| **DIBCO** | 131 | Historical degradation | Binarization GT | Academic |
| **OHR-Bench** | 8,561 entries | OCR hallucination | Text annotations | Research |
| **OmniDocBench** | metadata | Multi-task evaluation | Multiple | Research |
| **SmartDoc-QA** | 4,270 | Mobile capture QA | OCR accuracy (proxy) | Research |

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: B (82.6/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 85.8 | 25% |  |
| Field Validity | 100.0 | 25% |  |
| Doc Completeness | 54.5 | 15% | Below threshold |
| Defect Rate | 95.4 | 15% |  |
| Cross-Source Agreement | 51.9 | 10% | Below threshold |
| VLM Accuracy | 85.0 | 10% |  |
| **Overall** | **82.6** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 3 defects (1 deferred, 2 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| D01 | domain_level1 | LOW | OPEN | 129/1000 samples have domain_level1=UNK from LLM classification |
| D02 | layout_detections | MEDIUM | OPEN | No layout detections available |
| D03 | text_has_content | MEDIUM | DEFERRED | No text transcription labels available |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 85.0%

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/ocr-quality/](../../scripts/audit/results/ocr-quality/)

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 1,000 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 1,000 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `language` | 100.0% | 0.000 |
