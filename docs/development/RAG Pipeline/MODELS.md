---
schema_type: common
title: "MODELS"
tags:
  - rag_pipeline
  - architecture
  - ml
  - training
status: published
owner: cv-team
purpose: Architecture documentation for models.
---

This document catalogs the models used across the four projects in the document
pipeline:

- **Project A** – Preprocessing & Image Quality Assessment (IQA)
- **Project B** – OCR, layout & structural extraction
- **Project C** – Post-processing, normalization & QA
- **Project D** – Downstream RAG applications

The goal is:

1. Make model choices explicit and reviewable.
2. Separate **core / required** models from **optional / future** ones.
3. Clarify **who owns what** and where fine-tuning happens.

---

## 1. High-Level Model Map

| Layer       | Purpose                                      | Primary Models                              | Projects |
|------------|----------------------------------------------|---------------------------------------------|----------|
| IQA & CV   | Blur/skew/contrast/warp, doc quality routing | ResNet18 (student), ResNet50 (teacher), classical OpenCV | A |
| Layout     | Layout detection for routing & OCR           | Document-specialized YOLO (YOLO-Doc / YOLOv10-doc), heuristics | A, B |
| OCR        | Text extraction & basic structure            | Marker, DeepSeek-OCR                        | B |
| Math OCR   | Formula → LaTeX                              | Nougat / pix2tex (optional per domain)      | B |
| LLM Helper | Cleanup, normalization, QA                   | Qwen3-4B-Instruct (via Unsloth)             | C |
| RAG LLM    | Domain reasoning & answer generation         | Domain-tuned 4–8B instruct models (via Unsloth) | D |
| Embeddings | Vector search for RAG                        | Modern sentence/embedding model (BGE-class) | D |
| VLM        | Multimodal fallback on very poor scans       | ColPali-class VLM (optional)                | D |

---

## 2. Project A – Preprocessing & IQA Models

Project A is responsible for **file intake, IQA, corrections, and routing
metadata**. It favors deterministic CV and compact CNNs.

### 2.1 IQA Backbone: Teacher–Student Pair

**Purpose:** Learned IQA features for blur, noise, contrast, and document
degradation / DQS features.

- **Teacher model (training only)**
  - **Name:** `resnet50_teacher_iqa`
  - **Type:** ResNet-50
  - **Role:** High-capacity backbone for IQA supervision and feature distillation.
  - **Usage:**
    - Trained on document IQA datasets (real + synthetic).
    - Used to produce soft targets and intermediate features.
    - Not deployed in production; used in training pipelines only.

- **Student model (production)**
  - **Name:** `resnet18_student_iqa`
  - **Type:** ResNet-18
  - **Role:** Main learned IQA model for production.
  - **Usage:**
    - Distilled from `resnet50_teacher_iqa`.
    - Outputs per-page / per-crop quality scores:
      - Overall quality
      - Sharpness / blur
      - Contrast / color fidelity
    - Integrated with classical CV metrics to produce IQA features and DQS inputs.

**Device policy (Project A):**

- **Preferred:** Local GPU (if available and adequate).
- **Fallback:** Local CPU.
- **Remote GPU (Modal):** Only for training / re-training, not routine inference.

### 2.2 Classical Computer Vision (OpenCV-based)

**Purpose:** Fast, deterministic IQA and correction guardrails.

- Blur metric: Laplacian variance
- Skew detection: minAreaRect / Hough transform
- Noise score: small connected components analysis
- Contrast score: histogram / bimodality analysis
- Illumination / shadow, bleed-through, warping, perspective: classical CV heuristics

These methods always run and feed into:

- Issue detection flags
- “Do-no-harm” guardrails for corrections
- Routing signals for downstream decisions

### 2.3 PDF Type Classifier

**Purpose:** Classify `.pdf` as `"image_only"`, `"born_digital"`, or `"hybrid"`.

- **Primary method:** PyMuPDF + heuristic rules (text objects vs embedded images).
- **Optional ML model (if needed):**
  - **Name:** `pdf_type_cnn`
  - **Type:** Lightweight CNN / shallow transformer on rendered low-res page(s).
  - **Role:** Backstop when heuristics are ambiguous (e.g., embedded vector text, odd layouts).
  - **Status:** Optional; only added if heuristic approach is systematically insufficient.

### 2.4 Language ID

**Purpose:** Per-document language detection and “non-Latin script” flag.

- **Model:**
  - **Primary:** fastText language ID or py3langid (library-based classifier).
- **Outputs:**
  - List of language codes (e.g., `["en"]`, `["en", "fr"]`)
  - `has_non_latin: bool` for script-aware routing.

### 2.5 Handwriting vs Printed Classifier

**Purpose:** Mark regions as `"handwritten"` vs `"printed"` for routing to
appropriate OCR.

- **Model:** `handwriting_resnet_classifier`
  - ResNet-style small classifier trained on IAM/SignaTR6K and mixed printed text.
- **Outputs:**
  - `text_type` field on layout elements in downstream JSON.

### 2.6 Layout Detection for Routing (Lightweight)

