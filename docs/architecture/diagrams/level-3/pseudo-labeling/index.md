---
owner: docs-team
purpose: Level 3 pseudo-labeling module documentation index
schema_type: common
status: active
tags:
  - architecture
  - level-3
  - pseudo-labeling
title: "Level 3: Pseudo-Labeling - Module Implementation"
---

# Level 3: Pseudo-Labeling - Module Implementation

**Status**: Active
**Lines of Code**: ~2,947 (Modal scripts)
**Purpose**: Detailed module-level documentation for the Pseudo-Labeling workstream (WS4), including ensemble stacking, calibration, and confidence filtering with LOC annotations.

## Related Diagrams

- **Level 0**: [RAG Pipeline Overview](../../level-0/index.md)
- **Level 1**: [Project A Architecture](../../level-1/index.md)
- **Level 2**: [Pseudo-Labeling](../../level-2/pseudo-labeling/index.md)

## Contents

### Swimlane Diagram

Complete pseudo-labeling swimlane with LOC annotations for each processing step.

- **Source**: [pseudo-labeling-swimlane.puml](pseudo-labeling-swimlane.puml)

### Ensemble Stacking

5-model ensemble architecture with variance-weighted voting, temperature scaling, and confidence filtering.

- **Document**: [ensemble-stacking.md](ensemble-stacking.md)
- **Models**: 3 classical (MUSIQ, QualiCLIP, DocIQ-Replica) + 2 VLM (Qwen3-VL-8B, InternVL3-8B)
- **Calibration**: Temperature scaling with ECE < 0.1 requirement
- **Filtering**: Agreement > 0.8 threshold, dead-letter queue for low-confidence samples

## Key Source Files

| File | LOC | Purpose |
| ---- | --- | ------- |
| `modal/generate_pseudo_labels.py` | 1,042 | Ensemble orchestration and label generation |
| `modal/stage1_deqa_inference.py` | 492 | DIQA inference pipeline |
| `modal/stage1_deqa_tarball_inference.py` | 333 | Batch tarball processing |
| `modal/teacher_inference.py` | 419 | Production model inference |
| `modal/shared/metrics_utils.py` | 223 | Shared metrics (PLCC, SRCC, ECE) |
| `modal/shared/gcs_utils.py` | 130 | GCS download/upload utilities |
| `modal/shared/dataset_utils.py` | 61 | Dataset loading utilities |
| `modal/shared/constants.py` | 58 | Shared constants |
| **Total** | **~2,758** | |

## Data Flow

```text
WS3 (Data Prep)     WS8 (Synthetic)
  base_data/           synthetic/
      |                    |
      +--------+-----------+
               |
     Benchmark Datasets
     (DIQA-5000, OHR-Bench)
               |
     +---------+---------+
     |                   |
  Track A             Track B
  Classical ML        VLM Models
  (MUSIQ, QualiCLIP,  (Qwen3-VL,
   DocIQ-Replica)      InternVL3)
     |                   |
     +---------+---------+
               |
     Ensemble Stacking
     (variance-weighted voting)
               |
     Temperature Scaling
     (ECE < 0.1)
               |
     Confidence Filtering
     (agreement > 0.8)
               |
     +----+----+----+
     |              |
  Pseudo-Labels   Dead-Letter
  (parquet)       Queue
     |
  Model Registry
  (checkpoint selection)
```

## Dependencies

- **Upstream**: WS3 (base datasets), WS8 (synthetic data)
- **Downstream**: WS2 (training labels), WS6 (arena validation)
- **Infrastructure**: Modal serverless GPU (A10), GCS storage

---

*Last Updated: February 2026*
