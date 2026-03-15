---
dataset_id: financebench
version: "1.0"
license: Research Only
commercial_use: false
iqa_profiles:
  - general
baseline_quality: null
training_suitable: true
benchmark_suitable: false
documentation_status: complete
---

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
- **GitHub Repository**: Contains PDFs, JSONL, and documentation — ⚠️ **No LICENSE file** in the GitHub repo (HTTP 404); license is only declared on HuggingFace. Pulling from GitHub without HuggingFace card is technically all-rights-reserved under copyright law.
- **GCS Bucket**: `gs://image_detection_b/image-preprocessing-detector/datasets/financebench/` (converted images)
- **Download**: Requires git clone of full repository to access PDFs

##### 10.4 License Restrictions

- **License**: CC-BY-NC-4.0 (Non-Commercial) — validated 2026-02-24 against HuggingFace card (SPDX: `cc-by-nc-4.0`)
- **License Scope**: Applies to Patronus AI's benchmark annotations (Q&A pairs, evidence citations, metadata). Covers only the open-source sample (150 Q&A pairs); full 10,231-question benchmark requires separate agreement (<contact@patronus.ai>).
- **GitHub inconsistency**: No LICENSE file in the GitHub repo (validated 2026-02-24). Canonical distribution point for license terms is HuggingFace.
- **Training Prohibited**: **NEVER use for model training** - benchmark integrity + license restriction
- **Evaluation Use**: Permitted for academic research and non-commercial benchmarking
- **Commercial Use**: Requires separate licensing agreement with Patronus AI
- **Attribution Required**: Must cite Islam et al. 2023 paper in any publications
- **SEC Filing PDF Copyright**: The underlying PDFs (10-K, 10-Q, 8-K filings) are copyrighted by the filing companies, not the US government. They are **not public domain** (17 U.S.C. § 105 applies to works by federal employees, not to company filings). While companies rarely enforce copyright on their SEC filings in research contexts, this is not equivalent to a public domain declaration. The CC-BY-NC-4.0 license covers Patronus AI's annotations only.

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

> **Audit Date**: 2026-02-16 | **Grade**: B (92.9/100) | **Auditor**: claude-opus-4-6

| Dimension | Score | Weight | Notes |
|-----------|------:|-------:|-------|
| Field Coverage | 88.3 | 18% |  |
| Field Validity | 100.0 | 18% |  |
| Doc Completeness | 63.6 | 6% | Below threshold |
| Defect Rate | 85.0 | 12% |  |
| Cross-Source Agreement | - | - | Excluded (no data) |
| VLM Accuracy | - | - | Excluded (no data) |
| **Overall** | **92.9** | | **Grade B** |

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

## 13. Training Head Coverage

### 13.1 Head Contribution Summary

| Head ID | Head Name | Contribution | Est. Samples | Label Type | Notes |
|---------|-----------|--------------|--------------|------------|-------|
| MNV4-H1 | orientation_cls | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| MNV4-H2 | skew_reg | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| MNV4-H3 | resolution_quality_reg | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| SIG-G1-1 | blur_score | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| SIG-G1-2 | noise_score | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| SIG-G1-3 | contrast_score | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| SIG-G1-4 | skew_score | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| SIG-G1-5 | compression_score | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| SIG-G1-6 | overall_quality | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| SIG-G2-1 | script_cls | ❌ | 0 | — | Benchmark reserved; Latin/English only anyway |
| SIG-G3-1 | orientation_cls (post) | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| SIG-G3-2 | skew_reg (post) | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |
| SIG-G4-1 | handwriting_presence_cls | ❌ | 0 | — | Benchmark reserved; 100% printed content, no handwriting present |
| SIG-G4-2 | handwriting_legibility_cls | ❌ | 0 | — | Benchmark reserved; 100% printed content, no handwriting present |
| SIG-G4-3 | handwriting_content_type_cls | ❌ | 0 | — | Benchmark reserved; 100% printed content, no handwriting present |
| SIG-G4-4 | presence_reg | ❌ | 0 | — | Benchmark reserved; 100% printed content, no handwriting present |
| SIG-G4-5 | legibility_reg | ❌ | 0 | — | Benchmark reserved; 100% printed content, no handwriting present |
| SIG-G5-1 | capture_method_cls | ❌ | 0 | — | Benchmark reserved; 100% born_digital confirmed by L2 stats |
| SIG-G5-2 | shadow_reg | ❌ | 0 | — | Benchmark reserved; no degradation present in L2 metadata |
| SIG-G5-3 | warping_reg | ❌ | 0 | — | Benchmark reserved; no degradation present in L2 metadata |
| SIG-G5-4 | code_cls | ❌ | 0 | — | Benchmark reserved; financial documents contain no source code |
| SIG-G5-5 | resolution_quality_reg | ❌ | 0 | — | Benchmark reserved; CC-BY-NC-4.0 prohibits training use |

### 13.2 Diversity Dimension Coverage

| # | Dimension | Coverage | Details |
|---|-----------|----------|---------|
| 1 | Script families | ❌ | Latin only (100% Latn per L2 stats); no script diversity |
| 2 | Capture method | ❌ | Born-digital only (100% born_digital per L2 stats); no scanning or camera samples |
| 3 | Document domain | ❌ | Finance only (100% FIN per L2 stats); no domain diversity |
| 4 | Layout type | ❌ | Benchmark reserved; L2 layout_types empty (DocLayout-YOLO not yet run) |
| 5 | Text density | ❌ | Benchmark reserved; L2 text_densities empty (not profiled) |
| 6 | Degradation types | ❌ | No degradation present (official SEC filings, professionally formatted); L2 degradation fields empty |
| 7 | Resolution/DPI range | ❌ | Benchmark reserved; all images converted at fixed 300 DPI via PyMuPDF |
| 8 | Document age | ❌ | Modern only (2015–2023 SEC filings); no historical or aged documents |
| 9 | Text scope | ❌ | Page-level only (100% page per L2 stats) |
| 10 | Content flags | ❌ | Benchmark reserved; L2 flags tables only (has_table: 100%); financial docs contain tables and text blocks |
| 11 | Binarization status | ❌ | Born-digital color PDFs; no binarization diversity |
| 12 | Artifact types | ❌ | No artifacts (clean SEC filings; no scanning artifacts, no camera noise) |
| 13 | Color mode | ❌ | Born-digital color mode only; no grayscale or binarized samples |
| 14 | Font variety | ❌ | Benchmark reserved; financial documents use a narrow set of professional serif/sans-serif fonts |

### 13.3 Corpus Role & Constraints

FinanceBench is a **benchmark-only evaluation corpus** — it MUST NOT contribute to any training pipeline under any circumstances. The CC-BY-NC-4.0 license prohibits commercial and training use, and training on this dataset would compromise benchmark integrity for RAG pipeline evaluation (Phase 10). All 54,120 images are stored under `02_benchmark_only/` and must remain exclusively in the OOD evaluation path.
