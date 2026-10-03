---
title: Prepare-Doc (image_detection) — System Overview (Detailed Reference)
schema_type: common
status: active
owner: core-maintainer
purpose: "Comprehensive technical reference: complete module map, canonical files, schema contract, config reference, and training infrastructure."
tags:
- architecture
- reference
---

# Prepare-Doc — System Overview (Detailed Reference)

> **Audience**: Engineers implementing, debugging, or extending the system.
> **Scope**: Target-state system — complete module map, schema contract, config reference,
> and training infrastructure. Canonical file paths for every system component.
>
> **Related documents**:
>
> - [docs/PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) — concise narrative introduction (start here)
> - [docs/planning/MASTER_PROJECT_PLAN.md](planning/MASTER_PROJECT_PLAN.md) — project status and remaining work
> - [docs/architecture/](architecture/) — implementation diagrams at all four levels
> - [docs/architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md](architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md) — when and how to update diagrams

---

## 1. What Is Prepare-Doc?

Document quality in real-world collections is highly variable. Pages arrive rotated, skewed,
blurred, shadowed, or photographed under poor lighting. Scripts span dozens of writing systems.
Some documents are born-digital PDFs; others are camera photographs of physical pages from
decades ago. Downstream OCR pipelines — which operate on the assumption of clean, upright,
legible input — fail silently or produce garbled output when these conditions are violated.

Prepare-Doc (image-preprocessing-detector) is the **preprocessing, IQA, and coarse layout gateway** for a six-service RAG
document pipeline. It accepts raw documents in any condition, assesses quality along multiple
dimensions, applies physical corrections, and produces two outputs for Unify (OCR
Orchestration): a corrected page image and a `DocumentMetadata.json` record containing
everything Unify needs to make informed routing decisions.

