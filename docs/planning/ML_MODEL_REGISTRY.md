# ML Model Registry — Project A

> **Status**: Living Reference Document
> **Scope**: All ML models and classical detectors used in Project A (production inference,
> labeling pipeline, training, and planned/deferred).
> **Last Updated**: 2026-02-21
> **Related Plans**: [SIGLIP2_MULTITASK_REQUIREMENTS.md](SIGLIP2_MULTITASK_REQUIREMENTS.md),
> [DATASET_DIVERSITY_REQUIREMENTS.md](DATASET_DIVERSITY_REQUIREMENTS.md),
> [TRAINING_OPTIMIZATION_PLAN.md](TRAINING_OPTIMIZATION_PLAN.md)

---

## Quick Reference

| Model | Role | Params | GPU Latency | CPU Latency | Status |
|---|---|---|---|---|---|
| **SigLIP 2 NAFlex** | Production — multi-task teacher | 88M | 50ms | 300–500ms | Primary (Phase 4+) |
| **MobileNetV4-Conv-S** | Production — pre-correction gate | 4M | 3ms | 8–12ms | Stage gate |
| **docling-layout-egret-xlarge** | Production — layout (accuracy) | ~30M | 25ms | 150–200ms | Accuracy variant |
| **docling-layout-heron** | Production — layout (speed) | ~20M | 10ms | 80–100ms | Speed variant |
| **Classical IQA (8 detectors)** | Fallback / validation | N/A | <25ms | <25ms | Always-on |
| **Classical Handwriting (Stroke Analysis)** | Fallback — handwriting | N/A | <10ms | <10ms | Confidence-gated |
| **Classical Orientation** | Fallback — orientation | N/A | <15ms | <15ms | CPU-only path |
| **SkewEstimator (MobileNetV4-Conv-S)** | Production — skew | 4M | — | 17.5ms | Complete |
| **MUSIQ** | Labeling | 27M | A10G | — | IQA pseudo-labels |
| **QualiCLIP** | Labeling | 150M | A10G | — | IQA consensus |
| **DocIQ-Replica** | Labeling | 25M | A100 | — | Doc quality labels |
| **Qwen3-VL-8B** | Labeling | 8B | A100-80GB | — | VLM consensus |
| **InternVL3-8B** | Labeling | 8B | A100-80GB | — | VLM alternative |
| **PaddleOCR DBNet** | Labeling | Pre-trained | A100 | ⚠️ SIGILL issue | Resolution labels |
| **ResNet-50 (Teacher IQA)** | Legacy | 25M | 30ms | 100–150ms | Superseded Phase 3 |
| **ResNet-18 (Student IQA)** | Legacy | 11M | 10ms | 40–100ms | Superseded Phase 3 |
| **MobileCLIP-2 S4** | Planned — mobile | 35M | 10ms | — | Deferred |
| **MobileCLIP-2 S0** | Planned — edge | 11.4M | — | 1.5ms mobile | Deferred |

---

## Section 1: Production Inference Models

These models run in the live document processing pipeline.

---

### 1.1 SigLIP 2 NAFlex

| Property | Value |
|---|---|
| **Backbone** | SigLIP 2 ViT-B/16, NaFlex (variable aspect ratio, max 784 patches) |
| **Parameters** | ~88M (86M backbone + ~2M task heads) |
| **GPU Latency** | ~50ms/page (A10 GPU) |
| **CPU Latency** | ~300–500ms/page (single-pass fallback) |
| **Memory (GPU)** | <6 GB (batch=16) |
| **Export** | ONNX (22 output heads), model registry |
| **Source File** | `src/image_preprocessing_detector/detection/siglip2_multitask.py` |
| **Config** | `config/siglip2_multitask.yaml` |
| **Training Script** | `modal/train_siglip2_multitask.py` |

**Purpose**: Unified multi-task analysis in a single inference pass after MobileNetV4 pre-correction.

**22 Task Heads Across 5 Groups**:

