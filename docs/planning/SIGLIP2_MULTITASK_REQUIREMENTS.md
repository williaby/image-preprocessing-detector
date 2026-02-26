# SigLIP 2 NAFlex: Comprehensive Model Requirements & Training Dataset Plan

## Context

Prepare-Doc needs to produce a `DocumentMetadata` JSON that drives Docling OCR routing decisions in Unify. The current pipeline has significant gaps: no script/language detection, no handwriting assessment, and limited page attribute classification. SigLIP 2 NAFlex (88M params, VQualA 0.886 on DIQA-5000) is the chosen backbone for a **unified multi-task model** that will handle all vision-based classification and regression tasks in a single inference pass.

This plan identifies every model requirement in the pipeline, maps them to either SigLIP 2 or other models, and specifies the training datasets needed.

**Related Plans**:

- [DATASET_DIVERSITY_REQUIREMENTS.md](DATASET_DIVERSITY_REQUIREMENTS.md) -- Diversity characteristics for all 10 training datasets (14 dimensions, verification framework)
- [TRAINING_OPTIMIZATION_PLAN.md](TRAINING_OPTIMIZATION_PLAN.md) -- Phased optimization strategy (ILP, active learning, BO), multi-task training (PCGrad + Kendall), augmentation ordering fix

---

## 0. Open Design Decisions

Three architectural questions require resolution before training begins. Each affects the model architecture, training data, and pipeline integration.

### 0.1 Two-Model Pipeline: MobileNetV4 Pre-Correction + SigLIP 2 Multi-Task

**Decision**: Use MobileNetV4-Conv-S as a fast pre-correction stage gate, then run SigLIP 2 on the corrected image. SigLIP 2 is also trained on orientation/skew/resolution for redundancy and teacher capability.

**Rationale**: Running SigLIP on a 90°-rotated or low-resolution image degrades all downstream heads (script, IQA, handwriting). Phase 10 docs confirm: "Orientation detection/correction MUST be the FIRST step in the pipeline" and "rotated pages cause script detection to fail, text gate false negatives, IQA metrics to be invalid." MobileNetV4-Conv-S is already designed for Phase 10A (~3ms GPU, ~8-12ms CPU) and is the right model for fast pre-correction.

**Architecture**:

```
Document --> Pre-flight (PyMuPDF DPI metadata)
    |
    v
[MobileNetV4-Conv-S] (~3ms GPU, ~12ms CPU) --- STAGE GATE ---
    ├── Head 1: Orientation classification (4 classes: 0/90/180/270)
    ├── Head 2: Fine skew regression (±10°, target <0.5° residual)
    └── Head 3: Resolution quality regression (character-height-aware, 0-1)
    |
    v
CORRECTIONS (if needed):
    ├── Rotate by detected orientation (if confidence >0.9)
    ├── Deskew by predicted angle (if |angle| > 0.3°)
    └── Resolution adjustment (upscale if resolution_quality < 0.4, downscale if > 0.8 AND image very large)
    |       Target: 32-48px character height (optimal for OCR)
    |       Safety rails: never below 150 DPI, never above 600 DPI
    |
    v
[SigLIP 2 Multi-Task] (~50ms GPU) --- on corrected image ---
    ├── Group 1: IQA (6 regression heads)
    ├── Group 2: Script detection (1 classification)
    ├── Group 3: Orientation + Skew (1 cls + 1 reg) -- redundant/validation of MobileNetV4
    ├── Group 4: Handwriting (3 cls + 2 reg)
    └── Group 5: Page attributes (1 cls + 3 reg)
    |
    v (parallel)
[docling-layout-egret-xlarge / docling-layout-heron] (~25ms GPU) + [Classical IQA] (~25ms CPU) --- on corrected image ---
    |
    v
Aggregate + Remaining Corrections + Output

Total: ~55-65ms GPU (3ms MobileNet + 50ms SigLIP + overhead)
```

**Why SigLIP also has orientation/skew/resolution heads**:

1. **Teacher for MobileCLIP distillation**: SigLIP soft labels can train future mobile models
2. **Validation**: Compare MobileNetV4 and SigLIP predictions; flag discrepancies for human review
3. **Fallback**: If MobileNetV4 is unavailable (CPU-constrained path), SigLIP can handle everything in single pass
4. **Self-consistency**: SigLIP can verify that the pre-correction was applied correctly

### 0.2 Resolution Strategy: Character-Height-Aware (via MobileNetV4)

**Decision**: MobileNetV4 handles resolution assessment using a character-height-aware regression head. DPI bounds serve as safety rails.

**How it works**:

1. MobileNetV4 `resolution_quality` head outputs 0-1 score trained on:
   - 0.0 = characters too small for OCR (<16px, needs significant upscaling)
   - 0.3 = characters borderline (16-24px, light upscaling beneficial)
   - 0.5 = characters adequate (24-32px, acceptable as-is)
   - 0.7 = characters optimal (32-48px, ideal OCR range)
   - 1.0 = characters oversized (>96px, downscaling may help throughput)
2. The correction logic:
   - If score < 0.4: upscale by factor derived from score (target: 32-48px character height)
   - If score > 0.8 AND image > 4000px on any side: downscale (target: 48px char height)
   - Safety: never below 150 DPI, never above 600 DPI
3. SigLIP also has a resolution_quality head for redundancy (Group 5, see below)

**Training data for resolution head**: Generate pairs of documents at various resolutions with OCR accuracy labels. Use existing source datasets rendered at 72/150/200/300/400/600 DPI. Character height annotations derived from text line detection (Hough + connected components).

**Fallback**: If MobileNetV4 resolution assessment is uncertain (confidence <0.5), fall back to standard 300 DPI pipeline (current behavior).

**Open question**: The chicken-and-egg problem with character height estimation is resolved because MobileNetV4 learns to estimate resolution quality directly from image features (texture frequency, edge sharpness of strokes) rather than explicit character height measurement. The model implicitly learns what "too small" and "too large" text looks like.

### 0.3 Summary of Design Decisions