```text
Raw Documents (PDF, image, any condition)
        │
        ▼
┌────────────────────────────────────────┐
│             PREPARE-DOC                  │
│  Preprocessing, IQA & Coarse Gateway   │
│                                        │
│  • Orientation / skew correction       │
│  • Resolution normalization            │
│  • Image quality assessment (19 heads) │
│  • Script & language detection         │
│  • Handwriting analysis               │
│  • Page attribute classification       │
│  • Document Quality Score              │
│  • OCR routing recommendation          │
└────────────────┬───────────────────────┘
                 │  DocumentMetadata.json
                 │  + Corrected page images
                 ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│      UNIFY          │ ─▶ │     CHUNK           │ ─▶ │     EMBED           │
│  (Unify)            │    │  (data_ingestor)    │    │  (per-application)  │
│  OCR Orchestration  │    │  Fusion & Trust     │    │  Vector Indexing    │
│  Full Layout        │    │  Multi-Engine       │    │  Embeddings         │
│  Reading Order      │    │  RAG Chunking       │    │  Semantic Search    │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

Prepare-Doc makes no OCR decisions. It provides structured, validated metadata so Unify can
select the right engine, reading order strategy, and table extraction approach per page.

---

## 2. Two-Stage Processing Architecture

The core design insight is that **image quality assessment and content analysis cannot be done
reliably on an uncorrected image**. A document rotated 90° will fool a script detector, produce
invalid IQA metrics, and trigger false negatives in a text detection gate. Low resolution makes
every other analysis unreliable. Prepare-Doc therefore splits processing into two stages.

### Stage 1 — Pre-correction Gate

> **Diagram**: [production-runtime/prepare-doc-primary-workflow-detailed.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed.puml)
> — detailed activity diagram covering Stage 0 document routing through corrections and output.

**Model**: MobileNetV4-Conv-S | **Latency**: ~3ms GPU, ~12ms CPU
**Implementation**: `src/image_preprocessing_detector/models/skew_estimator.py`
**Config**: `config/skew_estimation.yaml`
**Training script**: `modal/train_skew_estimator.py`
**Trained checkpoint**: Best model val MAE = 0.837° (epoch 47, run `20260212_155402`)

**Note on Stage 0**: Before Stage 1 runs, a fast Document Type Router classifies the incoming
document (< 20ms CPU). Six tracks are possible: `native_text`, `born_digital`, `hybrid`,
`scanned`, `scanned_image`, and `born_digital_degraded`. The last track is a common source of
confusion:

> **Naming note — `born_digital_degraded`**: This does **not** mean "a physically degraded
> document". It means "a PDF that PASSES format detection as born-digital but FAILS text-layer
> quality validation". The validation checks word recognition rate, character entropy, and
> ToUnicode map integrity. "Degraded" refers to the text layer's OCR-processability, not the
> document's physical condition. A pristine, freshly-printed PDF with a corrupt ToUnicode map
> routes here. ~18% of born-digital submissions fall into this track and are redirected into the
> image pipeline.

`native_text` and validated `born_digital` documents skip Stage 1 entirely via the fast path.

**Note on Step 1b**: After rasterization and before MobileNetV4 inference, pages are converted
to lossless PNG format. This ensures the model receives a clean, artifact-free input regardless
of the source compression format.

Runs on the raw, uncorrected image. Three prediction heads:

| Head | Type | Output | Threshold |
| ---- | ---- | ------ | --------- |
| Orientation | 4-class cls | 0° / 90° / 180° / 270° | Confidence > 0.9 to apply |
| Fine skew | Regression | ±10°, sub-0.5° residual target | Apply if \|angle\| > 0.3° |
| Resolution quality | Regression (0–1) | Character-height-aware score | Upscale if < 0.4 |

Resolution quality scale: 0.0 = characters < 16px (unusable), 0.3 = 16–24px (marginal),
0.5 = 24–32px (adequate), 0.7 = 32–48px (optimal for OCR), 1.0 = >96px (oversized).
DPI bounds (150–600) serve as safety rails, not the primary criterion.

Physical corrections applied based on Stage 1 predictions:

- **Rotation** — `src/image_preprocessing_detector/correction/corrections.py`
- **Deskew** (Hough transform) — `src/image_preprocessing_detector/correction/corrections.py`
- **CLAHE contrast enhancement** — `src/image_preprocessing_detector/correction/corrections.py`
- **Border removal** — `src/image_preprocessing_detector/correction/border_removal.py`
- **Perspective correction** — `src/image_preprocessing_detector/correction/perspective_correction.py`
- **Resolution upscaling** (5 OpenCV algorithms) — `src/image_preprocessing_detector/ingestion/pdf_upscaler.py`

### Stage 2 — Full Multi-Task Analysis

> **Diagram**: [production-runtime/prepare-doc-primary-workflow-detailed.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed.puml)
> — SigLIP 2 inference section, fallback rules, and confidence thresholds.
> **Schema population**: [schema-field-population/schema-field-population-workflow.puml](architecture/diagrams/level-2/schema-field-population/schema-field-population-workflow.puml)
> — maps each of the 19 heads to `DocumentMetadata` fields.

**Model**: SigLIP 2 NAFlex (88M params) | **Latency**: ~50ms GPU
**Implementation**: `src/image_preprocessing_detector/detection/siglip2_multitask.py`
**Training script**: `modal/train_siglip2_multitask.py` (2,652 LOC)
**Config**: `config/siglip2_multitask.yaml`

Runs on the corrected image. A single forward pass drives all 19 prediction heads across
5 task groups:

| Group | Head | Type | Classes / Range | Feeds |
| ----- | ---- | ---- | --------------- | ----- |
| **1: IQA** | Blur severity | Regression | 0–1 | DQS |
| | Noise severity | Regression | 0–1 | DQS |
| | Contrast severity | Regression | 0–1 | DQS |
| | Skew severity | Regression | 0–1 (see note ①) | DQS |
| | Compression artifacts | Regression | 0–1 | DQS |
| | Overall quality | Regression | 0–1 | DQS, routing |
| **2: Script** | Script class | Classification | 27 trainable scripts (30 total; Mong/Syrc/Geor OOD-reserved) Phase 1: 10 grouped ML classes | OCR engine selection |
| **3: Orientation** | Coarse orientation | Classification | 4 classes | See note ② |
| | Fine skew | Regression | ±10° (see note ①) | See note ② |
| **4: Handwriting** | Presence | Classification | none / sparse / moderate / substantial / dominant | Handwriting OCR routing |
| | Legibility | Classification | n/a / illegible / poor / fair / good / excellent | Escalation |
| | Content type | Classification | printed / cursive / mixed / annotation / diagram_label | Engine selection |
| | Presence score | Regression | 0–1 (area ratio) | — |
| | Legibility score | Regression | 0–1 (quality) | — |
| **5: Page Attrs** | Capture method | Classification | 7 classes (see §4.4) | Artifact type prediction |
| | Shadow severity | Regression | 0–1 | Correction escalation |
| | Warping severity | Regression | 0–1 | Correction escalation |
| | Code content ratio | Regression | 0–1 | Code-aware OCR routing |
| | Resolution quality | Regression | 0–1 (see note ③) | Resolution validation |

> **① Skew head disambiguation** — Two heads measure skew but serve different purposes:
>
> - **Group 1 "Skew severity"** is a *quality degradation signal* (0–1, where 1 = severely skewed).
>   It answers "how bad is the skew problem?" and feeds the DQS degradation score.
> - **Group 3 "Fine skew"** predicts the *actual rotation angle in degrees* (±10°).
>   It answers "how many degrees to rotate to fix it?" and feeds the correction step.
>
> Both are necessary: Group 1 tells the DQS that a problem exists; Group 3 tells the correction
> pipeline how to solve it.
>
> **② Why SigLIP 2 has redundant orientation, skew, and resolution heads** — Group 3 duplicates
> MobileNetV4's orientation and skew outputs, and Group 5 duplicates its resolution_quality output.
> This is deliberate design with four distinct purposes:
>
> 1. **Teacher signal**: SigLIP 2 soft labels (Group 3 + Group 5) train MobileNetV4 during
>    Step 3 of the virtuous training cycle (KL-divergence, T=3). These heads are required for that
>    pipeline — without them, there is no teacher signal to distill into MobileNetV4.
> 2. **Validation**: The system compares MobileNetV4 and SigLIP 2 predictions; large divergence
>    (e.g., orientation mismatch > 1 class, skew divergence > 2°) flags the page for human review.
> 3. **CPU-only fallback**: When MobileNetV4 is unavailable (CPU-constrained path), SigLIP 2
>    handles orientation, skew, and resolution in a single pass — no pre-correction stage needed.
>    This degrades GPU latency from ~53ms to ~50ms but eliminates the pre-correction stage entirely.
> 4. **Self-consistency**: SigLIP 2 verifies that the correction was applied correctly before
>    computing IQA and handwriting scores on the (now corrected) image.
>
> **③ Resolution quality (Group 5)** is explicitly redundant with MobileNetV4 Head 3 for the
> same 4 reasons above. It uses the same 0–1 character-height-aware scale.

**`has_non_latin` and `has_rtl` are rule-derived outputs**, not separate ML heads. They are
computed from `script_class` using the ISO 15924 lookup table in
`schema_utils/iso_language_script.py`. (`has_non_latin` = script ∉ {Latn, Cyrl}; `has_rtl` =
script ∈ {Arab, Hebr, Thaa, …}.) They do not consume model capacity.

**Script ML classes**: The full universe is **30 ISO 15924 script codes** — 28 from OpenLID's
language coverage plus Mongolian (Mong) and Syriac (Syrc). Three are permanently OOD-reserved
(Mong, Syrc, Geor), leaving **27 trainable scripts**. Phase 1 groups these into **10 ML class
labels** for initial training. Configured in `config/script_ml_classes.yaml`. Mapping from
ISO 15924 codes to ML classes handled by
`src/image_preprocessing_detector/schema_utils/script_ml_mapping.py`.

**Running in parallel** with Stage 2, eight classical IQA detectors in
`src/image_preprocessing_detector/detection/iqa_classical.py` provide interpretable,
sub-25ms outputs as baseline anchors:

| Detector | Method |
| -------- | ------ |
| Blur | Laplacian variance |
| Noise | Local standard deviation |
| Contrast | Histogram spread |
| JPEG blockiness | DCT coefficient analysis |
| Illumination | Regional luminance variance |
| Binarization artifacts | Threshold quality analysis |
| Bleed-through | Cross-channel correlation |
| Skew | Hough line transform |

**Classical handwriting fallback**: `iqa_classical.py` also contains a stroke-analysis-based
handwriting detector (stroke width variance on connected components + run-length encoding on
binarized image). This detector activates when **any** SigLIP 2 Group 4 head returns confidence
below 0.5. It outputs `has_handwriting` (bool) and `handwriting_confidence` (0–1). Its output
overrides the low-confidence Group 4 predictions for downstream routing decisions.

### Complete Pipeline Flow

> **Diagrams**:
>
> - [production-runtime/prepare-doc-primary-workflow-high-level.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-high-level.puml) — condensed overview
> - [production-runtime/prepare-doc-primary-workflow-detailed.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed.puml) — full activity diagram with routing branches
> - [level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml](architecture/diagrams/level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml) — workstream context

```text
PDF/Image Input
        │
        ▼
[pdf_analyzer.py] — DPI detection (PyMuPDF)
        │
        ├─ Below 300 DPI ──▶ [pdf_upscaler.py] — upscale (lanczos/bicubic/linear/cubic/area)
        │
        ▼
[document_processor.py] — Standardize to 300 DPI images
        │
        ▼
[pdf_type_classifier.py] ── STAGE 0: Document Type Router
    ├── native_text / born_digital ──▶ Fast path to Unify (skip preprocessing)
    ├── born_digital_degraded ────────▶ Image pipeline (corrupt text layer)
    ├── scanned / scanned_image ──────▶ Image pipeline
    └── hybrid ───────────────────────▶ Image pipeline (per-page routing)
        │
        ▼ (image pipeline only)
[Step 1b: lossless PNG conversion]
        │
        ▼
[skew_estimator.py / MobileNetV4] ── STAGE 1
    ├── Orientation (4-class)
    ├── Fine skew (regression)
    └── Resolution quality (0-1)
        │
        ▼
[corrections.py + border_removal.py + perspective_correction.py]
        │
        ▼ (corrected image)
