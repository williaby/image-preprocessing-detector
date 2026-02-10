---
owner: docs-team
purpose: Level 3 synthetic generation module documentation index.
schema_type: common
status: active
tags:
- architecture
- level_3
- synthetic_generation
title: "Level 3: Synthetic Generation - Module Implementation"
---

# Level 3: Synthetic Generation - Module Implementation

**Status**: Active
**Lines of Code**: ~1,400+ (core pipeline)
**Purpose**: Detailed module-level documentation for the Synthetic Generation workstream (WS8), including multi-task generation, hybrid augmentation, and schema adaptation with LOC annotations.

## Related Diagrams

- **Level 0**: [RAG Pipeline Overview](../../level-0/index.md)
- **Level 1**: [Project A Architecture](../../level-1/index.md)
- **Level 2**: [Synthetic Generation](../../level-2/synthetic-generation/index.md)

## Contents

### Swimlane Diagram

Complete synthetic generation swimlane with LOC annotations for each processing step.

- **Source**: [synthetic-generation-swimlane.puml](synthetic-generation-swimlane.puml)

### Augmentation Pipeline

Hybrid augmentation architecture with 3 aging profiles, geometric transform ordering, and DPI tier selection.

- **Document**: [augmentation-pipeline.md](augmentation-pipeline.md)
- **Profiles**: MODERN (80%), AGED (15%), HISTORICAL (5%)
- **DPI Tiers**: 7 tiers (72/100/150/200/300/400/600 DPI)
- **Color Modes**: COLOR (60%), GRAYSCALE (30%), BINARIZED (10%)
- **Key Fix**: Geometric transforms applied BEFORE augmentation pipeline

## Key Source Files

| File | LOC | Purpose |
| ---- | --- | ------- |
| `src/.../synthetic/config.py` | ~300 | DPI tiers, ColorMode enum, augmentation params |
| `src/.../synthetic/generator.py` | ~400 | Multi-task generation engine |
| `src/.../synthetic/augmentation_hybrid.py` | ~350 | Hybrid augmentation (aging, degradation) |
| `src/.../synthetic/schema_adapter.py` | ~200 | Multi-task metadata schema adapter |
| `src/.../synthetic/cli.py` | ~150 | Synthetic generation CLI |
| **Total** | **~1,400** | |

## Data Flow

```text
Configuration
(DPI tier, color mode, scripts)
         |
   Text Rendering
   (30+ scripts, font selection)
         |
   Geometric Transforms        <-- Applied FIRST (clean image)
   (orientation 0/90/180/270,
    skew +-10 degrees)
         |
   Augmentation Pipeline        <-- Applied SECOND (on transformed image)
   (MODERN/AGED/HISTORICAL)
         |
   +-----+-----+
   |             |
 Measurement    Schema Adaptation
 (char_height,  (multi_task metadata,
  DPI check)    IQA vector 45-dim,
                 Tier 0 conf=1.0)
   |             |
   +-----+-----+
         |
   Output Artifacts
   (parquet + JSON,
    full provenance)
```

## Dependencies

- **Upstream**: Font corpus, text corpus (multi-script), config/layout_taxonomy.yaml
- **Downstream**: WS3 (data preparation), WS2 (training datasets)
- **Key Planning Docs**:
  - [DATASET_DIVERSITY_REQUIREMENTS.md](../../../../planning/DATASET_DIVERSITY_REQUIREMENTS.md)
  - [SIGLIP2_MULTITASK_REQUIREMENTS.md](../../../../planning/SIGLIP2_MULTITASK_REQUIREMENTS.md)

---

*Last Updated: February 2026*
