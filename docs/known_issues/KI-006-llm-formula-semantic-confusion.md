# KI-006: LLM Formula Detection Semantic Confusion

> **Severity**: MEDIUM | **Status**: MANUAL | **Discovered**: 2026-02-11

## Summary

LLM vision enrichment flags text that *discusses* chemistry, mathematics, or science as `has_formula=True` even when no rendered mathematical expressions are visible. The LLM detects semantic references to formulas rather than visual presence of rendered notation.

## Scope

All datasets processed with LLM vision enrichment, particularly those with scientific, educational, or technical content.

## Root Cause

The LLM's formula detection operates at a semantic level rather than a visual level. When text content mentions pH values, chemical compounds, mathematical concepts, or equations in prose form, the LLM flags `has_formula=True` regardless of whether a rendered mathematical expression is actually visible in the image.

## Evidence

**JSSODa (2,000 images)**:

| Metric | Value |
|--------|-------|
| LLM has_formula=True | 6 |
| True positives | 2 |
| False positives | 4 |
| False positive rate | 67% |

True positives (VLM-confirmed):

- `jssoda_horizontal_00537.png` - Visible math: `x = (c - b) / a`
- `jssoda_horizontal_00956.png` - Visible math: `(a+b)^2 = a^2 + 2ab + b^2`

False positives:

- `jssoda_horizontal_00231.png` - Chemistry discussion mentioning pH, no rendered formula
- `jssoda_horizontal_00993.png` - Text about South America, no formulas
- `jssoda_vertical_00031.png` - Vertical text with dark rendering, no formulas
- `jssoda_vertical_00669.png` - Vertical text, no formulas

## Mitigation

LLM `has_formula` should be treated as a candidate signal, not ground truth. For datasets where formula accuracy matters:

1. Collect all samples where LLM reports `has_formula=True`
2. VLM-inspect each to verify a rendered mathematical expression is visible
3. Record true positives in integration script (e.g., `VLM_FORMULA_TRUE_POSITIVES` frozenset)
4. Override remaining to `has_formula=False`

```python
# KI-006: VLM-verified formula true positives
VLM_FORMULA_TRUE_POSITIVES: frozenset[str] = frozenset({
    "sample_id_1",  # description of visible formula
    "sample_id_2",  # description of visible formula
})
data["has_formula"] = filename_stem in VLM_FORMULA_TRUE_POSITIVES
```

## Related Files

- `scripts/audit/results/jssoda/vlm_corrections.json` - Per-sample audit trail
- `scripts/integrate_jssoda_enrichments.py` - VLM_FORMULA_TRUE_POSITIVES pattern
