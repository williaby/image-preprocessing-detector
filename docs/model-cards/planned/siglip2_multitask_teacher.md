---
owner: core-maintainer
purpose: 'Model card for the SigLIP 2 NAFlex multi-task teacher (training not yet run).'
schema_type: common
status: draft
tags:
- machine_learning
- multi_task
- iqa
- model_registry
- licensing
title: 'Model Card: SigLIP 2 NAFlex Multi-Task Teacher'
---

> **Status: PLANNED. No trained weights exist.** The training script
> (`modal/train_siglip2_multitask.py`) is ready; dataset assembly is in progress
> (see [RUNSHEET_DATA_ASSEMBLY.md](../../planning/RUNSHEET_DATA_ASSEMBLY.md)).
> Every metric field below is intentionally `TBD`; do not fill in numbers until a
> trained checkpoint is evaluated on held-out and OOD data.

## Model Summary

| Field | Value |
| --- | --- |
| Model ID | `siglip2-multitask-teacher` (version TBD at first release) |
| Backbone | SigLIP 2 NAFlex, ~88M parameters (~50 ms/page GPU target) |
| Heads (Release 1) | 16, across Group 1 IQA (3 regression: overall, sharpness, color), Group 2 Script, Group 3 Orientation (+ skew), Group 5 Page Attributes |
| Deferred to Release 2 | Group 4 Handwriting (5 heads) and narrow-range skew (SIG-G3-2) |
| Role | Multi-task teacher: Stage 2 analysis after the MobileNetV4 pre-correction gate; teacher for MobileCLIP-2 S4 → S0 distillation |
| Training | Kendall uncertainty weighting + PCGrad; two phases (frozen backbone heads-only, then full fine-tune) |
| Evaluation | TBD (go/no-go trigger for API work: mAP > 0.88 on holdout) |
| Maintainer | Byron Williams |

## License

**Released weights: CC-BY-SA-4.0** (decision 2026-10-01; see
[MASTER_PROJECT_PLAN.md](../../planning/MASTER_PROJECT_PLAN.md), Tier 0). The project
license is already CC-BY-SA-4.0; `REUSE.toml` applies the same license to `models/**`.

This satisfies the share-alike terms of CC-BY-SA training data (kuzushiji, hiertext,
midv2020). It does not by itself resolve the status of data under other terms:

| Class | Policy for the production model |
| --- | --- |
| permissive, public domain, share-alike, our own generated data | Eligible |
| non-commercial (e.g. wsrd), GPL (e.g. anyphotodoc6300), unspecified (e.g. warpdoc, docalign12k) | **Excluded** from training; evaluation/calibration use only |
| research-terms-only (e.g. rvl-cdip, mdiw13, smartdoc-qa, realdae) | **OPEN DECISION** (`LICENSE_IMPACT_REPORT.md` rates these high risk for a public release). This card must be updated with the outcome before release |

Every training-manifest record carries `license` and `license_class`
(`schema_utils/dataset_license.py`), and `prepare_multitask_datasets.py merge
--exclude-license-class` can filter by class, so the final training set's license mix can be
reported exactly. **Before release, append the per-class record counts of the
manifests actually used.**

Pseudo-labels: IQA labels for the corpus come from DeQA-Doc (mPLUG-Owl2-7B). **TBD: confirm
that DeQA-Doc / mPLUG-Owl2 output terms permit use as training labels for a CC-BY-SA model.**

## Training Data

Planned task manifests: `script`, `orientation`, `source`, `shadow`, `warping`, plus IQA
pseudo-labels (gate: ≥125K images with IQA labels). Mixing caps: script ≤60% synthetic,
orientation ≤40%, shadow ≤50%, warping ≤30% (currently warnings, not enforced).

Reserved out-of-distribution (never trained on): scripts Armn, Geor, Goth, Mong, Syrc, and the
OOD registry (`metadata_registry/ood_registry.jsonl`; leak check run at manifest build).

## Intended Use and Limitations

Intended: document-image quality assessment, script / orientation / page-attribute prediction
that feeds Prepare-Doc corrections and Unify routing metadata.

Known gaps (from `WILD_CONDITIONS_ANALYSIS.md`): overall wild-condition coverage is low
(2 of 60 conditions fully covered across heads); handwriting, non-Latin cursive, ADF-scanner
artifacts and screen-recapture/moire are not covered in Release 1; 5 heads have zero labeled
OOD images. Warping severity labels are calibrated to the warpdoc `1 - SSIM` scale (doc3d
backward-map method); shadow severity labels are SSIM-based. Evaluation must use the corrected
OOD metrics (Energy Score for abstention) recorded in the master plan.

## Provenance

Architecture and head definitions: `modal/train_siglip2_multitask.py`,
`config/siglip2_multitask.yaml`, [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md).
