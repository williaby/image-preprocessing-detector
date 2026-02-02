---
name: dataset-documentation-standards
description: Shared context for dataset documentation patterns, operational scripts, and standards
---

# Dataset Documentation Standards

Shared context for dataset-related agents and workflows. Defines the three-tier documentation structure, naming conventions, Layer 2 schema requirements, parser patterns, and operational scripts.

## Authoritative References

| Document | Purpose | Location |
|----------|---------|----------|
| **DATASET_TEMPLATE.md** | Authoritative entry format (v1.2.0) | docs/datasets/DATASET_TEMPLATE.md |
| **DATASET_GAPS_REPORT.md** | Known gaps and issues | docs/planning/DATASET_GAPS_REPORT.md |
| **layer2_enrichment.schema.json** | Layer 2 schema definition | docs/schema/layer2_enrichment.schema.json |
| **DATASET_NAMING_STANDARD.md** | Canonical names and aliases | docs/datasets/DATASET_NAMING_STANDARD.md |

**Template Version**: 1.2.0 (includes Section 2 Source Data Inventory, Section 5.2-5.3, Section 6.5, Section 10)

## Three-Tier Documentation Structure

| Tier | File | Size | Purpose |
|------|------|------|---------|
| 1 | DATASET_QUICK_REFERENCE.md | ~8K tokens | Training task selection, quick stats |
| 2 | DATASET_PROCESSING_STATUS.md | ~5K tokens | Operational status, blockers |
| 3 | DATASET_CATALOG.md | ~45K tokens | Comprehensive technical details |

**Usage Rule**: Always start with Tier 1, escalate only when needed.

## Operational Scripts

### Metadata Generation & Annotation

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/annotate_base_metadata.py` | Full metadata annotation run | `uv run python scripts/annotate_base_metadata.py --dataset {name}` |
| `scripts/annotate_base_metadata_incremental.py` | Incremental updates | `uv run python scripts/annotate_base_metadata_incremental.py --dataset {name}` |
| `scripts/aggregate_layer2_metadata.py` | Aggregate Layer 2 stats | `uv run python scripts/aggregate_layer2_metadata.py --dataset {name}` |

### Text & Language Processing

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/calculate_text_statistics.py` | Compute text statistics | `uv run python scripts/calculate_text_statistics.py --input {json}` |
| `scripts/enrich_language.py` | Enrich language/script metadata | `uv run python scripts/enrich_language.py --dataset {name}` |
| `scripts/run_language_enrichment.py` | Batch language enrichment | `uv run python scripts/run_language_enrichment.py` |

### Validation & Reporting

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/metadata_completeness_report.py` | Check metadata completeness | `uv run python scripts/metadata_completeness_report.py` |
| `scripts/validate_annotation_output.py` | Validate parser output | `uv run python scripts/validate_annotation_output.py --dataset {name}` |
| `scripts/validate_datasets.py` | Validate dataset structure | `uv run python scripts/validate_datasets.py` |

### GCS & Cloud Operations

| Script | Purpose | Usage |
|--------|---------|-------|
| `deployment/scripts/process_datasets.py` | GCS batch processing | `uv run python deployment/scripts/process_datasets.py` |

## Parser Architecture

```
src/image_preprocessing_detector/annotation/parsers/
├── __init__.py          # Exports and registry
├── base.py              # DatasetParser protocol definition
├── registry.py          # ParserRegistry with explicit registration
├── template.py          # Parser template generator for new datasets
├── generic.py           # Generic fallback parser
├── quality/             # Quality score parsers
│   ├── dibco.py         # DIBCO binarization
│   ├── diqa.py          # DIQA-5000 quality scores
│   ├── ocr_quality.py   # OCR quality reference
│   └── smartdoc.py      # SmartDoc-QA mobile capture
├── layout/              # Layout detection parsers
│   ├── doclaynet.py     # DocLayNet (text extraction example)
│   ├── docsynth300k.py  # DocSynth300K synthetic
│   ├── fintabnet.py     # FinTabNet financial tables
│   ├── funsd.py         # FUNSD forms (text extraction example)
│   ├── funsd_plus.py    # FUNSD+ extended
│   ├── pubtabnet.py     # PubTabNet scientific tables
│   ├── sroie.py         # SROIE receipts
│   └── tablebank.py     # TableBank tables
├── handwriting/         # Handwriting parsers
│   ├── hasyv2.py        # HASYv2 math symbols
│   ├── maths_handwriting.py
│   ├── nist_db2.py      # NIST SD-2 tax forms
│   ├── nist_sd6.py      # NIST SD-6 forms + handprint
│   ├── nist_sd19.py     # NIST SD-19 handwriting
│   ├── pucit_ohul.py    # PUCIT-OHUL Urdu
│   └── signatr.py       # SignaTR6K segmentation
├── multilingual/        # Script/language parsers
│   ├── arabic_docs.py   # Arabic OCR
│   ├── cc_ocr.py        # CC-OCR CJK mixed
│   ├── cocotext.py      # COCO-Text (multilingual example)
│   ├── cvsi.py          # CVSI script classification
│   ├── hiertext.py      # HierText hierarchical
│   ├── hindi_ocr_synthetic.py
│   ├── mdiw13.py        # MDIW-13 scripts
│   ├── mle2e.py         # MLe2e multilingual
│   ├── mlt19.py         # MLT-19 languages
│   ├── multilingual_scripts.py
│   ├── nepali_handwritten.py
│   ├── siw13.py         # SIW-13 scripts
│   ├── tibhcr.py        # Tibetan HCR
│   └── yarmouk.py       # Yarmouk Arabic
├── document/            # Document classification parsers
│   ├── financebench.py  # FinanceBench RAG
│   ├── midv500.py       # MIDV-500 ID documents
│   ├── multimodal_textbook.py
│   ├── ohr_bench.py     # OHR-Bench hallucination
│   ├── omnidocbench.py  # OmniDocBench multi-task
│   ├── realdae.py       # RealDAE enhancement
│   ├── rvl_cdip.py      # RVL-CDIP classification
│   └── tobacco800.py    # Tobacco-800 degraded
└── formula/             # Formula parsers
    └── im2latex.py      # im2latex-100k