┌────────────────────────────────────────────────────┐
│                  PARALLEL INFERENCE                │
│                                                    │
│  [siglip2_multitask.py]   [iqa_classical.py]      │
│   ~50ms GPU                ~25ms CPU               │
│   19 heads / 5 groups      8 detectors             │
│                                                    │
│  [doclayout_yolo.py]      [layout_lite/]           │
│   Layout detection         Coarse page attrs       │
└────────────────────────────────────────────────────┘
        │
        ▼
[dqs_calculator.py] — Document Quality Score (degradation + complexity)
        │
        ▼
[recommendation_engine.py + script_router.py + docling_router.py]
    — 4 routing strategies: ocr_fast / ocr_advanced / vision_simple / vision_structured
        │
        ▼
[json_generator.py] ── DocumentMetadata.json + corrected images ──▶ Unify
```

**Total latency**: ~55–65ms GPU (3ms Stage 1 + 50ms Stage 2 + I/O overhead).

---

## 3. Source Module Map

All modules live under `src/image_preprocessing_detector/`. Key canonical files:

### Detection (`detection/`)

| File | Purpose |
| ---- | ------- |
| `text_gate.py` | Fast text presence gate < 10ms (stroke density + CC + edge density) |
| `iqa_classical.py` | 8 classical IQA detectors, all < 25ms combined |
| `iqa_ml.py` | ResNet-50 teacher / ResNet-18 student IQA (Phase 3, stable) |
| `siglip2_multitask.py` | SigLIP 2 multi-task inference (19 heads, 5 groups) |
| `orientation_detector.py` | 4-class orientation detection |
| `script_detector.py` | ISO 15924 script classification heuristics |
| `handwriting_detector.py` | Handwriting presence detection (stroke analysis) |
| `shadow_detector.py` | Shadow / lighting gradient detection |
| `warping_detector.py` | Perspective / warping distortion detection (94.7% F1, ships as heuristic) |
| `code_detector.py` | QR / barcode / machine code presence |
| `blank_page_detector.py` | Blank / near-blank page detection |
| `discrepancy.py` | ML vs classical IQA discrepancy analyzer with escalation logic |
| `hybrid_iqa.py` | Adaptive weighting of classical + ML IQA scores |
| `doclayout_yolo.py` | Layout detection (transitional file — docling-layout egret-large / heron in use; YOLOv10-doc superseded in Stream 3) |
| `layout_lite/analyzer.py` | Layout-lite pipeline orchestrator (11 DocLayNet classes) |
| `layout_lite/layout_types.py` | Page layout type classification |
| `layout_lite/table_detector.py` | Table presence and complexity |
| `layout_lite/figure_detector.py` | Figure / image element detection |
| `layout_lite/fuzzy_scan_detector.py` | Fuzzy scan artifact detection |
| `layout_lite/watermark_detector.py` | Watermark presence |

### Ingestion (`ingestion/`)

| File | Purpose |
| ---- | ------- |
| `pdf_analyzer.py` | Pre-flight DPI analysis orchestrator |
| `pdf_resolution.py` | PyMuPDF DPI detection (100% accuracy validated) |
| `pdf_upscaler.py` | OpenCV upscaling — 5 algorithms, page-by-page, < 2GB memory |
| `document_processor.py` | Main pipeline: PDF/image → standardized 300 DPI images |
| `image_loader.py` | Single image loading with metadata extraction |

### Correction (`correction/`)

| File | Purpose |
| ---- | ------- |
| `corrections.py` | Core transforms: deskew, CLAHE, sharpening, denoising; transform history |
| `border_removal.py` | Crop scanner / camera borders from document edges |
| `perspective_correction.py` | Fix perspective distortion (camera captures) |

### Classification (`classification/`)

| File | Purpose |
| ---- | ------- |
| `pdf_type_classifier.py` | 3-class PDF type: image_only / born_digital / hybrid |
| `pdf_image_detector.py` | Image vs text content detection within PDFs |
| `pdf_text_extractor.py` | Text extraction for classification |

### Routing and Metrics (`routing/`, `metrics/`)

| File | Purpose |
| ---- | ------- |
| `routing/recommendation_engine.py` | 4-strategy OCR routing based on DQS + pdf_type + complexity |
| `routing/docling_router.py` | Docling CLI parameter generation from analysis results |
| `routing/script_router.py` | Tier 3 script → OCR engine mapping (config-driven, `config/script_routing.yaml`) |
| `routing/psm_recommender.py` | Tesseract PSM selection |
| `metrics/dqs_calculator.py` | Document Quality Score: degradation + structural complexity aggregation |

### Output (`output/`)

| File | Purpose |
| ---- | ------- |
| `output/json_generator.py` | Serialize `DocumentMetadata.json`, write corrected images, attach routing metadata |

### Models (`models/`)

| File | Purpose |
| ---- | ------- |
| `models/skew_estimator.py` | MobileNetV4-Conv-S definition — 3 heads (orientation, skew, resolution) |
| `models/onnx_runtime.py` | ONNX Runtime inference (zero-VRAM CPU path) |

### Workers, API, and Orchestration

| File | Purpose |
| ---- | ------- |
| `workers/celery_app.py` | Celery application: 3 queues (default, gpu, batch) |
| `workers/tasks.py` | Task definitions with GPU / batch routing |
| `orchestration/` | Pipeline integration layer |
| `api/routes/` | FastAPI endpoints (Phase 5, 23 stubs pending) |
| `drift/active_learning.py` | High-entropy sample harvesting |
| `drift/retraining.py` | Model retraining triggers |
| `drift/alerting.py` | Drift alerting with Prometheus integration |

### Utils

| File | Purpose |
| ---- | ------- |
| `utils/device_probe.py` | CUDA / Metal GPU detection, fallback chain |
| `utils/device_orchestration.py` | Device policy enforcement with budget caps |
| `utils/budget_enforcement.py` | GPU cost tracking (doc / batch / monthly levels) |
| `utils/tensor_cache.py` | Memory-efficient tensor caching for batch inference |
| `utils/gcs_uploader.py` | GCS bucket upload utilities |
| `utils/log_config.py` | Structlog + Rich console integration |
| `utils/path_security.py` | Symlink attack prevention |

---

## 4. Schema and Data Contract

### 4.1 Output Schema — `DocumentMetadata`

**Canonical file**: `src/image_preprocessing_detector/schema.py`

> **Diagram**: [schema-field-population/schema-field-population-workflow.puml](architecture/diagrams/level-2/schema-field-population/schema-field-population-workflow.puml)
> — traces how each of the 16 SigLIP heads, 8 classical detectors, Stage 0 router, and
> MobileNetV4 heads populate individual fields in `DocumentMetadata.json`.
> Summary view: [schema-field-population/schema-field-population-summary.puml](architecture/diagrams/level-2/schema-field-population/schema-field-population-summary.puml)

All output is serialized to `DocumentMetadata.json`. Key Pydantic v2 models:

**`DetectedIssue`** — A single quality issue on a page:

- `issue_type`: `IssueType` enum (NOISE, BLUR, SKEW, PERSPECTIVE, LOW_CONTRAST,
  ORIENTATION, LOW_DPI)
- `severity`: `IssueSeverity` (LOW / MEDIUM / HIGH / CRITICAL)
- `confidence`: float 0–1
- `bbox`: `[x, y, width, height]` — COCO format

**`DocumentElement`** — A layout element detected on a page:

- `category`: `ElementCategory` (11 DocLayNet classes: CAPTION, FOOTNOTE, FORMULA,
  LIST_ITEM, PAGE_FOOTER, PAGE_HEADER, PICTURE, SECTION_HEADER, TABLE, TEXT, TITLE;
  plus HANDWRITING, IMAGE, TEXT_BLOCK)
- `bbox`: `[x, y, width, height]` — COCO format (required for Unify LayoutParser)
- `quality_issues`: list of `DetectedIssue` (element-level hybrid IQA)

**`PageMetadata`** — Per-page analysis output:

- `detected_issues`: list of `DetectedIssue`
- `elements`: list of `DocumentElement`
- `orientation`: `OrientationAngle` (UPRIGHT / ROTATED_90 / ROTATED_180 / ROTATED_270)
- `skew_angle`, `blur_score`, `contrast_score`, `noise_score`
- `layout_type`, `has_tables`, `has_figures`, `has_dense_math`, `has_handwriting`

**`DocumentMetadata`** — Complete document output record:

- `document_type`: `DocumentType` (IMAGE / PDF / OFFICE_*)
- `pdf_type`: image_only / born_digital / hybrid
- `dpi_input`, `dpi_effective`
- `overall_quality`: 0–1 aggregate score
- `dqs`: Document Quality Score (degradation + structural complexity)
- `pre_ocr_risk`: 0–1 combined risk for OCR failure
- `ocr_routing_recommendation`: ocr_fast / ocr_advanced / vision_simple / vision_structured
- `docling_params`: structured params for docling-layout integration
- `detected_languages`: list of ISO 639-1 codes
- `scripts`: list of ISO 15924 script codes
- `transform_history`: list of applied corrections with parameters
- `pages`: list of `PageMetadata`

> **COCO bbox contract**: All bounding boxes use `[x, y, width, height]` format throughout —
> **never** `[x1, y1, x2, y2]`. This is required for LayoutParser compatibility in Unify.

### 4.2 Schema Utilities

**Location**: `src/image_preprocessing_detector/schema_utils/`

These modules standardize the metadata types used across the system. They follow a consistent
pattern: YAML-driven config, singleton accessor with `lru_cache`, hot-reload support.

| Module | Purpose | Key Config |
| ------ | ------- | ---------- |
| `script_ml_mapping.py` | ISO 15924 code → ML training class (Tier 2 of 3-tier architecture) | `config/script_ml_classes.yaml` |
| `layout_taxonomy.py` | 57-class canonical layout hub: DocLayNet ↔ Docling ↔ PubLayNet ↔ D4LA ↔ DocSynth300K | `config/layout_taxonomy.yaml` |
| `iso_language_script.py` | ISO 639-1/3 language codes, ISO 15924 script codes, script families | — |
| `iso_paper_sizes.py` | ISO 216 paper size detection from pixel dimensions + DPI | — |
| `text_scope.py` | Text granularity (PAGE / PARAGRAPH / LINE / WORD / CHARACTER) with content type | — |
| `bbox_utils.py` | COCO ↔ YOLO ↔ PASCAL bounding box conversion and standardization | — |
| `degradation_mapping.py` | 45-dim Layer 2 degradation vector → runtime issue types + severity | — |
| `dataset_source.py` | Dataset registry, sample provenance, license and capture method tracking | — |
| `resolution_quality.py` | Character-height-aware resolution scoring via PaddleOCR + KDE mode | — |
| `openlid_integration.py` | OpenLID-v2 language detection (108+ languages, ISO 639-3 aligned) | — |
| `split_registry.py` | Global SHA256-keyed split registry to prevent cross-dataset train/test leakage | — |
| `validation.py` | JSON Schema validation for `DocumentMetadata` and Layer 2 enrichments | — |

### 4.3 Three-Tier Script Architecture

Script information is represented at three distinct tiers, kept independently configurable:

- **Tier 1 (Storage)**: Full ISO 15924 codes (e.g., `Latn`, `Arab`, `Hans`). Never aggregated.
  Stored in Layer 2 metadata and `DocumentMetadata.scripts`.

- **Tier 2 (ML Training)**: ~10–18 configurable ML class labels (e.g., `LATN`, `ARAB`,
  `CJK_SIMPLIFIED`). Defined in `config/script_ml_classes.yaml`, mapped by
  `schema_utils/script_ml_mapping.py`. Changing training classes does not require schema changes.

- **Tier 3 (OCR Routing)**: Configurable script → engine policy. Defined in
  `config/script_routing.yaml`, applied by `routing/script_router.py`. Changing routing
  policy requires no retraining.

### 4.4 Capture Method Classification

The Page Attributes capture method head assigns one of seven classes:

| Class | Description |
| ----- | ----------- |
| born_digital | Rendered PDF — no physical capture artifacts |
| scanner_flatbed | Flatbed scanner — JPEG bands, slight geometric distortion |
| scanner_adf | ADF scanner — skew, occasional page-edge artifacts |
| camera_smartphone | Smartphone camera — shadow gradients, perspective warp |
| camera_dedicated | Dedicated camera — higher quality, still has perspective |
| synthetic | Programmatically generated — known provenance |
| unknown | Cannot classify |

---

## 5. Configuration Reference

All YAML configs live in `config/`. They are loaded via `resolve_config_path()` pattern with
singleton + `lru_cache` for performance.

| File | Purpose | Key Sections |
| ---- | ------- | ------------ |
| `siglip2_multitask.yaml` | SigLIP 2 multi-task teacher — backbone + 5 head groups | `model.backbone`, `heads.{iqa,script,source,orientation,shadow,warping}`, `training.phase1/2` |
| `script_ml_classes.yaml` | ISO 15924 → ML class mapping (19 classes) | `ml_classes`, `iso15924_to_ml_class`, `unmapped_default`, `class_weights` |
| `layout_taxonomy.yaml` | 57-class canonical layout hub with cross-schema mappings | `canonical_classes` (57 entries), `schema_mappings` (6 external schemas), `uncertainty_thresholds` |
| `script_routing.yaml` | Tier 3: ML script class → OCR engine (fully configurable policy) | `routing_policies`, `engine_selection`, `fallback_chains` |
| `skew_estimation.yaml` | MobileNetV4-Conv-S — 3 heads, inference settings | `model`, `training` (50 epochs), `inference.batch_size`, `inference.quantization` |
| `agent_orchestration.yaml` | Device priority policy + cost budget caps | `device_policy`, `budget_caps.doc_level`, `budget_caps.batch_level`, `budget_caps.monthly` |
| `training_criticality.yaml` | Training task priority ordering for ILP allocation | `criticality_levels` (P0 IQA+Script, P1 Orientation+Skew, P2 Page Attrs) |
| `iaa_gold_standard.yaml` | Inter-annotator agreement thresholds for dataset validation | `iaa_thresholds` (κ / ICC targets per task) |
| `audit_scorecard.yaml` | Dataset audit rubric (scoring dimensions, pass criteria) | `audit_dimensions`, `pass_criteria`, `scoring_weights` |

---

## 6. What the System Detects

### Image Quality Assessment

> **Diagram**: [monitoring-drift/monitoring-drift-architecture.puml](architecture/diagrams/level-2/monitoring-drift/monitoring-drift-architecture.puml)
> — per-head prediction distribution monitoring, PLCC-drop alerting, and active learning harvest.

Six IQA regression heads produce 0–1 scores for blur, noise, contrast, skew severity,
compression artifacts, and an overall quality composite. Combined with the eight classical
detectors in `iqa_classical.py`, these feed the Document Quality Score (`metrics/dqs_calculator.py`):

```text
DQS = w₁ · degradation_score + w₂ · structural_complexity_score
```

DQS drives the four-strategy routing decision: `ocr_fast` (DQS > 0.8), `ocr_advanced`
(DQS 0.5–0.8, complex layout), `vision_simple` (image-dominant, high quality),
`vision_structured` (complex tables / figures, lower quality).

### Script and Language Detection

The Phase 1 script classifier uses 10 grouped ML classes to identify the primary writing system.
This drives OCR engine selection in Unify. The full scope is **30 ISO 15924 script codes** (28
from OpenLID's language coverage + Mongolian + Syriac), of which **27 are trainable** (Mongolian,
Syriac, and Georgian are permanently OOD-reserved). Phase 2 expands from 10 grouped ML classes
to all 27 trainable scripts without backbone retraining.

Script taxonomy documentation: `docs/planning/SCRIPT_TAXONOMY.md`
Script ML class config: `config/script_ml_classes.yaml`
ISO 15924 reference: `schema_utils/iso_language_script.py`

#### SigLIP 2 Script Outputs → Docling Parameters

The following table maps SigLIP 2 outputs to downstream Docling OCR parameters. This is the
mechanism by which Prepare-Doc metadata drives routing decisions in Unify.

| SigLIP 2 Output | Docling Parameter Affected | Notes |
| --------------- | -------------------------- | ----- |
| `script_code = "Hans"` or `"Hant"` | `ocr_engine: "paddleocr"`, `ocr_lang: "ch"` | PaddleOCR excels at CJK |
| `script_code = "Arab"` | `ocr_engine: "paddleocr"`, `ocr_lang: "ara"` | Arabic-optimized OCR |
| `script_code = "Deva"` | `ocr_engine: "paddleocr"`, `ocr_lang: "hi"` | Hindi/Nepali |
| `script_code = "Jpan"` | `ocr_engine: "paddleocr"`, `ocr_lang: "japan"` | Japanese OCR |
| `script_code = "Tibt"` | `pipeline: "vlm"` | No production Tibetan OCR engine; VLM is the only viable path |
| `has_non_latin = true` | `page_batch_size: reduced` | CJK/Arabic models require more GPU memory |
| `has_rtl = true` | Layout engine RTL mode | Arabic/Hebrew reading-order correction |
| `handwriting.presence >= MODERATE` | `ocr_routing: "ocr_advanced"` or `"vision_simple"` | Handwriting requires dedicated handling |
| `handwriting.legibility <= FAIR` | `pipeline: "vlm"` | Poor legibility; VLM generalizes better than OCR engines |
| `shadow_score > 0.3` | Trigger DocRes shadow removal pre-pass | Severe shadow degrades all OCR engines equally |
| `warping_score > 0.3` | Trigger DocRes dewarping pre-pass | Geometric correction before OCR |
| `code_confidence > 0.5` | `enrich_code: true` | Enable code syntax detection in Docling |
| `orientation != 0` (Group 3) | Auto-rotate before OCR handoff | SigLIP self-consistency check; correction already applied in Stage 1 |
| `capture_method = CAMERA_*` | Adjust correction thresholds | Expect perspective warp + shadow gradient artifacts |
| `IQA overall_quality < 0.5` | `ocr_routing: "vision_structured"` | Low overall quality; structured vision model handles degradation better |

Configuration for the script → engine mapping lives in `config/script_routing.yaml` and is
applied by `routing/script_router.py`.

### Warping Detection

Warping binary detection is handled by the heuristic `detection/warping_detector.py`
(94.7% F1, Stream 3 Go/No-Go: PASS). The SigLIP warping regression head adds continuous
severity (0–1) and per-type accuracy improvement over the WarpDoc benchmark. Binary detection
does not require a trained model; only severity does.

---

## 7. Training Infrastructure

> **Diagrams**:
>
> - [model-training/prepare-doc-training-workflow-high-level.puml](architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-high-level.puml) — end-to-end training workflow (data → train → arena → deploy)
> - [model-training/prepare-doc-distillation.puml](architecture/diagrams/level-2/model-training/prepare-doc-distillation.puml) — SigLIP 2 → MobileCLIP-2 distillation cascade
> - [model-training/prepare-doc-training-infrastructure.puml](architecture/diagrams/level-2/model-training/prepare-doc-training-infrastructure.puml) — Modal GPU infrastructure and cost controls
> - [data-preparation/stream-4c-dataset-preparation.puml](architecture/diagrams/level-2/data-preparation/stream-4c-dataset-preparation.puml) — Stream 4C dataset assembly pipeline
> - [level-3/model-training/model-training-swimlane.puml](architecture/diagrams/level-3/model-training/model-training-swimlane.puml) — module-level swimlane with LOC annotations

### Modal Training Scripts (`modal/`)

| Script | Purpose | Status |
| ------ | ------- | ------ |
| `train_siglip2_multitask.py` | SigLIP 2 teacher (5 task groups, 8 active heads + expanding to 16) | Active — awaiting dataset manifests |
| `train_siglip2_iqa_v2.py` | SigLIP 2 IQA base (overall, sharpness, color — VQualA 0.886) | Complete |
| `train_skew_estimator.py` | MobileNetV4-Conv-S (orientation, skew, resolution) | Complete — val MAE 0.837° |
| `train_phase6_layout_lite.py` | Layout-lite YOLO training | Legacy — pre-trained model used |
| `app.py` | Modal infrastructure definition | Config |

**Training manifest contract** (must be followed exactly for `train_siglip2_multitask.py`):

```json
[
  {
    "image_path": "script/images/img_0001.jpg",
    "script": "LATN",
    "source": "scanned",
    "orientation": 0,
    "shadow": 0.3,
    "warping": 0.1,
    "split_type": "train"
  }
]
```

- Format: **flat JSON list** — NOT `{"samples": [...]}`
- `image_path`: relative to `/data/` (Modal Volume mount at `multitask-datasets`)
- `split_type`: must be one of `train` / `val` / `test` / `ood` — REQUIRED field
- OOD leakage validation runs at manifest write time via `_validate_manifest_no_ood()`

### Dataset Assembly Scripts (`scripts/`)

Phase 1 — View generation (scripts written, not yet run):

| Script | Output |
| ------ | ------ |
| `generate_v3_shadow_view.py` | 8K shadow images (4 types: edge/cast/spotlight/scanner_lid) |
| `generate_v3_warping_view.py` | 5K warped images (perspective/page_curl/fold) |
| `derive_v3_orientation_view.py` | 20K non-Latin orientation synthetics with sidecar `orientation_class` |
| `build_orientation_real_component.py` | 11K real orientation images via DocLayNet + RVL-CDIP PDFs |

Phase 2 — Severity labeling (partially complete):

| Script | Status |
| ------ | ------ |
| `label_shadow_severity.py` | Running — sd7k ~3h remaining |
| `label_warping_severity.py` | Complete for warpdoc; wsrd queued |
| `label_resolution_quality.py` | Complete for DIQA-5000 (5,499 images) |
| `integrate_resolution_quality.py` | Integrates labels into L2 metadata |

Phase 3 — Manifest assembly (not yet implemented):

| Script | Purpose |
| ------ | ------- |
| `prepare_multitask_datasets.py` | 6 Click sub-commands: script / source / orientation / shadow / warping / merge |
| `generate_multitask_labels.py` | **Phase A (SigLIP 2 training)**: merge all 5 task manifests into unified training manifest. **Phase B (student distillation)**: run trained SigLIP 2 inference to generate soft pseudo-labels for MobileCLIP-2 student training — see §9 Distillation |

Schema and taxonomy scripts:

| Script | Purpose |
| ------ | ------- |
| `standardize_layout_labels.py` | Convert layout labels across schemas via `layout_taxonomy.py` |
| `audit_layout_labels.py` | Validate layout label conversions |
| `audit_v3_per_script_counts.py` | Audit script-level counts in synth-multiscript-v3 |
| `audit_font_coverage.py` | Audit font coverage across generated scripts |
| `evaluate_dataset_diversity.py` | Generate Dataset Diversity Reports (DDRs) |
| `aggregate_layer2_metadata.py` | Aggregate Layer 2 stats (capture method, domain, content flags) |

### Training Datasets

| Dataset | Images | Purpose | Status |
| ------- | ------ | ------- | ------ |
| Orientation | 50,000 | MobileNetV4 Head 1 + SigLIP Group 3 | ✅ GCS-ready |
| Skew | 90,412 | MobileNetV4 Head 2 + SigLIP Group 3 | ✅ GCS-ready, val MAE 0.837° |
| Resolution quality | 30K target / 5.5K done | MobileNetV4 Head 3 + SigLIP Group 5 | ⚠️ V2 labeling in progress |
| IQA curated | 16K target / ~14K done | SigLIP Group 1 | ⚠️ VLM pilot complete |
| IQA synthetic | 100K | SigLIP Group 1 | ❌ Requires pseudo-labels |
| Script detection | 108K | SigLIP Group 2 | ⚠️ Generating from synth-multiscript-v3 |
| Shadow | 15K | SigLIP Group 5 | ❌ Pending severity labeling |
| Warping | 20K | SigLIP Group 5 | ❌ Pending wsrd labels |
| Handwriting | 60K | SigLIP Group 4 | ❌ Deferred |
| Capture method | 50K | SigLIP Group 5 | ❌ Deferred |

Source datasets: `docs/datasets/DATASET_QUICK_REFERENCE.md` (51 source datasets, 57 with L2 metadata)
Training datasets: `docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md`
GCS bucket: `gs://image_detection_b/`