| Group | Heads | Task Type | Output |
|---|---|---|---|
| G1: IQA | blur, noise, contrast, skew, compression, overall_quality | 6× regression | 0–1 severity |
| G2: Script | script_code, has_non_latin, has_rtl | 1× classification + 2× boolean | ISO 15924 class + flags |
| G3: Orientation + Skew | orientation_cls, skew_reg, confidence | 1× classification + 1× regression + 1× confidence | 4-class + degrees |
| G4: Handwriting | presence_cls, legibility_cls, content_cls, presence_score, legibility_score | 3× classification + 2× regression | 5/6/7-class + 0–1 |
| G5: Page Attributes | capture_cls, shadow_reg, warping_reg, code_reg, resolution_quality_reg | 1× classification + 4× regression | 7-class + 0–1 |

**Head Architecture (shared pattern)**:

```
Group 1–3 heads: Linear(768→256) → ReLU → Dropout(0.3) → Linear(256→N_out)
Group 4–5 heads: Linear(768→128) → Linear(128→N_out)   [shallower for P2 tasks]
```

**Training Strategy**:

- Phased multi-task: Warmup (G1+G2, 5 ep) → Expand (+G3+G4, 5 ep) → Full (all, 20–40 ep) → Refine (5–10 ep)
- Loss: Kendall uncertainty weighting + PCGrad gradient surgery + NormInNormLoss (IQA)
- Optimizer: AdamW, CosineAnnealing, bfloat16 mixed precision
- Dataset: ~503K images across 10 purpose-built datasets

**Classical Fallback Triggers** (per-head):

| Head | Confidence Threshold | Fallback |
|---|---|---|
| Orientation | < 0.70 | Hough line transform |
| Skew | < 0.60 | Hough skew detector |
| Resolution | < 0.50 | DPI + character height estimation |
| IQA (any) | < 0.50 | Classical 8-detector ensemble |
| Script | < 0.60 | Unicode range analysis (OpenLID mapping) |
| Handwriting (any) | < 0.50 | Stroke analysis (see Section 3.2) |

**Performance Targets**:

| Phase | Metric | Target | Validation Set |
|---|---|---|---|
| Phase 1 (IQA) | VQualA | ≥ 0.92 | DIQA-5000 test (1,000) |
| Phase 2 (Script) | Overall accuracy | ≥ 90% | MLT19 + held-out MDIW13 |
| Phase 2 (Script) | Tibetan accuracy (real only) | ≥ 80% | 5-fold CV on 200 real samples |
| Phase 3 (Handwriting) | Presence accuracy | ≥ 88% | HierText val + COCO-Text val |
| Phase 3 (Handwriting) | Legibility accuracy | ≥ 85% | HierText val |
| Phase 4 (Orientation) | Overall accuracy | ≥ 98% | Orientation test (7,500) |
| Phase 4 (Orientation) | Vertical Japanese as 0° | ≥ 95% | Special eval slice |
| Phase 4 (Skew) | MAE | < 0.3° | Skew test set |
| Phase 4 (Skew) | % within 0.5° of GT | ≥ 90% | Skew test set |
| Phase 5 (Page Attrs) | Capture method accuracy | ≥ 85% | RVL-CDIP val |
| Phase 5 (Page Attrs) | Shadow/warping MAE | < 0.08 | Doc3D val |
| Phase 6 (Joint fine-tune) | No task regression | < 2% drop on any metric | All val sets |

---

### 1.2 MobileNetV4-Conv-S (Pre-Correction Stage Gate)

| Property | Value |
|---|---|
| **Backbone** | MobileNetV4-Conv-S (ImageNet pretrained) |
| **Parameters** | ~4M (~3.5M backbone + ~0.5M heads) |
| **Feature Dim** | 1280-dim (NOTE: `model.num_features` returns 960; probe with dummy forward pass) |
| **GPU Latency** | ~3ms/page (A10 GPU) |
| **CPU Latency** | ~8–12ms/page (4-core CPU) |
| **Export** | ONNX (~16MB), TorchScript |
| **Source File** | `src/image_preprocessing_detector/detection/mobilenetv4_precorrection.py` (planned) |
| **Orchestrator** | `src/image_preprocessing_detector/detection/stage_gate.py` (planned) |
| **Config** | `config/mobilenetv4_precorrection.yaml` (planned) |
| **Training Script** | `modal/train_mobilenetv4_precorrection.py` (planned) |

