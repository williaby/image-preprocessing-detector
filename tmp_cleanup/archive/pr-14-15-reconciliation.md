<!-- markdownlint-disable MD013 -->
<!--
SPDX-FileCopyrightText: 2024 Byron Williams <byronawilliams@gmail.com>
SPDX-License-Identifier: MIT
-->

---
schema_type: common
title: "PR 14-15 Reconciliation Document"
description: "Analysis and recommendations for integrating PRs 14-15 into current project architecture"
tags: [planning, reconciliation, documentation, pr_review]
status: draft
owner: "docs-team"
review_cycle_days: 30
authors:

- name: "Claude Code"
purpose: "Provide clear guidance on what content from PRs 14-15 should be kept, discarded, or updated to align with current PROJECT_PLAN and ADRs."

---

> **Generated**: 2025-11-11
> **PRs Analyzed**: #14 (williaby-patch-1), #15 (williaby-patch-2)
> **Status**: RECONCILIATION REQUIRED - DO NOT MERGE AS-IS

---

## Executive Summary

PRs 14-15 contain four strategic planning documents that predate several critical architectural decisions:

**Documents:**

1. `docs/functional_requirements.md` - Detailed FR/NFR specifications
2. `docs/project_mandate.md` - Business justification and strategic context
3. `docs/technical_nethodology.md` - Implementation methodology
4. `docs/image_preprocessing.doc` - Academic research report

**Assessment:** These documents contain **valuable strategic context** but have **significant technical discrepancies** with current implementation (Phase 1B, ADRs 0007-0021, text detection gate).

**Recommendation:**

- ❌ **DO NOT merge PRs 14-15 as-is**
- ✅ **Extract and integrate valuable content** using this reconciliation guide
- ✅ **Create updated versions** aligned with current architecture

---

## 🟢 CONTENT TO KEEP (High Value)

### 1. Strategic Business Context (project_mandate.md)

**Keep Entire Document** - This provides excellent strategic justification missing from PROJECT_PLAN.

**Value:**

- Articulates the "garbage in, garbage out" problem clearly
- Documents the OCR-based vs. Vision-based pipeline trade-off
- Explains why intelligent preprocessing/routing is necessary
- Provides business case for the project

**Integration Target:**

- Add to PROJECT_PLAN Executive Summary (lines 9-16)
- Create new section: "Strategic Context and Business Justification"
- Reference in README.md to explain project purpose

**Action Items:**

- [ ] Extract Section 2 ("The Core Problem") → Add to PROJECT_PLAN introduction
- [ ] Extract Section 3 ("The Central Challenge") → Add to ARCHITECTURE_SUMMARY
- [ ] Extract Section 5 ("The Strategic Outcome") → Add to PROJECT_PLAN Executive Summary
- [ ] Keep all citations and references intact

---

### 2. Academic Research Context (image_preprocessing.doc)

**Keep Sections: I (Taxonomy), II (Image Quality), Appendix (References)**

**Value:**

- Section I: Comprehensive taxonomy of document failures
- Table 1: Excellent visualization of issue → impact mapping
- Section II: Detailed CV algorithm explanations with academic rigor
- References: 50+ citations providing research foundation

**Integration Target:**

- Create `docs/research/document_quality_taxonomy.md`
- Add citations to ADRs (especially ADR-0014, ADR-0007)
- Use Table 1 as reference for DQS ADR (to be created)

**Action Items:**

- [ ] Extract Table 1 → Use in new ADR-0028 (DQS)
- [ ] Extract Section II.1-II.3 → Add to `docs/research/cv_algorithms_reference.md`
- [ ] Extract all citations → Create `docs/research/bibliography.md`
- [ ] Keep academic writing style for research documentation

---

### 3. Document Quality Score (DQS) Framework (image_preprocessing.doc Section 1.4)

**Keep Entire Concept** - This is a novel contribution not in current PROJECT_PLAN.

**Value:**

- Defines two-axis scoring: Degradation vs. Structural complexity
- Provides quantitative routing logic for pipeline selection
- Maps directly to OCR-based vs. Vision-based trade-off

**Integration Target:**

- Create new ADR-0028: Document Quality Score (DQS) Framework
- Add DQS to PROJECT_PLAN Phase 4 (Production) as a routing mechanism
- Update schema.py to include DQS in DocumentMetadata

