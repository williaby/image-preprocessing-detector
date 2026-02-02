### OmniDocBench

> **Quick Stats**: 1,355 PDF pages | 9 document types | Multi-task evaluation | CVPR 2025
>
> **License**: Research | **Commercial Use**: Research only

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
- **Critical**: **NEVER train on this dataset - benchmark only**

#### Project Usage

- **Path**: `02_benchmark_only/omnidocbench/`
- **Phase(s)**: Benchmark evaluation (Phase 10)
- **Purpose**: Multi-task document parsing evaluation
- **Parser**: [`parse_omnidocbench_labels`](../scripts/annotate_base_metadata.py#L2979) | ✅ Complete

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
