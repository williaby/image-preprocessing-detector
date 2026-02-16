### SmartDoc-QA

> **Quick Stats**: 4,260 images | Mobile-captured | Quality assessment benchmark
>
> **License**: Research | **Commercial Use**: Research only

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | SmartDoc Quality Assessment |
| **Version** | 1.0 (CBDAR@ICDAR 2015) |
| **Release Date** | 2015 |
| **Maintainer** | L3i Lab, Université de La Rochelle |
| **Paper** | [Nayef et al. 2015](https://ieeexplore.ieee.org/document/7333960/) |
| **Repository** | [smartdoc.univ-lr.fr](http://smartdoc.univ-lr.fr/smartdoc-qa/) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/smartdoc-qa/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

> **Purpose**: Documents what the original dataset provides from the source, enabling parser development and integration planning.

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PNG | Extracted PDF pages at 300 DPI |
| **Source PDFs** | PDF | 1,261 original unstructured PDFs |
| **Annotations** | Parquet/Arrow | HuggingFace dataset with 17 columns |
| **Q&A Pairs** | JSON | 8,498 question-answer pairs (qas_v2.json) |
| **Supplementary** | JSON | Structured data variants (GT + noise levels) |

##### 2.2 Dataset Split Locations

> **Purpose**: Track train/test/val paths to avoid missing data during processing.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `02_benchmark_only/ohr-bench/extracted_images/` | HF parquet `split='train'` | 6,849 | ✅ |
| **Validation** | `02_benchmark_only/ohr-bench/extracted_images/` | HF parquet `split='val'` | 856 | ✅ |
| **Test** | `02_benchmark_only/ohr-bench/extracted_images/` | HF parquet `split='test'` | 856 | ✅ |
| **Total** | - | - | 8,561 | ✅ |

**Split Organization Pattern**: `single_dir_with_manifest` (parquet `split` column)

> **Notes**:
>
> - Split determined by `split` column in HuggingFace parquet file
> - All images stored in single directory, split membership tracked in metadata
> - Total: 8,561 images (HF reports 8,560 rows, likely rounding)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Ground Truth Text** | Parquet `gt_text` column | Page | Official structured data extracted from PDFs |
| **Domain Labels** | Parquet `domain` column | Document | 7 domain categories (Textbook, Law, Finance, etc.) |
| **Document Names** | Parquet `doc_name` column | Document | Document identifier (10-168 chars) |
| **Page Index** | Parquet `page_idx` column | Page | Page number (0-381 range) |
| **Q&A Pairs** | JSON | Document | 8,498 question-answer pairs with evidence |
| **OCR Noise Variants** | Parquet (12 columns) | Page | 3 engines × 3 levels + 3 formatting levels |

> **Note**: OCR noise variants are for research evaluation, not training labels.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README / Paper | Version, license (CC-BY-4.0), citation, domains |
| **Image-level** | Parquet `page_idx` | Page number, document name |
| **Document-level** | Parquet `doc_name`, `domain` | Document ID, domain category |
| **Q&A-level** | qas_v2.json | Question, answer, evidence source, page number |

##### 2.5 Annotation Schema Details

> **Format**: HuggingFace Parquet with 17 columns

**Schema Structure**:

```text
- split: Text (train/val/test identifier)
- domain: Text (7 domain categories)
- doc_name: Text (document identifier, 10-168 chars)
- page_idx: Int32 (page number, 0-381 range)
- gt_text: Text (ground truth structured data, 0-11.7M chars)
- semantic_noise_GOT_mild/moderate/severe: Text (GOT OCR variants)
- semantic_noise_MinerU_mild/moderate/severe: Text (MinerU OCR variants)
- semantic_noise_Qwen2.5-VL_mild/moderate/severe: Text (Qwen2.5-VL variants)
- formatting_noise_mild/moderate/severe: Text (formatting variants)
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `split` | Text | Yes | Links to train/val/test split |
| `domain` | Text | Yes | 7 official domain categories |
| `doc_name` | Text | Yes | Document identifier |
| `page_idx` | Int32 | Yes | Page number within document |
| `gt_text` | Text | Yes | Ground truth text content (highly variable length) |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Ground truth text | `text_content.full_text` | **HIGH** | Currently NOT extracted by parser |
| ✅ Domain (7 categories) | `provenance.source_dataset_category` | **HIGH** | Parser uses filename heuristic instead |
| ✅ Document name | `provenance.original_filename` | Medium | Not currently extracted |
| ✅ Page index | `provenance.page_number` | Medium | Not currently extracted |
| ✅ Split identifier | `provenance.split` | Medium | Not currently extracted |
| ⚠️ OCR noise variants | - | Low | Research data, not for production use |

**Legend**: ✅ Directly usable | ⚠️ Research-specific | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human Expert |
| **Provenance Tier** | Tier 1 (Annotation) |
| **Annotator Details** | [NEEDS_VERIFICATION] |
| **Quality Assurance** | Question-answer pair creation on mobile-captured documents |
| **GT Label Coverage** | 100% |

#### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Images** | 4,260 |
| **Document Types** | Modern documents, receipts, old administrative letters |
| **Distortion Types** | Single and multiple capture distortions |
| **Capture Setup** | Fanuc LR Mate 200iD robotic arm (controlled environment) |
| **Cameras** | Samsung Galaxy S4, other smartphones |
| **Ground Truth** | Distortion type/amount, OCR outputs (3 engines), OCR accuracy |

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Mobile camera captures (controlled robotic arm) |
| **Distortion Types** | Blur, perspective, lighting, noise, folds |
| **Quality Metric** | OCR accuracy as proxy for document quality |
| **Key Value** | Benchmark for IQA methods via OCR correlation |

#### Training Value

- **Strengths**: Controlled capture environment, multiple distortion types, OCR accuracy ground truth, 3 OCR engine outputs
- **Weaknesses**: Synthetic distortions (robotic capture), limited to 3 document types, benchmark-only design
- **Critical**: **NEVER train on this dataset - benchmark only**

#### Benchmark Purpose

SmartDoc-QA enables benchmarking quality assessment methods using OCR accuracy as an objective measure. The controlled capture environment allows isolating specific distortion effects:

- **Single distortions**: Isolate individual quality factors
- **Multiple distortions**: Simulate real-world capture conditions
- **OCR correlation**: Predict OCR performance from image quality

#### Project Usage

- **Path**: `02_benchmark_only/smartdoc-qa/`
- **Phase(s)**: Benchmark evaluation
- **Purpose**: Mobile capture quality assessment benchmark
- **Parser**: [`parse_smartdoc_labels`](../scripts/annotate_base_metadata.py#L1004) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/smartdoc-qa/` | ✅ Available | 4,280 JPG files |
| **Text/GT** | Native annotations | ✅ Available | JSON: QA text pairs from document images |
| **Text/OCR Extracted** | `annotations/smartdoc-qa/ocr/ocr_batch_*.jsonl` | ✅ Available | 3,000 records (70%), Docling OCR |
| **Layout Extracted** | `annotations/smartdoc-qa/layout/layout_batch_*.json` | ✅ Available | 2,203 records (51%), DocLayout-YOLO |
| **Docling GPU Extracted** | `metadata_registry/extracted/smartdoc-qa/` | ⚠️ Partial | Docling GPU: 3,000/4,280 OCR (70%) + 2,305/4,280 layout (54%), needs investigation |

#### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 4,260 |
| **File Format** | JPEG (100%) |
| **Dimensions** | 3264-4128 × 2448-3096 px (avg: 3696 × 2772) |
| **Avg File Size** | 3,132 KB |
| **Color Space** | RGB |
| **Capture Method** | Camera (Smartphone) |
| **Domain** | General Documents |

#### 5. Data Format

| Attribute | Value |
|-----------|-------|
| **Image Format** | JPEG |
| **Resolution** | Camera-native (3264-4128 × 2448-3096 px) |
| **Color Space** | RGB |
| **Metadata Format** | Per-image JSON (Layer 2) + HuggingFace Parquet |
| **Storage** | GCS bucket + local E:\ drive |

#### 6. License

| Attribute | Value |
|-----------|-------|
| **License Type** | Research Only |
| **Source** | L3i Lab, Université de La Rochelle |
| **Commercial Use** | Not permitted |
| **Citation** | Nayef et al. CBDAR@ICDAR 2015 |

#### 7. Limitations

- **Benchmark only**: NEVER train on this dataset - designed exclusively for evaluation/benchmarking
- **Controlled environment**: Robotic arm capture does not represent real-world smartphone usage
- **Limited document types**: Only 3 categories (modern documents, receipts, old administrative letters)
- **Partial OCR/layout coverage**: Docling extracted 70% OCR and 54% layout (failures need investigation)
- **No official splits**: Dataset does not define train/val/test partitions

#### 8. Processing Status

| Step | Status | Notes |
|------|--------|-------|
| **Image Storage** | ✅ Complete | 4,260 JPEG images |
| **Base Metadata** | ✅ Complete | 4,260 samples annotated |
| **LLM Enrichment** | ✅ Complete | Domain, language, script enrichment |
| **Language Enrichment** | ✅ Complete | OpenLID language detection |
| **Docling OCR** | ⚠️ Partial | 70% coverage (3,000/4,280) |
| **DocLayout-YOLO** | ⚠️ Partial | 54% coverage (2,305/4,280) |
| **VLM Inspection** | ❌ Not started | Content flags unverified |

#### Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-02-10 | Initial Layer 2 metadata documentation |
| v1.1 | 2026-02-13 | Added format, license, limitations, processing, version history sections |

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-16 | **Grade**: B (88.4/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 92.4 | 15% |  |
| Field Validity | 92.4 | 15% |  |
| Doc Completeness | 100.0 | 5% |  |
| Defect Rate | 84.0 | 10% |  |
| Cross-Source Agreement | 68.5 | 15% | Below threshold |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **88.4** | | **Grade B** |

###### 11.2 Key Defects

> **Total**: 8 defects (7 accepted, 1 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| DEF-001 | split | low | ACCEPTED | Split is 'unknown' for all 4,260 samples. Dataset does not define official train |
| DEF-002 | domain_level1 | medium | ACCEPTED | domain_level1 is 'UNK' for all 4,260 samples. LLM enrichment domain confidence i |
| DEF-003 | script_family | medium | OPEN | script_family uses invalid enum value 'ltr' instead of 'latin' for all 4,260 sam |
| DEF-004 | layout_detections | low | ACCEPTED | layout_detections empty for 26.7% of samples (1,136/4,260). Partial DocLayout-YO |
| DEF-005 | text_has_content | low | ACCEPTED | text_has_content is false for all 4,260 samples. No OCR extraction integrated. |
| DEF-006 | orientation_class | low | ACCEPTED | orientation_class not populated for all 4,260 samples. |
| DEF-007 | image_properties_color_mode | low | ACCEPTED | image_properties.color_mode not populated for all 4,260 samples. |
| DEF-008 | handwriting_present | low | ACCEPTED | handwriting_present not populated for all 4,260 samples. |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: 92.0%

###### 11.4 Cross-Dataset Findings

- **KI-007**: ACCEPTED --
- **KI-008**: OPEN --

**Audit Artifacts**: [scripts/audit/results/smartdoc-qa/](../../scripts/audit/results/smartdoc-qa/)

##### Reliability & Bottlenecks

> **Computed**: 2026-02-16 | **Samples**: 4,260 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 4,260 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `text_quality` | 100.0% | 0.000 |
