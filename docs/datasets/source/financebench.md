### FinanceBench

> **Quick Stats**: 368 PDFs | 150 Q&A pairs (open-source) | Financial RAG benchmark | CC-BY-NC-4.0
>
> **License**: CC-BY-NC-4.0 (Non-Commercial) | **Commercial Use**: No

#### Overview

| Attribute | Value |
|-----------|-------|
| **Full Name** | FinanceBench: A New Benchmark for Financial Question Answering |
| **Version** | 1.0 |
| **Release Date** | November 2023 |
| **Maintainer** | Patronus AI |
| **Paper** | [arXiv:2311.11944](https://arxiv.org/abs/2311.11944) |
| **Repository** | [GitHub: patronus-ai/financebench](https://github.com/patronus-ai/financebench) |
| **HuggingFace** | [PatronusAI/financebench](https://huggingface.co/datasets/PatronusAI/financebench) |
| **License** | CC-BY-NC-4.0 |
| **GCS** | `gs://image_detection_b/image-preprocessing-detector/datasets/financebench/` |
| **Documentation Status** | Complete |

#### 2. Source Data Inventory

##### 2.1 Provided File Types

| File Type | Format(s) | Description |
|-----------|-----------|-------------|
| **Images** | PDF (source), PNG (converted) | 368 SEC filings converted to 54,120 PNG images at 300 DPI |
| **Annotations** | JSONL | Q&A pairs with evidence citations |
| **Metadata** | JSONL | Document information (GICS, periods, URLs) |
| **Supplementary** | README.md | Repository documentation |

##### 2.2 Dataset Split Locations

> **Purpose**: This is a benchmark evaluation dataset with no train/test/val splits.

| Split | Images Path | Annotations Path | Count | Status |
|-------|-------------|------------------|-------|--------|
| **All** | `02_benchmark_only/financebench/extracted_images/` | `data/*.jsonl` | 54,120 | ✅ |

**Split Organization Pattern**: N/A - Single evaluation set (no training splits)

> **Notes**:
>
> - This is a **benchmark-only dataset** (CC-BY-NC-4.0 license restriction)
> - All 368 documents and 54,120 pages are used for evaluation
> - 150 Q&A pairs are open-source; 10,231 total Q&A pairs exist (proprietary)

##### 2.3 Provided Labels & Annotations

| Label Type | Format | Granularity | Description |
|------------|--------|-------------|-------------|
| **Q&A Pairs** | JSONL | Document-level | 150 open-source question-answer pairs with human annotations |
| **Evidence Citations** | JSONL | Page-level | Page numbers and text excerpts cited as evidence |
| **Document Metadata** | JSONL | Document-level | Company, period, type, GICS sector, source URL |
| **Reasoning Types** | JSONL | Question-level | 9 reasoning categories (e.g., metrics-generated, domain-relevant) |

> **Note**: This is a Q&A benchmark, NOT an OCR/layout dataset. No bounding boxes, text transcriptions, or layout annotations.

##### 2.4 Provided Metadata

| Metadata Type | Location | Content |
|---------------|----------|---------|
| **Dataset-level** | README.md | License, citation, usage instructions |
| **Document-level** | `financebench_document_information.jsonl` | 368 records with doc_name, doc_type, period, GICS sector, URL |
| **Question-level** | `financebench_open_source.jsonl` | 150 records with question, answer, justification, evidence |
| **Image-level** | Filename pattern | Company, period, type, page number encoded in filename |

##### 2.5 Annotation Schema Details

**financebench_document_information.jsonl** (368 documents):

```json
{
  "doc_name": "3M_2018_10K",
  "doc_type": "10K",
  "doc_period": "2018",
  "doc_link": "https://...",
  "company_sector_gics": "Industrials"
}
```

**financebench_open_source.jsonl** (150 Q&A pairs):

```json
{
  "financebench_id": "FB001",
  "question": "What was 3M's revenue in 2018?",
  "answer": "$32.8 billion",
  "justification": "As stated in the 10K filing...",
  "question_type": "metrics-generated",
  "question_reasoning": "simple_fact_lookup",
  "company": "3M",
  "doc_name": "3M_2018_10K",
  "evidence": [
    {
      "doc_name": "3M_2018_10K",
      "evidence_page_num": 58,
      "evidence_text": "Total revenue: $32,765 million"
    }
  ]
}
```

**Key Fields for Parsing**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `doc_name` | str | Yes | Format: {COMPANY}_{PERIOD}_{TYPE} |
| `doc_type` | str | Yes | Enum: 10K, 10Q, 8K, EARNINGS |
| `company_sector_gics` | str | Varies | One of 9 GICS sectors |
| `evidence_page_num` | int | Varies | 0-indexed page number in evidence |
| `financebench_id` | str | Yes | Unique Q&A identifier |

##### 2.6 Parser Potential Summary

| Data Available | Parser Extractable | Priority | Notes |
|----------------|-------------------|----------|-------|
| ✅ Document metadata | ✅ Extracted | High | Company, period, type, GICS, URL |
| ✅ Evidence page flags | ✅ Extracted | High | Boolean flag for pages cited in Q&A |
| ✅ Document taxonomy | ✅ Extracted | High | 10K/10Q/8K/EARNINGS classification |
| ⚠️ Domain classification | ⚠️ Inferred | Medium | FIN domain (financial documents) |
| ❌ Ground truth text | ❌ Not available | Low | Q&A benchmark, not OCR dataset |
| ❌ Layout annotations | ❌ Not available | Low | No bounding boxes or structure |

**Legend**: ✅ Directly usable | ⚠️ Requires transformation | ❌ Not available

##### 2.7 Ground Truth Provenance

| Aspect | Details |
|--------|---------|
| **Annotation Method** | Human-annotated Q&A with evidence citations |
| **Provenance Tier** | Tier 1 (Human-labeled) |
| **Quality Assurance** | Expert annotation with evidence citation checks |
| **GT Label Coverage** | 100% of open-source Q&A subset (150 pairs out of 10,231 total) |

#### 3. Project Usage

##### 3a. Training Purpose & Dataset Statistics

**Purpose**: Benchmark evaluation (Phase 10), RAG pipeline evaluation

| Metric | Value |
|--------|-------|
| **Open-Source Q&A Pairs** | 150 |
| **Full Dataset Q&A Pairs** | 10,231 |
| **PDF Documents** | 368 |
| **Extracted Images** | 54,120 PNG at 300 DPI |
| **Document Types** | 10K, 10Q, 8K, Earnings Reports |
| **Companies** | Multiple publicly traded (GICS classified) |
| **Question Types** | 3 (metrics-generated, domain-relevant, novel-generated) |
| **Reasoning Types** | 9 categories |
| **GICS Sectors** | 9 |

#### Document Types

| Type | Description |
|------|-------------|
| **10K** | Annual financial reports |
| **10Q** | Quarterly financial reports |
| **8K** | Current event reports |
| **EARNINGS** | Earnings call transcripts |

#### Data Structure

**`financebench_open_source.jsonl`** (150 examples):

- `financebench_id`: Unique question identifier
- `question`: Question text
- `answer`: Human-annotated gold answer
- `justification`: Human-annotated justification
- `question_type`: metrics-generated, domain-relevant, novel-generated
- `question_reasoning`: Reasoning type needed
- `company`: Company of interest
- `doc_name`: Document identifier (`{COMPANY}_{PERIOD}_{TYPE}`)
- `evidence`: List of evidence objects with page numbers and text extracts

**`financebench_document_information.jsonl`** (metadata):

- `doc_name`: Document identifier
- `doc_type`: 10K, 10Q, 8K, EARNINGS
- `doc_period`: Financial period (2015-2023)
- `doc_link`: URL to source document
- `company_sector_gics`: GICS sector classification

#### IQA Profile

| Aspect | Assessment |
|--------|------------|
| **Source Type** | SEC filings (born-digital financial documents) |
| **Key Value** | **Financial RAG evaluation benchmark** for LLM Q&A |
| **Unique Feature** | Evidence-annotated Q&A with page-level citations |
| **Document Quality** | High (official SEC filings, professionally formatted) |

#### Key Research Finding

> "GPT-4-Turbo used with a retrieval system incorrectly answered or refused to answer 81% of questions."

This benchmark exposes significant LLM limitations on financial document understanding.

#### Training Value

- **Strengths**: Real SEC filings, evidence-annotated Q&A, GICS sector diversity, professional document formatting
- **Weaknesses**: Non-commercial license, PDF-only (requires conversion), US-centric companies
- **Critical**: **NEVER train on this dataset - benchmark only** (license restriction + benchmark integrity)

##### 3b. Parser & Metadata Integration

| Aspect | Details |
|--------|---------|
| **Label Parser** | [`FinanceBenchParser`](../../src/image_preprocessing_detector/annotation/parsers/document/financebench.py) |
| **Parser Status** | ✅ Complete - Full metadata extraction with batch support |
| **Layer 1 Fields** | `company`, `doc_period`, `doc_type`, `page_num`, `gics_sector`, `doc_link`, `is_evidence_page`, `document_type` |
| **Layer 2 Auto-Derived** | `domain.primary_domain=FIN`, `domain.gics_sector`, `capture_method=born_digital`, `provenance.page_number`, `benchmark_metadata.evidence_page` |
| **Config Entry** | [`DATASET_CONFIGS["financebench"]`](../../scripts/annotate_base_metadata.py) |
| **Batch Support** | ✅ YES - Caches JSONL metadata for efficient processing |

**Parser Architecture**:

- **Filename Parsing**: Regex extraction of company, period, type, page from `{COMPANY}_{PERIOD}_{TYPE}_p{PAGE}.png`
- **Metadata Enrichment**: JSONL lookup for GICS sector, document URL
- **Evidence Linking**: Cross-references Q&A data to flag evidence pages
- **Caching**: Loads JSONL files once per batch for performance

**Parser Enhancements Available**:

- Domain classification (FIN) could be hardcoded in Layer 2 derivation
- Capture method (born_digital) could be explicitly set
- Benchmark metadata flag could be added to Layer 2 schema

> **Parser Reference**: See [LABEL_MAPPING_SPECIFICATION.md](../schema/LABEL_MAPPING_SPECIFICATION.md) for field mappings.

##### Data Locations

| Data Type | Path | Status | Notes |
|-----------|------|--------|-------|
| **Images** | `02_benchmark_only/financebench/` | ✅ Available | 54,121 PNG files |
| **Text/GT** | Native annotations | ✅ Available | JSON: QA text pairs from financial documents |
| **Text/OCR Extracted** | - | ❌ Not extracted | Docling OCR not yet run |
| **Layout Extracted** | - | ❌ Not extracted | DocLayout-YOLO not yet run |

**Location Status Legend**:

- ✅ Available - Data exists at this location
- ❌ None/Not created - Data not available or not yet processed
- 🔄 In progress - Currently being processed/extracted
- ⚠️ Partial - Some data available, incomplete

#### 10. Dataset-Specific Notes

##### 10.1 Annotation Caveats

- **Benchmark Contamination Risk**: This dataset is widely known and may be present in LLM training data. Use with caution for model evaluation.
- **Evidence Page Filtering**: Only 150 Q&A pairs are open-source; full 10,231 pairs are proprietary. Evidence pages may not cover all document content.
- **Page Indexing**: Evidence page numbers in JSONL are 0-indexed; filename page numbers are 1-indexed (parser handles conversion).
- **Document Completeness**: Some PDFs may have redacted or missing pages; verify page counts against source SEC filings.

##### 10.2 Implementation Notes

- **Filename Pattern**: `{COMPANY}_{PERIOD}_{TYPE}_p{PAGE:03d}.png` where PAGE is 3-digit zero-padded
- **Case Sensitivity**: Company names are uppercase in filenames, case-insensitive in JSONL lookups
- **Document Name Construction**: `{COMPANY}_{PERIOD}_{TYPE}` must match JSONL `doc_name` field exactly
- **Batch Processing**: Parser caches JSONL files on first access; clear cache between dataset versions
- **PDF Conversion**: Images converted at 300 DPI via PyMuPDF to standardize resolution

##### 10.3 External Resources

- **HuggingFace Dataset**: Contains JSONL files only (no PDFs)
- **GitHub Repository**: Contains PDFs, JSONL, and documentation
- **GCS Bucket**: `gs://image_detection_b/image-preprocessing-detector/datasets/financebench/` (converted images)
- **Download**: Requires git clone of full repository to access PDFs

##### 10.4 License Restrictions

- **License**: CC-BY-NC-4.0 (Non-Commercial)
- **Training Prohibited**: **NEVER use for model training** - benchmark integrity + license restriction
- **Evaluation Use**: Permitted for academic research and non-commercial benchmarking
- **Commercial Use**: Requires separate licensing agreement with Patronus AI
- **Attribution Required**: Must cite Islam et al. 2023 paper in any publications

**Critical Enforcement**:

- Dataset stored in `02_benchmark_only/` directory (not `01_base_data/`)
- Automated checks should prevent this dataset from entering training pipelines
- Processing status document marks as "benchmark reserved"

#### Download Instructions

```bash
# Clone repository (includes PDFs)
git clone https://github.com/patronus-ai/financebench.git 02_benchmark_only/financebench

# Or download via HuggingFace (Q&A data only, no PDFs)
from datasets import load_dataset
ds = load_dataset("PatronusAI/financebench")
```

---

## 3. Training Datasets (03_training_datasets/)

Generated augmented datasets with labels, ready for model training.

## 11. Layer 2 Audit Summary

> **Purpose**: Captures the results of a Layer 2 metadata audit (if performed). Populated
> after running the [audit execution template](../audit/AUDIT_EXECUTION_TEMPLATE.md) and
> [compute_scorecard.py](../../scripts/audit/compute_scorecard.py).

### 11.1 Quality Scorecard

> **Audit Date**: 2026-02-14 | **Grade**: B (84.6/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 86.7 | 28% |  |
| Field Validity | 96.3 | 28% |  |
| Doc Completeness | 54.5 | 17% | Below threshold |
| Defect Rate | 85.0 | 17% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | 95.0 | 11% |  |
| **Overall** | **84.6** | | **Grade B** |

### 11.2 Key Defects

> **Total**: 2 defects (2 open)

| ID | Field | Severity | Status | Description |
|----|-------|----------|--------|-------------|
| FB-D01 | layout_detections | HIGH | OPEN |  |
| FB-D02 | text_has_content | MEDIUM | OPEN |  |

### 11.3 VLM Inspection Summary

> **Samples Inspected**: 0 | **Corrections**: 0 | **Passing Accuracy**: N/A

### 11.4 Cross-Dataset Findings

- No cross-dataset known issues identified for this dataset.

**Audit Artifacts**: [scripts/audit/results/financebench/](../../scripts/audit/results/financebench/)

---

#### Reliability & Bottlenecks

> **Computed**: 2026-02-10 | **Samples**: 54,120 | **Avg Min Confidence**: 0.000

**Composite Category Distribution**:

| Category | Count | Pct |
|----------|------:|----:|
| hard_label | 0 | 0.0% |
| soft_label | 0 | 0.0% |
| active_learning | 0 | 0.0% |
| unreliable | 54,120 | 100.0% |

**Top Bottleneck Fields** (most frequently the weakest):

| Rank | Field | Bottleneck % | Avg Confidence |
|-----:|-------|-------------:|---------------:|
| 1 | `has_formula` | 100.0% | 0.000 |
