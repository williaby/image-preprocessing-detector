### OHR-Bench

> **Quick Stats**: 8,561 PDF pages | 7 domains | 8,498 Q&As | OCR impact on RAG benchmark | ICCV 2025
>
> **License**: Research | **Commercial Use**: Research only

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | OHR-Bench: OCR Hinders RAG Benchmark |
| **Version** | 1.0 |
| **Release Date** | December 2024 |
| **Maintainer** | OpenDataLab |
| **Paper** | [arXiv:2412.02592](https://arxiv.org/abs/2412.02592) (ICCV 2025) |
| **Repository** | [GitHub: opendatalab/OHR-Bench](https://github.com/opendatalab/OHR-Bench) |
| **License** | Research |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/ohr_bench/` |
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

## Detailed Dataset Entries

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/ohr-bench/` | ✅ Available | 16,091 JPG files |
| **Text/GT** | Native annotations | ✅ Available | Parquet: Structured ground truth text (`gt_text` field in HuggingFace parquet) |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |
| **Docling GPU Extracted** | `metadata_registry/extracted/ohr-bench/` | ✅ Available | Docling GPU: 1,261 PDFs → 1,259 OCR records (99.8% success) + 1,259 layout images, 136,555 annotations, 14 Docling categories |
| **Language Detected** | `metadata_registry/extracted/ohr-bench/language_detection.json` | ✅ Available | fastText: 79.5% English, 18.1% Chinese, 1.2% other (fr/ca/ru/de). Scripts: 84.1% Latin, 15.6% Chinese |
| **Layer 2 Metadata** | `metadata_registry/json/ohr-bench_metadata.json` | ✅ Complete | 8,303 samples (2026-02-09) |

##### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 8,303 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 8,303 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `language` | 100.0% | 0.000 |
