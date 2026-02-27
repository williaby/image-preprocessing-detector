---
title: Master Project Plan
schema_type: common
status: active
owner: core-maintainer
purpose: "Consolidated roadmap: completed work, current status, and remaining work for Prepare-Doc."
tags:
- planning
- roadmap
- status
---

# Master Project Plan

> **Supersedes**: [PROJECT_PLAN.md](PROJECT_PLAN.md) and
> [PHASE_10_11_RESTRUCTURED_PLAN.md](PHASE_10_11_RESTRUCTURED_PLAN.md)
>
> **Last Updated**: 2026-02-26
>
> **For system narrative** (what the system does and why its design is sound), see
> [docs/PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md).

---

## 1. Service Identity and Mission

**Prepare-Doc** (`foundry-prepare-doc`) is the **preprocessing, IQA, and coarse layout gateway**
in a six-service RAG document pipeline. It accepts raw documents in any condition — rotated,
blurred, shadowed, photographed — and delivers corrected page images plus a
`DocumentMetadata.json` record to Unify. Every downstream service depends on the accuracy of
this output.

```text
Ingest                                                                        (foundry-ingest)
    │ (file upload + workflow trigger)
    ▼
    ├── Native text / born-digital PDFs ────────────────────────────────────────────────────┐
    │                                                                                        │
    ├── Images / scanned PDFs ──▶ Prepare-Doc (foundry-prepare-doc) ──▶ corrected images    │
    │                             IQA, corrections, routing metadata         + metadata ──┐  │
    │                                                                                     │  │
    └── Audio / Video ─────────▶ Prepare-Audio (foundry-prepare-audio) ─▶ transcript ──┐ │  │
                                  FFmpeg + Deepgram Nova-2 + diarization     + metadata ┘ │  │
                                                                                          ▼  ▼
                                                          Unify (foundry-unify) ◄──────────────
                                                          Multi-engine OCR + Docling DOM
                                                                    │
                                                                    ▼
                                                          Chunk (foundry-chunk)
                                                          Trust scoring + RAG chunking
                                                                    │
                                                                    ▼
                                                          Application Embedding
                                                          (per-application — each AI app
                                                           handles embedding per its own needs)
```

### Service Naming Glossary

All documentation uses **service names**, not legacy project identifiers. This table provides
backwards compatibility for readers of older documents.

| Legacy ID | Service Name | Repository | Primary Function |
| --- | --- | --- | --- |
| ~~Project A~~ | **Prepare-Doc** | `foundry-prepare-doc` | Visual quality, corrections, routing metadata (THIS REPO) |
| ~~Project B~~ | **Unify** | `foundry-unify` | Multi-engine OCR, Docling DOM unification |
| ~~Project C~~ | **Chunk** | `foundry-chunk` | Semantic chunking, trust scoring |
| ~~Project D~~ | **Embed** | *(application-specific)* | Per-app embedding — not a shared foundry service |
| ~~Project E~~ | **Prepare-Audio** | `foundry-prepare-audio` | Audio transcription, speaker diarization |
| ~~Project F~~ | **Ingest** | `foundry-ingest` | Web UI, file upload, Cloud Workflows triggering |

**Naming rules**: Use service names in all documentation and code. Legacy IDs appear only in
`docs/_archived/` with ~~strikethrough~~ notation.

### Two-Stage Pipeline

Prepare-Doc's image pipeline applies corrections in two stages:

**Stage 1 — Pre-Correction Gate** (MobileNetV4, before SigLIP 2):

- MobileNetV4 detects orientation (4-class), skew (regression ±10°), and resolution quality
- Corrections applied: rotation, deskew, DPI upscaling
- **Why these must come first**: SigLIP 2's downstream heads (script, IQA, handwriting) are
  unreliable on rotated, skewed, or sub-resolution images. MobileNetV4 corrects the conditions
  that would impair SigLIP 2's ability to do its job.

**Stage 2 — Full Analysis + Remaining Corrections** (SigLIP 2 + Classical IQA, on corrected
image):

- SigLIP 2 (19 heads) + classical IQA (8 detectors) + layout-lite produce all fields in
  `DocumentMetadata.json`
- SigLIP 2 and classical IQA outputs **also trigger additional corrections** within Prepare-Doc:
  IQA blur/noise/contrast scores drive CLAHE enhancement, sharpening, and denoising; Group 5
  shadow/warping scores can trigger shadow removal and dewarping before the image moves
  downstream
- The final corrected images + metadata are delivered to Unify
- **Architectural boundary for OCR routing**: Prepare-Doc delivers rich metadata signals and
  Unify translates them into docling configuration (engine selection, CLI flags, VLM model
  choice). `DoclingRoutingEngine` in Prepare-Doc is advisory until migrated.

**Current architecture** (as of Feb 2026): MobileNetV4-Conv-S (~3ms GPU) as a fast
pre-correction gate, followed by SigLIP 2 NAFlex (88M params, ~50ms GPU) as a multi-task
teacher covering IQA, script, handwriting, and page attributes — both detecting quality
issues and triggering corrections — sitting atop a classical heuristic layer providing
interpretable baseline signals.

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

The original phase structure was retired in favour of value streams, each deliverable
independently:

| Stream | Name | Scope |
| --- | --- | --- |
| 0 | Document Type Router | Stage 0 routing: native text / scanned image / audio |
| 1 | Foundation & Schema | Schema utils, script taxonomy, annotation system |
| 2 | Heuristic Detectors | 11 detector modules (shadow, warping, orientation, etc.) |
| 3 | Benchmarking | Go/No-Go decisions for all candidate heuristics |
| 4A | Teacher Model Architecture | SigLIP 2 multi-task training script |
| 4B | Dataset Assembly | 10 training datasets, manifests, GCS upload |
| 4C | OOD & Diversity | Dataset Diversity Reports, OOD holdout design |
| 4D | MobileNetV4 Integration | Wire trained model into production pipeline |
| 4E | Handwriting Dataset | Acquire non-Latin handwriting datasets + train heads |
| 5 | DoclingRouter | Docling-layout integration and routing logic |
| 6 | Geometric Corrections | Perspective correction, border removal |
| 7 | Pseudo-Labeling | DocIQ architecture for ~2.5M unlabelled images |
| 8 | Student Distillation | MobileCLIP-2 S4 → S0 cascade from SigLIP 2 teacher |

Key architectural decisions made during this restructuring:

- **SigLIP 2 NAFlex** replaces the ResNet teacher-student pair for IQA, expanding coverage
  to 19 heads across 5 task groups (IQA, Script, Orientation+Skew, Handwriting, Page Attrs)
- **MobileNetV4-Conv-S** is added as a fast pre-correction gate before SigLIP 2
- **docling-layout** (egret-large / heron) replaces YOLOv10-doc for layout detection
- **YOLOv10-doc** remains stable and deployed; it will be replaced in Stream 5

### Dataset Complexity (2026 Q1): The Ongoing Challenge

Building the 10 training datasets required for SigLIP 2 has proven substantially harder than
originally estimated. Key problems encountered:

- The synth-multiscript-v3 generator had a bug causing severe per-script imbalance (Arabic
  generated 49K images; 17 of 27 scripts fell below their 12,963 target). Bug was fixed in
  Feb 2026, but the completion run to reach 350K images has not yet been executed — current
  GCS count is 190,485 images.
- L2 metadata enrichment (which provides labels for capture method, shadow severity, warping
  severity, etc.) requires significant compute and has been running across 57+ source datasets.
