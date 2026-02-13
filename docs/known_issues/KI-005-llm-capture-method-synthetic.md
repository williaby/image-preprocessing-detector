# KI-005: LLM Cannot Detect Synthetic Capture Method

> **Severity**: HIGH | **Status**: PATTERN | **Discovered**: 2026-02-11

## Summary

LLM vision enrichment classifies synthetic images as `born_digital` or `scanner_flatbed` instead of `synthetic`. The LLM has 0% accuracy on synthetic capture method detection.

## Scope

All synthetic datasets processed with LLM vision enrichment.

## Root Cause

LLM vision has no reliable way to distinguish clean synthetic renders from high-quality born-digital documents. Both appear as crisp, artifact-free rendered text with no scanner noise, camera distortion, or other physical capture artifacts.

## Evidence

**JSSODa (2,000 images)**:

| Metric | Value |
|--------|-------|
| LLM predictions | 100% misclassified as `born_digital` or `scanner_flatbed` |
| Correct value | `synthetic` (from dataset documentation) |
| LLM accuracy | 0% |

## Mitigation Pattern

For known synthetic datasets, override `capture_method` from dataset documentation:

```python
# KI-005: LLM cannot detect synthetic capture method
data["capture_method"] = "synthetic"
data["capture_method_confidence"] = 1.0
data["capture_method_source"] = "dataset_documentation"
```

Do NOT use the LLM-predicted value for synthetic datasets.

## Known Synthetic Datasets

- `jssoda` - Japanese synthetic OCR dataset
- `synth-multiscript-250k` - Multi-script synthetic dataset
- `docsynth300k` - DocSynth300K synthetic dataset

## Related Files

- `scripts/integrate_jssoda_enrichments.py` - Override pattern (D02 section)
- `scripts/audit/results/CROSS_DATASET_KNOWN_ISSUES.json` - Machine-readable advisory
