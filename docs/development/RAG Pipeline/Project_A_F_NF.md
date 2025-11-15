# Project A – Preprocessing & IQA Requirements

**Project:** A – Image Preprocessing & IQA Gateway
**Version:** 1.0
**Date:** 2025-11-15
**Status:** Active

## 1. Purpose & Scope

### 1.1 Purpose

Project A is the **front-door** for all documents entering the OCR/RAG pipeline. Its job is to:

* Normalize **input documents** into consistent page images
* Assess and correct **image quality issues** (blur, noise, skew, illumination, etc.)
* Run **teacher–student IQA models** to produce robust, document-aware quality scores
* Perform **layout-lite detection** to characterize structural complexity (without full semantic layout)
* Compute **Document Quality Score (DQS)** and **routing recommendations** for downstream workflows
* Hand off **cleaned images + structured JSON** to **Project B** (core OCR / semantic extraction)

Project A must be good enough that if OCR fails later, no one can blame preprocessing with a straight face.

### 1.2 Scope

**In scope**

* Input handling for:

  * Images: `.jpg`, `.jpeg`, `.png`, `.tiff`, `.bmp`
  * PDFs: `.pdf` (image-only, born-digital, hybrid)
* Rendering PDFs to page images at a **golden DPI** (e.g., 300)
* Classical IQA:

  * Blur, noise, skew, contrast, illumination, compression artifacts
* ML-based IQA:

  * **ResNet-50 teacher** (high-capacity)
  * **ResNet-18 student** (production default)
  * Uncertainty / discrepancy / high-risk **gating** for teacher fallback
* Layout-lite:

  * Page-level block types (text, table, figure, handwriting presence, background noise)
  * Structural complexity score
* Corrections with **do-no-harm guardrails**:

  * Deskew, denoise, contrast enhancement, illumination correction, mild dewarping / perspective
* Document Quality Score (DQS) & routing recommendation
* JSON metadata & cleaned image output to Project B
* Device-priority execution:

  * **Local GPU → Local CPU → Modal GPU** in that order

**Out of scope (Project A explicitly does NOT)**

* Full OCR or text recognition
* Reading order prediction
* Full DocLayNet-style 11+ class layout semantics
* Table structure reconstruction (rows/columns/cells)
* Chunking or paragraph segmentation
* Embeddings and vector DB ingestion
* RAG evaluation and question-answer metrics

Those belong to Projects B–D.

---

## 2. Functional Requirements (FR)

### FR-A1: File Ingestion & Preflight

1. **Supported inputs**

   * SHALL accept:

     * Single file path (absolute or relative)
     * Byte stream (in-memory)
   * SHALL support:

     * `.pdf`, `.jpg`, `.jpeg`, `.png`, `.tiff`, `.bmp`

2. **Preflight checks**

   * System SHALL run preflight on every file:

     * Confirm supported type by **magic bytes**, not just extension
     * Detect:

       * Password-protected or encrypted PDFs
       * Corruption / unreadable files
       * Empty documents or zero-page PDFs
       * Files over configurable size / page limits
   * On failure, system SHALL:

     * Emit **error JSON** describing the issue
     * NOT crash the service

3. **PDF type classification (lite)**

   * System SHALL classify PDFs into:

     * `image_only`, `born_digital`, or `hybrid`
   * Method:

     * Try text extraction (PyMuPDF or equivalent) + embedded image inspection
   * Result SHALL be written to `pdf_type` in the JSON output.

---

### FR-A2: Rendering & Normalization

1. **Page rendering**

   * PDFs SHALL be rendered to images at a configurable DPI (default: 300).
   * Images SHALL be converted to a consistent color space (e.g. RGB).

2. **Resolution normalization**

   * System SHALL detect image resolution:

     * Width, height (pixels)
     * DPI from metadata if available
   * If **effective DPI < target** (default 300), upscaling SHALL be considered per FR-A7 guardrails.

3. **Golden representation**

   * For each page, system SHALL produce:

     * A “golden” normalized image used for:

       * Classical IQA
       * ML IQA
       * Corrections
       * Hand-off to Project B

---

### FR-A3: Classical IQA

For every page image (normalized):

1. **Blur detection**

   * Compute numeric `blur_score` using Laplacian variance (or equivalent).
   * Normalize to [0.0, 1.0] and INCLUDE in JSON.

2. **Noise detection**

   * Estimate `noise_score` using:

     * Connected components for salt-and-pepper
     * Local variance / frequency estimators
   * Normalize and record.