| Decision | Chosen Approach | Impact on Architecture |
|---|---|---|
| Pre-correction stage gate | **MobileNetV4-Conv-S** fast pre-pass (~3ms) + SigLIP full pass (~50ms) | Two models; MobileNetV4 has 3 heads (orientation, skew, resolution); SigLIP trained on same tasks for redundancy |
| Resolution strategy | **Character-height-aware** via MobileNetV4 head + DPI safety rails | MobileNetV4 gets resolution_quality head; SigLIP also gets it in Group 5 |
| Skew detection | **Dedicated regression head** in both MobileNetV4 (pre-correction) and SigLIP Group 3 (validation) | Separate from IQA skew severity; predicts actual angle for correction |

---

## 1. Complete Model Requirements Matrix

### Schema fields -> Model assignment

| Schema Field | Current Model | Proposed Model | Task Type | Priority |
|---|---|---|---|---|
| **IQA: blur/noise/contrast/skew/compression** | ResNet-18 student | SigLIP 2 Head Group 1 | 5x regression (0-1) | P0 |
| **IQA: overall_quality** | ResNet-18 student | SigLIP 2 Head Group 1 | 1x regression (0-1) | P0 |
| **Script: script_code (ISO 15924)** | NONE (gap) | SigLIP 2 Head Group 2 | Classification (10 classes Phase 1, full OpenLID Phase 2+; Mong/Syrc/Geor OOD-reserved) | P0 |
| **Script: script_family, has_non_latin, has_rtl** | NONE (gap) | Derived from script_code | Rule-based derivation | P0 |
| **Orientation: detected_angle (0/90/180/270)** | Classical CV ensemble | SigLIP 2 Head Group 3 | Classification (4 classes) | P1 |
| **Skew: residual_skew_degrees** | Classical Hough (0.5° precision) | SigLIP 2 Head Group 3 | Regression (continuous, ±45°) | P1 |
| **Handwriting: presence** | NONE (gap) | SigLIP 2 Head Group 4 | Classification (5 classes) | P1 |
| **Handwriting: legibility** | NONE (gap) | SigLIP 2 Head Group 4 | Classification (6 classes) | P1 |
| **Handwriting: content_type** | NONE (gap) | SigLIP 2 Head Group 4 | Classification (7 classes) | P1 |
| **Handwriting: presence_score, legibility_score** | NONE (gap) | SigLIP 2 Head Group 4 | 2x regression (0-1) | P1 |
| **Page: shadow_score** | NONE (gap) | SigLIP 2 Head Group 5 | Regression (0-1) | P2 |
| **Page: warping_score** | NONE (gap) | SigLIP 2 Head Group 5 | Regression (0-1) | P2 |
| **Page: code_confidence** | NONE (gap) | SigLIP 2 Head Group 5 | Regression (0-1) | P2 |
| **Page: resolution_quality** | MobileNetV4 Head 3 | SigLIP 2 Head Group 5 (redundant) | Regression (0-1, char-height-aware) | P2 — provides teacher signal back to MobileNetV4 + single-pass CPU fallback |
| **Page: capture_method** | NONE (gap) | SigLIP 2 Head Group 5 | Classification (7 classes) | P2 |
| **Layout: 11 DocLayNet elements + bboxes** | docling-layout-egret-xlarge / docling-layout-heron | **Keep docling-layout** | Object detection | N/A |
| **Layout: layout_type** | Derived from docling-layout | **Keep derivation** | Rule-based | N/A |
| **Layout: has_tables/figures/math** | docling-layout-egret-xlarge / docling-layout-heron | **Keep docling-layout** | Boolean from element presence | N/A |
| **Layout: complexity_score** | DQS calculator | **Keep aggregation** | Rule-based | N/A |
| **PDF type: born_digital/image_only/hybrid** | Rule-based (text layer) | **Keep rule-based** | Heuristic | N/A |
| **DPI: dpi_input, dpi_effective** | PyMuPDF | **Keep PyMuPDF** | Metadata extraction | N/A |
| **Corrections: deskew/CLAHE/sharpen/denoise** | OpenCV | **Keep OpenCV** | Image processing | N/A |
| **DQS: degradation + complexity** | Aggregation engine | **Keep, fed by SigLIP 2 IQA** | Rule-based | N/A |
| **Routing: ocr_routing_recommendation** | Decision tree | **Keep, enhanced with script info** | Rule-based | N/A |
| **Text scope: scope/density/content_type** | NONE (gap) | SigLIP 2 Head Group 6 (future) | Classification | P3 |
| **Paper size: detected_size** | DPI + dimensions | **Keep rule-based** | Heuristic | N/A |

### What SigLIP 2 NAFlex handles (single inference pass, ~50ms GPU)

**19 task heads across 5 head groups:**

- **Group 1 (IQA)**: 5 regression heads (blur, noise, contrast, skew, compression) + overall_quality
- **Group 2 (Script)**: 1 classification head (10 classes Phase 1, expanding to full OpenLID coverage; Mong/Syrc/Geor permanently excluded as OOD anchors)
- **Group 3 (Orientation + Skew)**: 1 classification head (4 classes: 0/90/180/270) + 1 regression head (fine skew in degrees)
- **Group 4 (Handwriting)**: 3 classification heads (presence, legibility, content_type) + 2 regression (presence_score, legibility_score)
- **Group 5 (Page Attributes)**: 1 classification head (capture_method) + 4 regression (shadow, warping, code, resolution_quality)

### What stays with other models

