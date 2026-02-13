# KI-004: LLM Handwriting Detection Unreliable on Synthetic Images

> **Severity**: HIGH | **Status**: PATTERN | **Discovered**: 2026-02-11

## Summary

LLM vision enrichment falsely flags synthetic (typed/rendered) text as containing handwriting. In one case, the word "handwriting" appearing in the text content itself confused the LLM into a false positive.

## Scope

All synthetic datasets processed with LLM vision enrichment.

## Root Cause

LLM vision cannot reliably distinguish between typed/rendered text and handwriting on synthetic images. Two failure modes observed:

1. **Visual confusion**: Clean rendered text misidentified as handwritten
2. **Semantic confusion**: Text content *discussing* handwriting (e.g., the word 手書き in Japanese) triggers false detection

## Evidence

**JSSODa (2,000 images)**:

| Metric | Value |
|--------|-------|
| LLM has_handwriting=True | 4 |
| True positives | 0 |
| False positives | 4 |
| False positive rate | 100% |

Sample details:

- `jssoda_horizontal_00330.png` - All typed text, no handwriting
- `jssoda_horizontal_00484.png` - All typed text, no handwriting
- `jssoda_horizontal_00934.png` - All typed text; word 手書き (handwriting) in content confused LLM
- `jssoda_vertical_00362.png` - All typed text, no handwriting

## Mitigation Pattern

For known synthetic datasets, apply this override in integration scripts:

```python
# KI-004: LLM handwriting detection unreliable on synthetic images
data["has_handwriting"] = False
data["handwriting_present"] = False
# confidence 1.0 because determination is from dataset documentation,
# not from the unreliable LLM detector
```

For mixed datasets (containing both synthetic and real images), VLM verification is required for each `has_handwriting=True` sample.

## Known Synthetic Datasets

- `jssoda`
- `synth-multiscript-250k`
- `docsynth300k`

## Related Files

- `scripts/audit/results/jssoda/vlm_corrections.json` - Per-sample audit trail
- `scripts/integrate_jssoda_enrichments.py` - Override pattern (D07 section)
