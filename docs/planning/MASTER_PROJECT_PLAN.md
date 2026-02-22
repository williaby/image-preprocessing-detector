---
title: Master Project Plan
schema_type: common
status: active
owner: core-maintainer
purpose: "Consolidated roadmap: completed work, current status, and remaining work for Project A."
tags:
- planning
- roadmap
- status
---

# Master Project Plan

> **Supersedes**: [PROJECT_PLAN.md](PROJECT_PLAN.md) and
> [PHASE_10_11_RESTRUCTURED_PLAN.md](PHASE_10_11_RESTRUCTURED_PLAN.md)
>
> **Last Updated**: 2026-02-22
>
> **For system narrative** (what the system does and why its design is sound), see
> [docs/PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md).

---

## 1. Project Mission

Project A is the **preprocessing, IQA, and coarse layout gateway** in a four-project RAG
document pipeline. It accepts raw documents in any condition — rotated, blurred, shadowed,
photographed — and delivers corrected page images plus a `DocumentMetadata.json` record to
Project B (OCR Orchestration). Every downstream project depends on the accuracy of this output.

```text
Project A (THIS REPO)     →    Project B          →    Project C         →    Project D
Preprocessing & IQA              OCR Orchestration       Fusion & Trust         Vector Indexing
─────────────────────           ─────────────────       ──────────────         ───────────────
IQA & Corrections               Full Layout             Multi-Engine           Embeddings
Script Detection                Reading Order           Fusion                 Vector DB
Orientation/Skew                Table Structure         Trust Scoring          Search
Handwriting Analysis            Multi-Engine OCR        RAG Chunking
Page Attribute Classification
Routing Metadata

OUTPUT:
DocumentMetadata.json
+ Corrected Images
```

**Current architecture** (as of Feb 2026): a two-model ML pipeline — MobileNetV4-Conv-S
(~3ms GPU) as a fast pre-correction gate for orientation, skew, and resolution, followed by
SigLIP 2 NAFlex (88M params, ~50ms GPU) as a multi-task teacher covering IQA, script,
handwriting, and page attributes — sitting atop a classical heuristic layer that provides
interpretable baseline signals for all eight core IQA dimensions.

---

## 2. How We Got Here

### Foundation Phases (2024 Q4 – 2025 Q2): Phases 0–6 Complete

The project began as a classical computer vision pipeline with a phased implementation plan
(Phases 0–9). The foundation delivered a fully working preprocessing and IQA system:

- **Ingestion**: PyMuPDF PDF extraction, DPI detection, automatic upscaling for sub-300 DPI inputs
- **Classical IQA**: 8 detectors (skew, blur, contrast, noise, illumination, JPEG blockiness,
  binarization, bleed-through), all validated with < 25ms combined latency
- **ML IQA**: ResNet-50 teacher (val_loss=0.27) and ResNet-18 student (val_loss=0.14), trained
  on OHR-Bench via Modal GPU
- **Layout-lite**: YOLOv10-doc for coarse page attribute detection (11 DocLayNet classes)
- **Routing**: Document Quality Score (DQS) calculation, 4-strategy OCR routing engine
- **PDF type classification**: image_only / born_digital / hybrid
- **Corrections**: Deskew, CLAHE, sharpening, denoising, border removal, perspective correction
- **Production hardening**: Celery worker pool, device-priority execution (Local GPU → Modal GPU
  → CPU), budget enforcement, Prometheus metrics, drift detection, active learning pipeline

All original phases (0–1C, 2, 3, 4, 6) are stable, tested, and in production use.

### Architecture Evolution (2025 Q3 – 2026 Q1): Restructuring into Value Streams

Stream 3 Go/No-Go benchmarking revealed that the original pipeline had significant capability
gaps: script detection heuristics achieved only 15.6% accuracy; document source classification
reached 64.7%; shadow detection 60.1% F1. These results made clear that a more capable ML
architecture was necessary.

The original phase structure was retired in favour of eight parallel value streams, each
deliverable independently:

| Stream | Name | Scope |
| ------ | ---- | ----- |
| 1 | Foundation & Schema | Schema utils, script taxonomy, annotation system |
| 2 | Heuristic Detectors | 11 detector modules (shadow, warping, orientation, etc.) |
| 3 | Benchmarking | Go/No-Go decisions for all candidate heuristics |
| 4A | Teacher Model Architecture | SigLIP 2 multi-task training script |
| 4B | Dataset Assembly | 10 training datasets, manifests, GCS upload |
| 4C | OOD & Diversity | Dataset Diversity Reports, OOD holdout design |
| 5 | DoclingRouter | Docling-layout integration and routing logic |
| 6 | Geometric Corrections | Perspective correction, border removal |
| 7 | Pseudo-Labeling | DocIQ architecture for ~2.5M unlabelled images |
| 8 | Student Distillation | MobileCLIP-2 S4 → S0 cascade from SigLIP 2 teacher |