**Action Items:**

- [ ] Create ADR-0028 documenting DQS decision (HIGH PRIORITY)
- [ ] Add DQS calculation to PROJECT_PLAN Phase 4 deliverables
- [ ] Design DQS schema fields (degradation_score, structural_score, routing_recommendation)

---

### 4. PDF Type Classification (functional_requirements.md FR-2.1)

**Keep Requirement** - This is valuable and missing from PROJECT_PLAN.

**Original Text (FR-2.1):**

```text
Classify PDFs as:
- "Image-Only": No extractable digital text (scanned)
- "Born-Digital": Extractable text, no significant images
- "Hybrid": Both extractable text and embedded images with text
```text

**Value:**

- Critical for routing decisions (OCR vs. text extraction)
- Aligns with "Visual Reconciliation" strategy in technical_methodology.md
- Mentioned in PROJECT_PLAN but not detailed

**Integration Target:**

- Add to PROJECT_PLAN Phase 1B or Phase 2
- Create implementation task for pdf_analyzer.py
- Add to DocumentMetadata schema

**Action Items:**

- [ ] Add PDF classification to PROJECT_PLAN Phase 2 (lines 920-950)
- [ ] Update schema.py with pdf_type field: Literal["image_only", "born_digital", "hybrid"]
- [ ] Create implementation task: `src/ingestion/pdf_classifier.py`

---

### 5. Language Detection Requirement (functional_requirements.md FR-5.3)

**Keep Requirement with Updates**

**Original Text (FR-5.3):**

```text
FR-5.3.1: Detect primary language(s) (e.g., ['en', 'fr'])
FR-5.3.3: Flag Non-Latin scripts (Arabic, Chinese, Japanese)
```text

**Value:**

- Important for OCR language pack selection
- Critical for multi-script documents
- PROJECT_PLAN mentions it (line 93) but lacks details

**Integration Target:**

- Add to PROJECT_PLAN Phase 2 or Phase 3
- Specify library (langdetect, fasttext, or py3langid)
- Add to DocumentMetadata schema

**Action Items:**

- [ ] Add language detection to PROJECT_PLAN Phase 2 deliverables
- [ ] Evaluate libraries: langdetect vs. fasttext vs. py3langid
- [ ] Update schema.py with languages: List[str] and has_non_latin: bool fields

---

### 6. Mathematical Content Detection (functional_requirements.md FR-5.1)

**Keep Requirement** - Aligns with PROJECT_PLAN Phase 3.

**Original Text (FR-5.1):**

```text
Identify mathematical equations by providing bounding boxes
for the Formula class (DocLayNet)
```text

**Value:**

- Already planned in PROJECT_PLAN (line 92: "Mathematical Formulas")
- Confirms DocLayNet Formula class is correct approach
- Validates current architecture

**Integration Target:**

- No changes needed to PROJECT_PLAN
- Use as validation that current plan is correct

**Action Items:**

- [ ] Cross-reference FR-5.1 with PROJECT_PLAN line 92 (already aligned)
- [ ] No action required - already in scope

---

## 🟡 CONTENT TO UPDATE (Needs Alignment)

### 7. Performance Targets (functional_requirements.md NFR-1)

**Update Required** - Current targets are 10-33x too conservative.

**Current PR Text (NFR-1.1, NFR-1.2):**

```text
NFR-1.1: 100 docs (5 pages) in <15 min = 0.56 pages/sec
NFR-1.2: Single 10-page doc in <60 sec = 6 sec/page
```text

**PROJECT_PLAN Targets (lines 547-558):**

```text
Latency (GPU): < 150ms per page (6.67 pages/sec)
Throughput: > 6 pages/sec per GPU worker
```text

**Issue:** PRs assume CPU-only; PROJECT_PLAN assumes GPU acceleration.

**Recommended Update:**

```markdown
### NFR-1: Performance

**Hardware Configuration:**
- **GPU Mode**: NVIDIA T4 or better (recommended for production)
- **CPU Mode**: Intel Xeon or equivalent (development/testing)

**Performance Targets (GPU Mode):**
- NFR-1.1: Latency: < 150ms per page (target), < 400ms (acceptable)
- NFR-1.2: Throughput: > 6 pages/sec per worker (target), > 2 pages/sec (acceptable)
- NFR-1.3: Batch Processing: 100 docs (5 pages each) in < 90 seconds

**Performance Targets (CPU Mode):**
- NFR-1.4: Latency: < 400ms per page (target), < 1000ms (acceptable)
- NFR-1.5: Throughput: > 2 pages/sec per worker (target), > 0.5 pages/sec (acceptable)
```text

