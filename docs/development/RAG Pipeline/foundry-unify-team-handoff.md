---
schema_type: common
title: "Unify: Team Handoff and Initial Scope"
description: "Complete onboarding handoff for the team assigned to build Unify.
  Covers pipeline position, input/output contracts, GCS artifact paths, reference files
  across all upstream repos, infrastructure already in place, known issues, and the
  phase roadmap."
tags:
  - pipeline
  - rag_pipeline
  - integration
  - specifications
  - documentation
status: active
owner: core-maintainer
purpose: "Give the Unify team everything they need to understand scope, locate
  all reference material, and begin Phase B1 without requiring context from prior sessions."
---

**Version:** 1.0.0 | **Status:** Active | **Last Updated:** 2026-05-05

---

## 1. Pipeline Position

Unify is the third stage in the six-service Foundry RAG pipeline. It sits between
two upstream preprocessing services and one downstream chunking service:

```text
rag-processor
      │
      ├── audio/video ──► audio-processor ──┐
      │                                            │
      └── documents ────► image_detection ─────┤
                                                   │
                                          Unify   ◄─── YOU ARE HERE
                                                   │
                                          data_ingestor
                                                   │
                                    per-application embedding
```

**Unify mission**: Receive preprocessing metadata and corrected artifacts from
both upstream tracks, run OCR orchestration and layout analysis via Docling, assemble a
unified Docling DOM, and write a single `DoclingDOM.json` artifact to GCS that
data_ingestor can consume regardless of whether the source was a document or audio file.

**Key architectural constraint**: Unify normalizes two radically different input tracks
into one output schema. The document track requires full OCR orchestration. The audio
track skips OCR entirely — Prepare-Audio pre-assembles the DOM; Unify only normalizes it.

---

## 2. GCS Artifact Paths (Canonical)

All services share a single GCS bucket namespaced by environment and trace ID:

```text
gs://rag-pipeline-{env}/{trace_id}/
  00-source/          ← Ingest writes raw uploads here
  01-preprocessed/    ← Prepare-Doc writes here (document track)
  02-transcribed/     ← Prepare-Audio writes here (audio track)
  03-docling-dom/     ← Unify writes here  ◄─── YOUR OUTPUT
  04-chunks/          ← Chunk reads from here (data_ingestor input)
```

| Artifact | Path | Written by | Read by |
|----------|------|-----------|---------|
| `DocumentMetadata.json` | `01-preprocessed/` | image_detection | Unify |
| Corrected page images (PNG, 300 DPI) | `01-preprocessed/` | image_detection | Unify |
| Model registry (ONNX models) | `01-preprocessed/models/` | image_detection | Unify |
| `TranscriptMetadata.json` | `02-transcribed/` | audio-processor | Unify |
| **`DoclingDOM.json`** | **`03-docling-dom/`** | **Unify** | **data_ingestor** |

---

## 3. Input Contracts

### 3.1 Document Track: Prepare-Doc → Unify

**Canonical contract**: [`docs/development/RAG Pipeline/prepare-doc-unify-contract.md`](prepare-doc-unify-contract.md)

Prepare-Doc delivers three things per document:

#### 3.1.1 DocumentMetadata.json (schema v2.0)

The primary routing signal. Key fields Unify must consume:

| Field | Type | How Unify uses it |
|-------|------|--------------------|
| `pdf_type` | `image_only \| born_digital \| hybrid` | OCR mode selection |
| `processing_recommendation.tier` | `standard \| vlm_assisted \| vlm_validated` | Pipeline tier selection (see Section 5) |
| `processing_recommendation.vlm_validation.recommended` | bool | Whether to invoke VLM pass |
| `processing_recommendation.vlm_validation.reasons` | array | Specific flags driving VLM recommendation |
| `processing_recommendation.specialist_routing` | object | Maps element types to recommended OCR specialists |
| `quality_assessment.pre_ocr_risk` | float 0-1 | Overall OCR difficulty estimate |
| `quality_assessment.degradation_score` | float 0-1 | Image quality degradation severity |
| `pages[].layout_attributes` | object | Per-page layout flags (tables, math, handwriting, columns) |
| `pages[].detected_elements` | array | Pre-detected element bounding boxes with type classifications |
| `pages[].detected_elements[].classifications.specialist_needed` | bool | Whether a specialist OCR engine is required |
| `pages[].detected_elements[].classifications.recommended_specialist` | string | Specific specialist to invoke |
| `docling_params` | `DoclingRoutingParams` | Pre-computed Docling CLI flags — see Section 3.1.3 |