```

## Known Gaps (from DATASET_GAPS_REPORT.md)

### Datasets with Both Text + COCO (Most Valuable)

9 datasets: doclaynet, funsd, pubtabnet, fintabnet, cocotext, hiertext, mlt19, sroie, invoices_kaggle

### High Priority Actions

1. **tablebank**: Has COCO layout, needs OCR extraction (278K images)
2. **rvl_cdip**: Has OCR, needs layout extraction (400K images)
3. **iam_handwriting**: Has XML bboxes, needs YOLO conversion (130K images)

### Template Compliance Gaps

- **Section 2 (Source Data Inventory)**: Missing from ALL catalog entries
- **Section 4.1 (Split Coverage)**: Missing from ALL catalog entries
- **Section 7 (Known Issues)**: Missing from ~45 entries

## Naming Convention

- **Canonical Format**: `kebab-case` (lowercase with hyphens)
- **Examples**: `nist-sd2`, `coco-text`, `ohr-bench`
- **Aliases**: Stored in DATASET_REGISTRY under `aliases` field
- **Directory Names**: Must match canonical name exactly

## Layer 2 Schema Key Fields

### Text Content (Required when text available)

```json
{
  "text_content": {
    "full_text": "string (required)",
    "source_type": "enum: ground_truth|ocr_tesseract|ocr_doctr|dataset_provided|...",
    "source_file": "string (optional)",
    "extraction_method": "string (optional)"
  }
}
```

### Source Type Values

| Value | Description |
|-------|-------------|
| `ground_truth` | Original dataset provides verified text |
| `dataset_provided` | Text from dataset annotations (may not be GT) |
| `ocr_tesseract` | Extracted via Tesseract OCR |
| `ocr_doctr` | Extracted via DocTR |
| `ocr_paddleocr` | Extracted via PaddleOCR |
| `transcription` | Human transcription |
| `synthetic` | Programmatically generated |

## Status Icons

| Icon | Meaning |
|------|---------|
| ✅ | Complete/Available |
| ⚠️ | Partial |
| ❌ | Missing/Blocked |
| 🔄 | In Progress |
| 📚 | Text Corpus (non-image) |
| ℹ️ | Not Applicable |

## Documentation Status Markers

| Marker | Meaning |
|--------|---------|
| `[Official]` | From official documentation/paper |
| `[Empirically Derived]` | Computed from actual samples |
| `[Inferred]` | Reasoned from available evidence |
| `[NEEDS_PROFILING]` | Requires empirical analysis |
| `[NEEDS_VERIFICATION]` | Information needs confirmation |

## Data Location Patterns

```text
/mnt/e/image_detection/
├── 01_base_data/           # Training-available images
│   ├── forms/              # Form datasets
│   ├── tables/             # Table datasets
│   ├── handwriting/        # Handwriting datasets
│   ├── language/           # Multilingual datasets
│   ├── documents/          # Document classification
│   └── degraded/           # Degraded document datasets
├── 02_benchmark_only/      # Reserved for evaluation ONLY
├── metadata_registry/      # Layer 2 metadata JSONs
│   └── json/               # Per-dataset JSON files
└── annotations/            # Extracted annotations
    └── {dataset}/
        ├── layout/         # COCO format layout
        ├── ocr/            # Extracted text
        └── ground_truth/   # Original GT if available
```

## Priority Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| P0 | Critical | Required for active training phase |
| P1 | High | Needed within current sprint |
| P2 | Medium | Nice to have, not blocking |
| P3 | Low | Future consideration |