**Action Items:**

- [ ] Update functional_requirements.md NFR-1 with GPU/CPU split
- [ ] Align with PROJECT_PLAN targets (150ms GPU, 400ms CPU)
- [ ] Add hardware configuration section

---

### 8. Layout Detection Classes (functional_requirements.md FR-4.2)

**Update Required** - Add handwriting detection, remove conflicts.

**Current PR Text (FR-4.2):**

```text
Detect all 11 DocLayNet classes:
Caption, Footnote, Formula, List-Item, Page-Footer,
Page-Header, Picture, Section-Header, Table, Text, Title
```text

**PROJECT_PLAN Additions (lines 87-95):**

```text
- Handwriting regions (not in DocLayNet)
- Revision Markings (Yale manuscripts, not in DocLayNet)
```text

**Recommended Update:**

```markdown
### FR-4: Layout Analysis (Per-page)

**FR-4.1:** Use YOLOv8 model fine-tuned on DocLayNet dataset.

**FR-4.2:** Detect and provide bounding boxes for the following layout classes:

**DocLayNet Classes (11):**
1. Caption - Descriptive text for figures/tables
2. Footnote - Notes at page bottom
3. Formula - Mathematical equations
4. List-Item - Bulleted/numbered list items
5. Page-Footer - Repeating footer content
6. Page-Header - Repeating header content
7. Picture - Figures, charts, diagrams
8. Section-Header - Section titles
9. Table - Structured data in rows/columns
10. Text - Main body paragraphs
11. Title - Document title

**Extended Classes (Phase 3):**
12. Handwriting - Handwritten text regions (requires separate classifier)
13. Revision-Marking - Strikethrough, insertions, margin notes (optional)

**FR-4.3:** Bounding boxes shall use COCO format: `[x, y, width, height]` (NOT `[x1, y1, x2, y2]`).
```text

**Action Items:**

- [ ] Update FR-4.2 with all classes (11 DocLayNet + 2 extended)
- [ ] **FIX CRITICAL:** Change bbox format to COCO `[x, y, width, height]`
- [ ] Add reference to ADR-0009 (COCO format decision)

---

### 9. Correction Thresholds (functional_requirements.md FR-3.2)

**Update Required** - Add do-no-harm guardrails from ADR-0021.

**Current PR Text (FR-3.2):**

```text
If absolute skew angle > 0.5 degrees, automatically de-skew.
```text

**ADR-0021 Requirements:**

```text
- Only deskew if angle > 2° AND variance improves > 5%
- Do-no-harm guardrails to prevent quality degradation
```text

**Recommended Update:**

```markdown
### FR-3.2: Skew Detection and Correction

**Detection:**
- Use cv2.minAreaRect() on content block to detect skew angle
- Report original angle in JSON metadata

**Correction (with Do-No-Harm Guardrails):**
- Threshold 1: Only correct if |angle| > 2.0 degrees (configurable)
- Threshold 2: Apply correction and measure variance improvement
- Threshold 3: Only keep correction if variance improves by > 5%
- Fallback: If correction degrades quality, use original image

**Rationale:** Prevents over-correction on already-clean documents (see ADR-0021).

**Configuration:**
- `skew_angle_threshold`: Default 2.0° (range: 0.5° - 5.0°)
- `variance_improvement_threshold`: Default 5% (range: 1% - 10%)
- `enable_deskew_guardrails`: Default true
```text

**Action Items:**

- [ ] Update FR-3.2 with 2° threshold (change from 0.5°)
- [ ] Add variance improvement check
- [ ] Reference ADR-0021 in functional requirements

---

### 10. Bounding Box Format (functional_requirements.md FR-4.3)

**CRITICAL UPDATE REQUIRED** - Wrong format specified.

**Current PR Text (FR-4.3):**

```text
bounding_box coordinates (e.g., [x1, y1, x2, y2])  ← WRONG!
```text

**ADR-0009 Requirement:**

