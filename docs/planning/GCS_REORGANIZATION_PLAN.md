---
schema_type: planning
title: GCS Bucket Reorganization Plan
description: Align GCS structure with local E drive organization
status: draft
owner: core-maintainer
purpose: Reorganize GCS bucket structure to align with local E drive organization.
component: Development-Tools
source: Manual creation
---

> **Bucket**: `gs://image_detection_b/`

---

## Current GCS Structure

```text
gs://image_detection_b/
├── configs/
├── datasets/
│   ├── benchmarks/
│   │   ├── diqa-5000/
│   │   └── smartdoc-qa/
│   ├── im2latex_100k/
│   ├── mathverse/
│   ├── phase2/
│   ├── phase7_mvp/
│   └── phase7_v3_clean/
├── image-preprocessing-detector/
│   └── datasets/
│       ├── cocotext/
│       ├── doclaynet/
│       ├── docsynth300k/
│       ├── fintabnet/
│       ├── funsd/
│       ├── iam_handwriting/
│       ├── invoices_kaggle/
│       ├── iqa_phase2/
│       ├── iqa_phase2_100k/
│       ├── mobile_receipts_voxel51/
│       ├── nist_db2/
│       ├── ohr_bench/
│       ├── omnidocbench/
│       ├── pubtabnet/
│       ├── receipts_hitl/
│       ├── signatr6k/
│       ├── synthetic_iqa/
│       ├── tablebank/
│       └── wili_2018/
├── models/
└── training/
```

---

## Target GCS Structure (Aligned with Local)

```text
gs://image_detection_b/
├── 01_base_data/
│   ├── tables/
│   │   ├── tablebank/
│   │   ├── pubtabnet/
│   │   └── fintabnet/
│   ├── documents/
│   │   ├── doclaynet/
│   │   └── rvl_cdip/
│   ├── forms/
│   │   ├── nist_db2/
│   │   ├── nist_sd6/
│   │   ├── funsd/
│   │   ├── funsd_plus/
│   │   └── sroie/
│   ├── handwriting/
│   │   ├── nist_sd19_pages/
│   │   ├── maths_handwriting/
│   │   ├── signatr6k/
│   │   └── iam_handwriting/
│   ├── formulas/
│   │   ├── im2latex/
│   │   └── mathverse/
│   ├── educational/
│   │   └── multimodal_textbook/
│   ├── degraded/
│   │   ├── tobacco800/
│   │   └── historical_degraded/
│   ├── text_detection/
│   │   └── cocotext/
│   └── language/
│       └── wili_2018/
├── 02_benchmark_only/
│   ├── diqa-5000/
│   ├── dibco/
│   ├── ohr-bench/
│   ├── omnidocbench/
│   └── smartdoc-qa/
├── 03_training_datasets/
│   ├── phase2_100k/
│   ├── phase7_v3/
│   └── phase7_v4/
├── 04_checkpoints/
├── 05_models/
├── configs/
└── legacy/                    # Old structure (to be deleted after verification)
    └── image-preprocessing-detector/
```

---

## Migration Commands

### Phase 1: Create New Structure and Copy Data

```bash
# Tables
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/tablebank/ gs://image_detection_b/01_base_data/tables/
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/pubtabnet/ gs://image_detection_b/01_base_data/tables/
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/fintabnet/ gs://image_detection_b/01_base_data/tables/

# Documents
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/doclaynet/ gs://image_detection_b/01_base_data/documents/

# Forms
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/nist_db2/ gs://image_detection_b/01_base_data/forms/
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/funsd/ gs://image_detection_b/01_base_data/forms/

# Handwriting
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/signatr6k/ gs://image_detection_b/01_base_data/handwriting/
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/iam_handwriting/ gs://image_detection_b/01_base_data/handwriting/

# Formulas
gsutil -m cp -r gs://image_detection_b/datasets/im2latex_100k/ gs://image_detection_b/01_base_data/formulas/im2latex/
gsutil -m cp -r gs://image_detection_b/datasets/mathverse/ gs://image_detection_b/01_base_data/formulas/

# Text Detection
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/cocotext/ gs://image_detection_b/01_base_data/text_detection/

# Language
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/wili_2018/ gs://image_detection_b/01_base_data/language/

# Benchmarks
gsutil -m cp -r gs://image_detection_b/datasets/benchmarks/diqa-5000/ gs://image_detection_b/02_benchmark_only/
gsutil -m cp -r gs://image_detection_b/datasets/benchmarks/smartdoc-qa/ gs://image_detection_b/02_benchmark_only/
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/ohr_bench/ gs://image_detection_b/02_benchmark_only/ohr-bench/
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/omnidocbench/ gs://image_detection_b/02_benchmark_only/

# Training Datasets
gsutil -m cp -r gs://image_detection_b/image-preprocessing-detector/datasets/iqa_phase2_100k/ gs://image_detection_b/03_training_datasets/phase2_100k/
gsutil -m cp -r gs://image_detection_b/datasets/phase7_v3_clean/ gs://image_detection_b/03_training_datasets/phase7_v3/
```

### Phase 2: Move Legacy to Archive

```bash
gsutil -m mv gs://image_detection_b/image-preprocessing-detector/ gs://image_detection_b/legacy/image-preprocessing-detector/
gsutil -m mv gs://image_detection_b/datasets/benchmarks/ gs://image_detection_b/legacy/datasets-benchmarks/
gsutil -m mv gs://image_detection_b/datasets/phase2/ gs://image_detection_b/legacy/datasets-phase2/
gsutil -m mv gs://image_detection_b/datasets/phase7_mvp/ gs://image_detection_b/legacy/datasets-phase7_mvp/
```

### Phase 3: Cleanup (After Verification)

```bash
gsutil -m rm -r gs://image_detection_b/legacy/
```

---

## Data Not Yet in GCS (Upload from Local)

| Local Path | GCS Destination | Priority |
|------------|-----------------|----------|
| `01_base_data/forms/nist_sd6/` | `gs://01_base_data/forms/nist_sd6/` | High |
| `01_base_data/forms/funsd_plus/` | `gs://01_base_data/forms/funsd_plus/` | High |
| `01_base_data/forms/sroie/` | `gs://01_base_data/forms/sroie/` | High |
| `01_base_data/documents/rvl_cdip/` | `gs://01_base_data/documents/rvl_cdip/` | Medium |
| `01_base_data/handwriting/nist_sd19_pages/` | `gs://01_base_data/handwriting/nist_sd19_pages/` | Medium |
| `01_base_data/handwriting/maths_handwriting/` | `gs://01_base_data/handwriting/maths_handwriting/` | Medium |
| `01_base_data/degraded/tobacco800/` | `gs://01_base_data/degraded/tobacco800/` | Low |
| `01_base_data/degraded/historical_degraded/` | `gs://01_base_data/degraded/historical_degraded/` | Low |
| `02_benchmark_only/dibco/` | `gs://02_benchmark_only/dibco/` | Medium |

---

## Estimated Costs

- **Data transfer**: Free (within same region)
- **Storage duplication during migration**: Temporary, ~2x for 1-2 days
- **Delete operations**: Free

---

## Verification Checklist

- [ ] All tables datasets accessible in new location
- [ ] All documents datasets accessible in new location
- [ ] All forms datasets accessible in new location
- [ ] All benchmarks isolated in 02_benchmark_only/
- [ ] Training datasets accessible in 03_training_datasets/
- [ ] Legacy folder can be safely deleted