---

## 8. Why the Design Can Be Trusted

### Heuristic-First Validation

No ML head was added without first measuring whether a classical heuristic could adequately
solve the problem. All candidates were benchmarked in Stream 3 (`docs/planning/STREAM_4_IMPLEMENTATION_PLAN.md`):

| Detector | Heuristic Performance | Target | Decision |
| -------- | --------------------- | ------ | -------- |
| Script detection | 15.6% accuracy | 80% | ML head required |
| Document source classification | 64.7% accuracy | 85% | ML head required |
| Shadow detection | 60.1% F1 | 85% | ML head required |
| Warping detection | 94.7% F1 | 80% | Ships as heuristic; ML adds severity |
| Orientation detection | ~85% accuracy | 98%+ target | ML head required |

### Dataset Diversity Validation

All 10 training datasets are evaluated across 14 diversity dimensions before admission to
training. Each receives a formal Dataset Diversity Report (DDR) generated by
`scripts/evaluate_dataset_diversity.py`. Dimensions:

capture_method · domain · script_family · script_code · resolution_range · text_density ·
layout_type · content_flags · degradation_type · content_type · paper_size ·
**color_mode** (binarized/grayscale/color) · **document_age** (modern/aged/historical) ·
handwriting_characteristics

Full specification: `docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md`