Key architectural decisions made during this restructuring:

- **SigLIP 2 NAFlex** replaces the ResNet teacher-student pair for IQA, expanding coverage
  to 16 heads across 5 task groups (IQA, Script, Orientation+Skew, Handwriting, Page Attrs)
- **MobileNetV4-Conv-S** is added as a fast pre-correction gate before SigLIP 2
- **docling-layout** (egret-large / heron) replaces YOLOv10-doc for layout detection
- **YOLOv10-doc** remains stable and deployed; it will be replaced in a future stream

### Dataset Complexity (2026 Q1): The Ongoing Challenge

Building the 10 training datasets required for SigLIP 2 has proven substantially harder than
originally estimated. Key problems encountered:

- The synth-multiscript-v3 generator had a bug causing severe per-script imbalance (Arabic
  generated 49K images; 17 of 27 scripts fell below their 12,963 target). Fixed in Feb 2026.
- L2 metadata enrichment (which provides labels for capture method, shadow severity, warping
  severity, etc.) requires significant compute and has been running across 57+ source datasets.
- Shadow and warping severity labeling (via PaddleOCR-based pipelines) is still in progress as
  of Feb 2026, blocking the assembly of the shadow and warping training manifests.
- The planning documents accumulated organically across this work — leading to the current
  situation where no single document captures the full picture.

---

## 3. Current Architecture

```text
Raw Input (any format: PDF, DOCX, HTML, image, audio, ...)
        │
        ▼
[Stage 0: Document Type Router] <20ms CPU  ◄── NEW — previously missing
    ├── Format detection (MIME type + content signature)
    ├── PDF sub-classification:
    │       born_digital | scanned | hybrid | born_digital_degraded
    ├── Routing outcome A: native text + born-digital PDFs → Unify (fast path, skip IQA)
    ├── Routing outcome B: images + scanned/hybrid PDFs → image pipeline (below)
    └── Routing outcome C: audio → PrepareAudio (separate ASR pipeline)
        │
        ▼ (images and image-like documents only)
[Pre-flight] PyMuPDF DPI detection
        │
        ▼
[MobileNetV4-Conv-S] ~3ms GPU
    ├── Orientation (4-class)
    ├── Fine skew (regression ±10°)
    └── Resolution quality (char-height-aware 0-1)
        │
        ▼
[Physical Corrections]
    ├── Rotate (if orientation ≠ 0°, confidence > 0.9)
    ├── Deskew (Hough transform, if |angle| > 0.3°)
    ├── Upscale (if resolution_quality < 0.4)
    └── CLAHE, border removal, denoising
        │
        ▼ (corrected image)
[SigLIP 2 NAFlex 88M] ~50ms GPU ──────── [Classical IQA] ~25ms CPU
    ├── Group 1: IQA (6 heads)                ├── Blur (Laplacian variance)
    ├── Group 2: Script (1 cls, 10 classes)   ├── Noise (local std dev)
    ├── Group 3: Orientation (1 cls + 1 reg)  ├── Contrast (histogram)
    ├── Group 4: Handwriting (3 cls + 2 reg)  ├── JPEG blockiness
    └── Group 5: Page Attrs (1 cls + 4 reg)   ├── Illumination uniformity
                                               ├── Binarization artifacts
[docling-layout] ~25ms GPU                    ├── Bleed-through
    └── Coarse layout + table/figure flags    └── Skew (Hough)
        │
        ▼
[DQS Calculation] Degradation + structural complexity → 0-1 score
        │
        ▼
[Routing Engine] → ocr_fast / ocr_advanced / vision_simple / vision_structured
        │
        ▼
DocumentMetadata.json + Corrected Images → Project B
```

**Key files**:

- Training script: `modal/train_siglip2_multitask.py` (2,652 LOC, ready to run)
- Training config: `config/siglip2_multitask.yaml`
- Dataset assembly: `scripts/prepare_multitask_datasets.py` (5 sub-commands, not yet written)
- Heuristic detectors: `src/image_preprocessing_detector/detection/`
- Classical IQA: `src/image_preprocessing_detector/detection/iqa_classical.py`
- Schema utils: `src/image_preprocessing_detector/schema_utils/`