- Shadow and warping severity labeling (via PaddleOCR-based pipelines) is still in progress as
  of Feb 2026, blocking the assembly of the shadow and warping training manifests.
- Three gap reports were produced during this work (OCR research gaps, Docling integration
  gaps, Wild Conditions Analysis) but were not integrated into this plan until Feb 2026.

### Naming Evolution

The project was originally scoped as "four projects" (Prepare-Doc/B/C/D). A sixth-service
architecture was later defined, adding Ingest and Prepare-Audio. The authoritative naming
(Prepare-Doc, Unify, Chunk, Embed, Ingest, Prepare-Audio) is established in the Level 0
architecture diagram. All new documentation uses service names. Older documents retain legacy
naming for historical context.

---

## 3. Current Architecture

```text
Raw Input (any format: PDF, DOCX, HTML, image, audio, ...)
        │
        ▼
[Stage 0: Document Type Router] <20ms CPU  ◄── STATUS: Planned (not yet implemented)
    ├── Format detection (MIME type + content signature)
    ├── PDF sub-classification:
    │       born_digital | scanned | hybrid | born_digital_degraded
    ├── Routing outcome A: native text + born-digital PDFs → Unify (fast path, skip IQA)
    ├── Routing outcome B: images + scanned/hybrid PDFs → image pipeline (below)
    └── Routing outcome C: audio → Prepare-Audio (separate ASR pipeline)
        │
        ▼ (images and image-like documents only)
[Pre-flight] PyMuPDF DPI detection
        │
        ▼
[MobileNetV4-Conv-S] ~3ms GPU          — STATUS: Trained; production integration pending (Stream 4D)
    ├── Orientation (4-class)
    ├── Fine skew (regression ±10°)
    └── Resolution quality (char-height-aware 0-1)
        │
        ▼
[Stage 1: Pre-Correction Gate]
    ├── Rotate (if orientation ≠ 0°, confidence > 0.9)
    ├── Deskew (if |angle| > 0.3°)
    └── Upscale (if resolution_quality < 0.4)
        │
        ▼ (corrected image — Stage 2 operates here)
[SigLIP 2 NAFlex 88M] ~50ms GPU         — STATUS: Training script ready; training not yet run
    ├── Group 1: IQA (6 heads)
    ├── Group 2: Script (1 cls, 10 classes)
    ├── Group 3: Orientation (1 cls + 1 reg)
    ├── Group 4: Handwriting (3 cls + 2 reg)       ◄── Stream 4E needed
    └── Group 5: Page Attrs (1 cls + 4 reg)

[Classical IQA] ~25ms CPU                — STATUS: Complete (8 detectors)
    ├── Blur (Laplacian variance)
    ├── Noise (local std dev)
    ├── Contrast (histogram)
    ├── JPEG blockiness
    ├── Illumination uniformity
    ├── Binarization artifacts
    ├── Bleed-through
    └── Skew (Hough)

[docling-layout] ~25ms GPU
    └── Coarse layout + table/figure flags
        │
        ▼
[Remaining Corrections] (triggered by SigLIP 2 + Classical IQA analysis)
    ├── CLAHE enhancement (if contrast issues detected)
    ├── Sharpening (if blur detected)
    ├── Denoising (if noise detected)
    ├── Shadow removal (if shadow_score > threshold)
    └── Dewarping (if warping_score > threshold)
        │
        ▼
[DQS Calculation] Degradation + structural complexity → 0-1 score
        │
        ▼
[Routing Engine] → ocr_fast / ocr_advanced / vision_simple / vision_structured
        │
        ▼
DocumentMetadata.json + Corrected Images → Unify
```

**Key files**:

- Training script: `modal/train_siglip2_multitask.py` (2,652 LOC, ready to run)
- Training config: `config/siglip2_multitask.yaml`
- Dataset assembly: `scripts/prepare_multitask_datasets.py` (6 sub-commands: script, orientation, source, shadow, warping, merge)
- Heuristic detectors: `src/image_preprocessing_detector/detection/`
- Classical IQA: `src/image_preprocessing_detector/detection/iqa_classical.py`
- Schema utils: `src/image_preprocessing_detector/schema_utils/`

---

## 4. Completed Work

The table below reflects **accurate current state**. Items marked ⚠️ have precision notes.

| Component | Stream / Phase | Key Deliverables | Status |
| --- | --- | --- | --- |
| Foundation pipeline (ingestion, corrections, CLI) | Phases 0–1C | Ingestion, text gate, 8 IQA detectors, correction pipeline | ✅ |
| ML IQA teacher-student (ResNet) | Phase 3 | ResNet-50 teacher (val_loss=0.27), ResNet-18 student (val_loss=0.14) | ✅ |
| Layout-lite + routing + DQS | Phase 2 | YOLOv10-doc, 4-strategy routing, DQS calculator | ✅ |
| Device-priority execution | Phase 4 | Celery workers, Modal GPU integration, budget enforcement | ✅ (98%) |
| Drift detection and monitoring | Phase 6 | Drift alerts, active learning pipeline, Prometheus metrics | ✅ (95%) |
| Schema utils | Stream 1 | layout_taxonomy.py, script_ml_mapping.py, ISO 15924, paper sizes | ✅ |
| Heuristic detectors | Stream 2 | 11 detector modules (shadow, warping, source, orientation, etc.) | ✅ |
| Go/No-Go benchmarking | Stream 3 | All 5 candidate heuristics benchmarked; decisions confirmed | ✅ |
| SigLIP 2 training **script** | Stream 4A | `train_siglip2_multitask.py` (8 heads, 5 groups) | ✅ script only ⚠️ |
| OOD holdout **design** | Stream 4C | OOD_DATASET_DESIGN.md, 8/10 DDRs complete | ✅ design only ⚠️ |
| Geometric corrections | Stream 6 | perspective_correction.py, border_removal.py | ✅ |
| Orientation training dataset | — | 50K images, 4-class balanced, GCS-ready | ✅ |
| Skew training dataset | — | 90,412 images (71K synth + 19K natural), GCS-ready, val MAE=0.837° | ✅ |
| MobileNetV4 **training** | — | conv_small @ 224px, orient_acc=99.5%, val MAE=0.837° (epoch 47) | ✅ training only ⚠️ |
| L2 metadata enrichment | — | 57/58 datasets enriched with capture method, domain, quality fields | ✅ |
| Annotation system refactoring | Stream 1 | Modular annotation package, 802 tests, Phases 1–5 complete | ✅ (85%) |

**Precision notes on ⚠️ items**:

- **SigLIP 2 training script**: The `train_siglip2_multitask.py` script is complete and
  validated. The actual multi-task **training run has not been executed** — no trained SigLIP 2
  model exists yet. Awaiting dataset assembly (Stream 4B completion).
- **OOD holdout design**: The design documents and DDRs 1–8 are complete.
  `metadata_registry/ood_registry.jsonl` has **9,155 entries** (76.3% of the 12,000-image
  target). Domain enrichment is complete for all 9,155 records. The registry is well past the
  P0 gate (7,000) and approaching the statistically rigorous target (~12,000 images). Remaining
  work: ~2,845 images from planned Phase 3 sources + labeling 5 at-risk heads (skew_score,
  handwriting_legibility, handwriting_legibility_score, resolution_quality, code_confidence —
  all at 0 labeled images). See `docs/datasets/OOD_COVERAGE_GAP_REPORT.md` for per-head status.
  DDRs 9 (shadow) and 10 (warping) are **blocked** pending Tier 0 severity labeling. **Two OOD
  evaluation metric errors** are also present and must be corrected before any trained model is
  evaluated against OOD data (see Section 6 Tier 1). Also: synth-multiscript-v3 generator bug
  is fixed, but the completion run to reach 350K images has not been executed (current count:
  190,485).