3. **Skew detection**

   * Estimate `skew_angle` in degrees (e.g., via minAreaRect or Hough).
   * Accuracy target defined in NFR; include angle and confidence.

4. **Contrast & illumination**

   * Compute `contrast_score` via histogram analysis.
   * Compute `illumination_score` for uneven lighting (quadrant / local variance approach).

5. **Compression / artifact score**

   * For JPEG or similar, estimate `compression_artifact_score` (blocking, ringing heuristics).

Classical IQA acts both as a stand-alone signal and a **sanity check** against the ML IQA outputs.

---

### FR-A4: Teacher–Student ML IQA

Project A SHALL implement a **two-tier IQA model strategy**:

1. **Teacher model**

   * Architecture: **ResNet-50** multi-head IQA network.
   * Outputs per page:

     * Blur, noise, skew, illumination, artifact / compression, plus any additional heads defined during training.
   * Purpose:

     * High-fidelity IQA reference
     * Distillation source for student
     * Selective inference on **difficult / high-risk** cases

2. **Student model**

   * Architecture: **ResNet-18** multi-head IQA network.
   * Purpose:

     * **Default** inference model in production
     * Near-teacher accuracy at much lower cost

3. **Primary inference**

   * System SHALL:

     * Run the **student** model on all pages by default.
     * Produce per-page ML IQA outputs written to JSON (e.g., `ml_blur_score`, `ml_noise_score`, etc.).

4. **Model loading**

   * System SHALL allow model file paths to be configured (e.g., ONNX weights paths).
   * Model loading SHALL support:

     * Local filesystem paths
     * Optional remote/model registry locations (if configured)

---

### FR-A5: Uncertainty & Teacher Escalation

Teacher inference is **optional and gated**. Project A SHALL implement:

1. **Uncertainty metrics**

   * For each page and each head, compute:

     * Softmax entropy
     * Top-2 logit margin (difference between highest and second-highest scores)
   * Aggregate into a per-page **uncertainty score**.

2. **Discrepancy metrics**

   * For key dimensions (blur, skew, contrast) compute:

     * |classical_value − student_value|
   * Normalize and aggregate to a **discrepancy score**.

3. **High-risk document tags**

   * System SHALL accept doc-level “risk tags” via:

     * Configurable rules (e.g. file path patterns, source system, metadata)
     * Manual flags in the API
   * Examples: “regulatory filing”, “canonical reference manual”, “legal contract”.

4. **Teacher gating policy**

   * System SHALL decide whether to run the teacher on a page based on:

     * `high_risk_doc == true` OR
     * `uncertainty_score > uncertainty_threshold` OR
     * `discrepancy_score > discrepancy_threshold`
   * Thresholds SHALL be configurable.

5. **Budget constraints**

   * System SHALL enforce:

     * Max pages per document where teacher may run (e.g. top-K worst pages)
     * Max pages per batch / job for teacher use
   * When budget is exceeded, teacher MUST NOT run and student outputs MUST be used instead.

6. **Teacher inference behavior**

   * If gating conditions are met AND resources are available (see FR-A6), system SHALL:

     * Run **ResNet-50** on flagged pages only.
     * Merge outputs so that teacher results **override** student results for those pages.
   * If teacher cannot run, system SHALL:

     * Log reason (no GPU, quota exhausted, budget exceeded, disabled by config).
     * Fall back to **student-only** outputs.

7. **Teacher usage flags**

   * JSON output SHALL include:

     * `teacher_used: bool` at document level
     * `teacher_pages: List[int]` (page indices)
     * Optional reasons per page (uncertainty, discrepancy, high-risk).

---

### FR-A6: Device-Priority Execution

Project A SHALL implement **explicit device selection** in this order:

1. **Device probing**

   * At runtime, system SHALL probe:

     * Local GPU availability (CUDA, memory, utilization)
     * Local CPU characteristics (core count, current load)
     * Modal GPU availability (quota, credentials, basic health)

2. **Priority rules**

   * For **student** inference:

     1. Prefer **local GPU** if available and under load threshold.
     2. Else use **local CPU** if latency fits NFR bounds.
     3. Else use **Modal GPU** if allowed and reachable.
     4. Else fallback to **local CPU** even if slow.
   * For **teacher** inference:

     1. Prefer **local GPU**.
     2. Else try **Modal GPU** if enabled and within quota.
     3. **Teacher MUST NOT run on CPU in production mode**, except:

        * In explicit QA/debug modes (config flag).
        * When manually triggered by an operator.