**Purpose**: Ultra-fast pre-correction before SigLIP 2. Ensures SigLIP 2 sees a correctly oriented, properly resolved image. Runs ~17× faster than SigLIP 2.

**3 Task Heads**:

```
Linear(1280→128) → ReLU → Linear(128→4)  [Head 1: Orientation, 4-class: 0/90/180/270]
Linear(1280→128) → ReLU → Linear(128→1)  [Head 2: Skew, regression ±10°]
Linear(1280→128) → ReLU → Linear(128→1)  [Head 3: Resolution quality, regression 0–1]
```

**Correction Gating** (applied after inference):

| Head | Confidence Gate | Action |
|---|---|---|
| Orientation | > 0.90 | Rotate by detected orientation |
| Skew | \|angle\| > 0.3° | Deskew by predicted angle |
| Resolution | < 0.40 | Upscale (target: 32–48px char height) |
| Resolution | > 0.80 AND image > 4000px | Downscale (target: 48px char height) |

Safety rails: never below 150 DPI, never above 600 DPI.

**Training Strategy**:

1. **Bootstrap**: Train on synthetic ground-truth labels (CE + MSE losses)
2. **Distillation**: Re-train using SigLIP 2 soft labels (KL-divergence, temperature T=3, α=0.7)

**Training Datasets**:

| Head | Dataset | Size | Status |
|---|---|---|---|
| Orientation | Same as SigLIP Group 3 | 50,000 | ✅ Ready |
| Skew | Shared sources + random skew | 40,000 | Need generation |
| Resolution | Multi-DPI renders | ~30,000 | Need generation |

**Performance Targets**:

| Stage | Orientation | Skew MAE | Resolution MAE | GPU Latency | CPU Latency |
|---|---|---|---|---|---|
| Bootstrap | ≥ 95% | < 0.5° | < 0.1 | < 5ms | < 15ms |
| After distillation | ≥ 98% | < 0.3° | < 0.08 | < 5ms | < 15ms |

---

### 1.3 docling-layout — Two Variants

| Property | docling-layout-egret-xlarge (Accuracy) | docling-layout-heron (Speed) |
|---|---|---|
| **Variant** | Accuracy-priority | Speed-priority |
| **GPU Latency** | ~25ms/page | ~10ms/page |
| **CPU Latency** | ~150–200ms | ~80–100ms |
| **mAP** | Higher | Lower |
| **Use Case** | Accuracy-first routing | Speed-first routing |
| **Selection** | Deployment config (not training) | Deployment config (not training) |

**Shared Properties**:

| Property | Value |
|---|---|
| **Architecture** | YOLOv10 backbone fine-tuned on DocLayNet |
| **Parameters** | egret-xlarge: ~30M, heron: ~20M |
| **Source File** | `src/image_preprocessing_detector/detection/doclayout_yolo.py` |
| **Integration** | `detection/layout_lite/doclayout_integration.py` |

**Purpose**: Object detection with spatial localization across 11 DocLayNet classes. Provides coarse layout attributes (has_tables, has_figures, etc.) that SigLIP 2 cannot provide (image-level only).

**11 DocLayNet Classes**: Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title

**Output**: COCO-aligned bboxes `[x, y, width, height]`, confidence per detection

**Performance**: Pre-trained by Docling project — no additional training required.

---

## Section 2: Classical Detection Models (Zero-Latency Fallbacks)

These run deterministically on CPU with no GPU requirement. Always available regardless of device policy.

---

### 2.1 Classical IQA Detectors (8-Detector Ensemble)