```text
COCO format: [x, y, width, height]
Rationale: LayoutParser compatibility
```text

**Recommended Update:**

```markdown
### FR-4.3: Bounding Box Format

**Format:** COCO-aligned bounding boxes: `[x, y, width, height]`

**Where:**
- `x`: X-coordinate of top-left corner (pixels from left edge)
- `y`: Y-coordinate of top-left corner (pixels from top edge)
- `width`: Width of bounding box (pixels)
- `height`: Height of bounding box (pixels)

**Rationale:**
- Industry-standard COCO format ensures compatibility with LayoutParser
- Consistent with DocLayNet dataset format
- See ADR-0009 for full decision rationale

**Example:**
```json
{
  "class_label": "Table",
  "bounding_box": [120, 340, 450, 200],
  "confidence": 0.94
}
```text

**Action Items:**

- [ ] **CRITICAL:** Update FR-4.3 to COCO format `[x, y, width, height]`
- [ ] Add reference to ADR-0009
- [ ] Update all examples in functional requirements

---

### 11. Accuracy Targets (functional_requirements.md NFR-2.3)

**Minor Update** - Align with PROJECT_PLAN.

**Current PR Text (NFR-2.3):**

```text
Layout Model: mAP ≥ 0.85 on DocLayNet validation
```text

**PROJECT_PLAN (line 528):**

```text
mAP@.50: > 0.82
```text

**Recommended Update:**

```markdown
### NFR-2.3: Layout Model Accuracy

**Primary Metric:**
- mAP@.50 (COCO metric): > 0.82 (target), > 0.75 (acceptable)

**Secondary Metrics:**
- mAP@.50-.95: > 0.70
- Per-class AP: > 0.70 for all 11 classes (ensure rare class performance)

**Validation Dataset:** DocLayNet validation set (6,480 pages)

**Note:** Changed from 0.85 to 0.82 to align with PROJECT_PLAN Phase 3 targets.
```text

**Action Items:**

- [ ] Update NFR-2.3 to 0.82 (align with PROJECT_PLAN)
- [ ] Add per-class AP requirement
- [ ] Specify validation dataset

---

## 🔴 CONTENT TO DISCARD (Obsolete or Out of Scope)

### 12. Office Format Support (functional_requirements.md FR-1.2)

**Defer to Phase 5** - Preprocessing embedded images in office documents.

**Decision:** ✅ **Add to Phase 5 with Docling Integration**

**PR Text:**

```text
The system shall support:
- Office: .doc, .docx, .xls, .xlsx
```text

**Context from Project Owner:**

- Downstream system uses **Docling** for office format ingestion
- Office files contain embedded images that can have quality issues
- Preprocessing embedded images improves Docling's OCR accuracy

**Fixable Issues in Office Documents:**

1. **Embedded Images with Quality Issues:**
   - Low DPI (72 DPI screenshots embedded in Word docs)
   - Blur (photos taken with phone cameras)
   - Skew (scanned documents saved as Word docs)
   - Noise (legacy scanned images embedded in documents)

2. **Hybrid Documents:**
   - Word docs containing scanned page images
   - Same quality issues as scanned PDFs
   - Common in legal/medical workflows

3. **Complex Layouts:**
   - Excel: Multi-sheet workbooks with charts and embedded images
   - Word: Multi-column layouts, embedded tables, mixed text+images
   - PowerPoint: Slide layouts with text boxes, images, diagrams

**Phase 5 Implementation Approach:**

```python
# src/ingestion/office_preprocessor.py

class OfficeDocumentPreprocessor:
    """Preprocess embedded images in office documents before Docling parsing."""

    def preprocess_docx(self, docx_path: Path) -> DocumentMetadata:
        """
        Extract and preprocess embedded images from Word documents.

        Integration with Docling:
        1. Use python-docx to extract all embedded images
        2. For each image:
           - Run DPI detection (may be 72 DPI screenshots)
           - Run blur/skew/noise detection
           - Apply corrections if needed
        3. Save corrected images
        4. Generate metadata with image quality scores
        5. Pass corrected images to Docling for text extraction
        """
        from docx import Document

        doc = Document(docx_path)
        embedded_images = self._extract_images(doc)

        # Run existing preprocessing pipeline on each image
        processed_images = []
        for idx, img_data in enumerate(embedded_images):
            img = self._bytes_to_image(img_data)
            page_metadata = self.preprocessing_pipeline.process(img)
            corrected_img = self._apply_corrections(img, page_metadata)

            processed_images.append({
                "index": idx,
                "corrected": corrected_img,
                "metadata": page_metadata
            })

        return DocumentMetadata(
            file_path=str(docx_path),
            document_type="office_word",
            embedded_images=processed_images
        )