---

## 4. Completed Work

| Component | Stream / Phase | Key Deliverables | Status |
| --------- | -------------- | ---------------- | ------ |
| Foundation pipeline (ingestion, corrections, CLI) | Phases 0–1C | Ingestion, text gate, 8 IQA detectors, correction pipeline | ✅ |
| ML IQA teacher-student (ResNet) | Phase 3 | ResNet-50 teacher (val_loss=0.27), ResNet-18 student (val_loss=0.14) | ✅ |
| Layout-lite + routing + DQS | Phase 2 | YOLOv10-doc, 4-strategy routing, DQS calculator | ✅ |
| Device-priority execution | Phase 4 | Celery workers, Modal GPU integration, budget enforcement | ✅ (98%) |
| Drift detection and monitoring | Phase 6 | Drift alerts, active learning pipeline, Prometheus metrics | ✅ (95%) |
| Schema utils | Stream 1 | layout_taxonomy.py, script_ml_mapping.py, ISO 15924, paper sizes | ✅ |
| Heuristic detectors | Stream 2 | 11 detector modules (shadow, warping, source, orientation, etc.) | ✅ |
| Go/No-Go benchmarking | Stream 3 | All 5 candidate heuristics benchmarked; decisions confirmed | ✅ |
| SigLIP 2 training architecture | Stream 4A | train_siglip2_multitask.py (8 heads, 5 groups) | ✅ |
| OOD holdout design | Stream 4C | ood_registry.jsonl, OOD_DATASET_DESIGN.md, 8/10 DDRs | ✅ |
| Geometric corrections | Stream 6 | perspective_correction.py, border_removal.py | ✅ |
| Orientation training dataset | — | 50K images, 4-class balanced, GCS-ready | ✅ |
| Skew training dataset | — | 90,412 images (71K synth + 19K natural), GCS-ready, val MAE=0.837° | ✅ |
| L2 metadata enrichment | — | 57/58 datasets enriched with capture method, domain, quality fields | ✅ |
| Annotation system refactoring | Stream 1 | Modular annotation package, 802 tests, Phases 1–5 complete | ✅ (85%) |

---

## 5. Remaining Work

### Tier 0 — Prerequisites (in flight)

These are actively running and block the next tier.

#### Shadow severity labeling (~3h GPU remaining)

- **What**: Run `scripts/label_shadow_severity.py` on sd7k (7,239 images) and wsrd (4,500 images)
- **Delivers**: `shadow_severity` field in L2 metadata for all sd7k and wsrd images
- **Warping note**: `label_warping_severity.py` on warpdoc (1,020 images) is already complete;
  wsrd warping labels still queued
- **Unblocks**: Shadow/warping view generation, shadow/warping manifest sub-commands, DDRs #9
  and #10

### Tier 1 — Ready to Start

These can begin once Tier 0 completes, or in parallel for the non-shadow/warping sub-commands.

#### Phase 5: Synthetic view generation

Four generation scripts are already written; they need to be run:

| Script | Output | Status |
| ------ | ------ | ------ |
| `scripts/generate_v3_shadow_view.py` | 8K shadow images from synth-multiscript-v3 | Script ready, not run |
| `scripts/generate_v3_warping_view.py` | 5K warped images from synth-multiscript-v3 | Script ready, not run |
| `scripts/derive_v3_orientation_view.py` | 20K non-Latin orientation synthetics | Script ready, not run |
| `scripts/build_orientation_real_component.py` | 11K real orientation images (DocLayNet + RVL-CDIP) | Script ready, not run |

#### Phase 6: `scripts/prepare_multitask_datasets.py`

This is the primary remaining implementation deliverable. It assembles five training manifests
from processed source datasets and L2 metadata. Each manifest is a flat JSON list (required
format for `modal/train_siglip2_multitask.py`).

Five Click sub-commands:

| Sub-command | Source data | Mixing cap | Notes |
| ----------- | ----------- | ---------- | ----- |
| `script` | MDIW13 (753 images, local) + synth-multiscript-v3 (GCS) | ≤60% synthetic | Computes class weights |
| `source` | L2 `capture_method` field across 57 datasets | — | Maps to scanned/camera/born_digital |
| `orientation` | Phase 5 outputs (real component + synthetic component) | ≥60% real | Validates 4-class balance |
| `shadow` | sd7k + wsrd (real) + generate_v3_shadow_view output (synth) | ≤60% synthetic | Requires Tier 0 first |
| `warping` | warpdoc + anyphotodoc6300 (real) + generate_v3_warping_view (synth) | ≤60% synthetic | Requires Tier 0 for wsrd |

