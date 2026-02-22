---
title: Prepare-Doc (foundry-prepare-doc) — System Overview (Detailed Reference)
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

Prepare-Doc (foundry-prepare-doc) is the **preprocessing, IQA, and coarse layout gateway** for a six-service RAG
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
│  • Image quality assessment (16 heads) │
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
│  (foundry-unify)    │    │  (foundry-chunk)    │    │  (foundry-embed)    │
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

**Model**: MobileNetV4-Conv-S | **Latency**: ~3ms GPU, ~12ms CPU
**Implementation**: `src/image_preprocessing_detector/models/skew_estimator.py`
**Config**: `config/skew_estimation.yaml`
**Training script**: `modal/train_skew_estimator.py`
**Trained checkpoint**: Best model val MAE = 0.837° (epoch 47, run `20260212_155402`)

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

**Model**: SigLIP 2 NAFlex (88M params) | **Latency**: ~50ms GPU
**Implementation**: `src/image_preprocessing_detector/detection/siglip2_multitask.py`
**Training script**: `modal/train_siglip2_multitask.py` (2,652 LOC)
**Config**: `config/siglip2_multitask.yaml`

Runs on the corrected image. A single forward pass drives all 16 prediction heads across
5 task groups:

| Group | Head | Type | Classes / Range | Feeds |
| ----- | ---- | ---- | --------------- | ----- |
| **1: IQA** | Blur severity | Regression | 0–1 | DQS |
| | Noise severity | Regression | 0–1 | DQS |
| | Contrast severity | Regression | 0–1 | DQS |
| | Skew severity | Regression | 0–1 | DQS |
| | Compression artifacts | Regression | 0–1 | DQS |
| | Overall quality | Regression | 0–1 | DQS, routing |
| **2: Script** | Script class | Classification | 10 classes (Phase 1) | OCR engine selection |
| **3: Orientation** | Coarse orientation | Classification | 4 classes | MobileNetV4 validation |
| | Fine skew | Regression | ±10° | MobileNetV4 validation |
| **4: Handwriting** | Presence | Classification | none / partial / dominant | Handwriting OCR routing |
| | Legibility | Classification | unreadable / poor / fair / good / excellent | Escalation |
| | Content type | Classification | printed / cursive / mixed / annotation / diagram_label | Engine selection |
| | Density | Regression | 0–1 | — |
| | Script family | Regression | Latin / CJK / Arabic / Devanagari / Cyrillic / etc. | — |
| **5: Page Attrs** | Capture method | Classification | 7 classes (see §4.4) | Artifact type prediction |
| | Shadow severity | Regression | 0–1 | Correction escalation |
| | Warping severity | Regression | 0–1 | Correction escalation |
| | Code content ratio | Regression | 0–1 | Code-aware OCR routing |
| | Effective resolution | Regression | 0–1 | Resolution validation |

**Script ML classes** (Phase 1, 10 classes): Configured in `config/script_ml_classes.yaml`.
Mapping from ISO 15924 codes to ML classes handled by
`src/image_preprocessing_detector/schema_utils/script_ml_mapping.py`.
Reserved OOD scripts (never trained): Mongolian (Mong), Syriac (Syrc), Georgian (Geor).

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

### Complete Pipeline Flow

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
[pdf_type_classifier.py] — image_only / born_digital / hybrid
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
│   16 heads / 5 groups      8 detectors             │
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
| `siglip2_multitask.py` | SigLIP 2 multi-task inference (16 heads, 5 groups) |
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

The 10-class script classifier (Phase 1) identifies the primary writing system. This
determination drives OCR engine selection in Unify. The architecture expands to 108
OpenLID-aligned classes in Phase 2 without backbone retraining.

Script taxonomy documentation: `docs/planning/SCRIPT_TAXONOMY.md`
Script ML class config: `config/script_ml_classes.yaml`
ISO 15924 reference: `schema_utils/iso_language_script.py`

### Warping Detection

Warping binary detection is handled by the heuristic `detection/warping_detector.py`
(94.7% F1, Stream 3 Go/No-Go: PASS). The SigLIP warping regression head adds continuous
severity (0–1) and per-type accuracy improvement over the WarpDoc benchmark. Binary detection
does not require a trained model; only severity does.