3. **Configuration**

   * Device selection rules SHALL be configurable via config file / env:

     * `allow_modal_gpu`
     * max local GPU utilization threshold
     * max tolerable CPU latency class
     * `allow_teacher_on_cpu_for_debug`

4. **Logging**

   * For each inference run, system SHALL log:

     * `student_device_used`
     * `teacher_device_used` (if any)
     * Reasons why any higher-priority device was skipped.

---

### FR-A7: Corrections & Guardrails

For each page, Project A SHALL:

1. **Decide corrections**

   * Use combined signals (classical IQA, ML IQA, layout-lite) to decide:

     * Deskew
     * Denoise
     * Contrast/CLAHE
     * Illumination correction
     * Perspective correction (if document boundary is clear)
     * Mild dewarping where feasible

2. **Do-no-harm guardrails (three tiers)**

   * **Tier 1: Preconditions**

     * Only apply a correction if:

       * IQA metrics exceed configured severity thresholds.
       * Detection confidence is above a minimum.
   * **Tier 2: Parameter bounding**

     * Clamp correction parameters to safe ranges (e.g., max rotation angle, max sharpen strength).
   * **Tier 3: Post-comparison**

     * Recompute relevant IQA metrics after correction.
     * If quality degraded beyond tolerance, **rollback** to original and log.

3. **Transform history**

   * For each page, system SHALL record:

     * `transform_history` array:

       * `action` (e.g. `deskew`, `clahe`)
       * `parameters`
       * `skipped: bool`
       * `skip_reason` or `rollback_reason` if applicable

---

### FR-A8: Layout-Lite & Structural Complexity

Project A does **not** do full DocLayNet layout, but SHALL provide **layout-lite** signals needed for routing:

1. **Block detection (lite)**

   * Detect coarse regions:

     * `text_block`
     * `table_block`
     * `figure_block` (pictures/diagrams)
     * `background_noise` (large non-text regions)
   * No fine class semantics (no captions, titles, headers, footers; that’s Project B).

2. **Handwriting presence**

   * Classify each page as:

     * `handwriting_present: bool`
   * Where possible, optionally produce a rough proportion (small/medium/high).

3. **Structural complexity score**

   * Compute a **complexity score** per page (0–1) based on:

     * Number and arrangement of text blocks
     * Presence of tables, figures
     * Multi-column indications
     * Handwriting presence
   * Aggregate to document-level structural complexity (for DQS).

---

### FR-A9: Document Quality Score (DQS) & Routing

Project A SHALL compute DQS and routing hints:

1. **DQS**

   * Two axes:

     * **Degradation**: blur, noise, skew, illumination, resolution, artifacts
     * **Structural complexity**: from layout-lite features
   * Output:

     * `dqs_degradation` ∈ [0, 1]
     * `dqs_complexity` ∈ [0, 1]

2. **Routing recommendation**

   * Using DQS + pdf_type + layout-lite + handwriting flags, system SHALL compute:

     * `routing_recommendation` in a small enum, e.g.:

       * `ocr_fast` (clean, simple)
       * `ocr_advanced` (complex layout or some degradation)
       * `vision_simple` (structured VLM for poor scans)
       * `vision_structured` (complex + degraded)
   * Also include:

     * `routing_confidence: float`
     * `routing_rationale: str` (human-readable summary)

Routing is an **advisory** field for Projects B–D, not a binding workflow engine.

---

### FR-A10: Interface & Output Schema

1. **CLI**

   * Provide CLI commands:

     * `prepA process <file>`
     * `prepA batch <directory>`
   * Options for:

     * Output directory
     * Override thresholds
     * Enabling/disabling teacher fallback
     * Device policy test modes

2. **Library/API**

   * Provide a Python API (or language of choice) to process:

     * Single document: returns an in-memory result object and/or JSON.
     * Batch documents: iterator / generator interface.

3. **Output**

   * Per document:

     * Document-level metadata:

       * `file_path`, `num_pages`, `pdf_type`, language hints if available
       * DQS
       * routing recommendation
       * teacher usage fields
     * Per page:

       * Classical IQA metrics
       * ML IQA metrics (student, teacher if used)
       * Layout-lite summary
       * Transform history
   * JSON MUST conform to a versioned schema (`schema_version` field).

---

### FR-A11: Logging & Observability

Project A SHALL:

1. Emit **structured logs** for:

   * Preflight results
   * Device selection decisions
   * Student / teacher runs
   * Teacher gating decisions & reasons
   * Corrections applied / rolled back
   * Errors & exceptions