Critical implementation contract (must match `train_siglip2_multitask.py`):

- Manifest format: flat JSON list (NOT `{"samples": [...]}`)
- Required fields: `image_path` (relative to `/data/`), `script`, `source`, `orientation`,
  `shadow`, `warping`, `split_type`
- `split_type` must be one of: `train` / `val` / `test` / `ood`
- OOD leakage check: `_validate_manifest_no_ood()` must pass before any manifest is written
- Dry-run results exist from Phase 4 validation (see `STREAM_4C_DATASET_HANDOFF.md`)

#### Stream 0: Document Type Router (new — architectural gap)

Project A currently assumes all inputs are PDFs or images. Docling accepts 17 format types across
5 behavioral categories. Many formats contain embedded text and require no image preprocessing;
sending them through the IQA pipeline wastes GPU compute and can actively degrade the content.

**What to build**: `src/image_preprocessing_detector/routing/document_type_router.py`

- Promote and generalize the existing `classification/pdf_type_classifier.py` to all formats
- File format detection: file extension + MIME type + content signature
- PDF sub-classification: expand from 3 categories to 4:
  - `born_digital` — valid text layer → fast path to Unify (no preprocessing)
  - `scanned_image` — no text layer; rasterized pages → full image pipeline
  - `hybrid` — mixed pages; per-page routing (scanned pages through image pipeline)
  - `born_digital_degraded` — text layer present but extraction is garbage (missing ToUnicode
    maps, mis-encoded CID fonts); ~18% of "born-digital" PDFs; falls back to image pipeline
  - Detection of degraded: lightweight text validity heuristic (dictionary hit rate or character
    distribution entropy sampling on first N pages)
- Encrypted PDF handling: emit halted `DocumentMetadata.json` (not silent rejection) so downstream
  systems can audit and escalate for manual review
- Audio: route out of Project A entirely before any processing begins

**New schema fields** (added to `DocumentMetadata.json`):

- `document_class`: `native_text | scanned_image | born_digital_pdf | hybrid_pdf | audio | encrypted | unknown`
- `file_format`: specific format identifier (pdf, docx, html, etc.)
- `router_confidence`: float [0,1]
- `page_type_map`: for hybrid PDFs only — array of per-page classifications

**Format routing table**:

| Format group | Examples | Route |
| ------------ | -------- | ----- |
| Native text | DOCX, HTML, MD, LaTeX, CSV, VTT, XML, EPUB | → Unify directly (no IQA) |
| PDF (born-digital) | Native PDF with valid text layer | → Unify directly |
| PDF (hybrid) | Mixed pages | → per-page: scanned pages → image pipeline; born-digital pages → Unify |
| PDF (scanned / degraded) | Scanned books, fax, garbled text layer | → full image pipeline |
| Images | JPG, PNG, TIFF, WebP, BMP | → full image pipeline |
| METS/GBS | Google Books archives | → image pipeline + `requires_advanced_dewarping` flag |
| Audio | WAV, MP3, MP4 | → exclude from Project A; route to PrepareAudio upstream |
| Encrypted | Password-protected PDF | → emit halted metadata; no further processing |

**Future formats to anticipate as native text fast-path**: EPUB, EML/MSG (email), ODT/ODS
(OpenDocument), RTF — register in format detector even if not immediately needed.

**Effort**: 2–3 weeks. No new infrastructure required — builds on PyMuPDF (already in stack).

**Reference**: `tmp_cleanup/docling_format_routing_analysis.md` (full format catalog +
5-model consensus results at 9/10 unanimous endorsement)

#### Stream 5: DoclingRouter

- `src/image_preprocessing_detector/routing/docling_router.py` exists as a stub
- Implement docling-layout integration for egret-large (accuracy) and heron (speed) variants
- Replace YOLOv10-doc in the production pipeline path

### Tier 2 — Requires Tier 1

#### Phase 7: GCS dataset upload

Upload all five task manifests and associated image sets to GCS:

- `gs://image_detection_b/datasets/script_training/`
- `gs://image_detection_b/datasets/source_training/`
- `gs://image_detection_b/datasets/orientation_training/`
- `gs://image_detection_b/datasets/shadow_training/`
- `gs://image_detection_b/datasets/warping_training/`

