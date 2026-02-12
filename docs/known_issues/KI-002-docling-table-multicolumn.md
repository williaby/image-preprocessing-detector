# KI-002: Docling Table Detection on Multi-Column Text

> **Severity**: HIGH | **Status**: MANUAL | **Discovered**: 2026-02-11

## Summary

Docling's layout models (both Egret-XLarge and DocLayout-YOLO) classify multi-column text regions as `Table`, producing false positive `has_table` content flags. On JSSODa, 10/10 Table detections were false positives caused by multi-column text layouts.

## Scope

- Synthetic datasets with multi-column text layouts (confirmed)
- Scanned/born-digital multi-column documents (likely, untested)
- Any dataset processed through Docling layout extraction

## Root Cause

Neither layout model was trained to distinguish "multi-column text" from "table". Both DocLayNet and Docling taxonomies treat `Table` as a class for spatially structured rectangular content. Multi-column text creates a grid-like visual pattern (regular column widths, consistent spacing) that triggers the Table classifier.

## Evidence

**JSSODa (2,000 images)**:

| Metric | Value |
|--------|-------|
| Total Table detections | 10 |
| True positives | 0 |
| False positives | 10 |
| False positive rate | 100% |

All 10 false positives were horizontal text images with 2-4 columns. None contained actual tabular data (headers, rows, cells, ruled lines). VLM visual inspection confirmed all 10.

Detailed per-sample audit: `scripts/audit/results/jssoda/vlm_corrections.json`

## Impact on Content Flags

When `has_table` is derived from layout detections via `derive_content_flags()`, any Table detection sets `has_table=True`. This propagates the false positive into Layer 2 metadata.

**Current mitigation**: Integration scripts for synthetic datasets override `has_table` based on VLM corrections. See `scripts/integrate_jssoda_enrichments.py` for the pattern.

## Impact on Text Extraction (KI-008)

This issue has a much deeper impact when Docling is used for full text extraction (OCR). See [KI-008](KI-008-docling-multicolumn-text-extraction.md) for the full analysis of how Table misclassification corrupts reading order and text output.

## Mitigation

**For content flags** (Layer 2 metadata):

1. Run integration with `derive_content_flags()` as baseline
2. VLM-inspect all samples where `has_table=True`
3. Override false positives in integration script
4. Record corrections in `vlm_corrections.json`

**For text extraction** (Docling OCR pipeline):

See [KI-008](KI-008-docling-multicolumn-text-extraction.md) for proposed fixes.

## Affected Datasets (Known/Likely)

- `jssoda` (confirmed, 100% FP rate)
- `synth-multiscript-250k` (likely, synthetic multi-column)
- `docsynth300k` (likely, synthetic)
- Any dataset with multi-column document layouts

## Related Files

- `scripts/audit/results/jssoda/vlm_corrections.json` - Per-sample audit trail
- `scripts/integrate_jssoda_enrichments.py` - Override pattern (D07 section)
- `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json` - Machine-readable advisory