| Property | Value |
|---|---|
| **Implementation** | `src/image_preprocessing_detector/detection/iqa_classical.py` |
| **Combined Latency** | < 25ms CPU (all 8 in parallel) |
| **Parameters** | N/A (classical algorithms) |
| **Status** | Phase 1C complete — always-on |

**8 Detectors**:

| Detector | Algorithm | Output | Correction Trigger |
|---|---|---|---|
| **Blur** | Laplacian variance | 0–1 severity | Sharpen (unsharp mask) if < 0.3 |
| **Noise** | Wavelet sigma estimation (high-freq std) | 0–1 severity | Denoise (bilateral) if > 0.5 |
| **Contrast** | Histogram spread (percentile range) | 0–1 severity | CLAHE if < 0.3 |
| **Skew** | Hough line transform | Degrees (±45°) | Deskew if > 0.3° |
| **Illumination** | Brightness map + uniformity | 0–1 severity | Flag only |
| **JPEG Blockiness** | DCT coefficient variance | 0–1 severity | Flag only |
| **Binarization Quality** | Otsu threshold separation | 0–1 quality | Flag only |
| **Bleed-Through** | Double-sided ink variance | 0–1 severity | Flag only |

---

### 2.2 Classical Text Gate

| Property | Value |
|---|---|
| **Implementation** | `src/image_preprocessing_detector/detection/text_gate.py` |
| **Latency** | < 10ms CPU |
| **Precision** | 99.5% |

**Algorithm**: Ensemble vote across stroke density, connected components, and edge density.
Routes to TEXT_DETECTED or NO_TEXT path before expensive model inference.

---

### 2.3 Classical Orientation Detector

| Property | Value |
|---|---|
| **Implementation** | `src/image_preprocessing_detector/detection/orientation_detector.py` |
| **Latency** | < 15ms CPU |
| **Accuracy** | ~85% |

**Algorithm**: Hough line direction analysis + text baseline detection. CPU-only fallback when both MobileNetV4 and SigLIP 2 are unavailable.

---

### 2.4 Classical Handwriting Detector (Stroke Analysis)

| Property | Value |
|---|---|
| **Implementation** | `src/image_preprocessing_detector/detection/iqa_classical.py` |
| **Latency** | < 10ms CPU |
| **Activation** | SigLIP 2 Group 4 any head confidence < 0.50 |

**Algorithm**:

1. **Binarize** input using Otsu threshold
2. **Connected component** extraction — filter to text-sized components
3. **Stroke width variance**: High variance → printed (regular strokes); low variance → handwriting (irregular)
4. **Run-length encoding** on horizontal scan lines — handwriting produces irregular run lengths
5. Combine into `has_handwriting` (bool) + `handwriting_confidence` (0–1)

**Output**: Binary `has_handwriting` flag + confidence score. Does NOT attempt legibility or content_type classification — those fall back to 0 / N/A when SigLIP 2 is unavailable.

---

## Section 3: Labeling Pipeline Models

These models run offline in the data preparation pipeline to generate pseudo-labels for training datasets. They do NOT run in production inference.

---

### 3.1 DeQA Pseudo-Labeling Ensemble

**Purpose**: Generate weak IQA labels for 2.5M images via consensus ensemble. All models run on Modal serverless GPU infrastructure.

**Architecture**: Batch scheduler distributes jobs → each model scores images independently → result aggregator computes consensus → layout mask cache (pre-computed via docling-layout) improves scores.

| Model | Params | Hardware | Purpose |
|---|---|---|---|
| **MUSIQ** (Mobile Photo Quality Assessment) | 27M | A10G | Photo quality scoring (0–100 scale) — weak IQA labels for real photo datasets |
| **QualiCLIP** | 150M | A10G | Vision-language quality assessment — cross-modal quality validation |
| **DocIQ-Replica** | 25M + layout masks | A100-80GB | Document-specific quality (distilled from teacher) — core pseudo-labeling signal |
| **Qwen3-VL-8B** | 8B | A100-80GB | Multi-modal document analysis with text understanding — labels ambiguous cases |
| **InternVL3-8B** | 8B | A100-80GB | General vision-language reasoning — alternative consensus signal, handwriting detection |