Each path receives: `train_manifest.json`, `val_manifest.json`, and `test_manifest.json`.

#### SigLIP 2 multi-task training

```bash
# Phase 1: frozen backbone, heads only (15 epochs, ~2-3h on A10G)
uv run modal run modal/train_siglip2_multitask.py --phase 1 --epochs 15

# Phase 2: full fine-tune (30-40 epochs)
uv run modal run modal/train_siglip2_multitask.py

# Monitor
modal app logs siglip2-multitask-training --follow
```

Training uses Kendall uncertainty weighting for multi-task loss balancing and PCGrad gradient
surgery to reduce task conflict. Phased head training: IQA + Script warmup (5 epochs) →
add Orientation + Skew (5 epochs) → full (20–40 epochs) → refine (5–10 epochs).

#### Dataset Diversity Reports for shadow (#9) and warping (#10)

Run `scripts/evaluate_dataset_diversity.py` for shadow and warping datasets after severity
labels are available. These are the final two DDRs; 8 of 10 are already complete.

### Tier 3 — Requires Trained SigLIP 2

#### Stream 7: Pseudo-Labeling

Use the trained SigLIP 2 teacher to generate soft labels across ~2.5M unlabelled source
dataset images. DocIQ architecture (Stage 1 complete; Stage 2 Phase 2 blocked pending
$80–140 budget approval).

#### Stream 8: Student Distillation

Train MobileCLIP-2 S4 from SigLIP 2 soft labels, then distil further to MobileCLIP-2 S0.
Each student stage targets the same 16 prediction heads with progressive latency reduction.

### Remaining Training Datasets (Parallel, Various Blockers)

| Dataset | Done | Target | Next Action | Blocker |
| ------- | ---- | ------ | ----------- | ------- |
| Resolution quality | 5.5K | 30K | Run V2 labeling pipeline (Sauvola + projection profiles) | Compute time |
| IQA curated | ~14K | 16K | Validate VLM prompt v2.0 on 30–50 images; scale if SRCC > 0.60 | Prompt validation |
| IQA synthetic | 0 | 100K | Generate from synth-multiscript-v3 with tier_0 pseudo-labels | Requires Stream 7 |
| Handwriting | 0 | 60K | HierText + IAM + COCO-Text annotation | Deferred beyond Stream 4 |
| Capture method | 0 | 50K | Assemble from L2-enriched datasets by capture_method field | Deferred |
| Shadow | 0 | 15K | Run Phase 5 view generation after Tier 0 | Tier 0 severity labeling |
| Warping | 0 | 20K | warpdoc complete; wsrd warping labels queued | wsrd warping labels |

### Deferred Work (Low Priority)

- **Phase 5 API endpoints**: 23 FastAPI endpoint stubs need implementations. Deferred pending
  training work. The framework (FastAPI + Docker + E2E test suite) is already in place.
- **Load testing and deployment automation**: Pending API endpoint completion.
- **ResNet model optimization (Phase 7 original)**: Superseded by SigLIP 2; not needed.

---

## 6. Dependency Map

```text
[Tier 0] Severity Labeling — sd7k/wsrd shadow (~3h GPU)
    │
    └──▶ shadow_severity + warping_severity in L2 metadata
              │
              ├──▶ Shadow view generation (generate_v3_shadow_view.py)
              ├──▶ Warping view generation (generate_v3_warping_view.py)
              ├──▶ Shadow DDR #9
              └──▶ Warping DDR #10

[Tier 1] Phase 5 View Generation + Phase 6 prepare_multitask_datasets.py
    │
    └──▶ [Tier 2] Phase 7: GCS Upload (5 task paths)
              │
              └──▶ SigLIP 2 Training (Modal A10G/A100)
                        │
                        ├──▶ [Tier 3] Stream 7: Pseudo-Labeling (~2.5M images)
                        │         └──▶ Stream 8: Student Distillation
                        │
                        └──▶ Evaluation vs Heuristic Baselines
                                  └──▶ DoclingRouter integration (Stream 5, parallel)
```

---

## 7. Key Design Decisions (Locked)

These architectural choices are settled. Changes require explicit consensus and version increment.

- **Two-model pipeline (MobileNetV4 pre-correction before SigLIP 2)**: Orientation must be
  corrected before script detection is reliable. SigLIP 2 also carries orientation/resolution
  heads for teacher distillation, validation, and CPU-only fallback.