**Full schema reference**: [`src/image_preprocessing_detector/schema.py`](../../../src/image_preprocessing_detector/schema.py)

- `DocumentMetadata` class: line 1249
- `PageMetadata` class: line 1116
- `DoclingRoutingParams` class: line 755
- `PDFType` enum: line 167
- `OCRRoutingStrategy` enum: line 175

**JSON schema**: [`docs/development/RAG Pipeline/document_metadata.schema.json`](document_metadata.schema.json)

#### 3.1.2 Corrected Page Images

- Format: PNG, 300 DPI, RGB
- Path: `01-preprocessed/{document_id}/page_NNNN.png`
- Corrections already applied: deskew, CLAHE, sharpening, denoising, resolution upscaling
- Unify should NOT re-apply image corrections — images arrive pipeline-ready

#### 3.1.3 DoclingRoutingParams (Pre-computed Docling Flags)

Prepare-Doc analyzes each document and pre-computes the optimal Docling configuration.
Unify should use these parameters rather than re-deriving them:

```python
# DoclingRoutingParams fields (schema.py:755)
pipeline: "standard" | "vlm" | "legacy"
vlm_model: str | None          # e.g., "ibm-granite/granite-docling-258M"
ocr_enabled: bool              # False for born-digital with clean text layer
ocr_force: bool                # Force OCR even if text layer present
ocr_engine: "auto" | "rapidocr" | "tesseract"
ocr_lang: str | None           # e.g., "ch", "ara+fas"
psm: int | None                # Tesseract Page Segmentation Mode (0-13)
tables_enabled: bool
table_mode: "fast" | "accurate"
enrich_code: bool
enrich_formula: bool
page_batch_size: int           # Reduce for CJK scripts or large pages
```

The params expose a `to_cli_args()` method that converts directly to Docling CLI arguments.
See the routing logic that generates these:
[`src/image_preprocessing_detector/routing/docling_router.py`](../../../src/image_preprocessing_detector/routing/docling_router.py)

#### 3.1.4 Model Registry (ONNX Element Classifiers)

Prepare-Doc trains and ships five ONNX models that Unify must load for element-level routing:

| Model | Classes | Purpose |
|-------|---------|---------|
| `doclayout_yolo_extended` | 17 | Extended layout detection (11 DocLayNet + 6 custom) |
| `handwriting_classifier` | 2 | Printed vs handwritten text |
| `table_type_classifier` | 6 | simple_grid / merged_header / nested_rows / financial / form_like / scientific |
| `formula_complexity_classifier` | 5 | simple_inline / block_equation / multi_line / matrix / handwritten_math |
| `parasitic_detector` | 4 | Watermark / stamp / header / footer detection |

Each model ships in `full` (GPU, Modal L4 target) and `light` (CPU) variants.
Registry interface code is provided in the contract:
[`docs/development/RAG Pipeline/prepare-doc-unify-contract.md`](prepare-doc-unify-contract.md) — Section 3.4

GCS backup location: `gs://image_detection_b/models/phase9/`

---

### 3.2 Audio Track: Prepare-Audio → Unify

**Canonical contract**: [`docs/development/RAG Pipeline/prepare-audio-unify-contract.md`](prepare-audio-unify-contract.md)