**Reference**: `docs/architecture/diagrams/level-2/data-preparation/schema-field-population-workflow.puml`

---

### 3.2 VLM IQA Labeling Pilot (Claude Opus 4.6)

| Property | Value |
|---|---|
| **Model** | Claude Opus 4.6 (in-session vision) |
| **Pilot Status** | Complete: 200/200 DIQA-5000 images scored |
| **SRCC (all)** | 0.39 |
| **SRCC (non-rotated)** | 0.53 |
| **SRCC sharpness** | 0.58 |

**Decision**: Proceed with prompt v2.0 (orientation-independent scoring + finer granularity). Scale to 2–5K if SRCC > 0.60.

**Root cause of low SRCC**: 48% of high-MOS images are rotated 90°. VLM penalizes rotation; DIQA MOS does not. Non-rotated SRCC=0.53 is +91% better than best classical detector (0.28).

**Scripts**: `scripts/select_iqa_vlm_images.py`, `scripts/collect_vlm_iqa_labels.py`

---

### 3.3 PaddleOCR DBNet (Resolution Quality Labeling)

| Property | Value |
|---|---|
| **Model** | PaddleOCR DBNet (text detection) |
| **Version Constraint** | `paddleocr>=2.7,<3.0` ONLY — v3 API completely incompatible |
| **Hardware** | A100 GPU (Vultr 207.246.124.234) |
| **CPU Caveat** | ⚠️ SIGILL on Intel Broadwell (no AVX-512) |
| **Throughput** | ~12.1 img/s with GPU (~7.6 min for DIQA-5000) |

**Purpose**: Stage 1 of resolution quality labeling pipeline. Detects text regions to enable character height measurement.

**2-Stage Pipeline**:

1. **Stage 1 (DBNet)**: Text detection → bounding boxes around text regions
2. **Stage 2 (CC Analysis)**: Connected component analysis within detected regions → character height distribution

**Output**: `char_height` (pixels), `resolution_quality` score (0–1), bucket label

**cuDNN Setup Required**:

```bash
pip install nvidia-cudnn-cu11 nvidia-cublas-cu11
# + symlink to /usr/local/cuda/lib64/
```

**Scripts**: `scripts/label_resolution_quality.py`, `scripts/integrate_resolution_quality.py`

---

### 3.4 Domain Classification LLMs (Metadata Labeling)

These LLMs assign domain labels (TAX, FIN, SCI, EDU, etc.) and capture method labels to source datasets. They run offline as part of Layer 2 metadata enrichment. Not referenced in production inference.

| Model | Hardware | Use |
|---|---|---|
| **DeepSeek-R1** | A100 | Primary domain classification |
| **Llama-3.3-70B** | A100 | Alternative/validation |
| **Step-3.5-Flash** | A100 | Speed-priority labeling |
| **Qwen3-Coder** | A100 | Code detection labeling |
| **Gemini-2.0-Flash** | API | Cross-validation |
| **Qwen2.5-VL-3B** | A10G | Lightweight visual classification |

---

## Section 4: Training Infrastructure Models

Models used during the training pipeline but not in production or labeling.

---

### 4.1 SkewEstimator (MobileNetV4-Conv-S Trained)

| Property | Value |
|---|---|
| **Architecture** | MobileNetV4 backbone (conv_small @ 224px) + 3 heads |
| **Parameters** | ~4M |
| **CPU Latency** | mean 17.5ms, p50 17.4ms, p95 18.8ms |
| **Dataset** | 90,412 images (71,498 synthetic + 18,914 natural scans) |
| **Training Script** | `modal/train_skew_estimator.py` |

**3 Heads**: Orientation (4-class), Skew bins (42-class discretization), Regression (continuous angle)