### OOD Holdout Design

Three scripts permanently reserved from all training and validation sets:

| Script | ISO | Distinguishing property |
| ------ | --- | ---------------------- |
| Mongolian Traditional | Mong | Top-to-bottom directionality |
| Syriac | Syrc | Right-to-left with distinct letterform clusters |
| Georgian | Geor | Unique letterforms, no cognate in other scripts |

OOD evaluation covers 7 distribution shift categories: script, geometry, resolution, domain,
degradation type, capture method, historical variants. All images are SHA256 + perceptual hash
(Hamming ≤ 5) deduplicated against training sets. Registry: `metadata_registry/ood_registry.jsonl`.
Full design: `docs/planning/OOD_DATASET_DESIGN.md`

### Two-Model Confound Elimination

Running a single model on uncorrected images creates correlations between rotation and all
other attributes (IQA metrics, script orientation, layout geometry). The two-stage design
ensures SigLIP 2 only ever processes images where orientation and resolution have been
addressed. Similarly, resolution is scored by character height (the OCR-relevant metric),
not DPI (a proxy that fails for miniaturized or large-print documents).

---

## 9. Production Reliability

### Device Priority and Budget Control

> **Diagrams**:
>
> - [production-runtime/prepare-doc-device-selection-flow.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-device-selection-flow.puml) — device priority decision tree and fallback chain
> - [production-runtime/prepare-doc-worker-architecture.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-worker-architecture.puml) — Celery worker pool with GPU/batch/default queues

