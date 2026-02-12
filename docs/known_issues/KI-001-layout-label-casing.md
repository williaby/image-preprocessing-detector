# KI-001: Docling Layout Label Casing Mismatch

> **Severity**: CRITICAL | **Status**: AUTOMATED | **Discovered**: 2026-02-11

## Summary

Docling layout extractor outputs `class_name` in lowercase/snake_case (`text`, `list_item`, `section_header`). The Layer 2 schema expects DocLayNet PascalCase (`Text`, `List-Item`, `Section-Header`). This mismatch causes 100% prescreening failure on the `layout_detections` field for every dataset processed with Docling.

## Scope

All 51 datasets using Docling layout extraction (both DocLayout-YOLO and Docling Egret-XLarge models).

## Root Cause

Docling uses its own 17-class label schema with lowercase/snake_case naming. The Layer 2 enrichment schema standardized on DocLayNet's 11-class PascalCase taxonomy. The Docling provider (`docling_layout.py`) maps model output to Docling keys but does not convert to DocLayNet PascalCase when writing `class_name` to metadata.

## Evidence

| Docling Output | Expected DocLayNet | Canonical |
|----------------|-------------------|-----------|
| `text` | `Text` | `TEXT` |
| `list_item` | `List-Item` | `LIST_ITEM` |
| `section_header` | `Section-Header` | `SECTION_HEADER` |
| `table` | `Table` | `TABLE` |
| `picture` | `Picture` | `PICTURE` |
| `formula` | `Formula` | `FORMULA` |
| `page_header` | `Page-Header` | `PAGE_HEADER` |
| `page_footer` | `Page-Footer` | `PAGE_FOOTER` |
| `caption` | `Caption` | `CAPTION` |
| `footnote` | `Footnote` | `FOOTNOTE` |
| `title` | `Title` | `TITLE` |

Observed on JSSODa (2,000/2,000 samples affected = 100%).

## Fix

Run `scripts/standardize_layout_labels.py --dataset <name>` before any integration script.

The script (updated 2026-02-11) now writes per detection:

- `source_label`: Preserves original Docling label
- `class_name`: Converted to DocLayNet PascalCase
- `canonical_class`: UPPERCASE canonical form
- `source_schema`: Source schema identifier
- `is_lossy`: Whether conversion loses information
- `conversion_confidence`: 1.0 for lossless, 0.0 for lossy

```bash
# Dry run
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/standardize_layout_labels.py --dataset <name> --dry-run

# Apply
PYTHONPATH=/home/byron/dev/image_detection:$PYTHONPATH \
    uv run python3 scripts/standardize_layout_labels.py --dataset <name>
```

## Related Files

- `scripts/standardize_layout_labels.py` - Automated fix script
- `config/layout_taxonomy.yaml` - Canonical label taxonomy
- `src/image_preprocessing_detector/schema_utils/layout_taxonomy.py` - Taxonomy module