- **doc3d license confirmed MIT**: doc3d (102,000 images with 3D mesh warping ground truth) was
  previously assumed NC-SA-blocked; confirmed MIT-licensed as of 2026-02-24. Now available in
  all commercial scenarios and is a primary source for SIG-G5-3 (warping_reg).
- **MobileNetV4 training**: Training is complete (best checkpoint: epoch 47,
  `modal/train_skew_estimator.py`, run ID `20260212_155402`). **Production pipeline integration
  has not been done** — MobileNetV4 does not yet run in the live pipeline. That is Stream 4D.

---

## 5. Key Design Decisions (Locked)

These architectural choices are settled. Changes require explicit consensus and version increment.

- **Two-model pipeline (MobileNetV4 pre-correction before SigLIP 2)**: Orientation must be
  corrected before script detection is reliable. SigLIP 2 also carries orientation/resolution
  heads for teacher distillation, validation, and CPU-only fallback.

- **Three-tier script architecture**: Tier 1 stores full ISO 15924 codes; Tier 2 uses ~10–18
  configurable ML training classes; Tier 3 maps to OCR routing targets. Tiers are independently
  configurable; changing routing config does not require retraining.

- **OOD reserved scripts**: Armenian (Armn), Georgian (Geor), Gothic (Goth), Mongolian (Mong),
  and Syriac (Syrc) are permanently excluded from training. They serve as OOD evaluation anchors
  spanning TTB (Mongolian), RTL (Syriac), and LTR with unique letterforms (Armenian, Georgian,
  Gothic). Enforcement set: `{"Armn", "Geor", "Goth", "Mong", "Syrc"}`. A lifecycle protocol
  tracks when a script can transition from OOD to training status.

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

- **Stage 0 Document Type Router before all IQA**: Prepare-Doc accepts any input format docling
  supports (17 format types). Native text formats (DOCX, HTML, MD, LaTeX, CSV, XML, EPUB) and
  born-digital PDFs with valid text layers must bypass the entire image preprocessing pipeline
  and route directly to Unify. PDF sub-classification uses four categories, not three: the
  fourth (`born_digital_degraded`) covers PDFs whose text layer extracts as garbage (~18% of
  "born-digital" PDFs per PDF Association 2025 data). Encrypted PDFs emit a halted
  `DocumentMetadata.json` record rather than being silently dropped. Audio is excluded from
  Prepare-Doc entirely and must be routed upstream before reaching this service.

- **Prepare-Doc applies corrections and delivers routing signals**: Prepare-Doc both corrects
  images (orientation, skew, resolution in Stage 1; CLAHE, sharpening, denoising, shadow
  removal, dewarping in Stage 2) and delivers rich `DocumentMetadata` signals — DQS, script
  detection, quality scores, page attributes, handwriting assessment. For OCR routing decisions
  (engine selection, CLI flags, VLM model choice), Prepare-Doc delivers signals and Unify
  translates them into docling configuration. `DoclingRoutingEngine` in this codebase is
  advisory; Unify may adopt, adapt, or override it. Migration to Unify is tracked as a
  Stream 5 pre-condition.

- **Canonical service naming**: All new documentation uses service names (Prepare-Doc, Unify,
  Chunk, Embed, Ingest, Prepare-Audio). Legacy "Prepare-Doc/B/C/D" identifiers appear only in
  archived historical documents. The Level 0 architecture diagram is the naming authority.

---

## 5a. Training Readiness Assessment (2026-02-24)

> **Full analysis**: [TRAINING_DATA_STRATEGIC_ANALYSIS.md](TRAINING_DATA_STRATEGIC_ANALYSIS.md)
> — 4-model consensus (Gemini 2.5 Pro, Gemini 3 Pro Preview, DeepSeek R1 0528, Grok 4),
> mean confidence 8.5/10. All tier trade-offs, head-by-head scoring matrix, and performance
> delta estimates are documented there. This section captures the actionable verdict.

### Verdict: CONDITIONAL GO — T4+T6 strategy, 16 heads, Release 1

Proceed with T4 (Enriched Current) + T6 (Computational Enhancements) data tier, descoped to
**16 heads** for Release 1. Defer 6 heads (G4 handwriting group of 5 + SIG-G3-2 narrow-range
skew) to Release 2, pending T5 targeted data acquisition.

**Current state**: mean D1–D6 readiness score 27/100; 8 heads blocked; no heads ready.
**T4+T6 target state**: 6 heads ready (≥75), 7 near-ready (60–74), 9 needs-work (30–59), 0
blocked; all 22 heads unblocked for training.

**T2 and T3 are inert tiers** — license-only tiers produce zero improvement for blocked heads.
The blocked heads are blocked on missing labeling scripts, not missing data volume.

### Three Architectural Defects (Critical Path — 3–5 hours total)

These are code defects that must be fixed **before any training labels are generated**.
Labels generated with these defects are permanently corrupted and cannot be salvaged.

| # | Defect | Severity | Heads Affected | Fix |
| --- | --- | --- | --- | --- |
| D1 | **N_A Sentinel Value**: `0.0` for "no handwriting" is identical to "absent/illegible" | CRITICAL | G4-1 through G4-5 (all 5 HW heads) | Change to `-1.0`; apply masked loss |
| D2 | **code_reg misclassified as regression**: binary task using MSE loss | HIGH | SIG-G5-4 | Rename `code_cls`; switch to BCE loss + AUC/F1 metrics |
| D3 | **SIG-G3-2 skew derivation conflict**: unsigned vs. signed target ambiguity | MEDIUM | SIG-G3-2 | Document signed/unsigned semantics; align implementation |

### Phased Training Schedule

| Phase | Weeks | Scope | Gate |
| --- | --- | --- | --- |
| 0 | 1–2 | Fix 3 architectural defects + deployment model decision + initiate license reviews | All 3 defects fixed; deployment model decided |
| 1 | 2–4 | Train MNV4-Conv-S: orientation (50K), skew (90K), resolution quality (15K) | T4 data assembled for 3 heads |
| 2 | 4–8 | Execute E11 (v3 completion) + E01 (shadow labeling); train SigLIP core 11 heads (G1 IQA + G2 Script + G5 Page Attrs) | E11 + E01 complete; SRCC gate for VLM IQA |
| 3 | 8–12 | Integrate G3 geometry heads; execute E03 (warping) + E05 (RQ V2); expand to 16 active heads | 14+ heads at quality gate |
| 4 | 12+ (Release 2) | T5 handwriting data (KHATT, CASIA-HWDB2, IIIT-HW-Hindi); build ILLEGIBLE class; train G4 heads | T5 acquisitions complete |

**Parallel track (Weeks 1–12)**: T5 data acquisition + legal review + OOD corpus expansion
(9,155 → 12,000 images).

