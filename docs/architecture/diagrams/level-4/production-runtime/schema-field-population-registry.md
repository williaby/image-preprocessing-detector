---
l4_category: schema-field-population
l4_generated: semi
l4_generator: scripts/generate_level4_registries.py
l4_last_generated: PENDING
owner: docs-team
tags:
- architecture
title: 'Level 4: Schema Field Population Registry'
---

# Schema Field Population Registry

This registry maps every field in `DocumentMetadata.json` to the pipeline component that
populates it. It consolidates the Level 2 PUML diagrams from
`docs/architecture/diagrams/level-2/schema-field-population/` into a searchable table.

<!-- AUTO-GENERATED-START -->
*Schema field population table not yet generated.*
<!-- AUTO-GENERATED-END -->

---

## Manual Reference

<!-- MANUAL SECTION — preserved across regenerations -->

### DocumentMetadata Top-Level Fields

| Field | Type | Populated By | Workstream | Phase | Notes |
|-------|------|-------------|-----------|-------|-------|
| `document_id` | str | `ingestion/ingestor.py` | WS1 | Phase 0 | UUID generated at ingest |
| `pdf_type` | str | `classification/pdf_type_classifier.py` | WS1 | Phase 2 | image_only/born_digital/hybrid |
| `dqs` | float | `metrics/dqs_calculator.py` | WS1 | Phase 2 | Document Quality Score 0-1 |
| `pre_ocr_risk` | float | `metrics/dqs_calculator.py` | WS1 | Phase 2 | Combined quality+complexity risk 0-1 |
| `ocr_routing_recommendation` | str | `routing/recommendation_engine.py` | WS1 | Phase 2 | ocr_fast/ocr_advanced/vision_simple/vision_structured |
| `pages` | list[PageMetadata] | orchestrator | WS1 | Phase 0 | One entry per page |

### PageMetadata Fields

| Field | Type | Populated By | Workstream | Phase | Notes |
|-------|------|-------------|-----------|-------|-------|
| `page_number` | int | `ingestion/ingestor.py` | WS1 | Phase 0 | 1-indexed |
| `width_px` | int | `ingestion/ingestor.py` | WS1 | Phase 0 | After upscaling |
| `height_px` | int | `ingestion/ingestor.py` | WS1 | Phase 0 | After upscaling |
| `dpi` | int | `ingestion/pdf_resolution.py` | WS1 | Phase 1B | Detected or upscaled to 300 |
| `has_text` | bool | `detection/text_gate.py` | WS1 | Phase 1 | Text gate ensemble result |
| `iqa_issues` | list[DetectedIssue] | `detection/iqa_classical.py` + `detection/iqa_ml.py` | WS1 | Phase 1C + 3 | Classical + ML IQA detectors |
| `layout_type` | str | `detection/layout_lite.py` | WS1 | Phase 2 | Coarse layout classification |
| `has_tables` | bool | `detection/layout_lite.py` | WS1 | Phase 2 | |
| `has_figures` | bool | `detection/layout_lite.py` | WS1 | Phase 2 | |
| `has_dense_math` | bool | `detection/layout_lite.py` | WS1 | Phase 2 | |
| `has_handwriting` | bool | `detection/layout_lite.py` | WS1 | Phase 2 | |
| `structural_complexity` | float | `metrics/dqs_calculator.py` | WS1 | Phase 2 | 0-1 complexity score |
| `corrected_image_path` | str | `correction/` modules | WS1 | Phase 1 | Output corrected image path |

### Source References

- [Level 2 schema field population PUML](../../../level-2/schema-field-population/schema-field-population-workflow.puml)
- [schema.py](../../../../../src/image_preprocessing_detector/schema.py) — Pydantic v2 models