```text

**Integration Pipeline:**

```text
Office File (.docx, .xlsx, .pptx)
    ↓
[Image Preprocessing Detector] (Phase 5)
    - Extract embedded images (python-docx, openpyxl)
    - Detect quality issues (blur, DPI, skew, noise)
    - Correct images (upscale, deskew, denoise)
    - Generate metadata + corrected images
    ↓
[Docling] (Downstream)
    - Parse document structure
    - Extract text using corrected images (better OCR)
    - Generate final output for RAG
```text

**Benefits for Docling Integration:**

- Improved OCR accuracy on upscaled images (72 DPI → 300 DPI)
- Cleaner text extraction from deskewed images
- Quality metadata for confidence scoring on embedded images
- Consistent preprocessing across all document types (PDF + Office)

**Phase 5 Timeline (Weeks 21-25):**

- Week 21: Add office format parsers (python-docx, openpyxl, python-pptx)
- Week 22: Implement embedded image extraction
- Week 23: Integrate with existing preprocessing pipeline
- Week 24: Test with Docling integration
- Week 25: Production deployment and monitoring

**Dependencies:**

- `python-docx`: Word document parsing
- `openpyxl`: Excel document parsing
- `python-pptx`: PowerPoint parsing (optional)

**Recommended FR-1.2 Update:**

```markdown
### FR-1.2: Supported File Formats

**In-Scope (Phase 1-4):**
- Images: .jpg, .jpeg, .png, .tiff, .bmp
- PDFs: .pdf (all types: image-only, born-digital, hybrid)

**Phase 5 (Office Format Preprocessing):**
- Office: .doc, .docx, .xls, .xlsx, .pptx
- Scope: Preprocess embedded images only (not full document parsing)
- Integration: Extract images → preprocess → pass to Docling

**Out-of-Scope:**
- Other: .odt, .rtf, .epub (no current demand)
- Full office parsing (handled by Docling downstream)

**Rationale:**
Office formats contain embedded images that benefit from preprocessing
(DPI upscaling, deskewing, denoising). Preprocessing improves downstream
Docling OCR accuracy. Full document parsing delegated to Docling.
```text

**Action Items:**

- [ ] Add Office format preprocessing to PROJECT_PLAN Phase 5
- [ ] Update FR-1.2 with Phase 5 scope (embedded images only)
- [ ] Document Docling integration architecture
- [ ] Add implementation tasks for Week 21-25

---

### 13. PDF Portfolio Detection (functional_requirements.md FR-2.2)

**Discard** - Out of scope permanently.

**Decision:** ✅ **Ignore completely**

**PR Text:**

```text
FR-2.2: Identify PDF Portfolio files and flag as "Portfolio"
```text

**Rationale:**

- PDF Portfolios are rare in modern workflows (< 0.1% of documents)
- Adobe deprecated this format in 2023
- Low ROI for implementation effort
- Project owner confirmed: ignore completely

**Recommended Action:**

```markdown
### FR-2.2: PDF Portfolio Handling (Out of Scope)

**Status:** Permanently out of scope

**Rationale:**
PDF Portfolios (collection of embedded files) are deprecated by Adobe
and rarely encountered in production RAG workflows. The tool shall NOT
support portfolio detection or processing.

**Error Handling:**
If encountered, PyMuPDF will raise an exception during standard PDF loading.
Return user-friendly error: "PDF Portfolio format not supported. Please
extract individual files and process separately."