**Acquisition sequencing**: The dataset gathering strategy
([DATASET_GATHERING_STRATEGY.md](DATASET_GATHERING_STRATEGY.md)) determines the order in which
dataset work is executed within each phase. It prioritizes real-world data acquisition by
difficulty (4 tiers: S/A/B/C), then fills gaps with synthetic generation. The strategy accounts
for cross-dataset sharing that reduces the unique image requirement from ~585K (naive per-head
sum across 11 dataset views) to ~420–440K actual unique images — see
[UNIFIED_TRAINING_CORPUS.md §1b](../datasets/UNIFIED_TRAINING_CORPUS.md#1b--unique-source-pool-analysis).

### Key Per-Group Findings

- **MNV4-H1 + MNV4-H2**: Only two immediately trainable heads (documented limitations:
  non-Latin coverage <1%; MNV4-H2 at 79.1% synthetic vs. ≤37.5% ideal cap).
- **G5-2 (shadow_reg)**: Highest single-action leverage — blocked at 13/100 now, reaches
  75/100 (ready) with one missing script: `label_shadow_severity.py` on sd7k + wsrd.
- **G5-3 (warping_reg)**: Warping severity formula must be defined before any labeling.
  doc3d (102K images, MIT-confirmed) is the primary source. Formula:
  `severity = clip(k * std(Z_grid_normalized), 0.0, 1.0)`.
- **G4 Handwriting**: Highest-risk group. No tier achieves "ready" in 12 weeks. ILLEGIBLE
  class at 0 examples; MIXED_TYPED_HW at 0 examples. G4-2 and G4-5 performance targets
  exceed inter-annotator agreement ceilings — targets must be revised downward before
  training. Deferred to Release 2.
- **SIG-G3-2**: The +/-2° narrow-range skew dataset does not exist and must be built from
  scratch (~20K images). No existing script creates it. T5 minimum viable tier for this head.
- **G1-6 (overall_quality)**: VLM prompt v2.0 must achieve SRCC > 0.60 on 30–50 validation
  images before scaling. Current SRCC = 0.53 is insufficient for regression training.
- **SIG-G5-4 (code_cls)**: Fastest path to improvement of any currently blocked head — dry-run
  produced 8,613 records; D6 fixed by code_reg→code_cls rename (Defect 2 above).

---

## 6. Remaining Work

### Tier 0 — Prerequisites (in flight, blocks everything)

#### Fix three architectural defects (~3–5h total, blocks all label generation)

Must be fixed before any training labels are generated. Labels created with these defects are
permanently corrupted. Full context in Section 5a.

| Defect | Location | Fix | Effort |
| --- | --- | --- | --- |
| N_A sentinel `0.0` in handwriting heads | All parsers that emit HW labels | Change to `-1.0`; add masked loss | 1–2h |
| `code_reg` configured with MSE loss | Head registry, training script, inference | Rename `code_cls`; switch BCE + AUC/F1 | 1–2h |
| SIG-G3-2 skew signed/unsigned ambiguity | Skew derivation logic | Document semantics; align implementation | 1.5h |

#### Decide deployment model (SaaS vs. distributed)

- **What**: Determines whether CC-BY-SA-4.0 datasets (e.g., kuzushiji, hiertext) can be used.
  CC-BY-SA-4.0 is potentially incompatible with distributed model distribution but not with
  SaaS/API. Legal review required.
- **Effort**: 1 day (decision) + 2 weeks (legal review if distributed model chosen)
- **Unblocks**: License strategy for T3 datasets; all 55+ dataset scope decisions

#### Initiate sd7k/wsrd license resolution

- **What**: sd7k (7,239 images) and wsrd (4,500 images) have unconfirmed licenses. Email dataset
  authors to request formal permission. Treat as all-rights-reserved for model card disclosure
  until confirmation received. Fallback if authors unresponsive: replace with synthetic shadow
  from v3 (8K images) + doc3d (MIT, for warping).
- **Effort**: 1 day (email drafting + send); resolution timeline: 2–4 weeks

#### Define warping severity formula for doc3d

- **What**: `label_warping_severity.py` cannot be implemented without a defined formula for
  converting doc3d's 3D mesh displacement to a scalar severity score. Decision needed:
  `severity = clip(k * std(Z_grid_normalized), 0.0, 1.0)` (consensus recommendation).
  Once defined, doc3d (102K images, MIT-confirmed) unlocks SIG-G5-3 at T4+T6 score 68 (near-ready).
- **Effort**: 0.5 days (domain decision) + 3–4 days (implementation and labeling on GPU VM)

#### Shadow severity labeling (~3h GPU remaining)

- **What**: Run `scripts/label_shadow_severity.py` on sd7k (7,239 images) and wsrd (4,500
  images) on the Vultr A100 GPU instance
- **Delivers**: `shadow_severity` field in L2 metadata for all sd7k and wsrd images
- **Warping note**: `label_warping_severity.py` on warpdoc (1,020 images) is already complete;
  wsrd warping labels still queued
- **Unblocks**: Shadow/warping view generation, shadow/warping manifest sub-commands, DDRs #9
  and #10

---

### Tier 1 — Ready to Start (parallel group, no blockers except Tier 0 for shadow/warping)

#### Stream 4B: Synthetic view generation

Four generation scripts are already written; they need to be run:

| Script | Output | Status |
| --- | --- | --- |
| `scripts/generate_v3_shadow_view.py` | 8K shadow images from synth-multiscript-v3 | Script ready, not run |
| `scripts/generate_v3_warping_view.py` | 5K warped images from synth-multiscript-v3 | Script ready, not run |
| `scripts/derive_v3_orientation_view.py` | 20K non-Latin orientation synthetics | Script ready, not run |
| `scripts/build_orientation_real_component.py` | 11K real orientation images (DocLayNet + RVL-CDIP) | Script ready, not run |

#### Stream 4B: Dataset assembly (`prepare_multitask_datasets.py`)

This is the primary remaining implementation deliverable. It assembles five training manifests
from processed source datasets and L2 metadata. Each manifest is a flat JSON list (required
format for `modal/train_siglip2_multitask.py`).

| Sub-command | Source data | Mixing cap | Notes |
| --- | --- | --- | --- |
| `script` | MDIW13 (753 images, local) + synth-multiscript-v3 (GCS) | ≤60% synthetic | Computes class weights |
| `source` | L2 `capture_method` field across 57 datasets | — | Maps to scanned/camera/born_digital |
| `orientation` | Synthetic view scripts + real component | ≥60% real | Validates 4-class balance |
| `shadow` | sd7k + wsrd (real) + shadow view script (synth) | ≤60% synthetic | Requires Tier 0 first |
| `warping` | warpdoc + anyphotodoc6300 (real) + warping view script (synth) | ≤60% synthetic | Requires Tier 0 for wsrd |

Critical implementation contract (must match `train_siglip2_multitask.py`):

- Manifest format: flat JSON list (NOT `{"samples": [...]}`)
- Required fields: `image_path` (relative to `/data/`), `script`, `source`, `orientation`,
  `shadow`, `warping`, `split_type`
- `split_type` must be one of: `train` / `val` / `test` / `ood`
- OOD leakage check: `_validate_manifest_no_ood()` must pass before any manifest is written

#### Stream 4B: Complete synth-multiscript-v3 generation run

The generator bug is fixed, but only 190,485 images were generated before the bug was
discovered. The remaining ~159,515 images (to reach the 350K target) must be generated.

- **Script**: `scripts/generate_base_dataset_v3.py` (bug fixed at line 811)
- **Target**: 350,000 images across 27 scripts, balanced to 12,963 per script
- **Prerequisite**: Verify the per-script dict fix is active before running

#### Stream 4C: OOD corpus build (9,155 → 12,000 images)

`metadata_registry/ood_registry.jsonl` has **9,155 entries** (76.3% of target). Domain
enrichment is complete for all records. Infrastructure (ood_utils.py, build_ood_dataset.py,
directory structure) is operational. P0-P2 acquisition phases are substantially complete;
remaining work focuses on gap closure and at-risk head labeling.

**Current per-category progress**:

| Category | Acquired | Notes |
| --- | --- | --- |
| ood_degradation | 2,930 | |
| ood_capture | 2,800 | +300 screen-recapture added |
| ood_handwriting | 1,990 | |
| ood_geometry | 1,740 | |
| ood_script | 1,221 | +446 CC-OCR (Hang 147, Cyrl 149, Arab 100, Jpan 50) |
| ood_domain | 959 | +100 CC-OCR document_text |
| ood_code | 500 | +424 code screenshots |
| ood_resolution | 365 | |
| ood_mixed | 338 | |

**Domain enrichment** (complete): EDU 29.8%, UNK 22.6%, GOV 13.8%, TEC 10.6%, SCI 8.2%,
FIN 7.0%, SCN 5.5%, LGL 2.6%. Inference methods: DocLayNet COCO lookup, source dataset rules,
reason prefix rules, code screenshot generator, OHR-Bench benchmark.

**At-risk heads** (0 labeled images — require intervention before model evaluation):

- `skew_score`: Run trained MobileNetV4 skew head over all 9,155 registered images
- `resolution_quality`: Run `label_resolution_quality.py` on Vultr A100 VM (365 ood_resolution)
- `handwriting_legibility` / `handwriting_legibility_score`: Human annotation needed for
  IIIT-INDIC/KHATT/CASIA-HWDB2 (~950 images)
- `code_confidence`: Model-internal confidence output — populated at inference time, no GT needed

**Remaining acquisition** (~2,845 images to reach 12K target):

- NDL Digital Collection: ~100 Japanese vertical-text images (public domain)
- DLC-2021 screen recaptures: ~100 (academic-only ⚠️)
- SCUT-HCCDoc CJK handwriting: ~100 (open)
- EUR-Lex government forms: ~240 (public domain)
- CBETA religious texts: ~150 (CC0)
- Internet Archive book gutter shadow: ~90 (CC0)
- Script OOD (KhmerST, AMADI_LontarSet, SANA, Georgian): ~425 (academic)
- CORD receipts: ~100 non-English camera receipts (CC-BY-4.0)
- Remaining compound/mixed generation: ~210

**License constraints**: ~2,200 entries are academic-only; ~6,955 are commercial-OK. Academic
entries (WarpDoc, RVL-CDIP, docalign12k, RealDAE, DLC-2021) cannot be used in production
without data refresh.

Full details: [OOD_COVERAGE_GAP_REPORT.md](../datasets/OOD_COVERAGE_GAP_REPORT.md)

#### Stream 0: Document Type Router (new — architectural gap)

Prepare-Doc currently assumes all inputs are PDFs or images. This stream adds the Stage 0
router that correctly classifies all 17 docling-supported format types.

- **What to build**: `src/image_preprocessing_detector/routing/document_type_router.py`
- **Format routing table**:

| Format group | Examples | Route |
| --- | --- | --- |
| Native text | DOCX, HTML, MD, LaTeX, CSV, VTT, XML, EPUB | → Unify directly (no IQA) |
| PDF (born-digital) | Native PDF with valid text layer | → Unify directly |
| PDF (hybrid) | Mixed pages | → per-page routing |
| PDF (scanned / degraded) | Scanned books, fax, garbled text layer | → full image pipeline |
| Images | JPG, PNG, TIFF, WebP, BMP | → full image pipeline |
| Audio | WAV, MP3, MP4 | → exclude; route to Prepare-Audio upstream |
| Encrypted | Password-protected PDF | → emit halted metadata |

- **New schema fields**: `document_class`, `file_format`, `router_confidence`, `page_type_map`
- **Effort**: 2–3 weeks; builds on existing `classification/pdf_type_classifier.py`

#### Stream 4D: MobileNetV4 pipeline integration (new stream)

MobileNetV4 training is complete (val MAE=0.837°, orient_acc=99.5%). The model has not been
wired into the production pipeline — it does not run on any document today.

- **What to build**: Integrate `best_model.pt` (epoch 47, run `20260212_155402`) into the
  pipeline before SigLIP 2
- **Steps**: ONNX export → integration test → replace Hough-only deskew with MobileNetV4 output
  → verify corrections are applied before SigLIP 2 receives the image
- **Confidence thresholds**: orientation correction if confidence > 0.9; skew correction if
  |angle| > 0.3°
- **Effort**: 1–2 weeks

#### Docling P0 bug fixes (before any integration testing with Unify)

Three bugs must be fixed before Prepare-Doc is integrated with Unify:

| Bug | File | Location | Fix |
| --- | --- | --- | --- |
| `paddleocr` is not a valid docling engine key | `schema.py`, `script_router.py`, `config/script_routing.yaml` | schema.py:766, script_router.py:173, yaml:67/73/79/84/92/98/103/108/114/122 | Replace all `paddleocr` with `rapidocr` |
| `--no-tables` never emitted when `tables_enabled=False` | `schema.py` | Lines 794–829 (`to_cli_args`) | Add `if not self.tables_enabled: args.append("--no-tables")` |
| VLM pipeline selects no VLM model; default undocumented | `docling_router.py` | Lines 80, 340–348 | Document default (`granite_docling`); expose `vlm_escalation_reason` in metadata |

#### JPEG quality detection (new classical IQA detector)

Research establishes that JPEG quality < 80 causes rapid OCR decline; quality < 50 is severe
degradation. The current classical IQA suite detects JPEG blockiness (a symptom) but not
quality factor (the root cause). This gap is not in any existing remediation plan.

- **What to add**: JPEG quantization table analysis to `detection/iqa_classical.py`
- **Thresholds**: flag quality < 80 (soft), reject quality < 50 (hard gate)
- **Schema field**: add `jpeg_quality_factor: int | None` to `PageMetadata`
- **Effort**: 1–2 days

#### Symmetric document orientation gap

Symmetric documents (uniform backgrounds, centered content) are indistinguishable at 0° vs.
180° by whitespace-based orientation cues. Current training set has 0% coverage of this
condition.

- **What to do**: Curate ~500 symmetric page examples from DocLayNet + blank forms; label both
  0° and 180° variants; include in orientation training set
- **Source**: DIVERSITY_REMEDIATION_PLAN.md P2-3
- **Effort**: 0.5 days (curation script)

#### Compound distortion IQA augmentation pipeline

Single-distortion IQA training results in 15–25% metric drop on real-world compound
degradations (blur + skew + noise simultaneously). This is P0-1 in DIVERSITY_REMEDIATION_PLAN
but is not in the current master plan.

- **What to build**: Augmentation pipeline on OHR-Bench / DIQA-5000 base images that applies
  2–5 distortions per image, generating compound examples
- **Effort**: 3–5 days

#### SIG-G3-2: Build +/-2° narrow-range skew dataset from scratch

The post-correction narrow-range skew dataset (~20,000 images at ±0.5–2° increments) does not
exist. No existing script creates it. T4 (which only runs existing scripts) does not address
this. **T5 is the minimum viable tier for SIG-G3-2.**

- **What to build**: Synthetically rotate clean DocLayNet, SROIE, and Arabic documents at
  0.1–2° increments; generate ~20,000 images; label with exact rotation angle as ground truth
- **Effort**: 2–3 weeks (generation script + GPU run)
- **Score impact**: Moves SIG-G3-2 from 20/100 (blocked) to 55/100 (needs-work) at T5

#### OOD evaluation metric corrections (fix before any model is evaluated on OOD data)

Two metric errors in the current OOD evaluation design must be corrected before any trained
model is evaluated against the OOD corpus. Evaluating with the current metrics will produce
misleading results even for heads that are training-ready.

| Error | Location | Fix |
| --- | --- | --- |
| ILLEGIBLE OOD floor uses classification accuracy (invalid — model has 0 training examples for that class) | OOD evaluation pipeline | Replace with OSR Energy Score rejection rate; gate: ≥70% |
| MNV4-H1 uses raw softmax confidence for abstention | MNV4 inference / evaluation | Replace with Energy Score (required for overconfident transformer architectures) |

#### ADF scanner training data sourcing

Enterprise auto-document feeder (ADF) scanners are the dominant scanning paradigm in high-volume
workflows, but produce distinct edge-curl and feed-skew artifacts not found in flatbed scans
(RVL-CDIP, which is 1990s CCD technology). See DIVERSITY_REMEDIATION_PLAN P1-6, P1-7, P2-6.

- **What to do**: Commission 500 ADF scan examples (curl, skew, feed artifacts)
- **Effort**: 2–3 weeks (data acquisition)

---

### Tier 2 — Requires Tier 1 completion

#### Stream 4B: GCS dataset upload

Upload all five task manifests and associated image sets to GCS:

- `gs://image_detection_b/datasets/script_training/`
- `gs://image_detection_b/datasets/source_training/`
- `gs://image_detection_b/datasets/orientation_training/`
- `gs://image_detection_b/datasets/shadow_training/`
- `gs://image_detection_b/datasets/warping_training/`

Each path receives: `train_manifest.json`, `val_manifest.json`, and `test_manifest.json`.

#### DDRs #9 (shadow) and #10 (warping)

Run `scripts/evaluate_dataset_diversity.py` for shadow and warping datasets after severity
labels are available. These are the final two DDRs; 8 of 10 are already complete.

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

---

### Tier 3 — Requires trained SigLIP 2

#### Stream 7: Pseudo-Labeling

Use the trained SigLIP 2 teacher to generate soft labels across ~2.5M unlabelled source
dataset images. DocIQ architecture (Stage 1 complete; Stage 2 Phase 2 blocked pending
$80–140 budget approval).

#### Stream 4E: Handwriting Dataset + Training Heads

Handwriting training data is at 0% (target: 60K images). The 5 handwriting heads (Group 4 in
SigLIP 2) are currently excluded from training. Non-Latin scripts are completely absent.

- **Taxonomy prerequisite** (must finalize before acquisition): Expand `handwriting_script` to
  9 fine-grained classes (Latin-Print, Latin-Cursive, CJK-Hanzi, CJK-Kanji, Arabic-Naskh,
  Arabic-Ruqah, Devanagari, Cyrillic, Other-Indic). Define `handwriting_density` as 5-tier
  categorical. Source: DIVERSITY_REMEDIATION_PLAN P0-4.
- **Datasets to acquire** (DIVERSITY_REMEDIATION_PLAN P0-5):
  - Arabic cursive: KHATT dataset
  - CJK: CASIA-HWDB
  - Devanagari: IIIT-INDIC
  - Cyrillic: HKR
  - Latin form fill-in: FUNSD expansion (currently only 199 images)
- **Effort**: Taxonomy (3–5 days) + dataset acquisition (4–6 weeks)

#### Stream 8: Student Distillation

Train MobileCLIP-2 S4 from SigLIP 2 soft labels, then distil further to MobileCLIP-2 S0.
Each student stage targets the same 16 prediction heads with progressive latency reduction.

---

### Remaining Training Datasets (Parallel, Various Blockers)

| Dataset | Done | Target | Next Action | Blocker |
| --- | --- | --- | --- | --- |
| synth-multiscript-v3 | 190,485 | 350,000 | Run completion generation | Generator bug fixed; run not executed |
| Resolution quality | 5.5K | 30K | Run V2 labeling pipeline (Sauvola + projection profiles) | Compute time |
| IQA curated | ~14K | 16K | Validate VLM prompt v2.0 on 30–50 images; scale if SRCC > 0.60 | Prompt validation |
| IQA synthetic | 0 | 100K | Generate from synth-multiscript-v3 with Stream 7 pseudo-labels | Requires Stream 7 |
| Handwriting | 0 | 60K | Finalize taxonomy; acquire KHATT, CASIA-HWDB, IIIT-INDIC, HKR | Stream 4E |
| Capture method | 0 | 50K | Assemble from L2-enriched datasets by capture_method field | Data acquisition |
| Shadow | 0 | 15K | Run Phase 5 view generation after Tier 0 | Tier 0 severity labeling |
| Warping | 0 | 20K | warpdoc complete; wsrd warping labels queued | wsrd warping labels |

---

### Chunk Service Transition (foundry-chunk)

The future `foundry-chunk` service will be built by refactoring `williaby/data_ingestor`, which
contains working chunking code developed in parallel with this project. Transition begins after
Prepare-Doc SigLIP 2 training is complete and validated (Tier 3 dependency).

**data_ingestor → foundry-chunk migration inventory:**

| Module | data_ingestor path | Disposition |
| --- | --- | --- |
| Chunking algorithms | `chunking/by_title_chunker.py`, `token_chunker.py` | **Keep** — core Chunk logic |
| Document router | `pipeline/router.py` | **Keep** — entry point classification |
| PDF parsers | `parsers/pdf_parser.py` | **Audit** — may overlap with Unify |
| DocLayNet evaluation | `evaluation/doclaynet_evaluator.py` | **Keep** — QA framework |
| Benchmarking suite | `benchmarking/` | **Keep** — performance baseline |
| PDF resolution utils | `utils/pdf_resolution.py`, `pdf_upscaler.py` | **Already extracted** into this repo |
| Export | `export/exporter.py` | **Keep** — JSON/Markdown output |
| Trust scoring | *(not built)* | **New work** — must consume Prepare-Doc IQA fields |
| GCS artifact I/O | *(not built)* | **New work** — read from `02-unified/`, write to `04-chunks/` |
| Old Ref Docs | `docs/Ref Docs/RAG Pipeline/project-a/b/c/d-*` | **Archive** to `docs/_archived/` in data_ingestor |

**Contract requirement**: The output `RAGChunkSet.json` must include `trust_score`,
`ocr_engine_provenance`, `chunk_id`, `document_id`, and `trace_id` per
[chunk-embed-contract.md](../development/RAG%20Pipeline/chunk-embed-contract.md). These fields
are mandatory — all per-application embedding implementations depend on them.

---

### Deferred Work (Explicit Trigger Conditions)

- **FastAPI endpoint implementations**: 23 endpoint stubs exist. Deferred until SigLIP 2
  training is complete and validated (trigger: SigLIP 2 mAP > 0.88 on holdout set).
- **Load testing and deployment automation**: Deferred until FastAPI endpoints are implemented.
- **ResNet model optimization**: Superseded by SigLIP 2; not needed.
- **Screen recapture/moiré detection**: RGB moiré from phone-photographing-monitor requires a
  new capture method class and moiré detection metric (Moran's I). Deferred to Tier 3 (after
  initial model training establishes the baseline). Source: WILD_CONDITIONS_ANALYSIS.md.
- **`DoclingRoutingEngine` migration to Unify**: Currently advisory in Prepare-Doc. Migration
  is a Stream 5 pre-condition — when Unify integration begins, `DoclingRoutingEngine` and
  `DoclingRoutingParams.to_cli_args()` are migration candidates.

---

## 7. Documentation Corrections Backlog

These specific corrections are tracked here to prevent the current fragmentation into separate
handoff documents. Priority: P0 = blocking, P1 = before Unify integration, P2 = good to have.

| # | File | Change Required | Priority |
| --- | --- | --- | --- |
| 1 | [docs/PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md) | Full service-name update (7 occurrences of "Prepare-Doc"); add audio track + Stage 0 context | P0 |
| 2 | [docs/PROJECT_OVERVIEW_DETAILED.md](../PROJECT_OVERVIEW_DETAILED.md) | Full service-name update (7 occurrences); fix `docling_parameters` → `docling_params` (line ~362) | P0 |
| 3 | [docs/planning/PREPARE_DOC_TO_UNIFY_HANDOFF_SPECIFICATION.md](PREPARE_DOC_TO_UNIFY_HANDOFF_SPECIFICATION.md) | Full v2 rewrite — v1 (Jan 2026) predates SigLIP 2 architecture, architectural boundary decision, 19 heads, `DoclingRoutingParams`, handwriting assessment | P0 |
| 4 | `src/image_preprocessing_detector/schema.py:766` | Replace `paddleocr` with `rapidocr` in `ocr_engine` field description | P0 |
| 5 | `src/image_preprocessing_detector/routing/script_router.py:173` | Replace `paddleocr` with `rapidocr` in `get_engine()` docstring | P0 |
| 6 | `config/script_routing.yaml` (12 entries) | Replace all `engine: "paddleocr"` with `engine: "rapidocr"` | P0 |
| 7 | `src/image_preprocessing_detector/schema.py:794-829` | Add `--no-tables` emission in `to_cli_args()` when `tables_enabled=False` | P0 |
| 8 | [docs/architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml](../architecture/diagrams/level-2/downstream-context/unify-ocr-layout-workflow.puml) | Redraw or archive — current diagram shows wrong OCR engines (YOLOv8, Marker/Llama, DeepSeek-OCR) instead of actual docling engines (RapidOCR, EasyOCR, Tesseract) | P1 |
| 9 | [docs/planning/DOCLING_INTEGRATION_GAP_REPORT.md](DOCLING_INTEGRATION_GAP_REPORT.md) | Replace "Prepare-Doc" → "Prepare-Doc", "Unify" → "Unify" (26 occurrences) | P1 |
| 10 | `CLAUDE.md` (project-level) | Verify previously applied P0 audit corrections are committed; service-name update throughout | P1 |
| 11 | [docs/architecture/diagrams/level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml](../architecture/diagrams/level-1/PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml) | Rename file → `PREPARE_DOC_ARCHITECTURE_OVERVIEW.puml`; update SVG | P2 |
| 12 | [docs/architecture/diagrams/level-1/PREPARE_DOC_WORKFLOW_HIERARCHY.puml](../architecture/diagrams/level-1/PREPARE_DOC_WORKFLOW_HIERARCHY.puml) | Rename file → `PREPARE_DOC_WORKFLOW_HIERARCHY.puml`; update SVG | P2 |
| 13 | Level 2 PUML diagrams (27 files, `project-a-*.puml`, `project-b-*.puml`) | Rename all to `prepare-doc-*.puml`, `unify-*.puml`, `chunk-*.puml`, `embed-*.puml` | P2 |
| 14 | [docs/development/RAG Pipeline/ingest-prepare-doc-contract.md](../development/RAG%20Pipeline/ingest-prepare-doc-contract.md) | Rename → `ingest-prepare-doc-contract.md`; update internal references (24 occurrences) | P2 |
| 15 | [docs/planning/IMPLEMENTATION_STATUS_MATRIX.md](IMPLEMENTATION_STATUS_MATRIX.md) | Update status rows to reflect completed work precision notes from Section 4 | P1 |

---

## 8. Dependency Map

**Sequencing guide**: [DATASET_GATHERING_STRATEGY.md](DATASET_GATHERING_STRATEGY.md) provides
the detailed acquisition ordering for all dataset work items below. It maps four gathering
phases (real data → coverage assessment → synthetic fill → gap remediation) onto the tier
structure shown here.

```text
[Tier 0 — All must complete before label generation or training]
    ├──▶ Fix: 3 architectural defects (N_A sentinel, code_cls, skew derivation) — 3-5h total
    ├──▶ Decision: Deployment model (SaaS vs. distributed) — 1 day; unlocks license strategy
    ├──▶ Action: Initiate sd7k/wsrd license resolution (email authors) — 1 day send; 2-4w wait
    ├──▶ Decision: Warping severity formula for doc3d — 0.5d decision + 3-4d implementation
    └──▶ GPU: Shadow severity labeling — sd7k/wsrd on Vultr A100 (~3h GPU)
              │
              └──▶ shadow_severity + warping_severity in L2 metadata
                        │
                        ├──▶ Shadow view generation (generate_v3_shadow_view.py)
                        ├──▶ Warping view generation (generate_v3_warping_view.py)
                        ├──▶ Shadow DDR #9
                        └──▶ Warping DDR #10

[Tier 1 — Parallel group, start concurrently]
    ├──▶ Stream 4B: Run 4 synthetic view scripts (shadow*, warping* require Tier 0)
    ├──▶ Stream 4B: prepare_multitask_datasets.py (shadow*, warping* require Tier 0)
    ├──▶ Stream 4B: synth-multiscript-v3 completion run (190K → 350K)
    ├──▶ Stream 4C: OOD corpus gap closure (9,155 → 12,000) + at-risk head labeling
    ├──▶ Stream 0: Document Type Router (2-3 weeks)
    ├──▶ Stream 4D: MobileNetV4 pipeline integration (1-2 weeks)
    ├──▶ Fix: 3 Docling P0 bugs (< 1 week total)
    ├──▶ Fix: OOD evaluation metric corrections (Energy Score for ILLEGIBLE + MNV4-H1)
    ├──▶ Fix: JPEG quality detection classical IQA head (1-2 days)
    ├──▶ Fix: Symmetric orientation dataset curation (0.5 days)
    ├──▶ Data: Compound distortion augmentation pipeline (3-5 days)
    ├──▶ Data: SIG-G3-2 narrow-range skew dataset build from scratch (2-3 weeks) [T5]
    ├──▶ Data: ADF scanner training data sourcing (2-3 weeks, long-running)
    ├──▶ Data: Dataset gathering strategy execution (Phases 1-4, real-first acquisition)
    └──▶ Docs: P0 documentation corrections (Section 7, items 1-7)
              │
              ▼ (all Tier 1 streams complete)
[Tier 2]
    ├──▶ Stream 4B: GCS upload (5 task manifests + image sets)
    └──▶ DDRs #9 and #10 (shadow + warping diversity reports)
              │
              ▼
[Tier 3] SigLIP 2 multi-task training (Modal A10G/A100, 30-40 epochs)
    │
    ├──▶ Stream 4D: Evaluation vs heuristic baselines
    ├──▶ Stream 5: DoclingRouter integration (parallel to evaluation)
    └──▶ Stream 4E: Handwriting taxonomy → acquisition (KHATT, CASIA-HWDB, IIIT-INDIC, HKR)
              │
              ▼
[Tier 4] Stream 7: Pseudo-Labeling (~2.5M images via DocIQ)
    │
    ├──▶ IQA synthetic dataset (100K from pseudo-labeled synth-multiscript-v3)
    └──▶ FastAPI endpoint implementations (trigger: SigLIP 2 mAP > 0.88)
              │
              ▼
[Tier 5] Stream 8: Student Distillation (MobileCLIP-2 S4 → S0 cascade)
```

---

## 9. Wild Condition Remediation Backlog

Based on `docs/planning/WILD_CONDITIONS_ANALYSIS.md`. Overall coverage: **3%** (2 of 60
conditions fully covered across all 19 model heads). P0 = blocking production; P1 = pre-scale;
P2 = monitor and improve.

| Head Group | Coverage | Key P0 Gaps | Tier | Plan Reference |
| --- | --- | --- | --- | --- |
| **IQA (6 heads)** | 0% | Multiply-distorted (blur+skew+noise), mobile blur+defocus, JPEG quality < 50 | Tier 1 | DIVERSITY_REMEDIATION_PLAN P0-1; OCR-2 (new task above) |
| **Script (1 head)** | 11% | Historical typography, decorative fonts | Tier 3 | Route to specialized models; no training fix |
| **Orientation+Skew (2 heads)** | 0% | Symmetric documents (0°/180°), non-Latin RTL, multi-column skew validation | Tier 1-2 | P2-3 curation; P1-8 RTL expansion; OCR-9 cross-detector |
| **Handwriting (5 heads)** | 0% | Arabic cursive, CJK, Devanagari, Cyrillic all absent | Tier 3 | Stream 4E; DIVERSITY_REMEDIATION_PLAN P0-4, P0-5 |
| **Capture Method (1 head)** | 0% | Modern CIS flatbed (2020+), ADF scanner, screen recapture | Tier 1-3 | P1-6/P1-7/P2-6 sourcing; screen recapture deferred Tier 3 |
| **Shadow (1 head)** | 0% | Book gutter shadow (gradient + curvature) | Tier 2 | P1-1 real-world curation |
| **Warping (1 head)** | 20% | Crumpled page + combined skew+warping | Tier 2-3 | P1-4 combined; P2-2 crumple |
| **Resolution (1 head)** | 0% | Vector PDF at low effective DPI, upscaled raster (bicubic 2x-4x) | Tier 1 | Synthetic confound dataset (new task) |

**Additional P0 gaps not yet in any plan**:

1. **Screen recapture / moiré detection** — RGB moiré from phone-photographing-monitor; Moran's
   I z-statistic detection; add to capture method taxonomy as 8th class. Deferred to Tier 3.
2. **Multi-column skew cross-detector validation** — Global Hough fails across column gutters;
   add projection profile second estimator; flag disagreement as layout complexity. Tier 2.
3. **Vector PDF / upscaled raster resolution confounds** — Vector PDFs at low DPI give
   misleading char-height signals; bicubic 2x-4x upscaling inflates char height artificially.
   Requires synthetic confound dataset. Tier 1 (can build now).
4. **ECE confidence calibration tracking** — Multi-head overconfidence; add Expected Calibration
   Error per head to `drift/alerting.py` with baseline config. Tier 2.

---

## 10. Reference Index

| Topic | Document |
| --- | --- |
| System narrative (what it does, why it's sound) | [docs/PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md) |
| SigLIP 2 architecture detail (19 heads, training data) | [SIGLIP2_MULTITASK_REQUIREMENTS.md](SIGLIP2_MULTITASK_REQUIREMENTS.md) |
| Training optimization (ILP, Kendall, PCGrad) | [TRAINING_OPTIMIZATION_PLAN.md](TRAINING_OPTIMIZATION_PLAN.md) |
| Dataset diversity specs (14 dimensions, DDR framework) | [DATASET_DIVERSITY_REQUIREMENTS.md](DATASET_DIVERSITY_REQUIREMENTS.md) |
| OOD holdout design (reserved scripts, 7 categories) | [OOD_DATASET_DESIGN.md](OOD_DATASET_DESIGN.md) |
| Stream 4 implementation detail | [STREAM_4_IMPLEMENTATION_PLAN.md](STREAM_4_IMPLEMENTATION_PLAN.md) |
| Dataset prep handoff (manifests, GCS paths) | [STREAM_4C_DATASET_HANDOFF.md](STREAM_4C_DATASET_HANDOFF.md) |
| Wild conditions analysis (60 conditions, per-head coverage) | [WILD_CONDITIONS_ANALYSIS.md](WILD_CONDITIONS_ANALYSIS.md) |
| OCR research gaps (10 integration gaps) | [../../tmp_cleanup/ocr_research_gaps_report.md](../../tmp_cleanup/ocr_research_gaps_report.md) |
| Docling integration gaps (3 P0 bugs, architectural boundary) | [DOCLING_INTEGRATION_GAP_REPORT.md](DOCLING_INTEGRATION_GAP_REPORT.md) |
| Diversity remediation plan (all P0/P1/P2 actions) | [DIVERSITY_REMEDIATION_PLAN.md](DIVERSITY_REMEDIATION_PLAN.md) |
| Prepare-Doc → Unify handoff specification | [PREPARE_DOC_TO_UNIFY_HANDOFF_SPECIFICATION.md](PREPARE_DOC_TO_UNIFY_HANDOFF_SPECIFICATION.md) |
| Source dataset catalog | [docs/datasets/DATASET_QUICK_REFERENCE.md](../datasets/DATASET_QUICK_REFERENCE.md) |
| Training dataset catalog | [docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md](../datasets/TRAINING_DATASET_QUICK_REFERENCE.md) |
| Implementation status by planning document | [IMPLEMENTATION_STATUS_MATRIX.md](IMPLEMENTATION_STATUS_MATRIX.md) |
| Stage 0 router: format catalog + consensus | [../../tmp_cleanup/docling_format_routing_analysis.md](../../tmp_cleanup/docling_format_routing_analysis.md) |
| Training readiness assessment (Go/No-Go, tier scoring, phased schedule) | [TRAINING_DATA_STRATEGIC_ANALYSIS.md](TRAINING_DATA_STRATEGIC_ANALYSIS.md) |
| OOD corpus build plan (5 phases, hardware substitutes, sub-commands) | [../../tmp_cleanup/OOD_CORPUS_PLAN.md](../../tmp_cleanup/OOD_CORPUS_PLAN.md) |
| Dataset gathering strategy (real-first acquisition sequencing) | [DATASET_GATHERING_STRATEGY.md](DATASET_GATHERING_STRATEGY.md) |
| Unified training corpus (per-head sizes, sharing analysis, acceptance criteria) | [../datasets/UNIFIED_TRAINING_CORPUS.md](../datasets/UNIFIED_TRAINING_CORPUS.md) |
| Corpus OOD review (acceptance scorecard, gap analysis) | [CORPUS_OOD_REVIEW_REPORT.md](CORPUS_OOD_REVIEW_REPORT.md) |
| Architecture diagrams (all four levels) | [docs/architecture/](../architecture/) |
| Historical plan (Phases 0–9, superseded) | [PROJECT_PLAN.md](PROJECT_PLAN.md) |
| Value-stream plan (Streams 1–8, superseded) | [PHASE_10_11_RESTRUCTURED_PLAN.md](PHASE_10_11_RESTRUCTURED_PLAN.md) |
