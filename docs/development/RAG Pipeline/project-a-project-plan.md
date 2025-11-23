---
schema_type: common
title: "Project A Implementation Plan"
description: "Detailed 10-week implementation roadmap for Project A"
tags: [planning, roadmap, development, project_management]
status: published
owner: "docs-team"
purpose: "Provide week-by-week implementation plan for Project A preprocessing and IQA system."
---

## 2. Scope

### **In Scope **

* Teacher–student pipeline:

  * ResNet-50 training
  * Distillation to ResNet-18
* Selective teacher inference triggered by:

  * Document risk classification
  * Student uncertainty thresholds
  * Discrepancies between classical IQA and student output
* Device-priority execution:

  1. Local GPU
  2. Local CPU
  3. Modal GPU
* Document ingestion, rendering, classical IQA
* ML IQA, layout-lite, corrections
* Routing metadata

## 4. Architecture

```
                   ╔════════════════════════════════════════╗
                   ║           TRAINING PHASE               ║
                   ╠════════════════════════════════════════╣
Raw Datasets
   ↓
[ResNet-50 Teacher Training]
   ↓
Teacher Weights
   ↓
[Knowledge Distillation → ResNet-18]
   ↓
Student Model (default inference)
Teacher Model (selective inference)
Registered in local + Modal registries


                   ╔════════════════════════════════════════╗
                   ║           RUNTIME PHASE                ║
                   ╠════════════════════════════════════════╣
Incoming Document
   ↓
Preflight Checks
   ↓
Rendering (golden DPI)
   ↓
[Primary IQA Pass → ResNet-18]
       ↓
[Uncertainty Gate]
   ├── If low uncertainty & no conflicts → accept student output
   ├── If high-risk doc → escalate to teacher
   ├── If softmax entropy high → escalate to teacher
   ├── If classical vs student discrepancy high → escalate to teacher
       ↓
[Teacher Pass (ResNet-50) - device priority logic]
       ↓
IQA Metrics Merged
       ↓
Layout-Lite Detection
       ↓
Corrections
       ↓
DQS + Routing
       ↓
Output Package → Project B
```

## 6. Non-Functional Requirements

### **Performance**

* Student inference (CPU): ≤40 ms/page
* Student inference (GPU): ≤10 ms/page
* Teacher inference should NEVER run on CPU unless explicitly forced for QA/evaluation

### **Cost Optimization**

* Modal GPU usage must be optional and bounded
* Teacher fallback is disabled by default in high-volume batch mode

### **Stability**

* If teacher unavailable (no GPU locally or remote budget exceeded), pipeline MUST continue using student-only outputs.

## PHASE 0 — Project Setup (Week 0–1) ✅ COMPLETE

0.1 ✅ Project skeleton (poetry, pre-commit, CI/CD)
0.2 ✅ Modal workspace + credentials (gcs-credentials secret)
0.3 ✅ GPU/CPU device probing utilities
0.4 ✅ Configuration system (YAML) including:

* teacher_fallback_enabled
* uncertainty thresholds
* discrepancy thresholds
* max_pages_for_teacher
0.5 ✅ Logging/telemetry scaffolding (structlog + rich)

## PHASE 2 — ResNet-50 Teacher & ResNet-18 Student Training (Week 2–4)

### Infrastructure (COMPLETE ✅)

2.0a ✅ Three-tier storage architecture (NFS + local symlinks + GCS backup)
2.0b ✅ Dataset management scripts (create_symlinks.py, organize_dual_storage.py)
2.0c ✅ 100K dataset generation pipeline with 13-dimensional distribution tracking
2.0d ✅ Modal training infrastructure with GCS integration

### Teacher Training (COMPLETE ✅)

2.1 ✅ Multi-head model architecture (ResNet-50, 5 IQA heads)
2.2 ✅ Loss functions for classification + regression (MultiHeadIQALoss)
2.3 ✅ Heavy augmentations for robustness (100K synthetic dataset)
2.4 ✅ Training loops for Modal GPU (T4/A10)
2.5 ✅ Best checkpoint: epoch 20, val_loss=0.2694
2.6 ✅ Export teacher to ONNX (gs://image_detection_b/models/phase2_iqa/)
2.7 Teacher accuracy/latency report (pending formal benchmark)
2.8 Register in model registries (GCS complete, local pending)

### Student Distillation (IN PROGRESS 🔄)

2.9 ✅ ResNet-18 student architecture (12.5M params, 2.47x smaller)
2.10 ✅ DistillationLoss (KL divergence + BCE, T=4.0, α=0.7)
2.11 ✅ StudentTrainer with frozen teacher soft targets
2.12 🔄 Student training on Modal T4 GPU (30 epochs, started 2025-11-22)
2.13 ⬜ Export student to ONNX + TorchScript
2.14 ⬜ Student vs teacher performance comparison

## PHASE 4 — Classical IQA (Week 5–6)

4.1 Laplacian-based blur
4.2 Wavelet noise estimator
4.3 Hough skew
4.4 Lighting metrics
4.5 JPEG blockiness
4.6 Student vs classical discrepancy threshold tuning

## PHASE 6 — Layout-Lite Detection (Week 6–8)

6.1 YOLOv8-nano detector (text block, table block, figures)
6.2 Handwriting classifier
6.3 Complexity scorer
6.4 Integrated “structural features” API

## PHASE 8 — DQS & Routing (Week 9)

8.1 DQS weighting tuned against OCR/RAG performance
8.2 Per-page + per-document scoring
8.3 Routing logic updates based on:

* teacher results
* layout-lite classifications
* complexity flags
  8.4 JSON schema output

## PHASE 10 — Validation, Reporting, Documentation (Week 10)

10.1 Benchmark full pipeline
10.2 Teacher vs student end-to-end performance report
10.3 Stress tests (large batches)
10.4 Update PlantUML diagrams
10.5 Final README + API reference

## 8. Summary of the Teacher Policy

**Default inference:**

* **ResNet-18 only**

**Teacher runs only if:**

* Document is high-risk
* Student output has high entropy
* Student contradicts classical IQA
* Config explicitly forces teacher pass
* GPU available locally or via Modal

**Teacher must NOT run:**

* If no GPU exists
* During high-volume batch runs unless explicitly enabled
* If page budget exceeded

---
