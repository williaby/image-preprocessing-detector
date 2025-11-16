---
schema_type: common
title: "Project A Functional and Non-Functional Requirements v2.0"
tags:
  - rag_pipeline
  - architecture
  - requirements
  - specifications
  - functional
  - non_functional
status: published
owner: cv-team
purpose: Architecture documentation for project a functional and non-functional requirements v2.0.
---

**Project:** A – Image Preprocessing & IQA Gateway
**Version:** 2.0 (COMPREHENSIVE RESTORATION)
**Date:** 2025-11-15
**Status:** DRAFT - Pending Review
**Supersedes:** Project_A_F_NF.md v1.0

---

## Document Control

**Changes from v1.0:**
- ✅ Added office format support (FR-1.2)
- ✅ Added comprehensive error handling (FR-1.4)
- ✅ Added PDF type classification (FR-2.1)
- ✅ Added text detection gate evaluation (FR-2.4)
- ✅ Added binarization quality (FR-3.9), bleed-through (FR-3.11), hybrid IQA (FR-3.14)
- ✅ Changed layout model to YOLOv10-doc with full 11 DocLayNet classes (FR-4.1-4.2)
- ✅ Added COCO bounding box specification (FR-4.3)
- ✅ Added vertical text, table quality, spatial hints (FR-4.7, 4.11, 4.12)
- ✅ Added specialized content detection (FR-5.1, 5.4-5.7)
- ✅ Added binarization correction, dewarping, bleed-through suppression (FR-6.6, 6.8, 6.10)
- ✅ Restored detailed NFRs (accuracy targets, configurability, deployment)

---

## 1. Purpose & Scope

### 1.1 Purpose

Project A is the **front-door** for all documents entering the four-project OCR/RAG pipeline. Its mission:

**"Identify, Assess, Correct, Route"**

* **Normalize** input documents (PDFs, images, office files) into consistent page images
* **Assess** image quality comprehensively (classical + ML IQA, per-page and per-element)
* **Detect** all layout elements, specialized content, and quality issues
* **Correct** quality defects with do-no-harm guardrails
* **Calculate** Document Quality Score (DQS) for intelligent routing
* **Route** to appropriate downstream workflows in Project B
* **Hand off** cleaned images + rich structured metadata to Project B

Project A must be good enough that if OCR fails later, no one can blame preprocessing with a straight face.

### 1.2 Scope

**In Scope (Project A Responsibilities)**

* **Input handling:**
  * Images: `.jpg`, `.jpeg`, `.png`, `.tiff`, `.bmp`
  * PDFs: `.pdf` (all types: image-only, born-digital, hybrid)
  * Office documents: `.docx`, `.xlsx`, `.pptx` (embedded image extraction only)

* **Image quality assessment (Classical + ML):**
  * Classical IQA: Blur, noise, skew, contrast, illumination, binarization, bleed-through, warping, perspective, compression artifacts
  * ML IQA: ResNet-50 teacher (high-capacity), ResNet-18 student (production default)
  * Hybrid IQA: Per-element quality assessment on figures, tables, embedded images