| Model | Task | Why Keep |
|---|---|---|
| **MobileNetV4-Conv-S** | Pre-correction stage gate: orientation (4-class) + skew (regression) + resolution quality (regression) | Ultra-fast (~3ms GPU) pre-correction before SigLIP. Ensures SigLIP sees correctly oriented, properly resolved images. Already designed for Phase 10A. |
| **DocLayout-YOLO (docling-layout)** | Layout element detection (11 classes + bboxes) | Object detection with localization - YOLO excels here, SigLIP is image-level only. **Two inference variants**: `egret-xlarge` (accuracy-priority, higher mAP) and `heron` (speed-priority, lower latency); variant selected by deployment configuration, not training |
| **Classical IQA (8 detectors)** | Validation/fallback for blur, noise, skew etc. | Zero-latency, deterministic, no GPU needed. Also triggers corrections |
| **Classical Text Gate** | Fast text presence routing (<10ms) | Pre-filter before expensive model inference |
| **Classical Orientation** | Fallback when MobileNetV4 + SigLIP unavailable | CPU-only heuristic path (85% accuracy) |
| **Classical Handwriting (Stroke Analysis)** | Handwriting presence fallback when SigLIP 2 Group 4 confidence <0.5 | Stroke width variance on connected components + run-length encoding on binarized image; implemented in `detection/iqa_classical.py`; outputs `has_handwriting` bool and `handwriting_confidence` (0-1). Activation threshold: Group 4 any head confidence <0.5 |
| **OpenCV Corrections** | Deskew, CLAHE, sharpen, denoise | Image transforms, not classification |
| **PyMuPDF** | DPI detection, PDF text layer analysis | Metadata extraction, not vision |

---

## 2. SigLIP 2 NAFlex Multi-Task Architecture

### Model structure

```
Input: Document page image (variable aspect ratio, NaFlex preserves ratio)
    |
SigLIP 2 ViT-B/16 Backbone (86M params, 784 max patches)
    |
Shared Feature Vector (768-dim)
    |
    +---> Group 1: IQA Heads (5 regression + 1 aggregate)
    |     - blur_score, noise_score, contrast_score, skew_score, compression_score
    |     - Each: Linear(768->256) -> ReLU -> Dropout(0.3) -> Linear(256->2) [mu, sigma_sq]
    |
    +---> Group 2: Script Detection Head (1 classification)
    |     - Linear(768->256) -> ReLU -> Dropout(0.3) -> Linear(256->N_scripts)
    |     - Output: probability distribution over 10-20 script classes
    |
    +---> Group 3: Orientation + Skew Heads (1 classification + 1 regression)
    |     - orientation_cls: Linear(768->256) -> ReLU -> Dropout(0.3) -> Linear(256->4)
    |       Output: softmax over [0, 90, 180, 270] (coarse rotation)
    |     - skew_reg: Linear(768->256) -> ReLU -> Dropout(0.3) -> Linear(256->2) [mu, sigma_sq]
    |       Output: fine skew angle in degrees (target <0.5° residual after correction)
    |       Range: ±10° (fine angular deviation AFTER coarse orientation is resolved)
    |       Note: Orientation handles 90° increments; skew handles fractional degrees
    |
    +---> Group 4: Handwriting Heads (3 classification + 2 regression)
    |     - presence_cls: Linear(768->128) -> Linear(128->5)   [NONE..DOMINANT]
    |     - legibility_cls: Linear(768->128) -> Linear(128->6) [N/A..ILLEGIBLE]
    |     - content_cls: Linear(768->128) -> Linear(128->7)    [n/a..specialized]
    |     - presence_reg: Linear(768->128) -> Linear(128->1)   [0-1 area ratio]
    |     - legibility_reg: Linear(768->128) -> Linear(128->1) [0-1 quality]
    |
    +---> Group 5: Page Attribute Heads (1 classification + 4 regression)
          - capture_cls: Linear(768->128) -> Linear(128->7) [born_digital..fax]
          - shadow_reg: Linear(768->128) -> Linear(128->1)  [0-1 severity]
          - warping_reg: Linear(768->128) -> Linear(128->1) [0-1 severity]
          - code_cls: Linear(768->128) -> Linear(128->1)    [0-1 confidence; sigmoid+BCE]
          - resolution_quality_reg: Linear(768->128) -> Linear(128->1) [0-1, char-height-aware]
            (Redundant with MobileNetV4 head; provides teacher signal + validation)

Total: ~101M params (86M backbone + ~15M heads)
Inference: ~50ms on A10 GPU, ~300-500ms CPU (single-pass; see Section 0.1 for two-pass option)
```

### Production inference flow

```text
Document --> Pre-flight (DPI metadata: PyMuPDF for PDFs, EXIF for images)
    |        Supports: PDF, JPG, PNG, TIFF, BMP, WEBP
    v
[MobileNetV4-Conv-S] (~3ms GPU, ~12ms CPU) ---- STAGE GATE ----
    |  Head 1: Orientation (4-class)
    |  Head 2: Fine skew (regression, ±10°)
    |  Head 3: Resolution quality (regression, 0-1)
    |
    v
CORRECTIONS (gated by confidence):
    |  Rotate if orientation confidence >0.9
    |  Deskew if |skew| > 0.3°
    |  Upscale if resolution_quality < 0.4 (target 32-48px char height)
    |  Downscale if resolution_quality > 0.8 AND image > 4000px
    |  Safety rails: 150 DPI floor, 600 DPI ceiling
    |
    v  (corrected image)
[SigLIP 2 Multi-Task] (50ms GPU) ---- FULL ANALYSIS ----
    |  Group 1: IQA (6 regression)
    |  Group 2: Script (1 classification)
    |  Group 3: Orientation + Skew (1 cls + 1 reg) -- validates MobileNetV4
    |  Group 4: Handwriting (3 cls + 2 reg)
    |  Group 5: Page attrs (1 cls + 4 reg, incl. resolution_quality)
    |
    v  (parallel, on corrected image)
[docling-layout-egret-xlarge / docling-layout-heron] (25ms GPU) --> 11 layout elements with bboxes
[Classical IQA] (25ms CPU) --> Validation, correction triggers
    |
    v
Aggregate: DQS, pre-OCR risk, routing recommendation
Remaining corrections: CLAHE, sharpen, denoise (from classical IQA triggers)
    |
    v
Output: DocumentMetadata.json + corrected images --> Unify (Docling)

Total GPU: ~55-65ms (3ms MobileNet + 50ms SigLIP + overhead)
Total CPU fallback: ~500-600ms (SigLIP handles everything in single-pass)
```

---

## 3. Training Datasets by Task Group

