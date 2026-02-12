# KI-003: Docling Picture Detection on Dense Text

> **Severity**: MEDIUM | **Status**: MANUAL | **Discovered**: 2026-02-11

## Summary

Docling's layout models classify dense text blocks or dark rendering artifacts as `Picture`, producing false positive `has_figure` content flags.

## Scope

Synthetic datasets with dense text blocks, dark background rendering, or vertical text. Potentially affects scanned documents with poor contrast.

## Root Cause

Dense text regions or unusual rendering (dark backgrounds, tightly packed vertical text blocks) trigger the Picture classifier. The model interprets large dark/dense regions as images rather than text.

## Evidence

**JSSODa (2,000 images)**:

| Metric | Value |
|--------|-------|
| Total Picture detections (flagged) | 3 |
| True positives | 0 |
| False positives | 3 |
| False positive rate | 100% |

Sample details:

- `jssoda_horizontal_00537.png` - Text with math expressions, no figure
- `jssoda_vertical_00794.png` - Vertical text about a city, no figure
- `jssoda_vertical_00911.png` - Dense vertical text with dark rendering, no figure

## Mitigation

1. VLM-inspect all samples where `has_figure=True` on synthetic datasets
2. Override false positives in integration scripts
3. Lower confidence for figure detection on text-heavy synthetic documents

## Related Files

- `scripts/audit/results/jssoda/vlm_corrections.json` - Per-sample audit trail
- `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json` - Machine-readable advisory
