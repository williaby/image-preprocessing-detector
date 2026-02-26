---
owner: docs-team
title: 'Level 4: Annotation Enrichment Provider Registry'
l4_category: provider
l4_generated: auto
l4_generator: scripts/generate_level4_registries.py
l4_last_generated: 2026-02-23
tags:
- architecture
- level_4
- registry
---

# Level 4: Annotation Enrichment Provider Registry

> **Auto-generated** — do not edit manually. Regenerate with:
> `python scripts/generate_level4_registries.py --category provider`

Total: 5 enrichment providers.

| Provider File | Task | Workstream | Provides | Status |
| ------------- | ---- | ---------- | -------- | ------ |
| `src/image_preprocessing_detector/annotation/enrichment/providers/siglip.py` | iqa | WS3 | `iqa_scores, quality_vector` | ✅ |
| `src/image_preprocessing_detector/annotation/enrichment/providers/simulated.py` | iqa | WS3 | `simulated_quality_labels` | ✅ |
| `src/image_preprocessing_detector/annotation/enrichment/providers/language_detector.py` | language | WS3 | `detected_script, language_code` | ✅ |
| `src/image_preprocessing_detector/annotation/enrichment/providers/docling_layout.py` | layout | WS3 | `layout_type, bounding_boxes` | ✅ |
| `src/image_preprocessing_detector/annotation/enrichment/providers/yolo.py` | layout | WS3 | `yolo_layout_boxes` | ✅ |
