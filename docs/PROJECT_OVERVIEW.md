---
title: Project A — System Overview
schema_type: common
status: active
owner: core-maintainer
purpose: "Narrative technical introduction: what the system does, why it is designed this way, and why its outputs can be trusted."
tags:
- architecture
- overview
- reference
---

# Project A — System Overview

> **Audience**: Engineers joining the project or reviewing its design.
> **Scope**: Target-state system — what it does, how it works, and why the design is reliable.
>
> **Related documents**:
>
> - [docs/PROJECT_OVERVIEW_DETAILED.md](PROJECT_OVERVIEW_DETAILED.md) — complete module map, canonical files, schema contract, config reference
> - [docs/planning/MASTER_PROJECT_PLAN.md](planning/MASTER_PROJECT_PLAN.md) — project status and remaining work
> - [docs/architecture/](architecture/) — implementation diagrams at all four levels

---

## 1. What Is Project A?

Document quality in real-world collections is highly variable. Pages arrive rotated, skewed,
blurred, shadowed, or photographed under poor lighting. Scripts span dozens of writing systems.
Some documents are born-digital PDFs; others are camera photographs of physical pages from
decades ago. Downstream OCR pipelines — which operate on the assumption of clean, upright,
legible input — fail silently or produce garbled output when these conditions are violated.

Project A is the **preprocessing, IQA, and coarse layout gateway** for a four-project RAG
document pipeline. It accepts raw documents in any condition, assesses quality along multiple
dimensions, applies physical corrections, and produces two outputs: a corrected page image and
a `DocumentMetadata.json` record containing everything the downstream OCR system needs to
make informed routing decisions.

