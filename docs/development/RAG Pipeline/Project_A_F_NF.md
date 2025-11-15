---
schema_type: common
title: "Project A Functional and Non-Functional Requirements"
description: "Comprehensive requirements specification for Project A preprocessing and IQA"
tags: [documentation, planning, architecture, iqa]
status: published
owner: "docs-team"
purpose: "Define all functional and non-functional requirements for Project A preprocessing and image quality assessment."
---

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