2. Provide **metrics hooks** for:

   * pages_processed_total
   * teacher_pages_total
   * teacher_skipped_due_to_budget_total
   * teacher_skipped_due_to_resources_total
   * average_student_latency_{cpu,gpu,modal}
   * average_teacher_latency_{gpu,modal}

---

## 3. Non-Functional Requirements (NFR)

### NFR-A1: Performance

1. **Student (ResNet-18)**

   * CPU:

     * Target: ≤ 40 ms / page
     * Acceptable: ≤ 100 ms / page
   * GPU:

     * Target: ≤ 10 ms / page
     * Acceptable: ≤ 25 ms / page

2. **Teacher (ResNet-50)**

   * GPU (local or Modal):

     * Target: ≤ 30 ms / page for flagged pages
     * Teacher MUST NOT be used on CPU in production modes.

3. **End-to-end latency**

   * (Rendering + IQA + layout-lite + corrections + DQS)
   * Target:

     * GPU-enhanced path: < 150 ms / page (for documents not dominated by teacher use)
     * CPU-only path: < 400 ms / page
   * Acceptable:

     * Up to 400 ms / page (GPU) and 1000 ms / page (CPU) for worst-case documents.

4. **Throughput**

   * Target: ≥ 2 pages/sec/worker in CPU-only mode
   * Target: ≥ 6 pages/sec/worker with GPU in normal-case documents.

---

### NFR-A2: Accuracy & Reliability

1. **IQA accuracy**

   * Teacher:

     * Correlation with target IQA labels (Pearson/Spearman) ≥ 0.8 on validation sets.
   * Student:

     * Correlation vs teacher ≥ 0.9.
     * Overall mAP (for quality categories) within small margin of teacher (e.g., Δ ≤ 0.03).

2. **PDF type classification**

   * Accuracy ≥ 99.5% on validation set.

3. **Skew estimation**

   * Error ≤ ±0.5° on typical document scans.

4. **Teacher gating**

   * On curated test corpus:

     * Teacher SHOULD run on:

       * ≥ X% of genuinely hard documents (high-degradation / high-risk)
       * ≤ Y% of trivially easy documents
     * X and Y to be set during tuning, but gating logic MUST be demonstrably non-random and effective.

5. **Fallback behavior**

   * Service MUST remain operational under:

     * No GPU available
     * Modal outages
     * Teacher model missing or corrupted
   * In such cases:

     * Fall back to student-only, CPU-capable mode.
     * Log degraded-mode operation.

---

### NFR-A3: Cost & Resource Control

1. Modal GPU usage MUST be:

   * Controlled via configuration:

     * `allow_modal_gpu`
     * `modal_budget_per_run`
   * Visible through logs/metrics.

2. Teacher usage MUST be:

   * Bounded by:

     * Per-document page limit
     * Per-run or per-batch document limit
   * Disabled by default for large batch jobs (unless explicitly enabled).

3. Local GPU utilization thresholds MUST:

   * Prevent Project A from starving other critical services on the host.

---

### NFR-A4: Maintainability & Extensibility

1. **Config-first**

   * All tunable thresholds and paths (gating, device selection, DPI, IQA thresholds) MUST live in configuration, not hard-coded.

2. **Model versioning**

   * Teacher and student models MUST:

     * Be versioned explicitly (e.g., `teacher_model_version`, `student_model_version`).
     * Allow rolling forward/back by config change, not code change.

3. **Clear interfaces**

   * Input/Output schema MUST be stable and versioned.
   * Downstream Projects B–D should not be broken by internal model swaps.

4. **Code quality**

   * Linting, typing, tests as previously agreed:

     * Formatter and linter enforced
     * Type checking on critical modules
     * Unit + integration tests for all major flows.

---

### NFR-A5: Observability & Debuggability

1. **Traceability**

   * A single document run MUST be traceable end-to-end:

     * Which device was used
     * Which pages escalated to teacher and why
     * Which corrections were applied or rolled back

2. **Reproducibility**

   * Given the same input and configuration, system SHOULD produce deterministic outputs (within floating-point tolerances).

---

### NFR-A6: Security & Robustness

1. **Input safety**

   * Enforce file size and page count limits.
   * Validate file headers to prevent obvious parser exploits.

2. **Secrets & credentials**

   * Modal and any remote registry credentials MUST be supplied via environment or secret store.
   * No secrets in source code or committed configuration.

3. **Failure isolation**

   * A failure on a single file MUST NOT bring down the service.
   * Batch mode MUST continue processing remaining files after logging a failure for one.