**Best Configuration Results** (conv_small @ 224px, 50 epochs):

| Metric | Value |
|---|---|
| Val MAE | 0.837° (epoch 47) |
| Test MAE | 0.956° |
| SRCC | 0.936 |
| Orientation accuracy | 99.5% |
| Within 0.5° | 70.8% |

**Run ID**: `20260212_155402`, checkpoint: `best_model.pt` (epoch 47)

**Next Steps**: ONNX INT8 quantization, dataset expansion, longer training (100+ epochs)

---

## Section 5: Planned / Deferred Models

---

### 5.1 MobileCLIP-2 S4 (Distillation Intermediate)

| Property | Value |
|---|---|
| **Parameters** | ~35M |
| **GPU Latency** | ~10ms/page |
| **Status** | PLANNED — deferred to mobile deployment phase |
| **Trigger** | Mobile scanning app requiring < 5ms on-device |

**Purpose**: Intermediate step in distillation cascade. Preserves more of SigLIP 2's knowledge before further compression to S0.

**Training**: KL-divergence from SigLIP 2 soft labels (T=3) + hard labels

**Performance Targets**: Orientation ≥ 95%, Script ≥ 85%

---

### 5.2 MobileCLIP-2 S0 (Edge / On-Device Final)

| Property | Value |
|---|---|
| **Parameters** | ~11.4M |
| **Mobile Latency** | ~1.5ms on-device |
| **Status** | PLANNED — deferred to mobile deployment phase |

**Purpose**: Ultra-compact on-device model. Learns orientation + script only (minimal heads).

**Training**: KL-divergence from S4 soft labels (NOT directly from SigLIP 2 — too large a gap)

**Performance Targets**: Orientation ≥ 92%, Script ≥ 80%

**Distillation Cascade**:

```
SigLIP 2 (88M, ~50ms GPU)
    ↓ soft labels (T=3)
MobileCLIP-2 S4 (35M, ~10ms GPU)     ← validates first
    ↓ soft labels (T=3)
MobileCLIP-2 S0 (11.4M, 1.5ms mobile) ← final mobile target
```

---

## Section 6: Legacy / Superseded Models

---

### 6.1 ResNet-50 (Teacher ML IQA — Phase 3)

| Property | Value |
|---|---|
| **Parameters** | ~25M |
| **GPU Latency** | ~30ms/page (selective inference only) |
| **CPU Latency** | ~100–150ms/page |
| **Training** | 50 epochs on OHR-Bench dataset |
| **Performance** | val_loss=0.27, mAP > 0.88 |
| **Export** | ONNX, TorchScript |
| **Status** | SUPERSEDED — replaced by SigLIP 2 NAFlex in Phase 4+ |

---

### 6.2 ResNet-18 (Student ML IQA — Phase 3)

| Property | Value |
|---|---|
| **Parameters** | ~11M |
| **GPU Latency** | ≤10ms/page (target), ≤25ms (acceptable) |
| **CPU Latency** | ≤40ms/page (target), ≤100ms (acceptable) |
| **Training** | 30 epochs on OHR-Bench, knowledge distillation from ResNet-50 |
| **Performance** | val_loss=0.14, mAP > 0.88 |
| **Export** | ONNX, TorchScript |
| **Status** | SUPERSEDED — replaced by SigLIP 2 NAFlex in Phase 4+ |

**Implementation**: `src/image_preprocessing_detector/detection/iqa_ml.py`

---

### 6.3 Layout Fusion Downsampler (LEGACY ResNet-50)

| Property | Value |
|---|---|
| **Status** | LEGACY — appears in model-training-swimlane legend only |
| **Notes** | Marked LEGACY in swimlane; superseded by docling-layout |

---

## Section 7: Production Pipeline Integration