**GitHub repo**: [ByronWilliamsCPA/audio-processor](https://github.com/ByronWilliamsCPA/audio-processor)

The audio track is fundamentally different from the document track. Unify MUST NOT run
any OCR engine for audio inputs.

#### 3.2.1 Source Track Detection

```python
# Before any processing, Unify must read source_track
with open("TranscriptMetadata.json") as f:
    meta = json.load(f)

if meta["source_track"] == "audio":
    # DOM-normalization-only mode — skip all OCR
    dom = meta["docling_document"]
    normalize_and_write(dom)
elif meta["source_track"] == "document":
    # Full OCR orchestration mode
    run_ocr_pipeline(meta)
else:
    raise ValueError(f"MISSING_SOURCE_TRACK: unknown track {meta['source_track']!r}")
```

#### 3.2.2 TranscriptMetadata.json Key Fields

| Field | Required | Description |
|-------|----------|-------------|
| `source_track` | YES | MUST be `"audio"` — absence is a hard error |
| `docling_document` | YES | Pre-assembled Docling DOM — use as-is after normalization |
| `document_id` | YES | Carry through to DoclingDOM.json |
| `trace_id` | YES | Carry through to DoclingDOM.json |
| `audio_quality.snr_db` | YES | If below threshold, add quality warning flag to output (do not reject) |
| `transcription.full_text` | YES | Absence is a hard error (`EMPTY_TRANSCRIPT`) |

#### 3.2.3 DOM Mapping (Audio → Docling)

| Audio Element | Docling DOM Type | Key Fields |
|---------------|------------------|------------|
| Speaker turn | `SectionItem` | `speaker_id`, `speaker_label` |
| Utterance | `TextItem` | `start_ms`, `end_ms`, `confidence`, `playback_url` |
| Summary | `SectionItem` | `is_summary: true`, rendered at top of DOM |

#### 3.2.4 Audio Track Error Handling

| Scenario | Required behavior |
|----------|------------------|
| Missing `source_track` | Reject — error code `MISSING_SOURCE_TRACK` |
| Missing `docling_document` | Reject — error code `MISSING_DOCLING_DOM` |
| Missing `transcription.full_text` | Reject — error code `EMPTY_TRANSCRIPT` |
| `audio_quality.snr_db` below threshold | Add quality warning to DoclingDOM, continue |

---

## 4. Output Contract: Unify → Chunk

**Canonical contract**: [`docs/development/RAG Pipeline/chunk-embed-contract.md`](chunk-embed-contract.md)

Unify writes a single artifact regardless of input track:

```text
gs://rag-pipeline-{env}/{trace_id}/03-docling-dom/DoclingDOM.json
```

The schema is identical for both document-track and audio-track outputs. data_ingestor
reads `DoclingDOM.json` and does not need to know which track produced it.

Key fields Chunk expects from Unify:

| Field | Description |
|-------|-------------|
| `document_id` | Stable identifier carried from upstream |
| `trace_id` | Pipeline trace ID for Cloud Workflows correlation |
| `source_track` | `"document"` or `"audio"` — preserved from input |
| `pages[]` | Ordered array of page representations |
| `pages[].elements[]` | Layout elements with type, bbox, text, reading_order |
| `pages[].elements[].ocr_engine_provenance` | Which engine produced this text |
| `pages[].reading_order_confidence` | Float — low values trigger fallback chunking in Chunk |
| `metadata.processing_tier` | Which tier was used (`standard / vlm_assisted / vlm_validated`) |

---

## 5. Processing Tiers

Prepare-Doc pre-selects the tier based on document analysis. Unify reads
`processing_recommendation.tier` and selects the corresponding Docling pipeline:

| Tier | Trigger (from Prepare-Doc) | Unify action |
|------|---------------------------|-------------|
| `standard` | DQS < 0.3, born_digital, simple layout | Docling `StandardPipeline` — no VLM |
| `vlm_assisted` | 0.3 ≤ DQS < 0.6, tables or math present, moderate complexity | Docling + `ibm-granite/granite-docling-258M` VLM on flagged regions |
| `vlm_validated` | DQS ≥ 0.6, handwriting present, complex/degraded layout | Docling and VLM run in parallel; results are cross-validated |

Tier thresholds config reference (calibrated by Prepare-Doc):

```yaml
# configs/project_b_thresholds.yaml (from contract doc)
tier_thresholds:
  standard_max_dqs: 0.3
  vlm_assisted_max_dqs: 0.6
vlm_triggers:
  handwriting_present: true
  table_complexity_threshold: 0.5
  formula_present: true
  degradation_above: 0.4
```

---

## 6. Format Routing (Document Track)

Not all documents need OCR. Prepare-Doc classifies the document type via
`pdf_type` and `processing_recommendation`. Unify must implement fast-path bypasses:

| Document class | `pdf_type` | OCR action |
|---------------|-----------|------------|
| Born-digital PDF, clean text layer | `born_digital` | Skip OCR — extract text layer directly |
| Born-digital PDF, degraded/garbled text | `born_digital` + high `pre_ocr_risk` | Force OCR via `ocr_force: true` |
| Scanned PDF / images | `image_only` | Full OCR — use corrected images |
| Hybrid PDF | `hybrid` | Per-page routing using `page_type_map` |
| Native text formats (DOCX, XLSX, HTML, MD) | n/a | Route to Docling directly — no image pipeline |
| Encrypted PDF | `image_only` + `processing_status: halted` | Emit `DoclingDOM.json` with `processing_status: halted` |

**Full format routing analysis** (40+ formats, 5-model consensus, Stage 0 router design):
[`tmp_cleanup/docling_format_routing_analysis.md`](../../../tmp_cleanup/docling_format_routing_analysis.md)

**Dynamic flag configuration guide** (Docling feature matrix, heuristics, performance benchmarks):
[`tmp_cleanup/docling_flag_research.md`](../../../tmp_cleanup/docling_flag_research.md)

---

## 7. Infrastructure Already in Place

### 7.1 Docling-Serve

A `docling-serve` instance is deployed and operational on the homelab network:

| Property | Value |
|----------|-------|
| Endpoint | `http://192.168.1.209:5001` |
| API path | `/v1/convert/file` |
| Health | `GET /health` |
| Deployment | Docker (standard, VLM, and GCS-sync variants) |

**Docker configs** (in `image_detection` repo — for reference):

- [`deployment/docker-compose.docling.yml`](../../../deployment/docker-compose.docling.yml) — Standard mode
- [`deployment/docker-compose.docling-vlm.yml`](../../../deployment/docker-compose.docling-vlm.yml) — VLM mode (`ibm-granite/granite-docling-258M`)
- [`deployment/docker-compose.docling-gcs.yml`](../../../deployment/docker-compose.docling-gcs.yml) — GCS sync variant
- [`deployment/deploy-docling.sh`](../../../deployment/deploy-docling.sh) — Deploy script

**Note**: These configs live in `image_detection` because docling-serve was originally
deployed there for testing. Unify should own its own deployment configuration in
the new repo. The existing configs are reference only.

### 7.2 HTTP Client Wrapper

A working REST client for docling-serve is already implemented:
[`src/image_preprocessing_detector/text_extraction/docling_client.py`](../../../src/image_preprocessing_detector/text_extraction/docling_client.py)

This can be copied into Unify as a starting point. It handles:

- File upload to `/v1/convert/file`
- Routing params as form data
- Text, markdown, and JSON extraction from response
- Timeout configuration (default 5 minutes)
- Page count and table count extraction

### 7.3 API Contract

A Foundry Unify Adapter API contract is defined in homelab-infra. This specifies the
service interface that Unify should implement:

- **Location**: `homelab-infra/docs/planning/contracts/DOCLING-API-CONTRACT.md`
- **GitHub**: [ByronWilliamsCPA/homelab-infra](https://github.com/ByronWilliamsCPA/homelab-infra) (private)
- **Status**: Draft — pending image team review

---

## 8. Specialist OCR Routing

Prepare-Doc recommends specialist OCR engines per element type. Unify must route to them:

| Element type | Recommended specialist | Selection basis |
|-------------|----------------------|-----------------|
| `table` (simple_grid, financial) | `tableformer` | Default for grids |
| `table` (merged_header, nested_rows, scientific) | `structeqtable` | Complex cell structure |
| `formula` (block_equation, multi_line) | `texify` | Block-level math |
| `formula` (matrix, handwritten_math) | `unimernet` | Complex and handwritten formulas |
| `formula` (simple_inline) | `granite-docling` | Inline within text flow |
| `handwriting` | `trocr` | Default |
| `handwriting` (domain-specific) | `trocr-domain` | If domain model available |
| `code_block` | `docling-standard` | Preserve formatting |

Parasitic elements (watermark, stamp, page_header, page_footer) should be excluded from
RAG chunks but preserved in metadata. OCR actions:

| Parasitic type | OCR action |
|---------------|-----------|
| `watermark` | Skip OCR entirely |
| `stamp` | OCR for metadata only |
| `page_header` / `page_footer` | OCR for metadata only |
| `signature` | Flag for review — do not OCR |

---

## 9. Known Issues (Document Before Writing Code)

Three known issues with the Docling layout models are already characterized.
Bake mitigations in from the start rather than discovering them later:

### KI-002: Multi-Column Text Misclassified as Table

**File**: [`docs/known_issues/KI-002-docling-table-multicolumn.md`](../../known_issues/KI-002-docling-table-multicolumn.md)
**Severity**: HIGH

- Both `docling-layout-egret-xlarge` and `DocLayout-YOLO` misclassify multi-column
  body text as `Table` — 10/10 false positives observed in evaluation
- Corrupts reading order and pollutes table extraction pipeline
- **Recommended mitigation** (priority order):
  1. Per-class confidence threshold — reclassify low-confidence Table detections
  2. Table structure gatekeeper — reclassify `TABLE → TEXT` if no rows/cols detected by TableFormer
  3. Geometric heuristic — column-width uniformity check

### KI-003: Dense Text / Dark Rendering Misclassified as Picture

**File**: [`docs/known_issues/KI-003-docling-picture-dense-text.md`](../../known_issues/KI-003-docling-picture-dense-text.md)
**Severity**: MEDIUM

- Docling misclassifies dense text blocks and dark-background rendering as `Picture`
- 100% false positive rate on 3 detections in evaluation sample
- **Recommended mitigation**: VLM inspection on `Picture` elements — override to `Text`
  if VLM returns text content

### KI-008: Table Misclassification Corrupts 5-Stage Docling Pipeline

**File**: [`docs/known_issues/KI-008-docling-multicolumn-text-extraction.md`](../../known_issues/KI-008-docling-multicolumn-text-extraction.md)
**Severity**: HIGH | **Status**: OPEN

- The damage from KI-002 propagates through five Docling pipeline stages:
  Layout → Postprocessor → PageAssemble → ReadingOrder → Export
- Reading order is disrupted because multi-column text in a false `TABLE` element
  is not included in the normal reading order sequence
- Fix KI-002 first — this issue is downstream of it

---

## 10. Architecture Diagrams

| Diagram | Path | Description |
|---------|------|-------------|
| Level 0 — Pipeline Overview | [`docs/architecture/diagrams/level-0/rag-pipeline-overview.puml`](../../architecture/diagrams/level-0/rag-pipeline-overview.puml) | Six-service pipeline context |
| Unify OCR Layout Workflow | [`docs/architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml`](../../architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml) | Detailed Unify internal flow |
| Prepare-Audio Transcription | [`docs/architecture/diagrams/level-2/downstream-context/prepare-audio-transcription-workflow.puml`](../../architecture/diagrams/level-2/downstream-context/prepare-audio-transcription-workflow.puml) | Audio track pipeline detail |

Pre-rendered SVG/PNG variants exist alongside each `.puml` file.

---

## 11. Related GitHub Repos

| Repo | Visibility | Relevance |
|------|-----------|-----------|
| [ByronWilliamsCPA/audio-processor](https://github.com/ByronWilliamsCPA/audio-processor) | Public | audio-processor — audio track upstream |
| [ByronWilliamsCPA/homelab-infra](https://github.com/ByronWilliamsCPA/homelab-infra) | Private | Deployment tracking, DOCLING-API-CONTRACT.md, integration plan |
| [ByronWilliamsCPA/DeQA-Doc](https://github.com/ByronWilliamsCPA/DeQA-Doc) | Public | OCR-IQA correlation research — includes working `DoclingOCREngine` implementation for reference |

Both `rag-processor` ([ByronWilliamsCPA/rag-processor](https://github.com/ByronWilliamsCPA/rag-processor))
and `image-preprocessing-detector` ([williaby/image-preprocessing-detector](https://github.com/williaby/image-preprocessing-detector))
have standalone repos. This IS the `image-preprocessing-detector` repo (local checkout:
`~/dev/image_detection/`).

---

## 12. Phase Roadmap

From the functional and non-functional requirements doc:
[`docs/_archived/cross-project/unify-f-nf.md`](../../_archived/cross-project/unify-f-nf.md)

### Phase B1 — Layout and Basic OCR (Start Here)

- Integrate Docling with DocLayNet-style layout classes (11 minimum)
- Per-page layout detection from corrected images
- Per-region OCR using base engine
- Simple reading order (column-aware)
- Read `DoclingRoutingParams` from `DocumentMetadata.json` and apply to Docling config
- Write `DoclingDOM.json` to GCS `03-docling-dom/`
- Source track detection (`"audio"` vs `"document"`) with correct branching

### Phase B2 — Parasitic Content and Advanced Reading Order

- Header / footer / page-number detection across pages
- Parasitic flags on elements — exclude from RAG chunks, preserve in metadata
- Graph-based reading order with confidence scoring
- Audio track normalization (DOM passthrough with schema normalization)

### Phase B3 — Tables, Structured Regions, Specialist Routing

- TableFormer and StructEqTable integration
- Figure–caption linking
- Footnote linking
- Math / formula detection and Texify/UniMERNet routing
- Watermark, stamp, signature, margin-note detection
- KI-002 and KI-003 mitigations (per-class confidence gating)

### Phase B4 — Tier Routing, Optimization, Hardening

- VLM pipeline (`vlm_assisted` and `vlm_validated` tiers)
- Performance tuning and batching
- Robust fallback modes with `layout_confidence` signaling to Chunk
- Prometheus metrics, structured logging, debug overlay images
- Integration tests against both upstream tracks

---

## 13. Performance Targets

| Metric | Target | Acceptable |
|--------|--------|-----------|
| Layout detection latency | ≤ 100 ms/page (GPU) | ≤ 300 ms/page |
| OCR latency, average complexity | ≤ 300 ms/page | ≤ 800 ms/page |
| Throughput per worker | ≥ 3–5 pages/second | — |
| Layout mAP@0.50 (DocLayNet classes) | ≥ 0.82 | — |
| Reading order pairwise F1 | ≥ 0.85 | — |
| Table structure similarity (TEDS) | ≥ 0.90 | — |
| OCR WER improvement over baseline | ≥ 10% relative | — |

---

## 14. Integration Test Checklist

From the contract doc — use to gate Phase B1 completion:

- [ ] Born-digital PDF → `standard` tier → DoclingDOM written to GCS
- [ ] Scanned PDF with tables → `vlm_assisted` tier recommended
- [ ] Handwritten document → `vlm_validated` tier invoked
- [ ] Audio input (`source_track: "audio"`) → OCR skipped, DOM normalized and written
- [ ] Watermarked document → watermark element flagged, excluded from chunk output
- [ ] Multi-page document → all pages processed, reading order correct
- [ ] Corrupt / partial-failure page → graceful degradation, `layout_confidence` flagged low
- [ ] `DoclingRoutingParams.to_cli_args()` applied correctly to Docling configuration
- [ ] Missing `source_track` → `MISSING_SOURCE_TRACK` error
- [ ] Missing `docling_document` in audio input → `MISSING_DOCLING_DOM` error

---

## 15. Key Reference Files — Quick Index

### In this repo (image-preprocessing-detector / image_detection)

| File | Purpose |
|------|---------|
| [`docs/development/RAG Pipeline/prepare-doc-unify-contract.md`](prepare-doc-unify-contract.md) | Full data + model + config handoff spec |
| [`docs/development/RAG Pipeline/prepare-audio-unify-contract.md`](prepare-audio-unify-contract.md) | Audio track interface contract |
| [`docs/development/RAG Pipeline/chunk-embed-contract.md`](chunk-embed-contract.md) | Unify output spec (what Chunk expects) |
| [`docs/development/RAG Pipeline/document_metadata.schema.json`](document_metadata.schema.json) | JSON Schema for DocumentMetadata.json |
| [`docs/development/RAG Pipeline/RAG-pipeline-project-overview.md`](RAG-pipeline-project-overview.md) | Pipeline-wide narrative overview |
| [`src/image_preprocessing_detector/schema.py`](../../../src/image_preprocessing_detector/schema.py) | All Pydantic models — DocumentMetadata, DoclingRoutingParams, etc. |
| [`src/image_preprocessing_detector/routing/docling_router.py`](../../../src/image_preprocessing_detector/routing/docling_router.py) | 6-rule routing engine that generates DoclingRoutingParams |
| [`src/image_preprocessing_detector/text_extraction/docling_client.py`](../../../src/image_preprocessing_detector/text_extraction/docling_client.py) | HTTP client for docling-serve (copy-ready) |
| [`tmp_cleanup/docling_format_routing_analysis.md`](../../../tmp_cleanup/docling_format_routing_analysis.md) | Format routing analysis — 40+ formats, 5-model consensus |
| [`tmp_cleanup/docling_flag_research.md`](../../../tmp_cleanup/docling_flag_research.md) | Docling feature matrix, heuristics, performance benchmarks |
| [`docs/known_issues/KI-002-docling-table-multicolumn.md`](../../known_issues/KI-002-docling-table-multicolumn.md) | Table misclassification — HIGH severity |
| [`docs/known_issues/KI-003-docling-picture-dense-text.md`](../../known_issues/KI-003-docling-picture-dense-text.md) | Picture misclassification — MEDIUM severity |
| [`docs/known_issues/KI-008-docling-multicolumn-text-extraction.md`](../../known_issues/KI-008-docling-multicolumn-text-extraction.md) | Reading order corruption — HIGH severity, OPEN |
| [`docs/_archived/cross-project/unify-f-nf.md`](../../_archived/cross-project/unify-f-nf.md) | Functional and non-functional requirements (Project B / Unify) |
| [`docs/architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml`](../../architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml) | Unify internal workflow diagram |
| [`deployment/docker-compose.docling.yml`](../../../deployment/docker-compose.docling.yml) | Reference docling-serve deployment config |
| [`deployment/docker-compose.docling-vlm.yml`](../../../deployment/docker-compose.docling-vlm.yml) | Reference VLM-mode deployment config |

### In homelab-infra repo (ByronWilliamsCPA/homelab-infra — private)

| File | Purpose |
|------|---------|
| `docs/planning/contracts/DOCLING-API-CONTRACT.md` | Foundry Unify Adapter API contract |
| `docs/planning/PAPERLESS-FOUNDRY-INTEGRATION-PLAN.md` | Full integration plan — Phase 4 covers Unify |
| `docs/planning/SERVICE-DEPLOYMENT-TRACKING.md` | Service deployment status |

### In audio-processor repo (ByronWilliamsCPA/audio-processor — public)

| File | Purpose |
|------|---------|
| `src/audio_processor/` | Prepare-Audio implementation — context for what Unify receives |
| `docs/planning/phases/phase-2-integration.md` | Audio track Docling DOM output plan |
| `pyproject.toml` | `docling-core>=2.3.0` declared as dependency (phase-2 implementation pending) |

---

## 16. Getting Started

1. **Read the contracts first** — Section 3 and Section 4. They define all field-level
   requirements. The rest of this document is context and reference.

2. **Review the known issues** — Section 9. All three are HIGH or MEDIUM severity and
   affect Phase B1. Plan mitigations before writing layout detection code.

3. **Start with Phase B1** — Document track, `standard` tier, born-digital PDFs only.
   Get `DoclingDOM.json` writing correctly to GCS before adding tiers or specialist routing.

4. **Use the existing HTTP client** — Copy
   [`src/image_preprocessing_detector/text_extraction/docling_client.py`](../../../src/image_preprocessing_detector/text_extraction/docling_client.py)
   as the docling-serve adapter. The endpoint is live at `http://192.168.1.209:5001`.

5. **Add audio track second** — It shares the same output schema and output path,
   but requires a completely separate code path. Phase B2 is the right milestone for this.

6. **Questions on Prepare-Doc outputs** — Raise in GitHub issues against this repo
   (image_detection). The schema and routing logic are owned here.