- **Three-tier script architecture**: Tier 1 stores full ISO 15924 codes; Tier 2 uses ~10–18
  configurable ML training classes; Tier 3 maps to OCR routing targets. Tiers are independently
  configurable; changing routing config does not require retraining.

- **OOD reserved scripts**: Mongolian (Mong), Syriac (Syrc), and Georgian (Geor) are permanently
  excluded from training. They serve as OOD evaluation anchors. A lifecycle protocol tracks
  when a script can transition from OOD to training status.

- **Manifest format (flat JSON list)**: The training script `train_siglip2_multitask.py`
  expects a flat JSON array, not `{"samples": [...]}`. All manifest writers must respect this.

- **Real/synthetic mixing caps (≤60% synthetic, ≥60% real for orientation)**: Enforced in
  `prepare_multitask_datasets.py`. These caps prevent synthetic data from dominating
  distribution in any training task.

- **docling-layout over YOLOv10-doc**: Validated in Stream 3 benchmarking. YOLOv10-doc
  remains deployed in the existing pipeline until DoclingRouter (Stream 5) is complete.

- **Heuristic-first validation**: No ML head is added without a Go/No-Go benchmark confirming
  that classical methods are insufficient. Warping detection (94.7% F1, passed Go/No-Go)
  ships as a heuristic; its ML head only adds severity regression.

- **Stage 0 Document Type Router before all IQA**: Project A accepts any input format docling
  supports (17 format types). Native text formats (DOCX, HTML, MD, LaTeX, CSV, XML, EPUB) and
  born-digital PDFs with valid text layers must bypass the entire image preprocessing pipeline
  and route directly to Unify. Running IQA corrections on these formats wastes GPU compute and
  actively degrades content. PDF sub-classification uses four categories, not three: the fourth
  (`born_digital_degraded`) covers PDFs whose text layer extracts as garbage (~18% of
  "born-digital" PDFs per PDF Association 2025 data) and must fall back to the image pipeline.
  Encrypted PDFs emit a halted `DocumentMetadata.json` record rather than being silently dropped.
  Audio is excluded from Project A entirely and must be routed upstream before reaching this
  service. See Stream 0 in Section 5 for implementation detail.

---

## 8. Reference Index

| Topic | Document |
| ----- | -------- |
| System narrative (what it does, why it's sound) | [docs/PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md) |
| SigLIP 2 architecture detail (16 heads, training data) | [SIGLIP2_MULTITASK_REQUIREMENTS.md](SIGLIP2_MULTITASK_REQUIREMENTS.md) |
| Training optimization (ILP, Kendall, PCGrad) | [TRAINING_OPTIMIZATION_PLAN.md](TRAINING_OPTIMIZATION_PLAN.md) |
| Dataset diversity specs (14 dimensions, DDR framework) | [DATASET_DIVERSITY_REQUIREMENTS.md](DATASET_DIVERSITY_REQUIREMENTS.md) |
| OOD holdout design (reserved scripts, 7 categories) | [OOD_DATASET_DESIGN.md](OOD_DATASET_DESIGN.md) |
| Stream 4 implementation detail | [STREAM_4_IMPLEMENTATION_PLAN.md](STREAM_4_IMPLEMENTATION_PLAN.md) |
| Dataset prep handoff (manifests, GCS paths) | [STREAM_4C_DATASET_HANDOFF.md](STREAM_4C_DATASET_HANDOFF.md) |
| Source dataset catalog | [docs/datasets/DATASET_QUICK_REFERENCE.md](../datasets/DATASET_QUICK_REFERENCE.md) |
| Training dataset catalog | [docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md](../datasets/TRAINING_DATASET_QUICK_REFERENCE.md) |
| Implementation status by planning document | [IMPLEMENTATION_STATUS_MATRIX.md](IMPLEMENTATION_STATUS_MATRIX.md) |
| Stage 0 router: format catalog + consensus | [tmp_cleanup/docling_format_routing_analysis.md](../../tmp_cleanup/docling_format_routing_analysis.md) |
| Architecture diagrams (all four levels) | [docs/architecture/](../architecture/) |
| Historical plan (Phases 0–9, superseded) | [PROJECT_PLAN.md](PROJECT_PLAN.md) |
| Value-stream plan (Streams 1–8, superseded) | [PHASE_10_11_RESTRUCTURED_PLAN.md](PHASE_10_11_RESTRUCTURED_PLAN.md) |