**Purpose:** Cheap **high-level layout signals** in Project A to inform routing,
without full structural extraction.

- **Model:** `layout_router_yolo`
  - Compact document-tuned detector (e.g., YOLO-Doc / YOLOv10-doc small variant).
  - Classes: coarse categories like “dense text,” “multi-column,” “table-heavy,”
    “image-heavy,” etc.
- **Usage:**
  - Used only in A to:
    - Estimate structural complexity.
    - Provide early hints to Project B for which branches to call.
  - Detailed element/reading-order logic is delegated to B.

---

## 3. Project B – OCR & Layout / Structure Extraction

Project B is the “heavy” processing stage: OCR, layout detection, table/figure
structure, and hierarchical text grouping.

### 3.1 Primary OCR Engine

**Purpose:** Extract textual content with structural hints.

- **Model / System:** **Marker**
  - Provides:
    - OCR text
    - Paragraph / block segmentation
    - Basic structural cues (headings, lists, captions, etc.).
- **Role in pipeline:**
  - Main text extraction for high-quality and mid-quality documents.
  - Produces paragraph-level chunks to reduce complexity for Project C and D.

### 3.2 Secondary OCR / Validation

**Purpose:** Provide secondary OCR signal for hard cases and cross-validation.

- **Model:** **DeepSeek-OCR** (or equivalent high-accuracy OCR model)
- **Usage:**
  - Invoked on:
    - Very noisy / low-quality pages signaled by Project A.
    - Complex visual regions: dense tables, figures, scientific layouts.
  - Used for:
    - Cross-checking Marker output.
    - Selective replacement when DeepSeek clearly outperforms.

### 3.3 Layout Detection (High-Accuracy)

**Purpose:** Precise detection of document elements and reading-order building
blocks.

- **Model:** `yolo_doc_layout`
  - Document-specialized YOLO variant (e.g., YOLO-Doc / YOLOv10-doc) trained on
    DocLayNet-style labels and OmniDocBench-class data.
  - Target classes:
    - Title, Section header, Text, List item, Caption, Picture, Table, Formula,
      Footnote, Page header, Page footer, etc.
- **Outputs:**
  - COCO `[x, y, width, height]` bounding boxes.
  - Class labels + confidences per element.
- **Responsibilities in B:**
  - Element detection for text, tables, figures, captions, formulas.
  - Parasitic content detection (headers/footers/watermarks) tags.
  - Inputs for reading-order algorithms and hybrid IQA per element.

### 3.4 Reading Order & Structural Inference

**Purpose:** Derive accurate **reading order** for elements to minimize RAG
performance loss.

- **Models / Methods:**
  - Primary: graph-based heuristics over YOLO layout output.
  - Optional future: learned reading-order model (GNN / transformer) if needed.
- **Outputs:**
  - Ordered list of element IDs with sequence numbers and confidence.
- **Note:** This is primarily algorithmic, not a separate large model in v1.

### 3.5 Table Structure Recognition

**Purpose:** Obtain internal table structure (rows, columns, cells) where needed.

- **Primary approach in v1:**
  - Prefer **Marker’s** built-in table parsing where accurate and sufficient.
- **Optional dedicated model (v2+):**
  - `table_transformer` (Table Transformer) or `cluster_tabnet`:
    - Input: cropped table region (from `yolo_doc_layout`).
    - Output: cell grid, row/column boundaries, header flags.
- **Status:**
  - **v1:** Rely on Marker’s table output where possible.
  - **v2+:** Introduce Table Transformer / ClusterTabNet only when:
    - Marker fails on complex tables that matter for downstream RAG, or
    - A use case requires precise cell-level semantics.

### 3.6 Math-Aware OCR (Optional per domain)

**Purpose:** Convert mathematical formulas to LaTeX (and optionally human text).

- **Model(s):**
  - `nougat` or `pix2tex` (math OCR).
- **Usage:**
  - Only on pages or regions identified as formula-heavy by layout & A’s metadata.
  - Output LaTeX stored alongside plain text for RAG and analytics.
- **Status:** Optional; enabled for math/technical domains, not mandatory for all
  deployments.

---

## 4. Project C – Post-Processing, Normalization & QA

Project C consumes B’s structured output and performs **cleanup, normalization,
consistency checks, and QA** before RAG ingestion.

### 4.1 Core Helper LLM (v1)

**Purpose:** Domain-agnostic helper for:

- Cleaning and normalizing text (headings, captions, lists).
- Enforcing JSON schema constraints across B’s outputs.
- Labeling / tagging issues (reading-order suspicion, low-confidence tables,
  parasitic content, etc.).
- Producing small natural-language rationales where useful.

**Model:**

- **Name:** `c_helper_qwen3_4b`
- **Type:** Qwen3-4B-Instruct, 4-bit (via Unsloth)
- **Training strategy:**
  - Fine-tuned with Unsloth using:
    - QLoRA / LoRA on a 4-bit base.
    - Task-specific prompts and JSON-only responses.
  - Training data includes:
    - Real + synthetic documents passed through A and B.
    - Gold-standard cleaned/normalized versions.
    - Examples of “issue detection” and “flagging” behavior.

