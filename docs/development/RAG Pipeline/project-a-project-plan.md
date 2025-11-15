# **PROJECT A – PROJECT PLAN**

---

# **1. Purpose**

Project A transforms arbitrary input documents into:

* normalized, corrected pages,
* page-level IQA metrics,
* a unified **Document Quality Score (DQS)**,
* lightweight layout indicators,
* and routing metadata for Project B.

**New addition:**
A **two-tier IQA model strategy**:

* **ResNet-18 student** = default production inference
* **ResNet-50 teacher** = selective fallback for:

  * high-risk documents
  * high student uncertainty
  * strong conflict with classical IQA

Performance and cost remain under control through **local→GPU→Modal** priority logic.

---

# **2. Scope**

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

---

# **3. OUT OF SCOPE**

* OCR
* Layout segmentation for reading order
* Paragraph chunking
* Table structure extraction
* Vector DB embedding
* LLM postprocessing

Anything that smells like OCR or chunking goes to Project B/C.

---

# **4. Architecture**

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

---

# **5. Functional Requirements**

### **5.1 Teacher Model Use**

The system MUST support inference-time use of ResNet-50 **under gated conditions**.

Teacher inference triggers:

1. **High-risk document tags**
2. **Student uncertainty**

   * softmax entropy above a threshold
   * or top-2 logit margin < threshold
3. **Student–classical conflict**

   * classical blur vs student blur_out disagree beyond Δ
   * skew estimator vs student skew_out disagree beyond Δ

Teacher use MUST adhere to:

* Maximum page budget per document
* Maximum document budget per run
* Device priority rules

### **5.2 IQA Pipeline**

* Student model always runs first
* Teacher model optionally reruns per flagged page
* Merge strategy:

  * teacher overrides student for flagged pages
  * student governs all others

### **5.3 Device Priority**

The system MUST evaluate and choose the inference device in this exact order:

1. **Local GPU** (if CUDA available & load < threshold)
2. **Local CPU** (if latency within acceptable bounds)
3. **Modal GPU** (remote fallback)

All branches must be logged.

### **5.4 Logging**

New logs required:

* teacher_invocations
* teacher_invocation_reason (risk, uncertainty, discrepancy)
* device_used (local_gpu, local_cpu, modal_gpu)
* gating_metrics

---

# **6. Non-Functional Requirements**

### **Performance**

* Student inference (CPU): ≤40 ms/page
* Student inference (GPU): ≤10 ms/page
* Teacher inference should NEVER run on CPU unless explicitly forced for QA/evaluation

### **Cost Optimization**

* Modal GPU usage must be optional and bounded
* Teacher fallback is disabled by default in high-volume batch mode

### **Stability**

* If teacher unavailable (no GPU locally or remote budget exceeded), pipeline MUST continue using student-only outputs.

---

# **7. Work Breakdown Structure (WBS)**

---

## **PHASE 0 — Project Setup (Week 0–1)**

0.1 Project skeleton
0.2 Modal workspace + credentials
0.3 GPU/CPU device probing utilities
0.4 Configuration system (YAML) including:

* teacher_fallback_enabled
* uncertainty thresholds
* discrepancy thresholds
* max_pages_for_teacher
0.5 Logging/telemetry scaffolding

---

## **PHASE 1 — Dataset Pipelines (Week 1–2)**

1.1 Dataset registry
1.2 Ingest DocLayNet
1.3 Ingest DocBank
1.4 Ingest TableBank
1.5 Handwriting datasets (IAM/NIST)
1.6 Synthetic augmentation: blur/noise/warp
1.7 Difficulty-bucket stratified sampling
1.8 Teacher-specific dataset pre-processing

---

## **PHASE 2 — ResNet-50 Teacher Model Training (Week 2–4)**

2.1 Multi-head model architecture
2.2 Loss functions for classification + regression
2.3 Heavy augmentations for robustness
2.4 Training loops for local GPU with fallback to Modal
2.5 Validation on OHR-Bench
2.6 Export teacher to ONNX + TorchScript
2.7 Teacher accuracy/latency report
2.8 Register in model registries

---

## **PHASE 3 — Knowledge Distillation (ResNet-18 Student) (Week 4–5)**

3.1 Distillation loss (KL + CE)
3.2 Soft-target generation from teacher
3.3 Student training (local GPU prioritized)
3.4 Benchmark student inference CPU vs GPU
3.5 Model selection winner (latency/accuracy tradeoff)
3.6 Export + registry packaging
3.7 Student/teacher discrepancy analysis

---

## **PHASE 4 — Classical IQA (Week 5–6)**

4.1 Laplacian-based blur
4.2 Wavelet noise estimator
4.3 Hough skew
4.4 Lighting metrics
4.5 JPEG blockiness
4.6 Student vs classical discrepancy threshold tuning

---

## **PHASE 5 — Uncertainty & Escalation Logic (Week 5–6)**

5.1 Softmax entropy calculator
5.2 Top-2 margin computation
5.3 Discrepancy scoring
5.4 High-risk document tagger configuration
5.5 Teacher escalation manager
5.6 Page-budget enforcement
5.7 Logging + metrics for fallbacks

---

## **PHASE 6 — Layout-Lite Detection (Week 6–8)**

6.1 YOLOv8-nano detector (text block, table block, figures)
6.2 Handwriting classifier
6.3 Complexity scorer
6.4 Integrated “structural features” API

---

## **PHASE 7 — Corrections (Week 8–9)**

7.1 Deskew models (ML + classical hybrid)
7.2 Denoise (BM3D + UNet-lite)
7.3 Contrast normalization
7.4 Shadow removal
7.5 Perspective correction
7.6 Pre/post snapshots
7.7 Correction-confidence safeguards

---

## **PHASE 8 — DQS & Routing (Week 9)**

8.1 DQS weighting tuned against OCR/RAG performance
8.2 Per-page + per-document scoring
8.3 Routing logic updates based on:

* teacher results
* layout-lite classifications
* complexity flags
  8.4 JSON schema output

---

## **PHASE 9 — Device-Priority Execution (Week 9)**

9.1 Local GPU load estimation
9.2 Local CPU fallback rules
9.3 Modal GPU remote inference client
9.4 End-to-end device-selection testing
9.5 Budget guards

---

## **PHASE 10 — Validation, Reporting, Documentation (Week 10)**

10.1 Benchmark full pipeline
10.2 Teacher vs student end-to-end performance report
10.3 Stress tests (large batches)
10.4 Update PlantUML diagrams
10.5 Final README + API reference

---

# **7. Deliverables (Updated)**

* Teacher model (ResNet-50)
* Student model (ResNet-18)
* Distillation toolkit
* Uncertainty + discrepancy gating logic
* Device-priority execution module
* IQA metrics
* Layout-lite models
* Correction engine
* DQS + routing generator
* All logs + monitoring hooks
* Full containerized runtime
* Benchmark results
* Updated PlantUML diagrams

---

# **8. Summary of the Teacher Policy**

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
