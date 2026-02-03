# Dataset Infrastructure Handoff Document

> **Created**: 2026-02-02
> **Purpose**: Handoff to incoming team - dataset parsing infrastructure, current state, and open items
> **Branch**: `feat/stream-1-schema-foundation`

---

## Executive Summary

The dataset annotation infrastructure provides parsers that extract structured metadata from 51+ datasets for ML training pipelines. The architecture uses a **BaseParser → OriginalLabels** pattern where each dataset has a specialized parser that reads native annotation formats and maps them to a unified schema.

### Current State

| Metric | Status |
|--------|--------|
| **Total Datasets** | 51 (41 training-ready, 8 in progress, 1 blocked, 1 text corpus) |
| **Parsers Implemented** | 47 parsers across 6 categories |
| **Layer 2 Metadata** | 20/51 datasets have aggregated statistics |
| **Total Training Images** | ~3.35M |

### Recent Work Completed (This Session)

1. ✅ **synth-multiscript-250k parser** - NEW: Reads co-located JSON metadata for 250K synthetic multi-script documents
2. ✅ **jssoda parser** - NEW: Japanese scene text with vertical/horizontal orientation
3. ✅ **pubtabnet text_content enhancement** - MODIFIED: Now extracts text from cell tokens (filtering HTML tags)
4. ✅ **Dataset config updated** - Added synth-multiscript-250k to DATASET_CONFIGS
5. ✅ **Registry updated** - Both new parsers registered in multilingual/**init**.py

---

## Architecture Overview

### Parser Protocol Pattern

```
src/image_preprocessing_detector/annotation/parsers/
├── base.py                 # BaseParser abstract class
├── registry.py             # ParserRegistry for dynamic lookup
├── generic.py              # Fallback parser
├── template.py             # Parser template for new implementations
├── layout/                 # Table/layout parsers (doclaynet, pubtabnet, fintabnet, etc.)
├── multilingual/           # Script/language parsers (mlt19, cvsi, synth_multiscript, etc.)
├── handwriting/            # Handwriting parsers (nist_*, hasyv2, etc.)
├── document/               # Document type parsers (rvl_cdip, midv500, etc.)
├── quality/                # IQA parsers (dibco, diqa, ocr_quality)
└── formula/                # Formula parsers (im2latex)
```

### Key Files

| File | Purpose | Location |
|------|---------|----------|
| **BaseParser** | Abstract base class defining `parse()` interface | [parsers/base.py](src/image_preprocessing_detector/annotation/parsers/base.py) |
| **OriginalLabels** | Immutable dataclass for parser output | [schemas/immutable.py](src/image_preprocessing_detector/annotation/schemas/immutable.py) |
| **DatasetConfig** | Per-dataset configuration | [config/datasets.py](src/image_preprocessing_detector/annotation/config/datasets.py) |
| **ParserRegistry** | Dynamic parser lookup by dataset name | [parsers/registry.py](src/image_preprocessing_detector/annotation/parsers/registry.py) |

### Parser Implementation Pattern

```python
class ExampleParser(BaseParser):
    @property
    def dataset_names(self) -> list[str]:
        """Return all dataset name aliases this parser handles."""
        return ["example-dataset", "example_dataset", "example"]

    def parse(
        self,
        dataset_path: Path,
        image_path: Path,
        config: dict[str, Any],
    ) -> OriginalLabels:
        """Parse annotations for a single image."""
        labels = OriginalLabels()
        labels.raw_labels = {}

        # Read native annotation format
        # Map to OriginalLabels fields
        # Return populated labels

        return labels
```

---

## Documentation Structure

### Tier System (Read in Order of Need)

| Tier | Document | Purpose | When to Read |
|------|----------|---------|--------------|
| **1** | [DATASET_QUICK_REFERENCE.md](docs/datasets/DATASET_QUICK_REFERENCE.md) | Training task selection, quick stats | START HERE for dataset questions |
| **2** | [DATASET_PROCESSING_STATUS.md](docs/datasets/DATASET_PROCESSING_STATUS.md) | Conversion/extraction status | Current state queries |
| **3** | [DATASET_NAMING_STANDARD.md](docs/datasets/DATASET_NAMING_STANDARD.md) | Canonical names, aliases | Name resolution |
| **4** | [docs/datasets/source/](docs/datasets/source/) | Per-dataset deep documentation | Specific dataset details |
| **5** | [docs/datasets/indices/](docs/datasets/indices/) | Task-based training recipes | Training task selection |

### Audit/Gap Reports

| Document | Purpose | Location |
|----------|---------|----------|
| **Gaps Report** | Missing images/text/COCO annotations per dataset | [docs/planning/DATASET_GAPS_REPORT.md](docs/planning/DATASET_GAPS_REPORT.md) |
| **Reconciliation Report** | GCS/E: drive alignment, naming inconsistencies | [docs/DATA_PREP_RECONCILIATION_REPORT.md](docs/DATA_PREP_RECONCILIATION_REPORT.md) |

---

## Open Items by Priority

### P0 - Critical (Blocks Training)

#### 1. Complete synth-multiscript-250k Generation

**Status**: 27K/250K generated (10.8%)
**Impact**: Blocks SigLIP script detection training
**Details**: [DATA_PREP_RECONCILIATION_REPORT.md § Section 4](docs/DATA_PREP_RECONCILIATION_REPORT.md#section-4-synthetic-250k-generation-status)

```bash
# Resume generation
python scripts/generate_dataset_parallel.py \
  --dataset synth-multiscript-250k \
  --output /mnt/e/image_detection/03_training_datasets/synthetic_multiscript/ \
  --resume --workers 4
```

#### 2. ohr-bench Parquet→PNG Conversion

**Status**: Parquet exists (2.1GB), images not extracted
**Impact**: IQA training baseline dataset
**Details**: [DATASET_PROCESSING_STATUS.md § In Progress](docs/datasets/DATASET_PROCESSING_STATUS.md)

```bash
python scripts/convert_parquet_to_images.py \
  --input /path/to/ohr-bench.parquet \
  --output /mnt/e/image_detection/02_benchmark_only/ohr-bench/ \
  --format png
```

---

### P1 - High (Significant Training Value)

#### 3. cocotext Parquet→JPG Conversion

**Status**: 800/63,686 images (1.3%)
**Impact**: Large scene text dataset for text detection gate
**Location**: [DATA_PREP_RECONCILIATION_REPORT.md § Section 2.1](docs/DATA_PREP_RECONCILIATION_REPORT.md#21-datasets-needing-parquet--image-conversion)

#### 4. iam_handwriting Parquet→PNG Conversion

**Status**: Parquet exists (~5GB), 130K images
**Impact**: Largest handwriting corpus
**Note**: XML bboxes available, need YOLO format conversion

#### 5. TableBank OCR Extraction

**Status**: Has COCO layout (278K images), NO text
**Impact**: Table text extraction for training
**Details**: [DATASET_GAPS_REPORT.md § Section 6](docs/planning/DATASET_GAPS_REPORT.md#6-recommended-actions-priority-order)

#### 6. rvl_cdip Layout Extraction

**Status**: Has extracted OCR (16K docs), NO COCO layout
**Impact**: Largest document classification dataset (400K images)

---

### P2 - Medium (Parser Enhancements)

#### 7. nist-sd6 text_content Enhancement

**Status**: Parser exists but doesn't extract text_content
**Effort**: ~30 minutes
**File**: [parsers/handwriting/nist_sd6.py](src/image_preprocessing_detector/annotation/parsers/handwriting/nist_sd6.py)
**Pattern**: Follow fintabnet/pubtabnet text_content pattern

#### 8. ohr-bench text_content Enhancement

**Status**: Parser exists, text_content not extracted
**Effort**: ~2 hours
**File**: [parsers/document/ohr_bench.py](src/image_preprocessing_detector/annotation/parsers/document/ohr_bench.py)

#### 9. cc_ocr Parser Fix

**Status**: TSV files have text in `answer` column, parser may not extract
**Details**: [DATASET_GAPS_REPORT.md § Section 8](docs/planning/DATASET_GAPS_REPORT.md#cc-ocr--has-text-labels)
**File**: [parsers/multilingual/cc_ocr.py](src/image_preprocessing_detector/annotation/parsers/multilingual/cc_ocr.py)

#### 10. Missing Dataset Downloads

**Datasets**: lrde-dbd (375 images), sleukrith-ocr (657 pages)
**Details**: [DATASET_PROCESSING_STATUS.md § Blockers](docs/datasets/DATASET_PROCESSING_STATUS.md#current-blockers)

---

### P3 - Low (Future Improvements)

#### 11. DocSynth300K Processing

**Status**: 300K synthetic images in parquet (15GB+)
**Impact**: Large but synthetic - lower training value
**Note**: Use chunked processing

#### 12. muharaf PAGE XML→YOLO Conversion

**Status**: Has PAGE XML polygons, needs YOLO bbox conversion
**Details**: [DATASET_GAPS_REPORT.md § Short-term](docs/planning/DATASET_GAPS_REPORT.md#short-term)

#### 13. Naming Inconsistencies

**Issue**: E: drive folder names don't match GCS/metadata names
**Fix**: Rename folders per [DATA_PREP_RECONCILIATION_REPORT.md § Section 1.3](docs/DATA_PREP_RECONCILIATION_REPORT.md#13-naming-inconsistencies)

---

## Implementation Reference

### Adding a New Parser

1. **Create parser file** in appropriate category folder
2. **Implement BaseParser** with `dataset_names` property and `parse()` method
3. **Register in `__init__.py`** of the category module
4. **Add to DATASET_CONFIGS** in [config/datasets.py](src/image_preprocessing_detector/annotation/config/datasets.py)
5. **Test** with sample images

**Template**: [parsers/template.py](src/image_preprocessing_detector/annotation/parsers/template.py)

### Common Label Fields (OriginalLabels)

| Field | Type | Description |
|-------|------|-------------|
| `language_code` | str | ISO 639 language code (e.g., "en", "ja") |
| `script_name` | str | Script name (e.g., "Latin", "Japanese") |
| `iso15924_script_code` | str | ISO 15924 code (e.g., "Latn", "Jpan") |
| `raw_labels` | dict | Dataset-specific metadata |
| `text_content` | dict | Extracted text with provenance |
| `layout_detections` | list | COCO-format bboxes `[x, y, w, h]` |
| `capture_method` | dict | born_digital/scanner/camera |
| `domain` | dict | FIN/SCI/TAX/EDU/etc. |
| `content_flags` | dict | has_table/has_formula/has_handwriting |

### Example: Recent pubtabnet Enhancement

```python
# Filter HTML tags from cell tokens
text_tokens = [
    t for t in cell["tokens"]
    if not (t.startswith("<") or t.endswith(">"))
]
# Join without spaces (tokens are individual chars)
cell_text = "".join(text_tokens)

# Set text_content with provenance
labels.text_content = {
    "full_text": " ".join(all_text),
    "source_type": "dataset_provided",
    "source_format": "jsonl_cell_tokens",
    "extraction_method": "PubTabNetParser.parse",
    ...
}
```

---

## Storage Locations

| Location | Purpose | Size |
|----------|---------|------|
| `/mnt/e/image_detection/01_base_data/` | Training datasets | ~420 GB |
| `/mnt/e/image_detection/02_benchmark_only/` | Benchmark-only (reserved test sets) | ~80 GB |
| `/mnt/e/image_detection/03_training_datasets/` | Augmented/synthetic datasets | ~165 GB |
| `/mnt/e/image_detection/metadata_registry/json/` | Layer 2 JSON metadata | ~2.2 GB |
| `gs://image_detection_b/` | GCS mirror | ~600 GB |

---

## Key Commands

```bash
# Run tests
uv run pytest tests/unit/annotation/ -v

# Type checking
uv run basedpyright src/image_preprocessing_detector/annotation/

# Lint and format
uv run ruff check --fix src/image_preprocessing_detector/annotation/
uv run ruff format src/image_preprocessing_detector/annotation/

# Run metadata annotation
python scripts/annotate_base_metadata.py --dataset <dataset_name> --verbose

# Convert parquet to images
python scripts/convert_parquet_to_images.py --input <path> --output <path> --format png
```

---

## Contact & Resources

- **Repository**: `/home/byron/dev/image_detection`
- **Branch**: `feat/stream-1-schema-foundation`
- **Git Status**: Multiple modified/untracked files (see `git status`)
- **Project Plan**: [docs/planning/PROJECT_PLAN.md](docs/planning/PROJECT_PLAN.md)
- **Architecture**: [docs/architecture/](docs/architecture/)

---

## Appendix: Parser Inventory

### Implemented Parsers (47 total)

| Category | Parsers | Files |
|----------|---------|-------|
| **Layout** | doclaynet, pubtabnet, fintabnet, tablebank, funsd, funsd_plus, sroie, docsynth300k, invoices_kg | 9 |
| **Multilingual** | arabic_docs, cc_ocr, cocotext, cvsi, hiertext, hindi_ocr_synthetic, jssoda, mdiw13, mle2e, mlt19, multilingual_scripts, nepali_handwritten, siw13, synth_multiscript, tibhcr, yarmouk | 16 |
| **Handwriting** | hasyv2, maths_handwriting, nist_db2, nist_sd6, nist_sd19, pucit_ohul, signatr | 7 |
| **Document** | financebench, midv500, multimodal_textbook, ohr_bench, omnidocbench, realdae, rvl_cdip, tobacco800 | 8 |
| **Quality** | dibco, diqa, ocr_quality, smartdoc | 4 |
| **Formula** | im2latex | 1 |
| **Base/Utility** | base, generic, registry, template | 4 |

### Recently Modified (This Session)

| File | Change |
|------|--------|
| `parsers/multilingual/synth_multiscript.py` | NEW - 250K synthetic multi-script |
| `parsers/multilingual/jssoda.py` | NEW - Japanese scene text |
| `parsers/multilingual/__init__.py` | Added new parser imports/registration |
| `parsers/layout/pubtabnet.py` | Enhanced text_content extraction |
| `config/datasets.py` | Added synth-multiscript-250k config |

---

*Document generated: 2026-02-02*
*Author: Claude Code (automated handoff generation)*
