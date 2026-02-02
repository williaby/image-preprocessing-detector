### invoices-kg

> **Quick Stats**: 1,414 images (989 train, 425 val) | Scanned invoices | Financial domain | Key-value extraction
>
> **License**: ODbL-1.0 | **Commercial Use**: Yes (with attribution + ShareAlike)

#### 1. Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | Kaggle High-Quality Invoice Images for OCR |
| **Version** | 1.0 |
| **Release Date** | 2022 (estimated) |
| **Maintainer** | Osama Hosam Abdellatif (Kaggle) |
| **Source** | [Kaggle Dataset](https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr) |
| **License** | [ODbL-1.0](https://opendatacommons.org/licenses/odbl/1-0/) |
| **Commercial Use** | Yes (with attribution + ShareAlike) |
| **Documentation Status** | Empirically Derived |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | JPG | Invoice scans/photos |
| **Annotations** | JSON | Manifest with structured invoice data + OCR text |
| **Metadata** | JSON | Dataset preparation metadata |

##### 2.2 Dataset Split Locations

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **Train** | `invoices_kaggle/train/images/` | `invoices_kaggle/train/annotations.json` | 989 | ✅ |
| **Validation** | `invoices_kaggle/val/images/` | `invoices_kaggle/val/annotations.json` | 425 | ✅ |
| **Total** | - | - | 1,414 | ✅ |

**Split Organization Pattern**: `by_folder` (train/val directories with annotations.json manifest)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Invoice Fields** | JSON (structured) | Document | client_name, seller_name, invoice_number, date, totals |
| **Line Items** | JSON (array) | Item-level | description, quantity, total_price |
| **OCR Text** | TXT (in JSON) | Page-level | Full invoice text transcription |

**Annotation Example**:

```json
{
  "invoice": {
    "client_name": "Davis, Li and Coleman",
    "seller_name": "Carpenter, Robinson and Jackson",
    "invoice_number": "41389063",
    "invoice_date": "03/17/2021",
    ...
  },
  "items": [
    {"description": "...", "quantity": "3.00", "total_price": "16.14"}
  ],
  "subtotal": {"tax": "1.47", "total": "16.14"}
}
```

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | `dataset_metadata.json` | Source, license, split info |
| **Image-level** | `annotations.json` | Original filename, CSV source path |
| **Annotation-level** | Embedded in JSON | Invoice fields, OCR text |

##### 2.5 Annotation Schema Details

**Format**: JSON manifest (one file per split)

Each manifest contains an array of annotation objects:

```json
[
  {
    "filename": "train_00000.jpg",
    "original_filename": "batch1-0965.jpg",
    "original_path": "data/downloads/...",
    "csv_source": "data/downloads/.../batch1_2.csv",
    "json_data": "{...structured invoice data...}",
    "ocred_text": "Invoice no: 41389063 Date of issue: ..."
  }
]
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `filename` | str | Yes | Links annotation to image |
| `json_data` | str (JSON) | Yes | Structured invoice fields |
| `ocred_text` | str | Yes | Full OCR transcription |
| `original_filename` | str | Yes | Provenance tracking |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Invoice fields | `raw_labels.{field}` | High | client, seller, invoice_number, date |
| ✅ Line items | `raw_labels.items` | High | Structured array of items |
| ✅ Totals | `raw_labels.{tax,total}` | High | Financial calculations |
| ✅ OCR text | `text_content.full_text` | High | Complete page transcription |
| ✅ Split info | `raw_labels.split` | Medium | train/val |

**Parser Implementation**: ✅ **Complete** - [`InvoicesKgParser`](../../src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py)

#### 3. Project Usage

| Aspect | Details |
|--------|---------|
| **Phase(s)** | Not currently used in training |
| **Purpose** | Key-value extraction, invoice IQA, OCR validation |
| **Local Path** | `01_base_data/forms/invoices_kaggle/` |
| **Subset Used** | Full dataset (1,414 images) |
| **Preprocessing** | `scripts/prepare_invoice_dataset.py` (flattens batch structure) |
| **Parser** | [`InvoicesKgParser`](../../src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py) |

#### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`InvoicesKgParser`](../../src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py) |
| **Parser Status** | ✅ Complete |
| **Layer 1 Fields** | `invoice_data`, `line_items`, `text_content` |
| **Layer 2 Auto-Derived** | `capture_method=scanned`, `domain.level1=FIN`, `domain.level2=INVOICE` |
| **Config Entry** | `DATASET_CONFIGS["invoices-kg"]` |

#### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `01_base_data/forms/invoices_kaggle/` | ✅ Available | 1,414 JPG files |
| **Text/OCR GT** | Embedded in annotations.json | ✅ Available | OCR text field |
| **Text/OCR Extracted** | `annotations/invoices-kaggle/ocr/` | ✅ Available | 1,414 OCR documents |
| **Layout GT** | None | ❌ None | No bounding boxes provided |
| **Layout Extracted** | `annotations/invoices-kaggle/layout/` | ✅ Available | 18,462 layout annotations |
| **Layer 2 Metadata** | `metadata_registry/json/invoices-kg_layer2.json` | ⚠️ To be generated | Pending parser integration |

#### 4. Dataset Statistics

##### 4.1 Sample Counts

| Metric | Value |
|--------|-------|
| **Total Images** | 1,414 |
| **Training Split** | 989 (70%) |
| **Validation Split** | 425 (30%) |
| **Test Split** | None |
| **File Format** | JPG |
| **Split Method** | Random (seed=42) |

##### 4.2 Content Composition

| Aspect | Details |
|--------|---------|
| **Domain** | Financial (invoices) |
| **Document Types** | Business invoices (mixed layouts) |
| **Language(s)** | English (Empirically Derived) |
| **Acquisition Method** | Scanned/photographed (mixed quality) |

#### 5. Known Issues & Limitations

- **Small Dataset**: Only 1,414 images (limited training utility)
- **No Bounding Boxes**: Source dataset does not provide spatial layout annotations
- **No Test Split**: Only train/val splits available
- **Quality Variance**: Mixed scan quality (not profiled yet)

#### 6. References

**Source**: [Kaggle Dataset](https://www.kaggle.com/datasets/osamahosamabdellatif/high-quality-invoice-images-for-ocr)

**Preparation Script**: `scripts/prepare_invoice_dataset.py`

**Parser Implementation**: `src/image_preprocessing_detector/annotation/parsers/layout/invoices_kg.py`

---
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
| **Total PDF Pages** | 8,500+ |
| **Selected Documents** | 350 unstructured PDFs |
| **Q&A Pairs** | 8,498 |
| **Domains** | 7 (Textbook, Law, Finance, Newspaper, Manual, Academic, Administration) |
| **OCR Components** | 5 (plain text, table, formula, chart, reading order) |
| **Format** | HuggingFace arrow file with text annotations |
| **Source PDFs** | Available as `pdfs.zip` (1.52 GB) on HuggingFace |

#### Document Domains

| Domain | Description |
|--------|-------------|
| Textbook | Educational materials |
| Law | Legal documents |
| Finance | Financial reports |
| Newspaper | News articles |
| Manual | Technical documentation |
| Academic | Research papers |
| Administration | Official documents |

##### 5.2 Class/Category Definitions

> **Purpose**: Define the taxonomy of classes/categories used in the dataset annotations.
> **Applicability**: Document domain classification (7 official categories).

**Official Domain Taxonomy** (from HuggingFace schema):

| Domain | ID | Description | Count [Inferred] |
|--------|-----|-------------|------------------|
| Academic | 1 | Research papers and scholarly articles | Unknown |
| Textbook | 2 | Educational textbooks | Unknown |
| Law | 3 | Legal documents and contracts | Unknown |
| Finance | 4 | Financial reports and statements | Unknown |
| Newspaper | 5 | News articles and journalism | Unknown |
| Manual | 6 | Technical manuals and documentation | Unknown |
| Administration | 7 | Official administrative documents | Unknown |

**Total Domains**: 7 (equal representation intended per paper)
**Source**: [Official] from HuggingFace `domain` column

> **Notes**:
>
> - Domain distribution not documented in paper
> - All 7 domains confirmed present in dataset
> - Domain extracted from parquet `domain` column, not filename heuristic
> - **Implementation Note**: Parser currently uses 16-type filename heuristic (academic, book, exam, finance, form, handwritten, legal, magazine, medical, newspaper, note, poster, receipt, research, resume, slide) which does NOT match official 7-domain taxonomy

#### IQA Profile

##### 6.1 Source Characteristics

| Characteristic | Description |
|----------------|-------------|
| **Source Type** | Unstructured PDF documents with multimodal elements |
| **Capture Device** | N/A (born-digital + scanned mixed) |
| **Original Quality** | Mixed (7 domains with varying quality) |
| **Compression** | PDF compression (original format) |
| **Known Artifacts** | Varies by domain and document source |

> **Note**: Source characteristics vary significantly across 7 domains. Dataset intentionally includes diverse quality levels for RAG evaluation.

##### 6.2 IQA Analysis

| Aspect | Assessment |
|--------|------------|
| **Source Type** | Unstructured PDF documents with multimodal elements |
| **Key Value** | Evaluating OCR noise impact on RAG systems |
| **Unique Feature** | Human-verified ground truth structured data per page |

#### OCR Noise Types Evaluated

| Noise Type | Impact on RAG |
|------------|---------------|
| **Semantic Noise** | Affects all retrievers and LLMs |
| **Formatting Noise** | Advanced models more resilient |

#### Key Finding

*"None of the current OCR solutions is fully capable of RAG systems across all scenarios."*

#### Training Value

- **Strengths**: 7 real-world domains, 8,498 Q&A pairs, human-verified ground truth, OCR noise categorization
- **Weaknesses**: No direct quality scores, requires PDF extraction
- **Stage 1 Status**: **EXCLUDED** - No direct quality scores, requires PDF extraction
- **Future Use**: Potential for domain diversity after preprocessing
- **Critical**: **NEVER train on this dataset - benchmark only**

#### 3. Project Usage

##### 3a. Training Purposes

> **Purpose**: Define which machine learning tasks this dataset supports.

**Not applicable** - This is a benchmark-only dataset (NEVER use for training).

##### 3b. Parser & Metadata Integration

| Integration Type | Status | Details |
|------------------|--------|---------|
| **Parser** | ⚠️ Incomplete | `OhrBenchParser` exists but missing critical features |
| **Ground Truth Text** | ❌ Not Extracted | Parser does NOT extract `gt_text` from parquet |
| **Domain Taxonomy** | ❌ Incorrect | Uses 16-type filename heuristic instead of official 7 domains |
| **Layer 2 Metadata** | ❌ Not Generated | Pending parser update |

**Parser Issues**:

1. Wrong HuggingFace dataset path: uses `vikp/ohr_bench` instead of `opendatalab/OHR-Bench`
2. Missing ground truth text extraction from `gt_text` column
3. Using filename heuristic (16 categories) instead of official 7 domains from parquet

##### 3c. Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/ohr-bench/extracted_images/` | ✅ Available | 8,561 PNG pages at 300 DPI |
| **Source PDFs** | `02_benchmark_only/ohr-bench/pdfs/` | ✅ Available | 1,261 original PDFs (1.52 GB) |
| **Text/OCR GT** | HuggingFace parquet `gt_text` column | ✅ Available | Ground truth structured data |
| **Annotations** | HuggingFace parquet (17 columns) | ✅ Available | Split, domain, page_idx, text |
| **Q&A Pairs** | GitHub `data/qas_v2.json` | ✅ Available | 8,498 question-answer pairs |
| **Layout GT** | - | ❌ None | No layout annotations provided |
| **Layer 2 Metadata** | `metadata_registry/json/ohr-bench_layer2.json` | ❌ Not extracted | Pending parquet conversion + parser update |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not extracted - Data not available or not yet processed
- 🔄 In progress - Currently being processed/extracted
- ⚠️ Partial - Some data available, incomplete

##### 4.1 Split Coverage

> **CRITICAL**: Always document ALL available splits and verify Layer 2 metadata includes them.

| Split | Source Count | Layer 2 Count | Coverage | Status |
|-------|--------------|---------------|----------|--------|
| **Train** | 6,849 | [NEEDS_PROFILING] | Unknown | ⚠️ Pending |
| **Validation** | 856 | [NEEDS_PROFILING] | Unknown | ⚠️ Pending |
| **Test** | 856 | [NEEDS_PROFILING] | Unknown | ⚠️ Pending |
| **Total** | 8,561 | [NEEDS_PROFILING] | Unknown | ⚠️ Pending |

**Split Status Legend:**

- ✅ Complete - All samples from this split are in Layer 2 metadata
- ⚠️ Partial - Some samples missing from Layer 2
- ❌ Missing - Split not included in Layer 2 metadata
- ℹ️ N/A - Split does not exist in source dataset

> **Note**: Layer 2 metadata annotation pending. Run `scripts/annotate_base_metadata.py --dataset ohr-bench` after parquet conversion complete.

#### Project Usage (Legacy)

- **Path**: `02_benchmark_only/ohr-bench/`
- **PDFs Path**: `02_benchmark_only/ohr-bench/pdfs/` (1,261 PDFs across 7 categories)
- **Images Path**: `02_benchmark_only/ohr-bench/extracted_images/` ✅ 8,561 images across 7 categories
- **Phase(s)**: Benchmark evaluation (Phase 10)
- **Purpose**: OCR hallucination and noise detection benchmark, RAG system evaluation
- **Parser**: ✅ `parse_ohr_bench_labels` (extracts document category from folder structure)
- **Conversion**: ✅ PDF→PNG conversion at 300 DPI via `scripts/convert_datasets_to_images.py --dataset ohr-bench`

#### 9. Citations & References

##### Primary Citation

```bibtex
@article{li2024ohr,
  title={OCR Hinders RAG: Evaluating the Cascading Impact of OCR on Retrieval-Augmented Generation},
  author={Li, Junyuan and others},
  journal={arXiv preprint arXiv:2412.02592},
  year={2024},
  note={To appear in ICCV 2025}
}
```

##### Related Works

- [OmniDocBench](#omnidocbench) - Complementary multi-task document parsing benchmark
- [DIQA-5000](#diqa-5000) - Document image quality assessment benchmark

##### Leaderboards

#### 10. Dataset-Specific Notes

> **Purpose**: Capture unique characteristics, caveats, and implementation details specific to this dataset that don't fit standard template sections.

##### 10.1 Annotation Caveats

- **Q&A Pair Linkage**: 8,498 Q&A pairs linked to pages via `evidence_page_no` field
- **Ground Truth Source**: Structured data extracted and verified by human annotators (per paper)
- **Text Length Variance**: Character count ranges 0-11.7M per page (highly variable)
- **Page Index Range**: Pages numbered 0-381 within documents

##### 10.2 Implementation Notes

**Parquet Schema Access**:

```python
from datasets import load_dataset
dataset = load_dataset("opendatalab/OHR-Bench")
train_data = dataset["train"]
gt_text = train_data["gt_text"]  # Ground truth text
domain = train_data["domain"]    # 7 domain categories
```

**Parser Taxonomy Mismatch**:

- **Official taxonomy**: 7 domains (from HF schema)
- **Parser heuristic**: 16 document types (from filename matching)
- **Resolution**: Use official 7 domains from parquet `domain` column, ignore filename heuristic

**Split Extraction**:

- Split membership stored in parquet `split` column (not directory-based)
- Pattern: `single_dir_with_manifest`

##### 10.3 External Resources

- **HuggingFace Dataset**: <https://huggingface.co/datasets/opendatalab/OHR-Bench>
- **Q&A Pairs**: Available in GitHub repo at `data/qas_v2.json`
- **Structured Data Variants**: `data/retrieval_base/` directory contains GT + noise variants
- **Evaluation Framework**: Bash scripts in `shell/` directory for retrieval/generation/end2end evaluation

##### 10.4 Custom Metrics

**OCR Noise Levels** (benchmark-specific):

- **Mild**: Low OCR error rate
- **Moderate**: Medium OCR error rate
- **Severe**: High OCR error rate

**Evaluated OCR Engines**:

1. GOT (General OCR Theory)
2. MinerU
3. Qwen2.5-VL (Vision-Language model)

**Noise Types**:

1. **Semantic Noise**: Affects content meaning (impacts all systems)
2. **Formatting Noise**: Affects structure only (advanced models more resilient)

> **Critical Warning**: This is a **benchmark-only dataset**. NEVER train models on this data - test set only for evaluation.

- No external leaderboards yet (dataset released December 2024)
- Paper reports internal RAG system evaluation results