### Group 1: IQA (6 regression heads: 5 individual + 1 aggregate)

**Status**: Training data ready. SigLIP 2 already trained on DIQA-5000 (VQualA 0.886).

| Dataset | Images | Labels | Status | Notes |
|---|---|---|---|---|
| **DIQA-5000** | 5,500 | Human MOS 1-5, 3 dimensions (overall, sharpness, color) | Ready | Only dataset with 3-dim document MOS |
| **OHR-Bench** | 8,561 | Quality scores 0-100, 7 domains | Ready | Page-level scores, PDF extraction needed |
| **RealDAE** | 1,200 | Before/after pairs, degradation types | Ready | Good for degradation-specific scoring |
| **OCR-Quality** | 1,000 | Human quality 1-4, Chinese/multilingual | Ready | Cross-validation for DeQA-Doc |
| **DIBCO** | 131 | Binarization ground truth | Ready | Extreme degradation edge cases |
| **Total ready** | **~16,300** | | | |

**Gap**: Current IQA heads predict overall/sharpness/color (DIQA-5000 scheme). Need to map to blur/noise/contrast/skew/compression (ResNet scheme) OR adopt the 3-dim scheme for DQS. The unified labeling strategy (UNIFIED_LABELING_STRATEGY.md) provides the pipeline for pseudo-labeling 2.5M images via DocIQ-Replica distillation.

**Data sufficiency**: ~16K images is sufficient for the 3-dimension IQA task (SigLIP already achieves VQualA 0.886 on DIQA-5000 alone). If expanding to 5-dimension IQA (blur/noise/contrast/skew/compression), additional pseudo-labeled data (~50-100K) will be needed via the DocIQ-Replica pipeline. The previously planned "IQA Phase 7 165K" dataset has been determined to be flawed and is excluded.

**Recommendation**: Train with DIQA-5000 3-dim scheme (overall, sharpness, color) as primary quality scores. Classical IQA (8 detectors) continues to provide specific issue detection (blur, noise, skew etc.) and triggers corrections. SigLIP 2 IQA replaces ResNet for the aggregate quality signal that feeds DQS.

### Group 2: Script Detection (10+ classes, expanding to full OpenLID)

**Status**: CRITICAL GAP. Datasets exist but need assembly.

**Phase 1 classes (10)**: Latin, CJK Mixed, Japanese, Korean, Tibetan, Arabic, Devanagari, Cyrillic, Thai, Hebrew

**Phase 2+ target**: Full OpenLID coverage (~107 languages, ~60+ ISO 15924 scripts). Training scope
expands beyond the 10-class Phase 1 set to cover all scripts supported by OpenLID. This
significantly changes what constitutes a truly OOD script — most scripts will become in-training
after Phase 2 completes.