```text
Raw Documents (PDF, image, any condition)
        │
        ▼
┌────────────────────────────────────────┐
│               PROJECT A                │
│  Preprocessing, IQA & Coarse Gateway   │
│                                        │
│  • Orientation / skew correction       │
│  • Resolution normalization            │
│  • Image quality assessment            │
│  • Script & language detection         │
│  • Handwriting analysis                │
│  • Page attribute classification       │
│  • Document Quality Score              │
│  • OCR routing recommendation          │
└────────────────┬───────────────────────┘
                 │  DocumentMetadata.json
                 │  + Corrected page images
                 ▼
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│     PROJECT B       │ ─▶ │     PROJECT C       │ ─▶ │     PROJECT D       │
│  OCR Orchestration  │    │   Fusion & Trust    │    │   Vector Indexing   │
│  Full Layout        │    │   Multi-Engine      │    │   Embeddings        │
│  Reading Order      │    │   Trust Scoring     │    │   Semantic Search   │
│  Table Structure    │    │   RAG Chunking      │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

Project A makes no OCR decisions. It provides structured, validated metadata so Project B can
select the right engine, reading order strategy, and table extraction approach per page. The
scope boundary is strict: full layout detection, table structure extraction, and reading order
prediction are Project B's responsibility.

---

## 2. Two-Stage Processing Architecture

The central insight behind the architecture is that **content analysis cannot be done reliably
on an uncorrected image**. A document rotated 90° will fool a script detector, produce invalid
IQA metrics, and generate misleading layout signals. Low resolution makes every other analysis
unreliable. Project A solves this by splitting processing into two sequential stages, each with
a distinct purpose.

### Stage 1 — Pre-correction Gate (MobileNetV4-Conv-S, ~3ms GPU)

The first stage runs on the raw, uncorrected image. It uses a lightweight MobileNetV4-Conv-S
model with three prediction heads: 4-class orientation detection, sub-degree fine skew
regression, and a character-height-aware resolution quality score. Resolution is scored against
actual OCR character height requirements — 32–48px characters is the optimal range — rather than
against DPI thresholds, which are a poor proxy for whether an OCR engine can reliably segment
individual characters.

Based on these predictions, physical corrections are applied before any further analysis:
rotation and deskewing using Hough line transforms, CLAHE contrast enhancement, border removal
to crop scanner or camera frame artifacts, perspective correction for camera-captured pages, and
resolution upscaling using one of five OpenCV algorithms when character height falls below the
viable threshold.

### Stage 2 — Full Multi-Task Analysis (SigLIP 2 NAFlex, ~50ms GPU)

The second stage runs on the corrected image. SigLIP 2 — an 88M-parameter vision-language model
with strong multi-script pretraining — drives all 16 prediction heads across 5 task groups in
a single forward pass. Eight classical IQA detectors (blur, noise, contrast, JPEG blockiness,
illumination, binarization artifacts, bleed-through, skew via Hough transform) run in parallel
as interpretable baseline anchors, providing sub-25ms outputs that validate and complement the
ML analysis.

The two-model split is not a complexity preference — it is a requirement for correctness. A
single model evaluating a rotated image conflates orientation with IQA, script detection, and
layout geometry. Separating the stages eliminates this confound and allows SigLIP 2 to operate
on inputs where the physical properties it needs to assess are actually visible.

Total pipeline latency is approximately 55–65ms GPU across both stages.

---

## 3. What the System Detects

All 16 prediction heads are organized into five task groups, each feeding a specific downstream
decision in Project B.

**Image Quality Assessment** (6 heads). Five regression heads score blur, noise, contrast, skew
severity, and compression artifacts on a 0–1 scale; a sixth produces an overall quality
composite. These combine with the eight classical detector outputs to produce the Document
Quality Score, which drives the four-strategy OCR routing decision: `ocr_fast` for high-quality
documents, `ocr_advanced` for moderate quality with complex layout, `vision_simple` for
image-dominant pages, and `vision_structured` for documents with tables and figures that need
specialist extraction.

**Script and Language** (1 head). A 10-class script classifier identifies the primary writing
system from the document image. This determination drives OCR engine selection in Project B —
different engines handle Latin, CJK, Arabic, Devanagari, and Cyrillic scripts with very
different accuracy profiles. The architecture is designed to expand to 108 OpenLID-aligned
classes in Phase 2 without backbone retraining; only the classification head and its training
data change.

**Orientation and Fine Skew** (2 heads). A 4-class rotation head and a sub-degree skew
regression head run in Stage 2 as a validation pass over the Stage 1 pre-correction. If the
Stage 2 orientation reading conflicts with Stage 1, a correction escalation is triggered.

**Handwriting** (5 heads). Three classification heads assess presence (none/partial/dominant),
legibility (unreadable through excellent), and content type (printed/cursive/mixed/annotation/
diagram label). Two regression heads score density and script family. Together these determine
whether Project B should route to a handwriting-specialized OCR engine and at what priority.

**Page Attributes** (5 heads). A 7-class capture method classifier distinguishes born-digital,
flatbed scanner, ADF scanner, smartphone camera, dedicated camera, synthetic, and unknown
origins. This matters because each capture method introduces a characteristic artifact signature
that the downstream system needs to anticipate. Four additional regression heads score shadow
severity, warping severity, code content ratio (for QR/barcode routing), and effective
resolution as a validation against the Stage 1 measurement.

---

## 4. Why the Design Can Be Trusted

Three practices underpin the reliability of the system's outputs.

### Heuristic-First Validation

No ML head was added to the system without first measuring whether a classical heuristic could
solve the problem adequately. Every candidate was benchmarked against a performance target
before an ML training investment was committed. Script detection reached only 15.6% accuracy
with heuristics against an 80% target — ML was clearly required. Document source classification
reached 64.7% against an 85% target — ML required. Shadow detection reached 60.1% F1 against
an 85% target — ML required. Warping detection reached 94.7% F1, exceeding the 80% target, so
it ships as a heuristic; the SigLIP head adds only the severity regression that the binary
heuristic cannot provide.

This discipline means every ML head in the system replaced a demonstrably inadequate alternative.
No head exists because ML seemed like the right approach in principle.

### Dataset Diversity Validation

A system trained on narrow data will fail on out-of-distribution inputs without warning. To
prevent this, every training dataset used in Project A is evaluated across 14 diversity
dimensions before being admitted to training: capture method, domain, script family, script
code, resolution range, text density, layout type, content flags, degradation type, content
type, paper size, color mode (binarized/grayscale/color), document age (modern/aged/historical),
and handwriting characteristics. Each dataset receives a formal Dataset Diversity Report that
identifies gaps and triggers specific remediation before training begins.

### OOD Holdout Design

Three scripts — Mongolian (Mong), Syriac (Syrc), and Georgian (Geor) — are permanently reserved
from all training and validation sets. They exist in the system only as out-of-distribution
evaluation examples, representing distribution shifts along script, directionality, and
letterform axes that the model has never encountered. OOD evaluation covers seven distribution
shift categories. All images are SHA256 and perceptual-hash deduplicated (Hamming ≤ 5) against
the training population to ensure leakage is structurally impossible, not just unlikely.

---

## 5. Quality Assurance and Reliability

### Device Priority and Budget Control

The inference layer is designed for predictable cost. Inference falls through a priority chain:
local GPU first, then Modal serverless GPU, then local CPU as a fallback. A budget enforcement
layer tracks costs at the document, batch, and monthly levels, and blocks escalation when
budget caps would be exceeded. The orchestration logic is implemented against a testable mock
device interface so that device-specific behavior can be validated without GPU hardware.

### Monitoring and Drift Detection

The production system monitors the prediction distribution of every head using Prometheus. When
any head's distribution shifts beyond a configured threshold — indicating that the input
population has changed in a way that may invalidate the trained model — an alert fires and
high-entropy samples are automatically harvested for active learning review. This creates a
closed-loop retraining path that can respond to drift without manual intervention.

### Teacher-Student Distillation Cascade

SigLIP 2 (88M params, ~50ms GPU) is the teacher model. The production target is a
MobileCLIP-2 S4 student (~12ms GPU), further distilled to a MobileCLIP-2 S0 student (~5ms GPU)
for edge deployments. Each student stage is trained on soft labels from the stage above,
preserving multi-task prediction quality at lower compute cost. The distillation cascade is
deferred until the SigLIP 2 teacher is fully trained and validated.

### Schema and Contract Validation

All output is serialized using Pydantic v2 models with strict type enforcement. Bounding boxes
use COCO format (`[x, y, width, height]`) throughout — never `[x1, y1, x2, y2]` — because
Project B's LayoutParser expects COCO conventions. The `DocumentMetadata.json` schema is
versioned; breaking changes require an explicit contract negotiation with the Project B team.

---

## 6. Technical Stack

| Component | Technology | Design Rationale |
| --------- | ---------- | ---------------- |
| Pre-correction gate | MobileNetV4-Conv-S (~3ms GPU) | Fast enough to run before any other analysis; orientation/resolution must be known first |
| Multi-task teacher | SigLIP 2 NAFlex, 88M params (~50ms GPU) | Vision-language pretraining handles multi-script naturally; 16 heads in one pass |
| Classical IQA baseline | OpenCV — 8 detectors (~25ms CPU) | Interpretable; sub-25ms; validated anchor for each ML head; no GPU dependency |
| Layout detection | docling-layout (egret-large / heron) | Validated over YOLOv10-doc in Stream 3 benchmarking |
| PDF ingestion | PyMuPDF | DPI-aware extraction; 100% accuracy on DPI metadata |
| Image corrections | OpenCV + Pillow | 5 upscaling algorithms, CLAHE, Hough deskew, perspective correction |
| Script architecture | 3-tier ISO 15924 design | Storage / ML training / OCR routing are independently configurable |
| Schema | Pydantic v2 + JSON | Type-safe; COCO-aligned bounding boxes; versioned Project B contract |
| Training | Modal A10G/A100 (serverless) | Budget-controlled GPU; GCS dataset integration |
| Orchestration | Celery + Redis (3 queues) | Separates default, GPU, and batch workloads |
| Monitoring | Prometheus + Grafana | Per-head drift detection; active learning integration |
| Language detection | OpenLID-v2 | 108+ languages; ISO 639-3 aligned; backbone-agnostic |

---

*For complete module maps, canonical files, schema contract details, and config reference, see
[docs/PROJECT_OVERVIEW_DETAILED.md](PROJECT_OVERVIEW_DETAILED.md).*

*For implementation progress and remaining work, see
[docs/planning/MASTER_PROJECT_PLAN.md](planning/MASTER_PROJECT_PLAN.md).*

*For architecture diagrams at all four levels, see
[docs/architecture/](architecture/).*
