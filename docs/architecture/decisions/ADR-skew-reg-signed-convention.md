# ADR: SIG-G3-2 Skew Regression — Signed Angle Convention

> **Status**: ✅ Accepted
> **Date**: 2026-02-24
> **Defect Reference**: Defect 3 in [TRAINING_DATA_STRATEGIC_ANALYSIS.md](../../planning/TRAINING_DATA_STRATEGIC_ANALYSIS.md)
> **HAR Reference**: [sig-g3-skew-reg.md](../../planning/har/sig-g3-skew-reg.md) §7 (Cross-Head Consistency)

---

## Context

SIG-G3-2 (`skew_reg`) estimates residual post-correction skew on corrected images. MNV4-H2 also
estimates skew (on raw images, pre-correction). Both heads share the same 90K assembled skew
training dataset. The design intent for the sign convention of SIG-G3-2 was previously
undocumented, creating ambiguity: `abs(skew_angle)` appears in `deskew_pipeline.py` and
triggered concern that unsigned angles might be used as training targets.

---

## Decision

SIG-G3-2 (`skew_reg`) uses **signed skew angles**, identical to MNV4-H2:

- **Sign convention**: positive = clockwise tilt (from vertical)
- **Training range**: ±10° (synthetic component); natural scans up to ±45° at inference
- **Label field**: `skew_angle` in training manifests (already signed in `generate_skew_dataset.py`)
- **No `abs()` in training**: the `abs_angle = abs(skew_angle)` in `deskew_pipeline.py:289` is
  an inference-time threshold check, not a label derivation

---

## Loss Function

Gaussian NLL (`gaussian_nll`) is mandated over SmoothL1 for this head. Rationale (SKEW-SIG-G04):

- The assembled dataset mixes synthetic (tier_0_exact, ±0.0° noise) and natural scans
  (tier_1_classical, ~±0.9° noise floor)
- SmoothL1 treats all samples equally, causing natural scan noise to corrupt gradients on precise
  synthetic labels
- Gaussian NLL allows the model to predict per-sample uncertainty (μ, σ²): it learns low σ for
  synthetic labels and high σ for natural scans, automatically downweighting uncertain samples

---

## Data Loader Implementation

```python
# In modal/train_siglip2_multitask.py — MultiTaskDataset label parsing
if "skew_angle" in entry:
    sample["labels"]["skew_reg"] = float(entry["skew_angle"])  # signed, no abs()
    sample["task_masks"]["skew_reg"] = 1
```

---

## Convention Alignment Requirement

The label field `skew_angle` and its sign convention **must remain identical** in both the MNV4-H2
training dataset and the SIG-G3-2 training dataset. Convention drift between the two heads is
prohibited. Any future augmentation or re-labeling pass must preserve this alignment.

---

## References

- [sig-g3-skew-reg.md §7](../../planning/har/sig-g3-skew-reg.md) — Cross-head consistency
- [sig-g3-skew-reg.md SKEW-SIG-G04](../../planning/har/sig-g3-skew-reg.md) — Loss function gap
- `scripts/generate_skew_dataset.py:528` — signed `skew_angle` label emission (verified)
- `src/image_preprocessing_detector/detection/deskew_pipeline.py:289` — `abs_angle` is
  inference threshold only; not involved in training label derivation