* **Layout detection (Light - All 11 DocLayNet Classes):**
  * Model: YOLOv10-doc (specifically trained on DocLayNet)
  * Classes: Caption, Footnote, Formula, List-Item, Page-Footer, Page-Header, Picture, Section-Header, Table, Text, Title
  * Output: Bounding boxes (COCO format), coarse attributes, structural complexity
  * **NOT full semantic layout** (no reading order, no element linking - that's Project B)

* **Specialized content detection:**
  * Formulas, watermarks, stamps/seals, signatures, margin annotations, handwriting, vertical text

* **Image corrections (with do-no-harm guardrails):**
  * Deskew, denoise, contrast enhancement, illumination normalization, DPI upscaling, binarization, dewarping, perspective correction, bleed-through suppression, sharpening

* **Document Quality Score (DQS):**
  * Two-axis scoring: Degradation (0-1) + Structural Complexity (0-1)
  * Routing recommendations: vision_simple, vision_structured, ocr_fast, ocr_advanced

* **Device-priority execution:**
  * Local GPU → Local CPU → Modal GPU (in that order)

**Out of Scope (Project B/C/D Responsibilities)**

* Full OCR text extraction (Project B)
* Reading order prediction (Project B)
* Full semantic layout with element linking (Project B)
* Footnote reference linking (Project B)
* Figure-caption semantic linking (Project B)
* Table structure reconstruction (rows/columns/cells) (Project B)
* Multi-engine OCR fusion (Project C)
* Trust scoring (Project C)
* RAG-optimized chunking (Project C)
* Vector embeddings and DB ingestion (Project D)
* Semantic search and retrieval (Project D)

### 1.3 Project A Philosophy

**What Project A Does:**
- Detect WHERE elements are (bounding boxes, quality scores, presence flags)
- Assess WHAT QUALITY elements have (blur, noise, contrast, per-element)
- Apply TARGETED CORRECTIONS (only where needed, with rollback safety)
- Provide ROUTING INTELLIGENCE (DQS, complexity, recommendations)

**What Project A Does NOT Do:**
- Determine WHAT'S IN elements (that requires OCR/text extraction - Project B)
- Determine HOW TO READ elements sequentially (reading order - Project B)
- Determine HOW ELEMENTS RELATE semantically (linking - Project B)
- Determine HOW TO CHUNK for RAG (semantic chunking - Project C)

---

## 2. Functional Requirements (FR)

### FR-1: General System & File Handling

#### FR-1.1: File Input

The system SHALL accept single file input via:
- File path (absolute or relative)
- Byte stream (in-memory processing)

#### FR-1.2: Supported File Formats

**Images:**
- `.jpg`, `.jpeg`, `.png`, `.tiff`, `.bmp`
- Color and grayscale images
- Single-page and multi-page TIFF

**PDFs:**
- `.pdf` (all types: image-only, born-digital, hybrid)
- Encrypted PDFs (error if password-protected)
- Multi-page PDFs

**Office Documents (NEW - Embedded Image Extraction Only):**
- `.docx` - Word documents
- `.xlsx` - Excel spreadsheets
- `.pptx` - PowerPoint presentations

**Office Document Workflow:**
1. Use Docling to extract all embedded images from office documents
2. Apply standard preprocessing pipeline to each extracted image:
   - Ingestion & normalization (FR-2.2)
   - Quality detection (FR-3.x classical + ML IQA)
   - Corrections with guardrails (FR-6.x)
   - Per-element metadata generation
3. Hand off preprocessed images + metadata to Project B
4. **Project B** handles office text extraction and structure parsing (using Docling)

**Scope Boundary:**
- Project A: Extract and preprocess embedded images only
- Project B: Parse office text, tables, formatting, structure

**Rationale:**
- Office documents contain embedded images (charts, diagrams, photos, scanned inserts) that benefit from IQA and correction
- Text and structure parsing is better handled by specialized office processors (Docling has native .docx/.xlsx/.pptx support)
- Separation of concerns: Project A owns image quality, Project B owns text/structure extraction

**Out of Scope:**
- PDF Portfolios (deprecated format, rarely encountered)
- Other formats: `.odt`, `.rtf`, `.epub` (no current demand)

#### FR-1.3: JSON Output

The system SHALL output a single, structured JSON metadata file conforming to **Pydantic v2 Schema** (see `src/image_preprocessing_detector/schema.py`).

**Schema:** `DocumentMetadata` model with fields:
- `schema_version`: str (e.g., "2.0")
- `file_path`: str
- `document_type`: Literal["image", "pdf", "office_word", "office_excel", "office_powerpoint"]
- `pdf_type`: Optional[Literal["image_only", "born_digital", "hybrid"]] (for PDFs)
- `num_pages`: int
- `languages`: Optional[List[str]] (primary detected languages)
- `quality_score`: DocumentQualityScore (DQS with degradation + complexity axes)
- `routing_recommendation`: RoutingRecommendation (ocr_fast/advanced, vision_simple/structured)
- `pages`: List[PageMetadata]
- `teacher_usage`: Optional[TeacherUsageSummary] (which pages used teacher, why)
- `processing_metadata`: ProcessingMetadata (timestamps, devices used, versions)

**Per-Page Schema:** `PageMetadata` with:
- `page_number`: int
- `resolution`: Resolution (width, height, DPI)
- `classical_iqa`: ClassicalIQAMetrics (blur, skew, noise, contrast, etc.)
- `ml_iqa`: MLIQAMetrics (student scores, teacher scores if used)
- `detected_elements`: List[DocumentElement] (layout bounding boxes in COCO format)
- `specialized_content`: SpecializedContent (formulas, watermarks, stamps, signatures, etc.)
- `transform_history`: List[TransformAction] (corrections applied, skipped, rolled back)
- `complexity_score`: float (0-1, structural complexity for this page)

#### FR-1.4: Error Handling (RESTORED)

The system SHALL gracefully handle and log errors for:

1. **Unsupported file formats:**
   - Return error JSON with `{"error": "unsupported_format", "message": "...", "file_path": "..."}`
   - Include suggested formats in error message
   - Exit code 1 (CLI mode)

2. **Corrupted files that cannot be opened:**
   - Return error JSON with `{"error": "file_corrupted", "message": "...", "file_path": "..."}`
   - Log stack trace for debugging (not exposed to user)
   - Continue processing remaining files in batch mode

3. **Password-protected or encrypted files:**
   - Return error JSON with `{"error": "file_encrypted", "message": "Password-protected files not supported"}`
   - Do NOT attempt to crack or bypass encryption

4. **PDF Portfolio files:**
   - Return error JSON with `{"error": "pdf_portfolio_not_supported", "message": "PDF Portfolio format is deprecated"}`
   - Suggest extracting individual PDFs from portfolio

5. **File size limit exceeded:**
   - Configurable limit (default: 100MB per file, 1000 pages per PDF)
   - Return error JSON with `{"error": "file_too_large", "message": "...", "size_mb": X, "limit_mb": Y}`

6. **Processing timeout:**
   - Configurable per-page timeout (default: 30 seconds/page)
   - Return partial results if some pages completed
   - Log timeout details for investigation

**Batch Mode Error Handling:**
- Continue processing remaining files after error
- Collect all errors and report at end
- Partial success: Return results for successful files, errors for failed files

**Error Logging:**
- All errors logged with structured logging (timestamp, file_path, error_type, stack trace)
- User-friendly error messages (no stack traces exposed to user)
- Debug mode: Verbose error details available via `--debug` flag

#### FR-1.5: Command-Line Interface

The system SHALL provide a CLI for document processing.

**Commands:**
- `prepA process <file>` - Process single document
- `prepA batch <directory>` - Process directory of documents

**Required Arguments:**
- Input file path (single file) or directory path (batch mode)

**Optional Arguments:**
- `--output <path>` - Output JSON file path (default: `<input_name>.json`)
- `--output-dir <path>` - Output directory for batch processing (default: `./results/`)
- `--config <path>` - Path to configuration file (overrides defaults)
- `--blur-threshold <float>` - Override blur detection threshold
- `--skew-threshold <float>` - Override skew detection threshold
- `--enable-teacher` - Enable teacher model fallback (default: disabled for batch)
- `--device <gpu|cpu|modal>` - Force specific device (overrides auto-selection)
- `--debug` - Verbose logging with stack traces

**Output:**
- JSON metadata file per document
- Processing logs to stdout/stderr (structured logging with `rich` console)
- Exit code 0 on success, non-zero on failure

**Error Handling:**
- Invalid file paths: Exit code 1, error message to stderr
- Processing errors in batch mode: Continue with remaining files, log errors
- Configuration errors: Exit code 2, validation message to stderr

---

### FR-2: File Format Analysis

#### FR-2.1: PDF Type Classification (RESTORED)

The system SHALL analyze all `.pdf` files and classify as:

- **"image_only"**: No extractable digital text (scanned document)
- **"born_digital"**: Extractable digital text, no significant image-based content
- **"hybrid"**: Both extractable digital text AND significant embedded images with text

**Method:**
- Use PyMuPDF text extraction attempt
- If zero text objects → "image_only"
- If text objects AND embedded images with text → "hybrid"
- If text objects AND no/minimal embedded images → "born_digital"

**Output:**
- Add `pdf_type` field to `DocumentMetadata`
- Add confidence score for classification

**Routing Impact:**
- `image_only` → Project B uses vision-based OCR (Marker vision mode)
- `born_digital` → Project B uses text extraction (PyMuPDF fast path)
- `hybrid` → Project B uses both (vision OCR + text extraction, reconcile conflicts)

**Rationale:**
- Critical for routing decisions in Project B
- Avoids expensive vision OCR on born-digital PDFs
- Enables hybrid strategy for documents with both digital text and scanned images

#### FR-2.2: Office Format Detection

The system SHALL identify office document types:
- `.doc`/`.docx` → `document_type: "office_word"`
- `.xls`/`.xlsx` → `document_type: "office_excel"`
- `.ppt`/`.pptx` → `document_type: "office_powerpoint"`

**Processing:**
- Route to Docling for embedded image extraction
- Extract images → Apply preprocessing pipeline → Hand off to Project B

#### FR-2.3: Learned Quality Assessment (ML IQA)

**ALREADY COVERED IN FR-A4 (Teacher-Student ML IQA)**

See FR-A4 for ResNet-50 teacher / ResNet-18 student architecture details.

#### FR-2.4: Text Detection Gate (EVALUATE - PENDING BENCHMARK)

**Decision Pending:** Prototype and benchmark before committing.

**Proposed Functionality:**
- Fast ensemble approach (stroke density, connected components, edge density)
- 2/3 consensus voting
- Routes documents to:
  - **No text detected** → IQA-only path (skip layout detection)
  - **Text detected** → Full pipeline (layout detection + hybrid IQA)

**Performance Requirements (if implemented):**
- Latency: <10ms/page (CPU), <5ms/page (GPU)
- Accuracy: Precision >95%, Recall >95%

**Evaluation Criteria:**
- Measure YOLOv10-doc latency on pure images vs text documents
- **Decision Rules:**
  - If layout detection <20ms on all types → **SKIP gate** (not worth complexity)
  - If layout detection >50ms on pure images → **IMPLEMENT gate** (meaningful savings)
  - If layout detection 20-50ms → **MARGINAL** (decision based on complexity tolerance)

**Action Item:**
- [ ] Benchmark YOLOv10-doc on pure images vs text documents
- [ ] Compare: (text_gate + conditional layout) vs (always layout)
- [ ] Document decision with benchmark results

**Rationale for Evaluation:**
- Original requirement assumed expensive layout detection (YOLOv8 at 25-70ms CPU)
- YOLOv10-doc may be significantly faster (better architecture, DocLayNet-specific training)
- If layout detection is fast enough (<20ms), gate adds complexity without benefit
- Need empirical data to make informed decision

---

### FR-3: Image Quality Detection & Correction

#### FR-3.1: Blur Detection

The system SHALL calculate a quantitative **blur_score** using:
- **Classical:** Laplacian variance (cv2.Laplacian)
- **ML:** Student model blur head (ResNet-18), Teacher model if flagged (ResNet-50)

**Output:**
- `classical_blur_score`: float (0-1, Laplacian variance normalized)
- `ml_blur_score`: float (0-1, student model output)
- `teacher_blur_score`: Optional[float] (0-1, if teacher was invoked)

**Interpretation:**
- High score (>0.8) = sharp image
- Low score (<0.4) = blurry image

#### FR-3.2: Skew Detection and Correction

The system SHALL detect document skew angle using:
- **Classical:** cv2.minAreaRect() on content block
- **ML:** Student/Teacher model skew head

**Detection Output:**
- `skew_angle`: float (degrees, -45° to +45°)
- `skew_confidence`: float (0-1)

**Correction (with Do-No-Harm Guardrails):**
1. **Threshold 1:** Only correct if |angle| > 2.0° (configurable)
2. **Threshold 2:** Apply correction and measure quality improvement
3. **Threshold 3:** Only keep correction if blur_score improves by >5%
4. **Rollback:** If correction degrades quality, use original image

**Configuration:**
- `skew_angle_threshold`: Default 2.0° (range: 0.5° - 5.0°)
- `variance_improvement_threshold`: Default 5% (range: 1% - 10%)
- `enable_deskew_guardrails`: Default true

#### FR-3.3: Noise Detection

The system SHALL calculate a **noise_score** to identify:
- Salt-and-pepper noise (small isolated components)
- Stains and smudges (large non-text components)
- Ink bleed-through (from opposite side of page)

**Methods:**
- **Classical:** Connected component analysis (cv2.connectedComponents)
- **ML:** Student/Teacher model noise head

**Output:**
- `classical_noise_score`: float (0-1)
- `ml_noise_score`: float (0-1)

#### FR-3.4-3.6: Image Resolution, DPI Detection, DPI Upscaling

**ALREADY COVERED IN FR-A2 (Rendering & Normalization)**

See FR-A2 for resolution normalization and upscaling details.

Additional requirements:
- Report original DPI in JSON
- Report whether upsampling was applied
- Track upscaling metadata (algorithm, processing time, file sizes)

**Upscaling Algorithms:**
1. `lanczos` - Best quality (recommended for production)
2. `bicubic` - Balanced speed/quality
3. `inter_linear` - Fastest
4. `inter_cubic` - Alternative high-quality
5. `inter_area` - Downsampling (for oversized images)

#### FR-3.7: Contrast Assessment

The system SHALL calculate a **contrast_score** using:
- **Classical:** Histogram analysis (bimodal = good, single-peak = low)
- **ML:** Student/Teacher model contrast head

**Output:**
- `classical_contrast_score`: float (0-1)
- `ml_contrast_score`: float (0-1)

#### FR-3.8: Do-No-Harm Guardrails for All Corrections

**ALREADY COVERED IN FR-A7 (implied)**

Expand with explicit three-tier guardrail system:

**Tier 1: Confidence Thresholds (Pre-Correction)**
- Skip corrections with low confidence scores (below configurable threshold)
- Reject extreme parameter values (e.g., skew >45°, blur_score >200)
- Validate input parameters within acceptable ranges

**Tier 2: Parameter Limits (During Correction)**
- Cap correction strength based on issue severity (LOW, MEDIUM, HIGH, CRITICAL)
- Adaptive parameters scale with severity:
  - CLAHE clip limit: 1.0 (LOW) → 4.0 (CRITICAL)
  - Sharpening amount: 0.5 (LOW) → 2.0 (CRITICAL)
- Maximum strength limits to prevent over-correction

**Tier 3: Quality Validation + Rollback (Post-Correction)**
- Measure quality metrics (blur, contrast, noise) before and after
- Compare corrected vs original image quality
- Rollback to original if quality degrades:
  - Blur increases >20%
  - Contrast drops >20%
  - Noise increases >15%
- Log rollback reason in transform history

**Output:**
- `transform_history`: List of corrections applied, skipped, or rolled back
- Each entry includes: action, timestamp, parameters, skipped (bool), skip_reason

#### FR-3.9: Binarization Quality Assessment (RESTORED)

The system SHALL assess binarization quality to detect poor text/background separation.

**Detection Methods:**
- Threshold analysis (Otsu, Sauvola, Niblack)
- Bimodal histogram validation
- Local variance analysis

**Output:**
- `binarization_quality_score`: float (0-1)
- `binarization_issues`: List[str] (e.g., ["poor_separation", "uneven_threshold"])

**Routing Impact:**
- Low binarization quality (<0.6) → Apply adaptive binarization correction (FR-6.6)

**Document Types:**
- Historical manuscripts
- Faded documents
- Photocopies
- Low-quality scans

**Rationale:**
- Poor binarization causes complete OCR failure
- Critical for degraded documents
- Early detection enables targeted correction

#### FR-3.10: Illumination Uniformity Detection

**ALREADY COVERED (implied in classical/ML IQA)**

Expand with explicit requirements:

**Detection Methods:**
- Local variance analysis across image regions
- Shadow detection algorithms
- Histogram analysis per quadrant

**Output:**
- `illumination_uniformity_score`: float (0-1)
- `illumination_issues`: List[str] (e.g., ["shadow_top_left", "gradient_across_page"])

**Routing Impact:**
- Low uniformity (<0.6) → Apply illumination normalization (FR-6.7)

#### FR-3.11: Bleed-Through Detection (RESTORED)

The system SHALL detect bleed-through (ink from opposite side of page visible).

**Detection Methods:**
- Dual-side image comparison (if available)
- Frequency domain analysis (single-side fallback)
- Color channel separation

**Output:**
- `bleed_through_severity`: float (0-1)
- `bleed_through_regions`: List[BoundingBox] (COCO format)

**Routing Impact:**
- High bleed-through (>0.4) → Apply suppression correction (FR-6.10)

**Document Types:**
- Historical manuscripts
- Thin paper documents
- Double-sided printing with heavy ink

**Rationale:**
- Bleed-through confuses OCR (treats reverse-side text as noise or false characters)
- Critical for historical document processing

#### FR-3.12: Warping/Curvature Detection

The system SHALL detect document warping and curvature (e.g., book spine curvature).

**Detection Methods:**
- Line straightness analysis
- Curve fitting algorithms
- Hough transform for curved lines

**Output:**
- `warping_severity`: float (0-1)
- `warping_type`: Optional[Literal["horizontal_curve", "vertical_curve", "corner_lift"]]

**Routing Impact:**
- Warping severity >0.4 → Apply dewarping correction (FR-6.8)

#### FR-3.13: Perspective Distortion Detection

The system SHALL detect perspective distortion (trapezoidal shape from camera angle).

**Detection Methods:**
- Corner detection
- Parallel line analysis (should be parallel but aren't)
- Homography estimation

**Output:**
- `perspective_distortion_score`: float (0-1)
- `perspective_corners`: Optional[List[Point]] (detected document corners)

**Routing Impact:**
- Perspective distortion >0.3 → Apply perspective correction (FR-6.9)

#### FR-3.14: Hybrid IQA on Embedded Images (RESTORED)

For documents containing layout elements (detected via FR-4.2), the system SHALL perform per-element quality assessment.

**Workflow:**
1. Layout detection (FR-4.2) identifies bounding boxes for all 11 DocLayNet classes
2. For each **Picture**, **Figure**, **Table**, and **Formula** element:
   - Crop region using bounding box
   - Run classical IQA (FR-3.1 through FR-3.13) on cropped region
   - Run ML IQA (student model, teacher if flagged) on cropped region
   - Store quality scores in `quality_issues` field of `DocumentElement`
3. Flag elements needing correction based on thresholds

**Output:**
- Add `quality_issues: List[DetectedIssue]` to each Picture/Figure/Table/Formula element
- Add `needs_correction: bool` flag
- Add `element_quality_score: float` (aggregate quality for this element)

**Example Output:**
```json
{
  "id": "picture_001",
  "category": "picture",
  "bbox": [100, 200, 300, 400],
  "confidence": 0.92,
  "quality_issues": [
    {
      "issue_type": "blur",
      "severity": "medium",
      "confidence": 0.87,
      "score": 0.42
    }
  ],
  "needs_correction": true,
  "element_quality_score": 0.58
}
```

**Rationale:**
- Technical documents contain embedded images (figures, charts, diagrams) with independent quality characteristics
- Per-element assessment enables targeted corrections without affecting high-quality regions
- Critical for academic papers, technical manuals, scientific literature

**Document Types:**
- Academic papers with figures
- Technical manuals with diagrams
- Reports with embedded charts
- Textbooks with illustrations

---

### FR-4: Layout Analysis

#### FR-4.1: Layout Detection Model (YOLOv10-doc)

The system SHALL use **YOLOv10-doc** for layout detection.

**Model Specifications:**
- Architecture: YOLOv10 (latest YOLO architecture)
- Training: Specifically trained on DocLayNet dataset
- Classes: All 11 DocLayNet classes (see FR-4.2)
- Format: ONNX for production inference

**Rationale for YOLOv10-doc (vs YOLOv8):**
- YOLOv10-doc specifically trained on DocLayNet (higher accuracy out-of-box)
- Better architecture than YOLOv8 (improved speed/accuracy tradeoff)
- Native support for document layout characteristics

**Project A Usage (Light Layout):**
- Detect all 11 classes, output bounding boxes
- Aggregate to coarse categories for DQS calculation
- Provide per-element bounding boxes for hybrid IQA (FR-3.14)
- Calculate structural complexity score
- **Do NOT perform:**
  - Semantic relationships (caption→figure linking)
  - Reading order prediction
  - Element hierarchy construction

**Project B Usage (Full Layout):**
- Use same YOLOv10-doc detections from Project A
- Add semantic relationships
- Predict reading order
- Link footnotes, captions, etc.

**Configuration:**
- `layout_model_path`: Path to YOLOv10-doc ONNX model
- `layout_confidence_threshold`: Default 0.5 (minimum confidence for detection)
- `layout_nms_threshold`: Default 0.4 (non-maximum suppression)

#### FR-4.2: Layout Element Detection (11 DocLayNet Classes - RESTORED)

The system SHALL detect and provide bounding boxes for ALL 11 DocLayNet classes:

1. **Caption** - Descriptive text for figures/tables
2. **Footnote** - Notes at page bottom
3. **Formula** - Mathematical equations
4. **List-Item** - Bulleted/numbered list items
5. **Page-Footer** - Repeating footer content
6. **Page-Header** - Repeating header content
7. **Picture** - Figures, charts, diagrams, photos
8. **Section-Header** - Section titles
9. **Table** - Structured data in rows/columns
10. **Text** - Main body paragraphs
11. **Title** - Document title

**Output Per Element:**
- `id`: str (unique identifier, e.g., "picture_001")
- `category`: str (one of 11 DocLayNet classes)
- `bbox`: List[float] (COCO format: [x, y, width, height])
- `confidence`: float (0-1, YOLOv10-doc detection confidence)
- `page_number`: int

**Additional Metadata (Project A Light Layout):**
- `quality_issues`: List[DetectedIssue] (from hybrid IQA, FR-3.14)
- `needs_correction`: bool
- `element_quality_score`: Optional[float]

**Aggregation for DQS:**
- Count of each element type (e.g., `num_tables: 3`, `num_formulas: 12`)
- Presence flags (e.g., `has_headers: true`, `has_footers: true`)
- Structural complexity contribution

**Project A Scope Boundary:**
- ✅ Detect all 11 classes
- ✅ Provide bounding boxes
- ✅ Assess per-element quality (hybrid IQA)
- ✅ Calculate complexity scores
- ❌ Do NOT link captions to figures (Project B)
- ❌ Do NOT link footnotes to references (Project B)
- ❌ Do NOT predict reading order (Project B)
- ❌ Do NOT extract table structure (Project B)

#### FR-4.3: Bounding Box Format (COCO) (RESTORED)

**CRITICAL:** Bounding boxes SHALL use **COCO format**: `[x, y, width, height]`

**Where:**
- `x`: X-coordinate of top-left corner (pixels from left edge)
- `y`: Y-coordinate of top-left corner (pixels from top edge)
- `width`: Width of bounding box (pixels)
- `height`: Height of bounding box (pixels)

**Rationale:**
- Industry-standard COCO format
- LayoutParser compatibility
- Consistent with DocLayNet dataset format
- Avoids `[x1, y1, x2, y2]` confusion

**Example:**
```json
{
  "id": "table_001",
  "category": "table",
  "bbox": [120, 340, 450, 200],
  "confidence": 0.94,
  "page_number": 3
}
```

**Validation:**
- All bounding boxes MUST fit within page dimensions
- Width and height MUST be positive
- Coordinates MUST be non-negative

#### FR-4.4: Parasitic Content Detection

The system SHALL detect parasitic content (headers, footers, watermarks) that should NOT be included in RAG chunks.

**Detection:**
- Use Page-Header and Page-Footer classes from FR-4.2
- Pattern matching across pages (repeated content)
- Spatial analysis (consistently at page top/bottom)

**Output:**
- Mark regions as `parasitic: true` in JSON
- Add `parasitic_content_ratio`: float (proportion of page that is parasitic)

**Project A Responsibility:**
- Detect and flag parasitic regions
- Calculate parasitic content ratio for DQS

**Project B/C Responsibility:**
- Filter parasitic content from OCR output
- Exclude from RAG chunks

#### FR-4.5: Footnote Detection

**Project A Responsibility:**
- Detect Footnote class regions via layout detection (FR-4.2)
- Provide bounding boxes (COCO format)
- Spatial metadata (position at page bottom, estimated count)

**Project B Responsibility:**
- Link footnote reference markers (e.g., superscript numbers) to footnote text
- OCR text extraction from footnote regions
- Semantic association for proper document structure

**Output (Project A):**
```json
{
  "id": "footnote_001",
  "category": "footnote",
  "bbox": [50, 1100, 500, 80],
  "confidence": 0.91,
  "spatial_hints": {
    "position": "page_bottom",
    "estimated_count": 3
  }
}
```

#### FR-4.6: Figure-Caption Detection

**Project A Responsibility:**
- Detect Caption class regions via layout detection (FR-4.2)
- Detect Picture class regions via layout detection (FR-4.2)
- Calculate spatial proximity (nearest Picture to each Caption)
- Provide proximity hints

**Project B Responsibility:**
- OCR text from Caption regions
- Pattern matching (e.g., "Figure 3:", "Fig. 2a")
- Semantic linking (associate Caption with correct Picture)

**Output (Project A):**
```json
{
  "id": "caption_001",
  "category": "caption",
  "bbox": [100, 560, 400, 40],
  "confidence": 0.92,
  "spatial_hints": {
    "nearest_picture": "picture_001",
    "proximity": "below",
    "distance_pixels": 12
  }
}
```

#### FR-4.7: Vertical Text Orientation Detection (RESTORED)

The system SHALL detect vertical text orientation.

**Detection Methods:**
- Text orientation analysis (0°, 90°, 180°, 270°)
- Asian vertical script detection (Chinese, Japanese, Korean)
- Rotated labels in diagrams

**Output:**
- `text_orientation`: Literal[0, 90, 180, 270] (degrees)
- `script_type`: Optional[Literal["horizontal_latin", "vertical_asian", "rotated_label"]]

**Project A Responsibility:**
- Detect orientation, flag in metadata

**Project B Responsibility:**
- Rotate text regions to 0° before OCR
- Use language-specific OCR for Asian vertical scripts

**Document Types:**
- Asian language documents (vertical writing)
- Technical diagrams (rotated labels)
- Mobile captures (rotated images)
- Posters and infographics

#### FR-4.8: Handwriting Detection

The system SHALL detect handwritten text regions.

**Method:**
- Classify each page as `handwriting_present: bool`
- Optionally classify proportion (small/medium/high)

**Project A Responsibility:**
- Detect handwriting presence (page-level or region-level if computationally feasible)

**Project B Responsibility:**
- Route handwritten regions to specialized handwriting OCR (Microsoft Azure Read API, Google Cloud Vision)

**Accuracy Target:**
- F1-score ≥ 0.95 on validation set

#### FR-4.11: Table Quality Assessment (RESTORED)

**Project A Responsibility (Quality Assessment):**
- Apply IQA detectors (FR-3.1 through FR-3.14) to table regions
- Assess table-specific quality:
  - Border presence (helps with cell detection)
  - Cell alignment quality
  - Contrast (text vs background)
- Estimate structural complexity (heuristics for row/column count)

**Output (Project A):**
```json
{
  "id": "table_001",
  "category": "table",
  "bbox": [120, 340, 450, 200],
  "confidence": 0.94,
  "quality_assessment": {
    "blur_score": 0.87,
    "contrast_score": 0.65,
    "has_borders": true,
    "needs_correction": false
  },
  "complexity_indicators": {
    "estimated_rows": 8,
    "estimated_columns": 5,
    "complexity_score": 0.62
  }
}
```

**Project B Responsibility (Structure Extraction):**
- Extract row/column structure using PubTables-1M model
- Parse cell contents with OCR
- Generate table-to-JSON representation
- Use quality scores from Project A for correction decisions

#### FR-4.12: Layout Spatial Hints for Reading Order (RESTORED)

**Project A Responsibility (Spatial Hints):**
- Detect multi-column layouts (2-3 column detection)
- Assign column membership to text blocks
- Calculate vertical position (top/middle/bottom)
- Identify spatial proximity between elements

**Output (Project A):**
```json
{
  "id": "text_001",
  "category": "text",
  "bbox": [50, 100, 200, 400],
  "confidence": 0.95,
  "spatial_hints": {
    "column_index": 0,
    "vertical_position": "top",
    "is_multi_column": true,
    "num_columns": 2
  }
}
```

**Project B Responsibility (Reading Order Prediction):**
- Use spatial hints from Project A
- Predict sequential reading order (critical for RAG)
- Handle complex layouts (sidebars, callout boxes, footnotes)
- Multi-column reading order (top-to-bottom per column, then next column)

**Rationale:**
- Spatial hints are layout-based (Project A strength)
- Reading order prediction requires semantic understanding (Project B strength)
- Reading order is critical for RAG (5-29% performance impact per OHR-Bench)

---

### FR-5: Specialized Content Detection

**Philosophy:** Project A detects specialized content and provides metadata. Project B handles specialized processing/extraction.

#### FR-5.1: Mathematical Content (Formula Detection) (RESTORED)

**Project A Responsibility:**
- Detect Formula class via layout detection (FR-4.2)
- Provide bounding boxes (COCO format)
- Assess formula quality via hybrid IQA (FR-3.14)

**Project B Responsibility:**
- Route formula regions to specialized math OCR (Nougat, pix2tex, MathPix)
- Extract LaTeX representation

**Output (Project A):**
```json
{
  "id": "formula_003",
  "category": "formula",
  "bbox": [200, 450, 350, 60],
  "confidence": 0.89,
  "quality_issues": []
}
```

**Document Types:**
- STEM textbooks
- Academic papers
- Technical specifications
- Scientific literature

#### FR-5.2: Handwritten Content

**ALREADY COVERED IN FR-4.8**

#### FR-5.3: Language Detection

The system SHALL perform language detection.

**Method:**
- Library-based detection (fasttext, langdetect, or py3langid)
- Detect primary language(s)
- Flag non-Latin scripts explicitly

**Output:**
- `languages`: List[str] (e.g., `["en", "fr"]`)
- `has_non_latin`: bool (e.g., Arabic, Chinese, Japanese)
- `script_types`: List[str] (e.g., `["latin", "arabic", "han"]`)

**Project A Responsibility:**
- Detect languages, provide hints

**Project B Responsibility:**
- Use language hints for OCR language pack selection
- Handle multi-script documents appropriately

#### FR-5.4: Watermark Detection (RESTORED)

**Project A Responsibility:**
- Detect watermarks via frequency domain analysis
- Pattern recognition (text vs image watermarks)
- Transparency/opacity analysis
- Provide bounding boxes

**Output:**
```json
{
  "watermark_detected": true,
  "watermark_type": "text",
  "watermark_regions": [
    {"bbox": [300, 500, 200, 50], "confidence": 0.82}
  ]
}
```

**Project B Responsibility:**
- Flag watermark regions in OCR output
- May require VLM for semantic interpretation of watermark content

**Project C Responsibility:**
- Filter watermark text from RAG chunks (avoid noise)

**Document Types:**
- Legal documents
- Contracts
- Official certificates
- Business reports

#### FR-5.5: Stamp/Seal Detection (RESTORED)

**Project A Responsibility:**
- Detect stamps/seals via:
  - Circle detection (Hough transform for circular seals)
  - Color analysis (stamps typically red, blue, or black ink)
  - Texture analysis
- Provide bounding boxes

**Output:**
```json
{
  "stamp_detected": true,
  "stamp_regions": [
    {"bbox": [400, 800, 100, 100], "confidence": 0.91, "shape": "circular"}
  ]
}
```

**Project B Responsibility:**
- Preserve stamp metadata (important for legal documents)
- May require VLM for stamp content interpretation

**Document Types:**
- Government documents
- Contracts
- Notarized documents
- International shipping documents

#### FR-5.6: Signature Detection (RESTORED)

**Project A Responsibility:**
- Detect signatures via:
  - Continuous stroke detection
  - Ink analysis (pen pressure patterns)
  - Spatial analysis (signatures typically at document bottom)
- Provide bounding boxes

**Output:**
```json
{
  "signature_detected": true,
  "signature_regions": [
    {"bbox": [100, 1050, 200, 50], "confidence": 0.87}
  ]
}
```

**Project B Responsibility:**
- Handle per compliance requirements:
  - Redact for privacy (if required)
  - Preserve for legal validation (if required)
- Separate from main text OCR

**Document Types:**
- Contracts
- Forms
- Legal documents
- Invoices and receipts

#### FR-5.7: Margin Annotation Detection (RESTORED)

**Project A Responsibility:**
- Detect margin annotations via:
  - Edge detection (notes typically in margins)
  - Spatial isolation (not part of main text flow)
  - Handwriting detection (typically handwritten vs printed main text)
- Provide bounding boxes

**Output:**
```json
{
  "margin_annotations": true,
  "annotation_regions": [
    {"bbox": [10, 200, 40, 300], "confidence": 0.78, "position": "left_margin"}
  ]
}
```

**Project B Responsibility:**
- Separate from main text
- Preserve for scholarly/historical analysis
- May require specialized handwriting OCR

**Document Types:**
- Historical manuscripts
- Academic papers (peer review annotations)
- Annotated drafts
- Student assignments

---

### FR-6: Correction Methods

**All corrections SHALL implement do-no-harm guardrails (FR-3.8).**

#### FR-6.1: Blur Correction

**Method:**
- Unsharp mask
- Deconvolution (Wiener filter)

**Guardrails:**
- Only apply if `blur_score < threshold` (default 0.6)
- Post-correction quality validation
- Rollback if blur increases

#### FR-6.2: Skew Correction

**Method:**
- Affine rotation transform

**Guardrails:**
- See FR-3.2 (detailed guardrails already specified)

#### FR-6.3: Noise Reduction

**Method:**
- Bilateral filter
- Non-Local Means (NLM)
- BM3D (advanced, if computationally feasible)

**Guardrails:**
- Only apply if `noise_score > threshold` (default 0.4)
- Preserve text sharpness during denoising

#### FR-6.4: Contrast Enhancement

**Method:**
- CLAHE (Contrast Limited Adaptive Histogram Equalization)
- Histogram equalization

**Guardrails:**
- Only apply if `contrast_score < threshold` (default 0.5)
- CLAHE clip limit adaptive (1.0-4.0 based on severity)

#### FR-6.5: DPI Upscaling

**ALREADY COVERED IN FR-A2 and FR-3.4-3.6**

#### FR-6.6: Binarization Correction (RESTORED)

The system SHALL apply adaptive binarization to improve text/background separation.

**Method:**
- Otsu thresholding (global)
- Sauvola thresholding (local adaptive)
- Niblack thresholding (local adaptive)

**Guardrails:**
- Only apply if `binarization_quality_score < 0.6` (from FR-3.9)
- Compare before/after via OCR confidence (if available) or edge density
- Only apply if improvement >10%
- Rollback if quality degrades

**Priority:** P0 (Critical for degraded documents)

**Document Types:**
- Historical manuscripts
- Faded documents
- Photocopies
- Low-quality scans

#### FR-6.7: Illumination Normalization

The system SHALL normalize uneven illumination.

**Method:**
- Illumination estimation (Gaussian smoothing)
- Adaptive histogram equalization per region
- Shadow removal algorithms

**Guardrails:**
- Only apply if `illumination_uniformity_score < 0.6` (from FR-3.10)
- Preserve original if normalization creates artifacts
- Post-correction quality validation

#### FR-6.8: Dewarping (RESTORED)

The system SHALL correct document warping and curvature.

**Method:**
- Polynomial regression (classical, faster)
- DocUNet (deep learning, higher quality)

**Guardrails:**
- Only apply if `warping_severity > 0.4` (from FR-3.12)
- Validate grid straightness after dewarping
- Rollback if correction introduces distortion

**Priority:** P1 (High for book scans)

**Document Types:**
- Book scans (spine curvature)
- Bound documents
- Mobile captures at angles

#### FR-6.9: Perspective Correction

The system SHALL correct perspective distortion.

**Method:**
- Corner detection (document boundaries)
- Homography matrix estimation
- Perspective transform (warp to rectangle)

**Guardrails:**
- Only apply if `perspective_distortion_score > 0.3` (from FR-3.13)
- Validate corner detection accuracy
- Preserve original if correction fails

#### FR-6.10: Bleed-Through Suppression (RESTORED)

The system SHALL suppress bleed-through artifacts.

**Method:**
- Frequency domain filtering
- Dual-side image subtraction (if both sides available)
- Color channel separation

**Guardrails:**
- Only apply if `bleed_through_severity > 0.4` (from FR-3.11)
- Preserve legibility of foreground text
- Rollback if suppression reduces foreground contrast

**Priority:** P1 (High for historical documents)

**Document Types:**
- Historical manuscripts
- Thin paper documents
- Double-sided printing with heavy ink

---

### FR-7: Document Quality Score (DQS)

**ALREADY COVERED IN ORIGINAL (FR-A9 implied)**

Expand with explicit requirements:

#### FR-7.1: DQS Calculation (Two-Axis)

The system SHALL calculate a Document Quality Score with two orthogonal axes:

**Axis 1: Degradation Score (0-1)**
- Measures physical image quality degradation
- Components: blur, noise, contrast, skew, resolution, illumination, binarization, bleed-through
- Calculation: Weighted average of all quality metrics
- Scale: 0.0 = severe degradation, 1.0 = pristine quality

**Axis 2: Structural Complexity Score (0-1)**
- Measures layout and content complexity
- Components: multi-column, tables, formulas, figures, mixed scripts, handwriting, element count
- Calculation: Complexity heuristics from layout detection
- Scale: 0.0 = simple single-column, 1.0 = highly complex layout

**Output:**
```json
{
  "quality_score": {
    "degradation_score": 0.82,
    "structural_complexity_score": 0.45,
    "overall_score": 0.685,
    "components": {
      "blur": 0.87,
      "noise": 0.91,
      "contrast": 0.78,
      ...
    }
  }
}
```

#### FR-7.2: Pipeline Routing Recommendation

The system SHALL provide routing recommendations based on DQS.

**Routing Matrix:**
```
                    LOW COMPLEXITY          HIGH COMPLEXITY
                    ─────────────────────────────────────────
HIGH DEGRADATION │  vision_simple       │  vision_structured   │
(Blurry, Noisy)  │  (VLM + Simple)      │  (VLM + Structure)   │
                 │                       │                      │
─────────────────┼──────────────────────┼──────────────────────┤
                 │                       │                      │
LOW DEGRADATION  │  ocr_fast            │  ocr_advanced        │
(Clean, Sharp)   │  (Tesseract)         │  (Nougat/Marker)     │
                 │                       │                      │
                 └───────────────────────┴──────────────────────┘
```

**Thresholds:**
- High degradation: degradation_score < 0.7
- Low degradation: degradation_score ≥ 0.7
- High complexity: structural_complexity_score > 0.5
- Low complexity: structural_complexity_score ≤ 0.5

**Output:**
```json
{
  "routing_recommendation": {
    "strategy": "ocr_advanced",
    "confidence": 0.89,
    "rationale": "Clean document with complex layout (tables, formulas). Use advanced OCR with structure preservation."
  }
}
```

---

## 3. Non-Functional Requirements (NFR)

### NFR-1: Performance (DETAILED RESTORATION)

#### NFR-1.1: Hardware Configuration

**GPU Mode (Recommended for Production):**
- Hardware: NVIDIA T4 or better (16GB VRAM)
- CUDA: Version 11.8+
- Use for: ML models (ResNet teacher/student), YOLOv10-doc layout detection

**CPU Mode (Development/Testing):**
- Hardware: Intel Xeon or AMD EPYC (8+ cores recommended)
- RAM: 16GB+ recommended
- Use for: Classical CV methods, validation, development

**Modal GPU (Fallback/Burst):**
- On-demand GPU access via Modal
- Use for: Teacher model when local GPU unavailable, burst capacity

#### NFR-1.2: Performance Targets (GPU Mode)

**Latency:**
- **Target:** < 150ms per page (full pipeline)
- **Acceptable:** < 400ms per page
- **Breakdown:**
  - Rendering: < 20ms
  - Classical IQA: < 15ms
  - ML IQA (student): < 10ms
  - Layout detection (YOLOv10-doc): < 25ms (evaluate via benchmark)
  - Corrections: < 50ms (if applied)
  - DQS calculation: < 10ms

**Throughput:**
- **Target:** > 6 pages/sec per worker
- **Acceptable:** > 2 pages/sec per worker

**Batch Processing:**
- **Target:** 100 docs (5 pages each) in < 90 seconds
- Calculation: 500 pages / 90 sec = 5.56 pages/sec

#### NFR-1.3: Performance Targets (CPU Mode)

**Latency:**
- **Target:** < 400ms per page
- **Acceptable:** < 1000ms per page
- **Breakdown:**
  - Classical IQA: < 50ms
  - ML IQA (student): < 40ms (target), < 100ms (acceptable)
  - Layout detection: < 150ms (evaluate via benchmark)
  - Corrections: < 100ms

**Throughput:**
- **Target:** > 2 pages/sec per worker
- **Acceptable:** > 0.5 pages/sec per worker

#### NFR-1.4: Resource Constraints

**GPU Memory:** < 2GB per worker

**CPU Cores:** 2-4 per worker

**RAM:** < 4GB per worker

**Disk:** Temporary file processing only (no persistent storage)

### NFR-2: Accuracy & Reliability (DETAILED RESTORATION)

#### NFR-2.1: PDF Type Classification Accuracy

PDF type classification (FR-2.1) SHALL be **99.9% accurate** on validation set.

**Validation:** Compare against manual ground-truth labels for 1000+ PDFs.

#### NFR-2.2: Skew Detection Accuracy

Skew angle detection (FR-3.2) SHALL be accurate to within **±0.5 degrees**.

**Validation:** Compare against manually measured angles on 500+ images.

#### NFR-2.3: Layout Model Accuracy (YOLOv10-doc)

Layout detection (FR-4.1, 4.2) SHALL achieve:

**Primary Metric:**
- **mAP@.50** (COCO metric): > 0.82 (target), > 0.75 (acceptable)

**Secondary Metrics:**
- **mAP@.50-.95**: > 0.70
- **Per-class AP**: > 0.70 for all 11 classes (ensure rare class performance)

**Validation Dataset:** DocLayNet validation set (6,480 pages)

#### NFR-2.4: Handwriting Classification Accuracy

Handwriting vs printed classification (FR-4.8) SHALL achieve **F1-score ≥ 0.95**.

**Validation:** Balanced test set with 1000+ samples per class.

#### NFR-2.5: ML IQA Model Accuracy

Student and teacher ML IQA models (FR-2.3, FR-A4) SHALL achieve:

**Primary Metric:**
- **mAP** (multi-label classification): > 0.88 on OHR-Bench document IQA validation

**Secondary Metrics:**
- **Per-head correlation** (Pearson/Spearman with ground truth):
  - Blur: r > 0.85
  - Noise: r > 0.80
  - Contrast: r > 0.82
  - Skew: r > 0.90

**Calibration:**
- **Expected Calibration Error (ECE)**: < 0.1

**Validation Dataset:** OHR-Bench (document-specific IQA) or DIQA-5000 (when released)

#### NFR-2.6: Error Handling & Reliability

The system SHALL log all processing errors (per FR-1.4) without crashing.

**Requirements:**
- Must return valid error-state JSON
- Error messages must be user-friendly
- Stack traces logged for debugging (not exposed to user)
- Graceful degradation: Partial results if possible

**Batch Mode:**
- Continue processing remaining files after error
- Collect all errors, report at end
- Partial success: Results for successful files, errors for failed files

#### NFR-2.7: Correction Quality (Do-No-Harm Validation)

All corrections (FR-6.x) SHALL achieve **zero quality degradation** on validation set.

**Validation Metrics:**
- Proportion of corrections that improve quality: > 95%
- Proportion of corrections that degrade quality: < 1%
- Proportion of corrections properly rolled back: 100% (when degradation detected)

**Validation Dataset:** 328+ images with diverse quality issues (Phase 1 validation set + additions)

### NFR-3: Configurability (DETAILED RESTORATION)

#### NFR-3.1: Threshold Externalization

ALL detection and correction thresholds SHALL be externalized into configuration (not hard-coded).

**Configuration File:** `.env` or `config.yaml` or Pydantic Settings class

**Examples:**
- `blur_threshold`: float (default 0.6)
- `skew_angle_threshold`: float (default 2.0 degrees)
- `contrast_threshold`: float (default 0.5)
- `binarization_quality_threshold`: float (default 0.6)
- `dqs_degradation_threshold`: float (default 0.7)
- `dqs_complexity_threshold`: float (default 0.5)
- `target_dpi`: int (default 300)
- `pdf_upscale_algorithm`: Literal["lanczos", "bicubic", ...] (default "lanczos")

**Implementation:** `src/image_preprocessing_detector/core/config.py`

#### NFR-3.2: Model Swapping

ALL model file paths SHALL be configurable (allow model updates without code deployment).

**Configuration:**
```python
layout_model_path: Path = Field(
    default=Path("models/yolov10_doc_doclaynet.onnx"),
    description="Path to YOLOv10-doc ONNX model"
)
teacher_model_path: Path = Field(
    default=Path("models/resnet50_iqa_teacher.onnx"),
    description="Path to ResNet-50 teacher ONNX model"
)
student_model_path: Path = Field(
    default=Path("models/resnet18_iqa_student.onnx"),
    description="Path to ResNet-18 student ONNX model"
)
```

### NFR-4: Deployment & Operations (DETAILED RESTORATION)

#### NFR-4.1: Containerization

The system SHALL be delivered as a containerized application.

**Requirements:**
- **Dockerfile** for building image
- **Pre-built image** on container registry (Docker Hub, GCR, or ECR)
- **Docker Compose** for local development
- **Base Image:** Python 3.12 slim or distroless (security)

**Dependencies:**
- All dependencies specified in `pyproject.toml`
- Reproducible builds (lock file: `poetry.lock`)

**Image Size:**
- Target: < 2GB (compressed)
- Acceptable: < 5GB

#### NFR-4.2: Logging (Structured + Human-Readable)

The system SHALL generate **structured, human-readable logs** for all major processing steps.

**Log Events:**
- `file_received` (file_path, size, format)
- `analysis_started` (page_number)
- `classical_iqa_complete` (blur_score, noise_score, etc.)
- `ml_iqa_complete` (student_scores, teacher_used, device)
- `layout_detection_complete` (num_elements, classes_detected)
- `correction_applied` (correction_type, parameters, success)
- `correction_rolled_back` (correction_type, reason)
- `analysis_complete` (dqs, routing_recommendation)
- `error_occurred` (error_type, message, stack_trace)

**Format:**
- Structured: JSON-formatted logs using `structlog`
- Human-readable: `rich` console output with color/formatting

**Output:**
- All logs written to stdout/stderr
- Log level configurable (DEBUG, INFO, WARNING, ERROR)

**Implementation:** `src/image_preprocessing_detector/utils/logging.py`

#### NFR-4.3: Statelessness

The application SHALL be **stateless**:
- No reliance on local disk (except temporary file processing)
- No in-memory session data between requests
- Each request is independent

**Rationale:**
- Enables horizontal scaling
- Kubernetes/Docker Swarm deployment-ready
- Fault tolerance (worker failures don't affect other requests)

#### NFR-4.4: Monitoring & Observability

The system SHALL support monitoring and observability.

**Metrics Export:**
- Prometheus-compatible metrics endpoint
- Metrics: latency (p50, p95, p99), throughput, error rate, device usage, teacher usage

**Tracing:**
- OpenTelemetry instrumentation (optional)
- Distributed tracing for multi-service deployments

**Health Checks:**
- `/health` endpoint (liveness probe)
- `/ready` endpoint (readiness probe)

### NFR-5: Security (DETAILED RESTORATION)

#### NFR-5.1: Input Validation

All file inputs SHALL be validated:

**File Size Limits:**
- Default: 100MB per file (configurable)
- Configurable per document type

**Page Count Limits:**
- Default: 1000 pages per PDF (configurable)

**File Format Verification:**
- Magic bytes validation (not just file extension)
- Reject files with mismatched magic bytes and extension

**Path Traversal Prevention:**
- No `../` in file paths
- Resolve to absolute paths, validate within allowed directories

**Configuration:**
```python
max_file_size_mb: int = 100
max_pages_per_pdf: int = 1000
allowed_input_directories: List[Path] = []
```

#### NFR-5.2: Dependency Scanning

All dependencies SHALL be scanned for vulnerabilities:

**Tools:**
- **Bandit**: Python security analysis (source code)
- **Safety**: Dependency vulnerability check (PyPI packages)
- **OSV-Scanner**: OpenSSF vulnerability database

**CI/CD:**
- Scans run automatically on every PR
- Weekly scheduled scans
- Fail build on HIGH/CRITICAL vulnerabilities

**Exception Handling:**
- False positives documented in `osv-scanner.toml`
- Approved exceptions require security team review

**Implementation:** `.github/workflows/security-analysis.yml`

#### NFR-5.3: Secrets Management

No secrets or API keys SHALL be hard-coded:

**Requirements:**
- All secrets in environment variables
- `.env.example` provided (no actual secrets)
- `.env` encrypted with GPG for local development (never committed)

**Secrets:**
- Modal API keys (if used)
- Model registry credentials (if used)
- Cloud storage credentials (if used)

**Kubernetes/Production:**
- Use Kubernetes Secrets or cloud secret managers (AWS Secrets Manager, GCP Secret Manager)

#### NFR-5.4: Least Privilege

The application SHALL run with least privilege:

**File System:**
- Read-only access to model files
- Write access only to temporary directories (configurable)
- No write access to system directories

**Network:**
- Outbound connections only to approved endpoints (Modal, model registry)
- No inbound connections (unless API mode)

**User:**
- Container runs as non-root user (UID 1000 or configurable)

---

## 4. Technology Stack Summary

**Language:** Python 3.12+

**Core Libraries:**
- PyMuPDF (PDF rendering)
- Pillow (image I/O)
- OpenCV 4.8+ (classical IQA, corrections)
- PyTorch 2.0+ (model training)
- ONNX Runtime (production inference)
- YOLOv10-doc (layout detection)

**Office Document Processing:**
- Docling (embedded image extraction from .docx/.xlsx/.pptx)

**ML Models:**
- ResNet-50 teacher (high-capacity IQA)
- ResNet-18 student (production IQA)
- YOLOv10-doc (layout detection)

**Framework:**
- Click (CLI)
- Pydantic v2 (JSON schema, validation)
- Structlog + Rich (logging)

**Deployment:**
- Docker (containerization)
- Modal (optional GPU burst capacity)

---

## 5. Phase Roadmap (Aligned with Original)

### Phase 0: Project Setup (Weeks 0-1) - ✅ COMPLETE

### Phase 2: ResNet Teacher-Student ML IQA (Weeks 2-4) - 📋 PLANNED

### Phase 4: Classical IQA + DPI Upscaling (Weeks 5-6) - 📋 PLANNED

### Phase 6: Layout Detection (YOLOv10-doc, 11 Classes) (Weeks 6-8) - 📋 PLANNED
- **Model:** YOLOv10-doc (replaces YOLOv8)
- **Classes:** All 11 DocLayNet classes
- **Hybrid IQA:** Per-element quality assessment

### Phase 8: DQS & Routing (Week 9) - 📋 PLANNED

### Phase 10: Validation & Documentation (Week 10) - 📋 PLANNED

**NEW: Phase 1B (Completed) - DPI Upscaling**
**NEW: Phase 5 - Office Format Support** (TBD)
- Docling integration for embedded image extraction

---

## 6. Open Questions & Decisions Needed

### Q1: Text Detection Gate
- [ ] Benchmark YOLOv10-doc latency on pure images vs text documents
- [ ] Decision: Implement if >30ms savings, skip if <15ms savings
- [ ] Document decision with benchmark results

### Q2: Office Document Processing (Docling Integration)
- [ ] Confirm Docling integration scope for Project A (image extraction only)
- [ ] Confirm Docling integration scope for Project B (text extraction)
- [ ] Document handoff interface between Project A and Project B for office documents

### Q3: YOLOv10-doc Model Availability
- [ ] Confirm YOLOv10-doc pre-trained model availability
- [ ] Evaluate need for fine-tuning on project-specific data
- [ ] Document model provenance and licensing

---

**End of Requirements v2.0**