**Config**: `config/agent_orchestration.yaml`
**Implementation**: `utils/device_orchestration.py`, `utils/budget_enforcement.py`

Inference falls back through: Local GPU → Modal serverless GPU → Local CPU. A budget
enforcement layer tracks costs at doc, batch, and monthly levels. The orchestration logic
is fully testable via a mock device interface.

### Monitoring and Drift Detection

> **Diagram**: [monitoring-drift/monitoring-drift-architecture.puml](architecture/diagrams/level-2/monitoring-drift/monitoring-drift-architecture.puml)
> — full monitoring architecture: per-head drift detection, PLCC alerting thresholds, active
> learning harvest pipeline, and retraining trigger logic.
> Level 3 detail: [level-3/monitoring-drift/monitoring-drift-swimlane.puml](architecture/diagrams/level-3/monitoring-drift/monitoring-drift-swimlane.puml)

**Implementation**: `drift/` subdirectory — `active_learning.py`, `alerting.py`, `retraining.py`
**Metrics**: Prometheus per-head prediction distribution; Grafana dashboards

When any head's prediction distribution shifts beyond a configured threshold, an alert fires
and high-entropy samples are harvested for active learning review.

### Teacher-Student Distillation Path

> **Diagram**: [model-training/prepare-doc-distillation.puml](architecture/diagrams/level-2/model-training/prepare-doc-distillation.puml)
> — distillation cascade stages, dataset requirements, and graduation criteria.

SigLIP 2 (88M params, ~50ms GPU) is the teacher. The planned production distillation cascade
(**PLANNED — deferred; SigLIP 2 ships to production first before any distillation begins**):

