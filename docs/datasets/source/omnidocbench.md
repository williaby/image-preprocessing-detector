### OmniDocBench

> **Quick Stats**: 1,355 PDF pages | 9 document types | Multi-task evaluation | CVPR 2025
>
> **License**: Research | **Commercial Use**: Research only

#### File Format

| Attribute | Value |
|-----------|-------|
| **Image Format** | PNG |
| **Annotation Format** | Parquet/Arrow (HuggingFace) + JSON |
| **Dimensions** | 570-6800 x 596-9212 px (avg: 2238 x 2667) |
| **Avg File Size** | 1,529 KB |
| **Total Size** | ~3 GB (images + annotations) |

##### Known Limitations

- Evaluation-only design - not intended for training (use stratified split for internal development only)
- Research license restricts commercial use
- Born-digital PDFs at 300 DPI - may not represent real-world scan degradation
- Domain imbalance across 9 document types (academic papers overrepresented)
- OCR noise variants are synthetic (3 engines x 3 levels) - not natural degradation
- No per-page language labels despite multilingual content (English + Chinese + mixed)

##### License & Citation

| Attribute | Value |
|-----------|-------|
| **License** | Research |
| **Commercial Use** | Research only |
| **Citation** | Chen et al. (2024). OmniDocBench: Benchmarking Diverse PDF Document Parsing. CVPR 2025. arXiv:2412.07626 |

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | OmniDocBench: Benchmarking Diverse PDF Document Parsing |
| **Version** | 1.0 |
| **Release Date** | December 2024 |
| **Maintainer** | OpenDataLab |
| **Paper** | [arXiv:2412.07626](https://arxiv.org/abs/2412.07626) (CVPR 2025) |
| **Repository** | [GitHub: opendatalab/OmniDocBench](https://github.com/opendatalab/OmniDocBench) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/omnidocbench/` |
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
| **Quality Assurance** | Multi-task comprehensive benchmark annotation |
| **GT Label Coverage** | 100% |

#### Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total PDF Pages** | 1,355 |
| **Document Types** | 9 (academic, textbooks, newspapers, handwritten, financial, etc.) |
| **Layout Types** | 4 |
| **Language Types** | 3 (English, Chinese, multi-lingual) |
| **Block-Level Elements** | 20,000+ (text paragraphs, titles, tables, etc.) |
| **Span-Level Elements** | 80,000+ (text lines, inline formulas, superscripts, etc.) |
| **Layout Categories** | 19 |
| **Attribute Labels** | 15 |

#### Document Sources

| Type | Description |
|------|-------------|
| Academic Papers | Scientific publications |
| Textbooks | Educational materials |
| Financial Reports | Business documents |
| Newspapers | Dense typeset layouts |
| Handwritten Notes | Challenging recognition |
| Slides | Presentation documents |
| And more... | 9 total document types |

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Multi-domain PDF documents (born-digital + scanned) |
| **Key Value** | Comprehensive multi-task parsing evaluation |
| **Unique Feature** | End-to-end + task-specific + attribute-based evaluation |

#### Benchmark Results (Document Parsing)

| Tool/Model | English Best | Chinese Best | Notes |
|------------|--------------|--------------|-------|
| **MinerU** | ✅ Best | - | Pipeline tool |
| **Mathpix** | - | ✅ Best | Pipeline tool |
| General VLMs | Strong generalization | Strong generalization | Better on long-tail scenarios |

*Finding: General VLMs show stronger generalization on slides and handwritten notes*

#### Training Value

- **Strengths**: 9 document types, 19 layout categories, multi-level evaluation (end-to-end, task-specific, attribute-based)
- **Weaknesses**: Evaluation-only design, requires document parsing pipeline
- **Split**: Stratified 70/15/15 train/val/test (938/203/217) by language+domain for training use
- **Benchmarking Note**: For formal benchmarking, the **full dataset** (all 1,358 samples) must be used as the evaluation set to ensure comparability with published results. The train/val/test split is for internal model development only.

#### Project Usage

- **Path**: `02_benchmark_only/omnidocbench/`
- **Phase(s)**: Benchmark evaluation (Phase 10)
- **Purpose**: Multi-task document parsing evaluation
- **Parser**: [`parse_omnidocbench_labels`](../scripts/annotate_base_metadata.py#L2979) | ✅ Complete

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/omnidocbench/` | ✅ Available | 1,358 PNG/JPG files |
| **Text/GT** | Native annotations | ✅ Available | Parquet: Multi-level ground truth text (`gt_text` field in HuggingFace parquet) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Docling GPU Extracted** | `metadata_registry/extracted/omnidocbench/` | ✅ Available | Docling GPU: 1,358 OCR records + 1,357 layout images, 28,614 annotations, 14 Docling categories |

#### Layer 2 Annotation Summary

| Metric | Value |
|--------|-------|
| **Annotated Samples** | 377 |
| **File Format** | PNG (100%) |
| **Dimensions** | 570-6800 × 596-9212 px (avg: 2238 × 2667) |
| **Avg File Size** | 1,529 KB |
| **Color Space** | RGB |
| **Capture Method** | Born-digital |
| **Domain** | Multi-domain Benchmark |

---

##### 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

###### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: D (81.8/100) | **Auditor**: claude-opus-4-6
> **Grade Cap**: B -> D (see notes below)

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 83.5 | 28% |  |
| Field Validity | 97.1 | 28% |  |
| Doc Completeness | 54.5 | 17% | Below threshold |
| Defect Rate | 75.0 | 17% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 90.0 | 11% |  |
| **Overall** | **81.8** | | **Grade D** |

**Grade Cap Applied**:
> Grade capped from B to D: Critical fields below 75%: domain_level1=0%. Language, script, and domain are critical training stratification fields. Datasets with <75% coverage on any of these fields cannot reliably support diversity-aware training splits or balanced sampling. A contact sheet VLM review or enrichment pipeline must bring these fields above 75% before the dataset can advance beyond Grade D.

###### 11.2 Key Defects

> **Total**: 3 defects (3 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| ODB-D01 | domain_level1 | HIGH | OPEN |  |
| ODB-D02 | layout_detections | MEDIUM | OPEN |  |
| ODB-D03 | text_has_content | MEDIUM | OPEN |  |

###### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

###### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/omnidocbench/](../../scripts/audit/results/omnidocbench/)

##### Processing Notes

- Parser: `parse_omnidocbench_labels` in `annotate_base_metadata.py`
- HuggingFace Parquet format with 17 columns including OCR noise variants
- Domain categories: 7 official (Textbook, Law, Finance, Academic, Newspaper, Magazine, Government)
- Split enrichment script: `scripts/audit/enrich_omnidocbench_split_colormode.py`
- Docling GPU extraction: 1,358 OCR records + 1,357 layout images, 28,614 annotations

##### Version History

| Version | Date | Change |
|---------|------|--------|
| v1.0 | 2024-12 | Initial dataset release (OpenDataLab, CVPR 2025) |
| L2 v1 | 2026-02-10 | Layer 2 base metadata annotation |
| L2 v2 | 2026-02-14 | Scorecard v2.0 audit, defect catalog created |

---

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 377 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 377 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `language` | 76.7% | 0.222 |
| 2 | `has_table` | 23.3% | 0.000 |