```
Raw Document
    │
    ▼
[Pre-flight: PyMuPDF DPI extraction] ← metadata only, no ML
    │
    ▼
[MobileNetV4-Conv-S] (~3ms GPU, ~12ms CPU) ←─── STAGE GATE
    ├── Orientation (4-class: 0/90/180/270)
    ├── Skew regression (±10°)
    └── Resolution quality (0–1)
    │
    ▼ Corrections applied (gated by confidence)
    │  Rotate if conf > 0.90
    │  Deskew if |angle| > 0.3°
    │  Upscale if quality < 0.40
    │  Safety: 150–600 DPI
    │
    ▼ (corrected image)
[SigLIP 2 NAFlex] (~50ms GPU)  ←──────────────── FULL ANALYSIS
    ├── G1: IQA (6 regression)
    ├── G2: Script (3 heads)
    ├── G3: Orientation + Skew (validation)
    ├── G4: Handwriting (5 heads)
    └── G5: Page attributes (5 heads)
    │
    ├── [LOW CONFIDENCE ANY HEAD] → Classical fallback
    │     Orientation < 0.70 → Hough
    │     Skew < 0.60 → Hough
    │     Resolution < 0.50 → DPI + char height
    │     IQA < 0.50 → 8-detector ensemble
    │     Script < 0.60 → Unicode range analysis
    │     Handwriting < 0.50 → Stroke analysis
    │
    ▼ (parallel, on corrected image)
[docling-layout] (~25ms GPU) ──────────────────── LAYOUT DETECTION
    ├── docling-layout-egret-xlarge (accuracy-priority)
    └── docling-layout-heron (speed-priority)
    11 DocLayNet classes + COCO bboxes
    │
[Classical IQA] (~25ms CPU) ──────────────────── VALIDATION
    8 detectors: blur, noise, contrast, skew,
    illumination, JPEG artifacts, binarization, bleed-through
    │
    ▼
Aggregate: DQS + pre_ocr_risk + routing recommendation
Remaining corrections: CLAHE, sharpen, denoise
    │
    ▼
DocumentMetadata.json + corrected images → Project B

Total GPU: ~55–65ms (3ms MobileNetV4 + 50ms SigLIP 2 + overhead)
Total CPU: ~500–600ms (SigLIP 2 single-pass fallback)
```

---

## Section 8: Hardware Requirements

| Context | GPU | Notes |
|---|---|---|
| **Production inference (preferred)** | Local GPU or A10 | MobileNetV4 + SigLIP 2 + docling-layout |
| **Production inference (fallback)** | Modal GPU (~60ms SigLIP 2) | Auto-fallback if local GPU unavailable |
| **Production inference (last resort)** | CPU only | ~500–600ms/page |
| **MobileNetV4 training** | A10 (~$0.60/hr) | 30-50 epochs, ~2–4 hours |
| **SigLIP 2 training** | A10 or A100 | ~10/run estimated |
| **DeQA pseudo-labeling** | A100-80GB | MUSIQ/QualiCLIP: A10G; Qwen3-VL-8B/InternVL3: A100 |
| **Resolution quality labeling** | A100 (A100-80GB preferred) | cuDNN setup required; NO Broadwell CPU |
| **PaddleOCR version constraint** | Any GPU | `paddleocr>=2.7,<3.0` ONLY — v3 incompatible |

---

## Section 9: OOD Script Reservation Policy

The following scripts are **permanently excluded** from all training manifests and reserved as OOD holdout anchors. This policy is enforced by `_check_ood_leakage()` in `prepare_multitask_datasets.py` and `_validate_manifest_no_ood()` in the training script.

| Script | ISO 15924 | OOD Anchor Role |
|---|---|---|
| **Mongolian** | Mong | Top-to-bottom (TTB) orientation anchor |
| **Syriac** | Syrc | Right-to-left (RTL) anchor |
| **Georgian** | Geor | Left-to-right (LTR) unique letterform anchor |

These scripts must **never** appear in any `train_manifest.json` or `val_manifest.json` regardless of training phase.

---

*Maintained by: Byron Williams | Last updated: 2026-02-21*
*Source of truth: `docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md`, `docs/architecture/diagrams/`*
