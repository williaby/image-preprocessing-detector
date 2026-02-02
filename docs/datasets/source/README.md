# Source Dataset Documentation

This directory contains individual markdown files for each dataset in the catalog.

## Purpose

These files are extracted from the master `DATASET_CATALOG.md` to enable:

- Easier navigation and linking to specific datasets
- Better modularity for documentation updates
- Individual dataset versioning if needed
- Reduced file size for LLM context consumption

## Structure

Each file follows the naming convention: `{canonical-name}.md`

Examples:

- `tablebank.md` - TableBank dataset documentation
- `diqa-5000.md` - DIQA-5000 benchmark dataset
- `ohr-bench.md` - OHR-Bench hallucination benchmark

## Canonical Names

All filenames use canonical names from `DATASET_NAMING_STANDARD.md`:

- Lowercase kebab-case format
- No descriptive suffixes (e.g., `dibco.md` not `dibco-document-image-binarization-competition.md`)
- Consistent across codebase, parsers, and metadata

## Generation

These files are automatically generated from `DATASET_CATALOG.md` using:

```bash
python scripts/split_dataset_catalog.py
```

**⚠️ Do not manually edit these files.** Edit the master `DATASET_CATALOG.md` instead, then re-run the script.

## Datasets Extracted

Total: 51 datasets

See `DATASET_NAMING_STANDARD.md` for the complete canonical name registry.

## Excluded

The following section from the catalog was intentionally skipped (not a standalone dataset):

- "Arabic OCR Dataset" (smaller 500-image dataset, not in canonical 51)

The canonical `arabic-docs` dataset refers to the "Arabic Documents OCR Dataset" (10,045 images).