```text
SigLIP 2 NAFlex (88M, ~50ms GPU) — Teacher  [ships first]
        │  soft labels
        ▼
MobileCLIP-2 S4 (~12ms GPU) — Student tier 1  [PLANNED, deferred]
        │  soft labels
        ▼
MobileCLIP-2 S0 (~5ms GPU) — Student tier 2  [PLANNED, deferred]
  (production edge target)
```

Each student stage is trained on soft labels from the stage above, preserving multi-task
prediction quality at lower compute.

---

## 10. Architecture Documentation

The architecture uses a 4-level hierarchy with automated link validation:

| Level | Description | Location |
| ----- | ----------- | -------- |
| 0 | Multi-project RAG pipeline (six-service context) | `docs/architecture/diagrams/level-0/` |
| 1 | Prepare-Doc architecture and 8-workstream overview | `docs/architecture/diagrams/level-1/` |
| 2 | Workstream details ("Level 2.5" standard with code examples) | `docs/architecture/diagrams/level-2/` |
| 3 | Module implementation swimlanes with LOC annotations | `docs/architecture/diagrams/level-3/` |

**Maintenance guide**: `docs/architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md`
**File inventory**: `docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md`
**LOC extraction**: `scripts/extract_workstream_loc.sh`
**Link validation**: `scripts/validate_architecture_links.sh`

### Level 0 — RAG Pipeline Context

| Diagram | Description |
| ------- | ----------- |
| [rag-pipeline-overview.puml](architecture/diagrams/level-0/rag-pipeline-overview.puml) | Six-service pipeline: Ingest → Prepare-Doc → Prepare-Audio → Unify → Chunk → Embed |

### Level 1 — Prepare-Doc System Overview

| Diagram | Description |
| ------- | ----------- |
| [PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml](architecture/diagrams/level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml) | All 8 workstreams, primary production flow, supporting feedback loops |
| [PREPARE_DOC_WORKFLOW_HIERARCHY.puml](architecture/diagrams/level-1/PREPARE_DOC_WORKFLOW_HIERARCHY.puml) | Workstream dependency hierarchy and execution order |

### Level 2 — Workstream Detail (WS 1: Production Runtime)

| Diagram | Description |
| ------- | ----------- |
| [production-runtime/prepare-doc-primary-workflow-high-level.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-high-level.puml) | Condensed end-to-end pipeline overview |
| [production-runtime/prepare-doc-primary-workflow-detailed.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed.puml) | Full activity diagram: Stage 0 router, Stage 1, Stage 2, corrections, DQS, output |
| [production-runtime/prepare-doc-device-selection-flow.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-device-selection-flow.puml) | Device priority decision tree: Local GPU → Modal → CPU fallback + budget gates |
| [production-runtime/prepare-doc-worker-architecture.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-worker-architecture.puml) | Celery worker pool: default / gpu / batch queues with routing logic |
| [production-runtime/prepare-doc-primary-workflow-test-coverage.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-test-coverage.puml) | Test coverage overlay on primary workflow |
| [production-runtime/prepare-doc-primary-workflow-detailed-test-coverage.puml](architecture/diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed-test-coverage.puml) | Test coverage overlay on detailed workflow |

### Level 2 — Workstream Detail (WS 2: Model Training)

| Diagram | Description |
| ------- | ----------- |
| [model-training/prepare-doc-training-workflow-high-level.puml](architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-high-level.puml) | End-to-end training: dataset assembly → Modal train → arena → registry → deploy |
| [model-training/prepare-doc-training-infrastructure.puml](architecture/diagrams/level-2/model-training/prepare-doc-training-infrastructure.puml) | Modal GPU infrastructure, GCS integration, cost controls |
| [model-training/prepare-doc-distillation.puml](architecture/diagrams/level-2/model-training/prepare-doc-distillation.puml) | SigLIP 2 → MobileCLIP-2 S4 → S0 distillation cascade (PLANNED, deferred) |
| [model-training/prepare-doc-training-workflow-v2.puml](architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-v2.puml) | Updated training workflow with multi-task head expansion |
| [model-training/prepare-doc-training-workflow-test-coverage.puml](architecture/diagrams/level-2/model-training/prepare-doc-training-workflow-test-coverage.puml) | Test coverage overlay on training workflow |

### Level 2 — Workstream Detail (WS 3: Data Preparation)

| Diagram | Description |
| ------- | ----------- |
| [data-preparation/prepare-doc-training-data-ingestion.puml](architecture/diagrams/level-2/data-preparation/prepare-doc-training-data-ingestion.puml) | Dataset ingestion and cataloging pipeline |
| [data-preparation/stream-4c-dataset-preparation.puml](architecture/diagrams/level-2/data-preparation/stream-4c-dataset-preparation.puml) | Stream 4C: 5-task manifest assembly for SigLIP 2 training |
| [data-preparation/resolution-quality-labeling-pipeline.puml](architecture/diagrams/level-2/data-preparation/resolution-quality-labeling-pipeline.puml) | PaddleOCR + KDE mode character-height labeling pipeline |
| [data-preparation/skew-orientation-labeling-pipeline.puml](architecture/diagrams/level-2/data-preparation/skew-orientation-labeling-pipeline.puml) | Skew and orientation label generation from classical + synthetic |
| [data-preparation/automated-data-labeling-pipeline.puml](architecture/diagrams/level-2/data-preparation/automated-data-labeling-pipeline.puml) | Automated labeling orchestration across all task heads |
| [data-preparation/l2-metadata-enrichment.puml](architecture/diagrams/level-2/data-preparation/l2-metadata-enrichment.puml) | Layer 2 metadata enrichment: 45-dim degradation vector + diversity fields |
| [data-preparation/metadata-schema-architecture.puml](architecture/diagrams/level-2/data-preparation/metadata-schema-architecture.puml) | Complete L2 metadata schema structure and field taxonomy |

### Level 2 — Workstream Detail (WS 4: Pseudo-Labeling)

| Diagram | Description |
| ------- | ----------- |
| [pseudo-labeling/diqa-training-phases.puml](architecture/diagrams/level-2/pseudo-labeling/diqa-training-phases.puml) | DIQA model training phases for pseudo-label generation |
| [pseudo-labeling/diqa-inference-pipeline.puml](architecture/diagrams/level-2/pseudo-labeling/diqa-inference-pipeline.puml) | DIQA inference pipeline for unlabeled dataset scoring |
| [pseudo-labeling/diqa-checkpoint-selection.puml](architecture/diagrams/level-2/pseudo-labeling/diqa-checkpoint-selection.puml) | Checkpoint selection criteria and validation strategy |
| [pseudo-labeling/diqa-pseudo-labeling-workflow.puml](architecture/diagrams/level-2/pseudo-labeling/diqa-pseudo-labeling-workflow.puml) | End-to-end pseudo-label workflow: inference → ensemble → threshold |
| [pseudo-labeling/soft-label-pipeline-integration.puml](architecture/diagrams/level-2/pseudo-labeling/soft-label-pipeline-integration.puml) | Soft label integration into SigLIP 2 training manifests |

### Level 2 — Workstream Detail (WS 5: Labeling & Benchmarking Models)

