---
l4_category: training-dataset
l4_generated: semi
l4_generator: scripts/generate_level4_registries.py
l4_last_generated: PENDING
owner: docs-team
tags:
- architecture
title: 'Level 4: Training Dataset Registry'
---

# Training Dataset Registry

> **Semi-automated** — table auto-generated from `l4_*` front-matter in `docs/datasets/training/*.md`.
> Regenerate with: `python scripts/generate_level4_registries.py --category training-dataset`

This registry catalogs all assembled training datasets used for MobileNetV4 and SigLIP 2
multi-task training. These are distinct from source (raw) datasets — they are assembled,
labeled, and purpose-built for specific ML training tasks.

<!-- AUTO-GENERATED-START -->
<!-- Last generated: 2026-02-23 -->
Total: 10 training datasets.

| Training Dataset | Images | Workstream | Sources | Generation Script | GCS Path | Status |
| ---------------- | ------ | ---------- | ------- | ----------------- | -------- | ------ |
| `capture-method` | 50000 | WS3 | doclaynet, rvl-cdip, smartdoc-qa +3 more | `scripts/prepare_multitask_datasets.py` | `—` | ⛔ |
| `code-detection` | 10000 | WS3 | multimodal-textbook, doclaynet, github-code-snippets | `scripts/generate_code_detection_dataset.py` | `—` | ⛔ |
| `handwriting` | 60000 | WS3 | hiertext, coco-text, iam +3 more | `scripts/harmonize_handwriting_labels.py` | `—` | ⛔ |
| `iqa` | 116000 | WS3 | diqa-5000, ohr-bench, synth-multiscript-v3 | `scripts/prepare_multitask_datasets.py` | `—` | ⛔ |
| `orientation` | 50000 | WS2 | doclaynet, tablebank, pubtabnet +7 more | `scripts/generate_orientation_dataset.py` | `—` | ✅ |
| `resolution-quality` | 30000 | WS2 | diqa-5000, ohr-bench, realdae +1 more | `scripts/label_resolution_quality.py` | `—` | ⛔ |
| `shadow` | 15000 | WS3 | sd7k, wsrd, doc3d +1 more | `scripts/prepare_multitask_datasets.py` | `—` | ⛔ |
| `skew` | 90412 | WS2 | funsd, doclaynet, sroie +10 more | `scripts/generate_skew_dataset.py` | `gs://image_detection_b/skew_training/` | ✅ |
| `synth-multiscript-v3` | 350012 | WS2 |  | `scripts/generate_base_dataset_v3.py` | `gs://image_detection_b/synth_multiscript_v3/` | ✅ |
| `warping` | 20000 | WS3 | doc3d, smartdoc-qa, anyphotodoc6300 +4 more | `scripts/prepare_multitask_datasets.py` | `—` | ⛔ |
<!-- AUTO-GENERATED-END -->

---

## Manual Notes

<!-- MANUAL SECTION — preserved across regenerations -->

### Dataset Overview

The 10 training datasets assembled for SigLIP 2 + MobileNetV4 training:

| Dataset | Target Head | Images | Notes |
|---------|-------------|--------|-------|
| orientation | Orientation 4-class | 50,000 | ✅ Complete — `E:\03_training_datasets\orientation\` |
| skew | Skew regression | 90,412 | ✅ Complete — GCS verified |
| synth-multiscript-v3 | Script detection | 190,485 | ⚠️ Generator bug stopped at 190K, treat as complete |
| resolution-quality | Char-height resolution | ~30,000 | ⚠️ In progress |
| iqa | Image quality assessment | 16K + 100K synth | ⚠️ In progress — IQA Phase 7 165K EXCLUDED (flawed) |
| script | Script classification | 108,000 | ❌ Pending dataset assembly |
| handwriting | Handwriting detection | 60,000 | ❌ Pending |
| capture | Capture method detection | 50,000 | ❌ Pending |
| shadow | Shadow severity | 15,000 | ❌ Pending |
| warping | Warping severity | 20,000 | ❌ Pending |

### Key Training Constraints

- Synthetic mixing cap: ≤60% synthetic per task dataset
- Real data floor for orientation: ≥60% real images
- Global split registry (SHA256-keyed) prevents cross-dataset train/test leakage

### Data Location

- Local (Windows): `E:\03_training_datasets\`
- Modal Volume: `multitask-datasets` at `/data/`
- GCS: `gs://image_detection_b/`