**No Implementation Required:** Standard PyMuPDF error handling sufficient.
```text

**Action Items:**

- [x] Confirm out of scope (decision from project owner)
- [ ] Remove FR-2.2 from functional requirements entirely
- [ ] Document in "Out of Scope" section
- [ ] No code changes required (PyMuPDF handles error naturally)

---

### 14. Adaptive Thresholding Requirement (functional_requirements.md FR-3.7)

**Discard or Revise** - Too prescriptive, conflicts with ML approach.

**PR Text:**

```text
FR-3.7: Apply adaptive thresholding (cv2.adaptiveThreshold)
to create clean, binarized image for layout analysis.
```text

**Issue:**

- Phase 3 uses deep learning (YOLOv8) which doesn't need binarization
- Classical methods (Phase 1) might use binarization, but it's implementation detail
- Functional requirements shouldn't specify algorithm (cv2.adaptiveThreshold)

**Recommended Revision:**

```markdown
### FR-3.7: Image Preprocessing for Analysis (Optional)

**Classical Methods (Phase 1):**
- May apply adaptive thresholding or other preprocessing as needed
- Implementation details are internal to detection modules

**ML Methods (Phase 2-3):**
- Deep learning models (YOLOv8, MobileNetV3) operate on RGB images
- No binarization required

**Rationale:**
Avoid over-specifying implementation details in functional requirements.
Preprocessing strategy is an internal decision based on detection method.
```text

**Action Items:**

- [ ] Revise FR-3.7 to be less prescriptive
- [ ] Remove specific cv2 function names from requirements

---

### 15. Column Count Detection (functional_requirements.md FR-4.4)

**Discard** - Redundant with layout detection.

**PR Text:**

```text
FR-4.4: Provide column_count (e.g., 1 or 2) by analyzing
spatial relationship of detected Text blocks.
```text

**Issue:**

- Layout detection already identifies multiple Text blocks
- Column count is derived from Text block positions
- Redundant with FR-4.2 output

**Recommended Action:**
Remove FR-4.4 and add note to FR-4.2:

```markdown
### FR-4.2: Layout Element Detection (Updated)

**Output:** List of detected elements with:
- class_label (e.g., "Text", "Table")
- bounding_box in COCO format [x, y, width, height]
- confidence score