| Diagram | Description |
| ------- | ----------- |
| [labeling-benchmarking/domain-classification-pipeline.puml](architecture/diagrams/level-2/labeling-benchmarking/domain-classification-pipeline.puml) | Domain classification labeling pipeline (TAX / FIN / SCI / EDU etc.) |

### Level 2 — Workstream Detail (WS 6: Model Arena)

| Diagram | Description |
| ------- | ----------- |
| [model-arena/model-arena-architecture.puml](architecture/diagrams/level-2/model-arena/model-arena-architecture.puml) | Three-phase arena: base eval → cross-validation → drift check; PLCC > 0.65 gate |

### Level 2 — Workstream Detail (WS 7: Monitoring & Drift)

| Diagram | Description |
| ------- | ----------- |
| [monitoring-drift/monitoring-drift-architecture.puml](architecture/diagrams/level-2/monitoring-drift/monitoring-drift-architecture.puml) | Per-head distribution monitoring, PLCC alerting, active learning harvest, retraining triggers |

### Level 2 — Workstream Detail (WS 8: Synthetic Generation)

| Diagram | Description |
| ------- | ----------- |
| [synthetic-generation/synthetic-generation-architecture.puml](architecture/diagrams/level-2/synthetic-generation/synthetic-generation-architecture.puml) | Synth-multiscript-v3 generator: 19 script classes, 7 DPI tiers, hybrid augmentation |

### Level 2 — Schema Field Population

| Diagram | Description |
| ------- | ----------- |
| [schema-field-population/schema-field-population-workflow.puml](architecture/diagrams/level-2/schema-field-population/schema-field-population-workflow.puml) | How each detector/head populates `DocumentMetadata` fields |
| [schema-field-population/schema-field-population-summary.puml](architecture/diagrams/level-2/schema-field-population/schema-field-population-summary.puml) | Summary matrix: source → field mapping |

### Level 2 — Downstream Context (Informational)

| Diagram | Description |
| ------- | ----------- |
| [downstream-context/unify-ocr-layout-workflow.puml](architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml) | Unify (OCR orchestration): how it consumes `DocumentMetadata.json` |
| [downstream-context/chunk-fusion-chunking-workflow.puml](architecture/diagrams/level-2/downstream-context/chunk-fusion-chunking-workflow.puml) | Chunk service: multi-engine fusion and RAG chunking |
| [downstream-context/embed-vectorstore-workflow.puml](architecture/diagrams/level-2/downstream-context/embed-vectorstore-workflow.puml) | Embed service: vector indexing pipeline |
| [downstream-context/prepare-audio-transcription-workflow.puml](architecture/diagrams/level-2/downstream-context/prepare-audio-transcription-workflow.puml) | Prepare-Audio: FFmpeg + Deepgram, diarization, TranscriptMetadata |

### Level 3 — Module Implementation Swimlanes

| Diagram | Description |
| ------- | ----------- |
| [level-3/production-runtime/production-runtime-swimlane.puml](architecture/diagrams/level-3/production-runtime/production-runtime-swimlane.puml) | WS1 module swimlane with LOC annotations |
| [level-3/model-training/model-training-swimlane.puml](architecture/diagrams/level-3/model-training/model-training-swimlane.puml) | WS2 module swimlane with LOC annotations |
| [level-3/data-preparation/data-preparation-swimlane.puml](architecture/diagrams/level-3/data-preparation/data-preparation-swimlane.puml) | WS3 module swimlane with LOC annotations |
| [level-3/pseudo-labeling/pseudo-labeling-swimlane.puml](architecture/diagrams/level-3/pseudo-labeling/pseudo-labeling-swimlane.puml) | WS4 module swimlane with LOC annotations |
| [level-3/synthetic-generation/synthetic-generation-swimlane.puml](architecture/diagrams/level-3/synthetic-generation/synthetic-generation-swimlane.puml) | WS8 module swimlane with LOC annotations |
| [level-3/monitoring-drift/monitoring-drift-swimlane.puml](architecture/diagrams/level-3/monitoring-drift/monitoring-drift-swimlane.puml) | WS7 module swimlane with LOC annotations |

PlantUML diagrams are generated with:

```bash
java -jar ~/.vscode-server/extensions/jebbs.plantuml-2.18.1/plantuml.jar -tsvg <file.puml>
```

---

## 11. Technical Stack

| Component | Technology | File | Design Rationale |
| --------- | ---------- | ---- | ---------------- |
| Pre-correction gate | MobileNetV4-Conv-S | `models/skew_estimator.py` | ~3ms GPU; orientation/resolution before SigLIP |
| Multi-task teacher | SigLIP 2 NAFlex (88M) | `detection/siglip2_multitask.py` | Vision-language pretraining; 19 heads one pass |
| IQA legacy models | ResNet-50/18 teacher-student | `detection/iqa_ml.py` | Stable Phase 3 models; superseded by SigLIP for new tasks |
| Layout detection | docling-layout (egret-large / heron) | `detection/doclayout_yolo.py` (transitional) | Validated over YOLOv10-doc in Stream 3 |
| Classical IQA | OpenCV (8 detectors) | `detection/iqa_classical.py` | Sub-25ms combined; interpretable; stream-3-validated baseline |
| PDF ingestion | PyMuPDF | `ingestion/pdf_resolution.py` | DPI-aware; metadata-rich; 100% DPI accuracy |
| Image processing | OpenCV + Pillow | `ingestion/pdf_upscaler.py`, `correction/corrections.py` | Geometric corrections, CLAHE, 5 upscaling algorithms |
| Script taxonomy | 3-tier ISO 15924 architecture | `schema_utils/script_ml_mapping.py`, `config/script_ml_classes.yaml` | Tier independence: storage / training / routing configurable separately |
| Layout taxonomy | 57-class canonical hub | `schema_utils/layout_taxonomy.py`, `config/layout_taxonomy.yaml` | Cross-schema conversion: DocLayNet ↔ Docling ↔ PubLayNet |
| Schema | Pydantic v2 + JSON | `schema.py` | Type-safe; COCO-aligned bboxes; versioned Unify contract |
| Training platform | Modal A10G/A100 | `modal/train_siglip2_multitask.py` | Serverless GPU; budget-controlled; GCS integration |
| Dataset storage | Google Cloud Storage | `utils/gcs_uploader.py` | `gs://image_detection_b/` — training manifests + images |
| Task orchestration | Celery + Redis | `workers/celery_app.py`, `workers/tasks.py` | 3 queues: default / gpu / batch |
| Monitoring | Prometheus + Grafana | `monitoring/` | Per-head distribution drift; retraining triggers |
| Language detection | OpenLID-v2 | `schema_utils/openlid_integration.py` | 108+ languages; ISO 639-3 aligned |
| Annotation pipeline | Custom parsers (50+ datasets) | `annotation/parsers/` | Layer 2 metadata enrichment across 57 source datasets |

---

*For implementation progress and remaining work, see
[docs/planning/MASTER_PROJECT_PLAN.md](planning/MASTER_PROJECT_PLAN.md).*

*For dataset inventory and training recipes, see
[docs/datasets/DATASET_QUICK_REFERENCE.md](datasets/DATASET_QUICK_REFERENCE.md).*

*For architecture diagrams at all four levels, see
[docs/architecture/](architecture/).*