---

## 7. Training Infrastructure

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
| `generate_multitask_labels.py` | Merge all 5 task manifests into unified training manifest |

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

**Config**: `config/agent_orchestration.yaml`
**Implementation**: `utils/device_orchestration.py`, `utils/budget_enforcement.py`

Inference falls back through: Local GPU → Modal serverless GPU → Local CPU. A budget
enforcement layer tracks costs at doc, batch, and monthly levels. The orchestration logic
is fully testable via a mock device interface.

### Monitoring and Drift Detection

**Implementation**: `drift/` subdirectory — `active_learning.py`, `alerting.py`, `retraining.py`
**Metrics**: Prometheus per-head prediction distribution; Grafana dashboards

When any head's prediction distribution shifts beyond a configured threshold, an alert fires
and high-entropy samples are harvested for active learning review.

### Teacher-Student Distillation Path

SigLIP 2 (88M params, ~50ms GPU) is the teacher. The planned production distillation cascade:

```text
SigLIP 2 NAFlex (88M, ~50ms GPU) — Teacher
        │  soft labels
        ▼
MobileCLIP-2 S4 (~12ms GPU) — Student tier 1
        │  soft labels
        ▼
MobileCLIP-2 S0 (~5ms GPU) — Student tier 2 (production edge target)
```

Each student stage is trained on soft labels from the stage above, preserving multi-task
prediction quality at lower compute.

---

## 10. Architecture Documentation

The architecture uses a 4-level hierarchy with automated link validation:

| Level | Description | Location |
| ----- | ----------- | -------- |
| 0 | Multi-project RAG pipeline (Projects A–D context) | `docs/architecture/diagrams/level-0/` |
| 1 | Prepare-Doc architecture and 8-workstream overview | `docs/architecture/diagrams/level-1/` |
| 2 | Workstream details ("Level 2.5" standard with code examples) | `docs/architecture/diagrams/level-2/` |
| 3 | Module implementation swimlanes with LOC annotations | `docs/architecture/diagrams/level-3/` |

**Maintenance guide**: `docs/architecture/ARCHITECTURE_MAINTENANCE_GUIDE.md`
**File inventory**: `docs/architecture/FILE_INVENTORY_WITH_WORKSTREAM_MAPPINGS.md`
**LOC extraction**: `scripts/extract_workstream_loc.sh`
**Link validation**: `scripts/validate_architecture_links.sh`

Key Level 2 diagrams by topic:

| Topic | File |
| ----- | ---- |
| Data preparation pipeline | `diagrams/level-2/data-preparation/prepare-doc-training-data-ingestion.puml` |
| Training workflow | `diagrams/level-2/model-training/prepare-doc-training-workflow-high-level.puml` |
| Distillation cascade | `diagrams/level-2/model-training/prepare-doc-distillation.puml` |
| Production runtime (detailed) | `diagrams/level-2/production-runtime/prepare-doc-primary-workflow-detailed.puml` |
| Schema field population | `diagrams/level-2/schema-field-population/schema-field-population-workflow.puml` |
| Resolution quality labeling | `diagrams/level-2/data-preparation/resolution-quality-labeling-pipeline.puml` |
| Skew/orientation labeling | `diagrams/level-2/data-preparation/skew-orientation-labeling-pipeline.puml` |
| Stream 4C dataset preparation | `diagrams/level-2/data-preparation/stream-4c-dataset-preparation.puml` |
| L2 metadata enrichment | `diagrams/level-2/data-preparation/l2-metadata-enrichment.puml` |

PlantUML diagrams are generated with:

```bash
java -jar ~/.vscode-server/extensions/jebbs.plantuml-2.18.1/plantuml.jar -tsvg <file.puml>
```

---

## 11. Technical Stack

| Component | Technology | File | Design Rationale |
| --------- | ---------- | ---- | ---------------- |
| Pre-correction gate | MobileNetV4-Conv-S | `models/skew_estimator.py` | ~3ms GPU; orientation/resolution before SigLIP |
| Multi-task teacher | SigLIP 2 NAFlex (88M) | `detection/siglip2_multitask.py` | Vision-language pretraining; 16 heads one pass |
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