**Derived Metadata:**
- Multi-column detection: Automatic from spatial analysis of Text blocks
- Reading order: Automatic from top-to-bottom, left-to-right sort
- Parasitic content: Flagged if class is Page-Header or Page-Footer
```text

**Action Items:**

- [ ] Remove FR-4.4 (redundant)
- [ ] Add derived metadata note to FR-4.2

---

## 📋 INTEGRATION ROADMAP

### Phase 1: Immediate Actions (This Week)

**Goal:** Incorporate high-value strategic content

1. **Create ADR-0028: Document Quality Score Framework**
   - Extract DQS concept from image_preprocessing.doc Section 1.4
   - Define degradation_score and structural_score calculation
   - Document routing logic for OCR vs. Vision pipelines
   - **Owner:** Claude Code (create now)
   - **Deadline:** Immediate

2. **Update PROJECT_PLAN Executive Summary**
   - Add strategic context from project_mandate.md Section 2-3
   - Explain OCR vs. Vision trade-off
   - Add business justification
   - **Files:** PROJECT_PLAN.md lines 9-16
   - **Deadline:** This week

3. **Extract Research Content**
   - Create `docs/research/document_quality_taxonomy.md` from image_preprocessing.doc Table 1
   - Create `docs/research/bibliography.md` with all citations
   - **Deadline:** This week

### Phase 2: Technical Updates (Next Week)

**Goal:** Align functional requirements with current architecture

1. **Update Functional Requirements Document**
   - Fix bounding box format (CRITICAL: [x,y,w,h] not [x1,y1,x2,y2])
   - Update performance targets (GPU/CPU split)
   - Update correction thresholds (2° with guardrails)
   - Remove Office format support (out of scope)
   - **Files:** Create `docs/requirements/functional_requirements_v2.md`
   - **Deadline:** Next week

2. **Add Missing Features to PROJECT_PLAN**
   - Add PDF type classification (Phase 2)
   - Add language detection details (Phase 2)
   - Add DQS routing logic (Phase 4)
   - **Files:** PROJECT_PLAN.md
   - **Deadline:** Next week

### Phase 3: Schema Updates (Week After)

**Goal:** Extend schema to support new features

1. **Update schema.py**
   - Add pdf_type field: Literal["image_only", "born_digital", "hybrid"]
   - Add languages: List[str] field
   - Add has_non_latin: bool field
   - Add dqs field: Dict with degradation_score, structural_score
   - **Files:** src/image_preprocessing_detector/schema.py
   - **Deadline:** 2 weeks

2. **Create Implementation Tasks**
   - Create src/ingestion/pdf_classifier.py (PDF type detection)
   - Create src/detection/language_detector.py (language detection)
   - Create src/scoring/dqs_calculator.py (DQS computation)
   - **Deadline:** Phase 2 planning

### Phase 4: Documentation Cleanup (Ongoing)

**Goal:** Maintain consistent documentation

1. **Archive PR Documents**
   - Move PRs 14-15 documents to `docs/archive/planning/`
   - Add "SUPERSEDED" header to each document
   - Reference updated versions
   - **Deadline:** After Phase 1-3 complete

2. **Update CHANGELOG**
   - Document what was extracted from PRs 14-15
   - Note what was discarded and why
   - **Deadline:** After all updates complete

---

## 🎯 SUCCESS CRITERIA

**This reconciliation is complete when:**

- [x] ADR-0028 (DQS) created and merged ✅
- [x] Project owner decisions documented ✅
- [ ] PROJECT_PLAN updated with strategic context from project_mandate.md
- [ ] PROJECT_PLAN Phase 5 updated with Office format preprocessing
- [ ] Research content extracted to docs/research/
- [ ] Functional requirements v2 created with all updates:
  - [ ] COCO bounding box format corrected (CRITICAL)
  - [ ] Performance targets aligned (GPU/CPU split)
  - [ ] Correction thresholds updated (2° with guardrails)
  - [ ] Office formats moved to Phase 5 (embedded image preprocessing)
  - [ ] PDF Portfolio removed (permanently out of scope)
- [ ] Schema updated with new fields (pdf_type, languages, dqs)
- [ ] PRs 14-15 documents archived with "SUPERSEDED" notice
- [ ] No conflicting documentation exists

---

## ✅ DECISIONS FROM PROJECT OWNER

**Date:** 2025-11-11
**Status:** All decisions confirmed, proceed with reconciliation

1. **Project Name:** ✅ **Keep "Image Preprocessing Detector"**
   - Current name maintained across all documentation
   - PRs 14-15 references to "RAG Triage Tool" should be updated

2. **Office Format Support:** ✅ **Defer to Phase 5 (with Docling integration)**
   - **Context:** Downstream system uses Docling for office format ingestion
   - **Scope:** Preprocess embedded images in office documents (.docx, .xlsx, .pptx)
   - **Rationale:** Office files contain embedded images that benefit from:
     - DPI upscaling (72 DPI screenshots → 300 DPI)
     - Blur/skew/noise detection and correction
     - Layout detection for document-containing images
   - **Integration:** Extract images → preprocess → pass corrected images to Docling
   - **Benefits:** Improved OCR accuracy on embedded images, quality metadata
   - **Timeline:** Phase 5 implementation (Weeks 21-25)
   - **See:** Updated section 12 below for implementation details

3. **PDF Portfolio Handling:** ✅ **Ignore completely**
   - Out of scope permanently
   - Add basic error message: "PDF Portfolio format not supported"
   - No detection or handling required

4. **DQS Framework:** ✅ **Implement in Phase 4**
   - ADR-0028 already created
   - Implementation timeline: Phase 4, Weeks 17-20
   - Routing logic for OCR vs. Vision pipeline selection

---

## 📚 REFERENCES

**Source Documents (PRs 14-15):**

- `docs/functional_requirements.md` (PR #14)
- `docs/project_mandate.md` (PR #14)
- `docs/technical_nethodology.md` (PR #14, note typo in filename)
- `docs/image_preprocessing.doc` (PR #15)

**Current Architecture:**

- `PROJECT_PLAN.md` (50+ pages)
- `docs/ADRs/0007-hybrid-iqa-approach.md`
- `docs/ADRs/0009-coco-bounding-box-format.md`
- `docs/ADRs/0021-do-no-harm-guardrails.md`
- `docs/PHASE_1B_IMPLEMENTATION_SUMMARY.md`

**Next Steps:**

- Create ADR-0028 (Document Quality Score Framework)
- Update PROJECT_PLAN with strategic content
- Create functional_requirements_v2.md

---

**Created:** 2025-11-11
**Last Updated:** 2025-11-11 (Updated with project owner decisions)
**Status:** Decisions Confirmed - Proceeding with Implementation
