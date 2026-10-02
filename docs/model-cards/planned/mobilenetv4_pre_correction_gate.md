---
owner: core-maintainer
purpose: 'Model card for the MobileNetV4-Conv-S pre-correction gate (trained, not yet integrated).'
schema_type: common
status: draft
tags:
- machine_learning
- skew_detection
- model_registry
- licensing
title: 'Model Card: MobileNetV4-Conv-S Pre-Correction Gate'
---

> **Status: TRAINED, NOT INTEGRATED.** A checkpoint exists, but it is not wired into the main
> pipeline (stream 4D). Inference code (`models/skew_estimator.py`,
> `detection/deskew_pipeline.py`) is reachable only from the CLI, and no exported `.onnx` is
> committed to `models/`.

## Model Summary

| Field | Value |
| --- | --- |
| Architecture | MobileNetV4-Conv-Small, 224 px input (~3 ms/page GPU target) |
| Heads | Orientation (4-class: 0/90/180/270), fine skew (regression, ±10°, signed, positive = clockwise), resolution quality (0–1; head training pending) |
| Role | Stage 1 gate: rotate (confidence > 0.9), deskew (\|angle\| > 0.3°), upscale (resolution quality < 0.4) *before* SigLIP 2 |
| Checkpoint | Epoch 47, run `20260212_155402` (`modal/train_skew_estimator.py`) |
| Reported (validation) | Orientation accuracy 99.5%, skew MAE 0.837° |
| Training data | Orientation 50K images (4-class balanced); skew 90,412 images (71K synthetic + 19K natural) |
| Not yet evaluated | OOD abstention (planned: Energy Score, not raw softmax); non-Latin coverage is under 1% of training data; the skew set is ~79% synthetic (71K of 90K) versus a ≤37.5% target cap |
| Maintainer | Byron Williams |

## License

**Released weights: CC-BY-SA-4.0** (decision 2026-10-01; `REUSE.toml` applies it to
`models/**`). Training data for this model is a mix of generated and source datasets; **TBD:
append per-license-class counts for the orientation and skew sets before release** (skew
dataset provenance in `SKEW_NATURAL_SCAN_STRATIFICATION.md`; orientation in
`MOBILECLIP2_S4_S0_DATASET_DESIGN.md`). Datasets that are non-commercial, GPL or unspecified
must not be in the production training set; research-terms-only datasets are an open decision
(see the SigLIP 2 card).

## Intended Use and Limitations

Fast correction gate so that SigLIP 2's heads see upright, deskewed, adequately sized images.
Known limitations: symmetric documents are ambiguous between 0° and 180° (no training
coverage), multi-column skew is not validated, the narrow-range (±2°) skew regime has no
dataset, and the resolution-quality head lacks the pre-upscaled-raster confound set.