**Deployment:**

- **Primary:** Local GPU (if adequate) in Project C container.
- **Fallback:** Local CPU 4-bit for low-volume workloads.
- **Overflow / heavy batch:** Remote GPU on Modal.

### 4.2 Domain-Specific Helper Heads (Future)

**Purpose:** Specialize C’s behavior for certain document categories without
changing the base model.

- **Approach:** Multiple LoRA adapters on the same Qwen3-4B base:
  - `c_helper_legal_lora` – legal/contract emphasis.
  - `c_helper_technical_lora` – technical/docs emphasis.
  - `c_helper_forms_lora` – form/key-value documents.

**Status:** Future enhancement; not required for v1.

---

## 5. Project D – RAG Applications

Project D is **per-domain**: each RAG application (tax & estate, ballistics,
network infrastructure, etc.) has its own configuration over shared
infrastructure.

### 5.1 Domain RAG LLMs

**Purpose:** Answer questions, perform reasoning, and orchestrate retrieval for
each domain using the cleaned and structured content produced by A–C.

**Base approach:**

- Use a shared small-to-medium base instruct model family (4–8B) via Unsloth,
  then derive per-domain models via LoRA fine-tuning.

**Examples:**

- **Base model (v1):** Qwen3-4B-Instruct via Unsloth
  - **Per-domain adapters:**
    - `d_tax_qwen3_4b_lora`
    - `d_ballistics_qwen3_4b_lora`
    - `d_network_qwen3_4b_lora`
    - etc.

- **Future higher-capacity base (v2+):** Llama-3.x 8B-Instruct via Unsloth
  - Drop-in replacement for the base, adapters retrained as needed.

**Deployment options:**

- Local GPU on Unraid for low-latency private workloads.
- Modal GPU hosting for heavier or spiky workloads.
- Same CPU → local GPU → remote GPU selection policy as Project C, adapted per
  project.

### 5.2 Embedding / Vector Models

**Purpose:** Turn cleaned text and structured content into embeddings for
retrieval.

**Model:**

- **Name:** `d_embedding_model`
- **Type:** High-quality sentence / document embedding model (BGE-class or
  equivalent).
- **Usage:**
  - Shared or per-project, depending on domain language and multilingual
    requirements.
  - Encodes:
    - Paragraphs and sections from B/C.
    - Optional aggregated levels (section, chapter, document).

### 5.3 Multimodal VLM (Optional)

**Purpose:** Provide **multimodal retrieval / QA** on extremely low-quality
documents where OCR is unreliable.

**Model:**

- **Example:** ColPali-class vision-language model.
- **Usage:**
  - Triggered by low DQS or severe OCR degradation from A.
  - Used to answer queries directly from page images where text is unreliable.

**Status:** Optional; reserved for deployments with strong multimodal demand and
adequate GPU budget.

---

## 6. Training vs Inference Strategy

To keep costs manageable and behavior predictable, the following principles
apply:

1. **Project A**
   - **Train:** ResNet50 teacher and ResNet18 student, IQA thresholds, and
     routing logic on dedicated GPU (local or Modal).
   - **Infer (prod):** ResNet18 student + classical CV, preferring local GPU,
     falling back to local CPU. No Modal calls for steady-state inference.

2. **Project B**
   - **Train:** Layout detector (`yolo_doc_layout`), optional table/math models,
     on GPU (likely remote).
   - **Infer (prod):** Layout detector + OCR engines locally where possible;
     remote GPU only for heavy OCR variants if absolutely necessary.

3. **Project C**
   - **Train:** Qwen3-4B-Instruct helper via Unsloth (QLoRA) on GPU (Modal or
     local).
   - **Infer (prod):** Prefer local GPU; CPU or Modal as fallbacks per workload.

4. **Project D**
   - **Train:** Per-domain LLMs as Unsloth LoRAs on GPU (Modal or local).
   - **Infer (prod):** Domain-specific LLMs and embedding model run in the
     RAG stack; GPU location and size is per-project and per-SLA.

---

## 7. Optional / Future Models

The following models are **explicitly optional** and should only be added when
a concrete use case demonstrates sufficient value:

- **PDF type CNN (`pdf_type_cnn`)**
  - Only if heuristics plus PyMuPDF are insufficient.

- **Table structure models (`table_transformer`, `cluster_tabnet`)**
  - Only when Marker’s table output fails on critical workloads.

- **Reading-order learned model**
  - Only if graph-based heuristics fail to meet reading-order error targets.

- **Math OCR (Nougat / pix2tex)**
  - Only for math-heavy domains.

- **Domain-specific helper LoRAs in Project C**
  - Only when domain-specific behavior diverges significantly.

- **Multimodal VLM (ColPali-class)**
  - Only when DQS/OCR degradation is common and multimodal RAG is justified.

Each optional model should have:

1. A clear success metric (e.g., NDCG uplift, reduced OCR error rate).
2. A small scoped experiment before being adopted into the baseline stack.
3. Documentation updates in this file when promoted to “core.”

---