> **RESERVED SCRIPTS (PERMANENT OOD EXCLUSION)**: Mongolian (Mong), Syriac (Syrc), and
> Georgian (Geor) must **never** appear in any training manifest regardless of Phase. These
> 3 scripts are permanently reserved for OOD holdout evaluation only:
>
> - Mongolian (Mong): Top-to-bottom (TTB) orientation anchor
> - Syriac (Syrc): Right-to-left (RTL) anchor
> - Georgian (Geor): Left-to-right (LTR) anchor with unique letterforms
>
> The `_validate_no_reserved_scripts()` guard in `prepare_multitask_datasets.py` enforces this.
> See [OOD Dataset Design — Script Reservation Policy](OOD_DATASET_DESIGN.md#script-reservation-policy).

| Dataset | Images | Scripts Covered | Status | Notes |
|---|---|---|---|---|
| **synth-multiscript-v3** | 190,485 (actual — generator bug stopped early; treat as complete) | 27 scripts, 8 IQA dims | Complete (GCS) — ⚠️ Imbalanced distribution | v2 (250K) DELETED; Arab 3.8x target; Mong absent (OOD-reserved); rebalancing required before training |
| **MDIW13** | 232,170 train | 13 scripts (doc/line/word levels) | Ready | Largest script dataset available |
| **MLT19** | 10,000 train | 10 languages | Ready | BENCHMARK RESERVED (val/test) |
| **SIW13** | 16,291 | 13 scripts | Ready | Competition dataset |
| **CVSI** | 10,715 | 10 scripts (video frames) | Ready | Scene text domain |
| **Arabic Docs OCR** | 10,045 | Arabic (12 doc types) | Ready | Strong Arabic coverage |
| **Nepal Devanagari** | 717 | Devanagari | Ready | Government documents |
| **Nepali Handwritten** | 4,000+ | Devanagari handwritten | Ready | Handwritten Nepali |
| **Dzongkha Digits** | 204 | Tibetan | Ready | Digits only (limited) |
| **TibHCR** | 5,000+ | Tibetan handwritten | Ready | Handwritten characters |
| **CC-OCR** | 6,525 | Multi-script | Ready | Cross-lingual |
| **COCO-Text** | 64,000+ | Multi-script | Ready | Scene text (noisy) |
| **Total ready** | **~583K+** | | | |

**Critical gap: Tibetan** - Only ~5,200 real Tibetan samples across all datasets. The MOBILECLIP2_S4_S0_DATASET_DESIGN.md calls for 3,800 synthetic Tibetan with style transfer from real samples. This is the highest risk area.

**Critical gap: Japanese vertical text** - Must be explicitly included and labeled as 0 degree orientation (not 270 degree). ~1,050 samples needed per design doc.

**Recommendation**: Start Phase 2 training with synth-multiscript-v3 (190,485 images actual, 27 scripts on GCS — ⚠️ rebalancing required before training; Mong absent by design) + MDIW13 (232K, 13 scripts) as the foundation, supplemented by SIW13 + CVSI. The 10-class Phase 1 grouping maps ISO 15924 codes to ML classes via `config/script_ml_classes.yaml`. Phase 2+ expands to full OpenLID; reserved scripts (Mong/Syrc/Geor) are blocked at manifest generation time.

### Group 3: Orientation + Skew Detection (4 classes + 1 regression)

This group has two distinct sub-tasks that work in tandem:

- **Orientation classification**: Detect major rotation (0°/90°/180°/270°) for coarse correction
- **Skew regression**: Detect fine angular deviation (±10°) for precision deskewing to <0.5° residual

The orientation head handles 90-degree increment rotations. The skew head detects fractional-degree deviations so the correction pipeline can achieve sub-0.5° alignment. Together they replace both the classical orientation ensemble (85% accuracy) and the Hough deskew detector (0.5° precision).

#### Orientation sub-task (classification)

**Status**: ✅ READY. 50,000 images generated and available at `E:\image_detection\03_training_datasets\orientation\`.

| Component | Count | Source | Status |
|---|---|---|---|
| **Scientific papers** | 2,000 | DocLayNet | ✅ Generated |
| **Financial reports** | 1,500 | DocLayNet, FinTabNet | ✅ Generated |
| **Forms** | 1,500 | FUNSD, FUNSD+, NIST SD-2/SD-6 | ✅ Generated |
| **Receipts** | 1,000 | SROIE | ✅ Generated |
| **Tables** | 1,500 | TableBank, PubTabNet | ✅ Generated |
| **Legal documents** | 1,000 | DocLayNet | ✅ Generated |
| **Handwritten pages** | 1,000 | NIST SD-19 | ✅ Generated |
| **Mixed layouts** | 1,000 | DocLayNet | ✅ Generated |
| **Arabic documents** | 1,500 | Arabic Docs OCR | ✅ Generated |
| **Devanagari documents** | 700 | Nepal Devanagari | ✅ Generated |
| **Japanese vertical text** | 1,050 | MLT + synthetic | ✅ Generated |
| **Total source docs** | **12,500** | | |
| **Total after 4x rotation** | **50,000** | | ✅ Ready |

**Generation details**: 12,500 unique source documents, rotated by 0/90/180/270 = 50,000 samples. Split by document ID BEFORE rotation (prevent leakage). 50% degradation applied (camera + scanner artifacts). Generated via `scripts/generate_orientation_dataset.py`.

**Location**: `E:\image_detection\03_training_datasets\orientation\`

**Key constraint**: Vertical Japanese samples labeled as 0 degree (upright), not 270 degree. Same images shared with script detection dataset.

#### Skew sub-task (regression)

**Status**: Dataset generation needed (can reuse same source documents as orientation).

**Approach**: Apply random sub-10° rotations to source documents with known ground-truth angles.

| Dataset Component | Count | Source | Labels | Status |
|---|---|---|---|---|
| **Clean documents + random skew** | 25,000 | Same 12,500 sources × 2 skew variants | Ground-truth angle (±0.01° precision) | Need generation |
| **Naturally skewed scans** | ~5,000 | RVL-CDIP, Tobacco800 (scanned docs) | Hough-derived angle (classical baseline) | Need labeling |
| **Synthetically degraded** | 10,000 | From clean sources + scanner simulation | Ground-truth angle + degradation | Need generation |
| **Total** | **~40,000** | | | |

**Generation process**:

1. Take source documents (already upright, orientation = 0°)
2. Apply random rotation ∈ [-10°, +10°] with known ground truth
3. Apply scanner-like degradation (50%): noise, slight blur, compression artifacts
4. Classical Hough detector provides cross-validation labels (existing `iqa_classical.py` at 0.5° precision)

**Key distinction from Group 1 IQA skew**: The IQA skew head (Group 1) detects skew as a **quality degradation signal** (severity 0-1). The Group 3 skew head predicts the **actual angle in degrees** for correction. Both are useful: IQA skew tells you "this image has a skew problem", Group 3 skew tells you "rotate by -2.3° to fix it."

**Loss function**: SmoothL1 on angle (robust to outliers) + optional GaussianNLL for uncertainty estimation.

### Group 4: Handwriting Assessment (5 heads)

**Status**: Multiple datasets with relevant labels exist but need label extraction/harmonization.

| Dataset | Images | Handwriting Labels | Status | Notes |
|---|---|---|---|---|
| **HierText** | 8,281 train | word-level `handwritten` bool + `legible` bool | Ready | GOLD STANDARD for graded assessment |
| **COCO-Text** | 43,686 train | word-level `class` (machine/handwritten) + `legibility` (legible/illegible) | Ready | Large scale, noisy labels |
| **IAM** | 6,161 lines | Line transcriptions + bboxes, 657 writers | Ready | Classic handwriting dataset |
| **Muharaf** | 24,952 | Arabic handwriting, variable quality | Ready | Arabic script handwriting |
| **PUCIT-OHUL** | 11,694 | Urdu handwritten lines | Ready | Urdu ligatures |
| **Nepali Handwritten** | 4,000+ | Nepali handwritten chars | Ready | Devanagari handwriting |
| **NIST SD-19** | 3,669 pages | Full handwritten pages | Ready | US census forms |
| **FUNSD** | 199 | Mixed print + handwriting forms | Ready | Handwritten field values |
| **Total** | **~102K+** | | | |

**Label harmonization needed**: Map diverse labels to unified schema:

- `presence`: Derive from text area ratio using schema-aligned thresholds:
  - NONE <1%, **MARGINAL** <10%, **PARTIAL** 10–50%, SUBSTANTIAL 50–90%, DOMINANT >90%
  - *(Previously used SPARSE/MODERATE — corrected to match `layer2_enrichment_v2.schema.json`)*
- `legibility`: Map HierText `legible` bool + COCO-Text `legibility` to 6-level scale.
  IAM, Muharaf, PUCIT-OHUL, and NIST-SD19 require multi-model VLM scoring
  (`scripts/score_handwriting_legibility.py`).
  **ILLEGIBLE class**: synthesize 200–500 examples via aggressive degradation augmentation
  (smear, heavy blur, ink overwrite) applied to IAM/Muharaf images — KHATT remains OOD-reserved.
- `content_type`: Derive from transcription patterns (digits-only = numeric, short = alphanumeric, long = prose)

**Negative samples** (non-handwriting): DocLayNet (80K printed docs), TableBank (278K tables), RVL-CDIP (400K mixed) - sample ~50K for class balance.

### Group 5: Page Attributes (4 heads)

**Status**: Datasets exist but need enrichment with target labels.

#### Capture Method (7 classes)

| Class | Training Sources | Est. Images | Status |
|---|---|---|---|
| BORN_DIGITAL | DocLayNet (born-digital subset), PubTabNet | ~100K | Ready (filter metadata) |
| SCANNER_FLATBED | RVL-CDIP, Tobacco800, NIST SD-2 | ~50K | Ready |
| SCANNER_ADF | RVL-CDIP (ADF artifacts subset) | ~10K | Need labeling |
| CAMERA_PROFESSIONAL | MIDV500, SmartDoc-QA | ~10K | Ready |
| CAMERA_SMARTPHONE | SROIE (mobile), RealDAE (camera) | ~5K | Ready |
| FAX | RVL-CDIP (fax subset) | ~5K | Need labeling |
| SYNTHETIC | DocSynth300K | ~50K | Ready |

**Gap**: Need to label capture method for RVL-CDIP (400K images, 16 doc classes - some map to capture method). Heuristic + manual validation needed (~2-3 days).

#### Shadow/Warping/Code Regression

| Attribute | Training Sources | Est. Images | Labels | Status |
|---|---|---|---|---|
| **Shadow** | RealDAE (1.2K shadow pairs), Doc3D (100K with 3D info) | ~15K | 0-1 severity | Need enrichment |
| **Warping** | Doc3D (100K with warping mesh), SmartDoc-QA (4.3K) | ~20K | 0-1 severity | Need enrichment |
| **Code blocks** | GitHub rendered code samples, RVL-CDIP | ~10K | 0-1 confidence | Need generation |

**Gap**: Shadow and warping scores need to be computed from existing datasets (Doc3D has 3D mesh data that can derive warping scores). Code block detection needs a small curated dataset.

---

## 4. Training Strategy

### Phased multi-task training

| Phase | Head Groups | Datasets | Duration | Prerequisite |
|---|---|---|---|---|
| **Phase 1: IQA** | Group 1 only | DIQA-5000 + OHR-Bench (~16K) | 2 weeks | None (already done, VQualA 0.886) |
| **Phase 2: + Script** | Groups 1+2 | Add MDIW13 + SIW13 + CVSI (~260K) | 3 weeks | Script class config |
| **Phase 3: + Handwriting** | Groups 1+2+4 | Add HierText + COCO-Text + IAM (~100K) | 2 weeks | Label harmonization |
| **Phase 4: + Orientation + Skew** | Groups 1+2+3+4 | Add orientation (50K) + skew (40K) datasets | 2 weeks | Dataset generation (10 days) |
| **Phase 5: + Page Attrs** | All groups | Add RVL-CDIP + Doc3D enriched (~80K) | 2 weeks | Enrichment pipeline |
| **Phase 6: Joint fine-tune** | All groups | Mixed batch from all (~500K+) | 1 week | All phases complete |

**Training approach per phase**:

1. Freeze backbone + all existing heads
2. Train new head(s) only for 5-10 epochs (warmup)
3. Unfreeze backbone with low LR (1/10x) for 20-30 epochs
4. Use PCGrad for conflicting gradients between task groups
5. Balanced batch sampling (equal representation per task group)

### Key training decisions

- **Loss functions**: NormInNormLoss + GaussianNLL for IQA regression, CrossEntropy (class-weighted) for classifications, SmoothL1 for continuous regressions
- **Class imbalance**: Balanced batch sampler for script (Latin 40% vs Hebrew 1%) and handwriting (NONE ~60% vs DOMINANT ~2%)
- **Multi-task conflicts**: PCGrad with gradient accumulation; per-task early stopping; LLRD (layer-wise learning rate decay)
- **Validation**: Separate val metrics per task group. Tibetan validated only on real samples (5-fold CV on 200 samples)

---

## 5. Docling OCR Routing Impact

### How SigLIP 2 outputs drive Docling decisions

The current routing logic (4 strategies: ocr_fast, ocr_advanced, vision_simple, vision_structured) will be enhanced with script-aware routing:

| SigLIP 2 Output | Docling Parameter Affected | Impact |
|---|---|---|
| **script_code = "Hans"** | `ocr_engine: "paddleocr"`, `ocr_lang: "ch"` | PaddleOCR excels at Chinese |
| **script_code = "Arab"** | `ocr_engine: "paddleocr"`, `ocr_lang: "ara"` | Arabic-optimized OCR |
| **script_code = "Deva"** | `ocr_engine: "paddleocr"`, `ocr_lang: "hi"` | Hindi/Nepali OCR |
| **script_code = "Jpan"** | `ocr_engine: "paddleocr"`, `ocr_lang: "japan"` | Japanese OCR |
| **script_code = "Tibt"** | `pipeline: "vlm"` | Tibetan has no good OCR; use VLM |
| **has_non_latin = true** | `page_batch_size: reduced` | CJK models use more memory |
| **has_rtl = true** | Layout engine RTL mode | Arabic/Hebrew reading order |
| **handwriting.presence >= PARTIAL** | `ocr_routing: "ocr_advanced"` or `"vision_simple"` | Handwriting needs special handling |
| **handwriting.legibility <= FAIR** | `pipeline: "vlm"` | Poor handwriting needs VLM |
| **shadow_score > 0.3** | Trigger DocRes shadow removal | Pre-correction before OCR |
| **warping_score > 0.3** | Trigger DocRes dewarping | Pre-correction before OCR |
| **code_confidence > 0.5** | `enrich_code: true` | Enable code syntax detection |
| **orientation != 0** | Auto-rotate before OCR | Correct page orientation |
| **capture_method = CAMERA_*** | Expect perspective/shadow artifacts | Adjust correction thresholds |
| **IQA overall < 0.5** | `ocr_routing: "vision_structured"` | Low quality needs vision model |

### Enhanced pre_ocr_risk formula (updated with script/handwriting)

```
pre_ocr_risk = 0.30 * degradation_score        # from IQA
             + 0.20 * complexity_score          # from layout
             + 0.15 * (1 if image_only else 0)  # pdf type
             + 0.10 * handwriting_penalty        # 0 if NONE, 0.3 if PARTIAL, 0.6 if SUBSTANTIAL, 1.0 if DOMINANT
             + 0.10 * script_difficulty          # 0 for Latin, 0.3 for CJK, 0.5 for Arabic, 0.8 for Tibetan
             + 0.10 * degradation_artifact       # shadow + warping combined
             + 0.05 * (1 - legibility_score)     # handwriting quality
```

---

## 6. Dataset Gaps & Generation Plan

### Critical path items (must complete before training)

| Gap | Effort | Blocks | Priority |
|---|---|---|---|
| ~~**Orientation dataset generation** (50K)~~ | ~~10 days~~ | ~~Phase 4 training~~ | ✅ DONE - available at `E:\image_detection\03_training_datasets\orientation\` |
| **Skew dataset generation** (40K) | 3-5 days | Phase 4 training + MobileNetV4 | HIGH - can share sources with orientation |
| **Resolution quality dataset** (30K) | 3-4 days | MobileNetV4 + SigLIP Group 5 | HIGH - multi-DPI renders with char height labels |
| ~~**synth-multiscript completion** (350K)~~ | ~~5-7 days~~ | ~~Phase 2~~ | ✅ DONE - 350,012 images on GCS (v3, imbalanced distribution — rebalancing needed) |
| **Handwriting label harmonization** | 3 days | Phase 3 training | HIGH |
| **Capture method labeling** for RVL-CDIP | 2-3 days | Phase 5 training | MEDIUM |
| **Shadow/warping enrichment** from Doc3D | 2-3 days | Phase 5 training | MEDIUM |
| **Tibetan real sample collection** (100-300 from Bhutan) | 2-4 weeks | Tibetan accuracy improvement | CRITICAL (long-lead) |

### Existing scripts for dataset generation

- `scripts/generate_orientation_dataset.py` - orientation dataset generation (exists, per design doc)
- `scripts/standardize_layout_labels.py` - layout label standardization
- `scripts/annotate_base_metadata.py` - Layer 1+2 enrichment pipeline
- `scripts/build_training_labels.py` - Layer 3 training label computation
- `scripts/aggregate_layer2_metadata.py` - metadata aggregation

---

## 7. Files to Modify/Create

### Existing files to modify

| File | Change | Purpose |
|---|---|---|
| `modal/train_siglip2_iqa_v2.py` | Add multi-task head groups, phased training loop, PCGrad | Multi-task training |
| `src/image_preprocessing_detector/schema.py` | Add DocumentScriptDetection, bridge HandwritingAssessment, add capture_method | Schema alignment |
| `docs/handoff/PREPARE_DOC_OUTPUT_SPECIFICATION.md` | Add script detection, handwriting, page attributes sections | Handoff contract |
| `docs/schema/document_metadata.schema.json` | Add missing fields (capture_method, text_scope, etc.) | JSON schema |
| `src/image_preprocessing_detector/routing/recommendation_engine.py` | Add script-aware routing, handwriting escalation | OCR routing |
| `src/image_preprocessing_detector/metrics/dqs_calculator.py` | Update pre_ocr_risk formula with script/handwriting | Quality scoring |

### New files to create

| File | Purpose |
|---|---|
| `config/siglip2_multitask.yaml` | Multi-task head configuration (classes, loss weights, LR multipliers) |
| `config/mobilenetv4_precorrection.yaml` | MobileNetV4 stage gate head configuration |
| `config/script_ml_classes.yaml` | 10-class -> ISO 15924 mapping (three-tier architecture) |
| `config/script_routing.yaml` | Script -> Docling OCR engine routing rules |
| `src/image_preprocessing_detector/detection/siglip2_multitask.py` | Production inference wrapper for multi-task model |
| `src/image_preprocessing_detector/detection/mobilenetv4_precorrection.py` | MobileNetV4 stage gate: orientation + skew + resolution quality |
| `src/image_preprocessing_detector/detection/stage_gate.py` | Orchestrator: MobileNetV4 -> corrections -> SigLIP 2 |
| `scripts/generate_handwriting_labels.py` | Harmonize HierText + COCO-Text + IAM labels to unified schema |
| `scripts/generate_skew_dataset.py` | Generate skew regression training data from source docs |
| `scripts/generate_resolution_dataset.py` | Generate multi-DPI training data with character height labels |
| `modal/train_mobilenetv4_precorrection.py` | MobileNetV4 training script (3 heads) |

---

## 8. Verification Plan

### Per-phase validation metrics

| Phase | Key Metric | Target | Validation Set |
|---|---|---|---|
| Phase 1 (IQA) | VQualA | >= 0.92 | DIQA-5000 test (1,000) |
| Phase 2 (Script) | Overall accuracy | >= 90% | MLT19 test + held-out MDIW13 |
| Phase 2 (Script) | Tibetan accuracy (real only) | >= 80% | 5-fold CV on 200 real samples |
| Phase 3 (Handwriting) | Presence accuracy | >= 88% | HierText val + COCO-Text val |
| Phase 3 (Handwriting) | Legibility accuracy | >= 85% | HierText val |
| Phase 4 (Orientation) | Overall accuracy | >= 98% | Orientation test (7,500) |
| Phase 4 (Orientation) | Vertical Japanese | >= 95% as 0-degree | Special eval slice |
| Phase 4 (Skew) | Mean absolute error | < 0.3° | Skew test set (synthetic + natural) |
| Phase 4 (Skew) | % within 0.5° of ground truth | >= 90% | Skew test set |
| Phase 5 (Page Attrs) | Capture method accuracy | >= 85% | RVL-CDIP val |
| Phase 5 (Page Attrs) | Shadow/warping MAE | < 0.08 | Doc3D val |
| Phase 6 (Joint) | No task regression | < 2% drop on any metric | All val sets |

### End-to-end integration test

```bash
# Run full pipeline on test documents
uv run imgprep process test_docs/ --output results/ --model siglip2-multitask

# Verify all schema fields populated
python -c "
import json
from jsonschema import validate
schema = json.load(open('docs/schema/document_metadata.schema.json'))
for doc_dir in Path('results/').iterdir():
    data = json.load(open(doc_dir / 'metadata.json'))
    validate(data, schema)
    assert data.get('languages'), 'Missing language detection'
    for page_summary in data['page_layout_summary']:
        assert 'handwriting_assessment' in page_summary
print('All validations passed')
"
```

### Performance benchmarks

| Metric | Target | How to Test |
|---|---|---|
| SigLIP 2 GPU latency | < 60ms/page | `uv run pytest tests/benchmark/ -k siglip2_latency` |
| Full pipeline GPU | < 200ms/page | End-to-end timing on 100 test docs |
| Full pipeline CPU | < 600ms/page | CPU-only mode timing |
| Memory (GPU) | < 6GB | Monitor during batch of 16 |

---

## 9. MobileNetV4-Conv-S Pre-Correction Model

### Architecture

MobileNetV4-Conv-S is the fast pre-correction stage gate (already selected in Phase 10A consensus).

```text
Input: Raw document page image (any orientation, any resolution)
    |
MobileNetV4-Conv-S backbone (~3.5M params)
    |
Shared Features (1280-dim)
    |
    +---> Head 1: Orientation (4-class classification)
    |     Linear(1280->128) -> ReLU -> Linear(128->4)
    |
    +---> Head 2: Fine Skew (regression)
    |     Linear(1280->128) -> ReLU -> Linear(128->1)
    |     Output: angle in degrees (±10°)
    |
    +---> Head 3: Resolution Quality (regression)
          Linear(1280->128) -> ReLU -> Linear(128->1)
          Output: 0-1 score (0=too small chars, 0.7=optimal, 1.0=oversized)

Total: ~4M params
Inference: ~3ms GPU (A10), ~8-12ms CPU
ONNX export: ~16MB
```

### Training Data (shared with SigLIP Group 3 + Group 5)

| Head | Dataset | Size | Source | Status |
|---|---|---|---|---|
| Orientation | Same as SigLIP Group 3 orientation | 50,000 | 12,500 docs x 4 rotations | ✅ Ready (`E:\image_detection\03_training_datasets\orientation\`) |
| Skew | Same as SigLIP Group 3 skew | 40,000 | Source docs with random skew | Need generation |
| Resolution | Multi-resolution renders | ~30,000 | Source docs at 72/150/200/300/400/600 DPI | Need generation |

**Resolution training data generation**:

1. Take source documents (any with text: DocLayNet, FUNSD, SROIE, etc.)
2. Render at multiple DPI levels: 72, 100, 150, 200, 250, 300, 400, 600
3. Measure character height per render using text line detection
4. Label: resolution_quality = f(character_height) where 32-48px = 0.7 (optimal), <16px = 0.0, >96px = 1.0
5. Cross-validate labels against OCR accuracy at each DPI level

**Training strategy**: Train MobileNetV4 first with synthetic labels, then distill from trained SigLIP 2 for improved accuracy. This creates a virtuous cycle:

1. Train MobileNetV4 on synthetic rotation/skew/resolution labels (ground truth)
2. Train SigLIP 2 multi-task (all heads including orientation/skew/resolution)
3. Re-train MobileNetV4 using SigLIP 2 soft labels as teacher (KL-divergence, T=3)

### MobileNetV4 Verification

| Metric | Target | Validation |
|---|---|---|
| Orientation accuracy | >= 95% (98% with SigLIP distillation) | Orientation test set |
| Skew MAE | < 0.5° | Skew test set |
| Resolution quality MAE | < 0.1 | Multi-DPI test set |
| GPU latency | < 5ms | A10 benchmark |
| CPU latency | < 15ms | 4-core CPU benchmark |

---

## 10. MobileCLIP-2 Distillation Path (Deferred)

Design SigLIP 2 so it can serve as teacher for a **two-stage distillation cascade**: SigLIP 2 → MobileCLIP-2 S4 → MobileCLIP-2 S0.

### Distillation Cascade

```text
Stage 1: SigLIP 2 Multi-Task (88M params, ~50ms GPU)
    │  Export soft label distributions (orientation, script, IQA)
    │  Temperature scaling T=3
    v
Stage 2: MobileCLIP-2 S4 (~35M params, ~10ms GPU)
    │  Trained first using SigLIP 2 soft labels (KL-divergence)
    │  Learns: orientation + script + IQA subset
    │  Validates accuracy is sufficient before distilling further
    v
Stage 3: MobileCLIP-2 S0 (11.4M params, ~1.5ms mobile)
    │  Trained using S4 soft labels (NOT directly from SigLIP 2)
    │  Learns: orientation + script only (minimal heads for on-device)
    v
Mobile/Edge deployment
```

**Why S4 first, then S0**: Direct distillation from a 88M model to 11.4M loses too much signal. The S4 intermediate model (35M) preserves more of SigLIP's knowledge, and S0 learns more effectively from S4's compressed representations than from SigLIP's full distributions.

**Implementation steps**:

1. Export SigLIP 2 soft labels (script + orientation probability distributions) during inference on training data
2. Train MobileCLIP-2 S4 on soft labels (KL-divergence, T=3) + hard labels (cross-entropy)
3. Validate S4 meets accuracy thresholds (orientation >= 95%, script >= 85%)
4. Export S4 soft labels on same training data
5. Train MobileCLIP-2 S0 on S4 soft labels (KL-divergence, T=3)
6. Validate S0 meets mobile accuracy thresholds (orientation >= 92%, script >= 80%)

**Trigger to implement**: When mobile scanning app requires <5ms on-device classification. Not needed for current server-only pipeline.

**Note**: MobileNetV4-Conv-S (Section 9) handles the server-side fast pre-correction. MobileCLIP-2 S4/S0 are for mobile/edge deployment only.
