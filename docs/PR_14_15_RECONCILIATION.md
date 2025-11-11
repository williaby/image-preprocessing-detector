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
```
Classify PDFs as:
- "Image-Only": No extractable digital text (scanned)
- "Born-Digital": Extractable text, no significant images
- "Hybrid": Both extractable text and embedded images with text
```

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
```
FR-5.3.1: Detect primary language(s) (e.g., ['en', 'fr'])
FR-5.3.3: Flag Non-Latin scripts (Arabic, Chinese, Japanese)
```

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
```
Identify mathematical equations by providing bounding boxes
for the Formula class (DocLayNet)
```

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
```
NFR-1.1: 100 docs (5 pages) in <15 min = 0.56 pages/sec
NFR-1.2: Single 10-page doc in <60 sec = 6 sec/page
```

**PROJECT_PLAN Targets (lines 547-558):**
```
Latency (GPU): < 150ms per page (6.67 pages/sec)
Throughput: > 6 pages/sec per GPU worker
```

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
```

**Action Items:**
- [ ] Update functional_requirements.md NFR-1 with GPU/CPU split
- [ ] Align with PROJECT_PLAN targets (150ms GPU, 400ms CPU)
- [ ] Add hardware configuration section

---

### 8. Layout Detection Classes (functional_requirements.md FR-4.2)

**Update Required** - Add handwriting detection, remove conflicts.

**Current PR Text (FR-4.2):**
```
Detect all 11 DocLayNet classes:
Caption, Footnote, Formula, List-Item, Page-Footer,
Page-Header, Picture, Section-Header, Table, Text, Title
```

**PROJECT_PLAN Additions (lines 87-95):**
```
- Handwriting regions (not in DocLayNet)
- Revision Markings (Yale manuscripts, not in DocLayNet)
```

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
```

**Action Items:**
- [ ] Update FR-4.2 with all classes (11 DocLayNet + 2 extended)
- [ ] **FIX CRITICAL:** Change bbox format to COCO `[x, y, width, height]`
- [ ] Add reference to ADR-0009 (COCO format decision)

---

### 9. Correction Thresholds (functional_requirements.md FR-3.2)

**Update Required** - Add do-no-harm guardrails from ADR-0021.

**Current PR Text (FR-3.2):**
```
If absolute skew angle > 0.5 degrees, automatically de-skew.
```

**ADR-0021 Requirements:**
```
- Only deskew if angle > 2° AND variance improves > 5%
- Do-no-harm guardrails to prevent quality degradation
```

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
```

**Action Items:**
- [ ] Update FR-3.2 with 2° threshold (change from 0.5°)
- [ ] Add variance improvement check
- [ ] Reference ADR-0021 in functional requirements

---

### 10. Bounding Box Format (functional_requirements.md FR-4.3)

**CRITICAL UPDATE REQUIRED** - Wrong format specified.

**Current PR Text (FR-4.3):**
```
bounding_box coordinates (e.g., [x1, y1, x2, y2])  ← WRONG!
```

**ADR-0009 Requirement:**
```
COCO format: [x, y, width, height]
Rationale: LayoutParser compatibility
```

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
```

**Action Items:**
- [ ] **CRITICAL:** Update FR-4.3 to COCO format `[x, y, width, height]`
- [ ] Add reference to ADR-0009
- [ ] Update all examples in functional requirements

---

### 11. Accuracy Targets (functional_requirements.md NFR-2.3)

**Minor Update** - Align with PROJECT_PLAN.

**Current PR Text (NFR-2.3):**
```
Layout Model: mAP ≥ 0.85 on DocLayNet validation
```

**PROJECT_PLAN (line 528):**
```
mAP@.50: > 0.82
```

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
```

**Action Items:**
- [ ] Update NFR-2.3 to 0.82 (align with PROJECT_PLAN)
- [ ] Add per-class AP requirement
- [ ] Specify validation dataset

---

## 🔴 CONTENT TO DISCARD (Obsolete or Out of Scope)

### 12. Office Format Support (functional_requirements.md FR-1.2)

**Discard** - Out of scope for current project.

**PR Text:**
```
The system shall support:
- Office: .doc, .docx, .xls, .xlsx  ← NOT IMPLEMENTED
```

**Rationale:**
- PROJECT_PLAN does not include Office formats
- No implementation exists in codebase
- Would require new dependencies (python-docx, openpyxl, LlamaParse)
- Significant scope expansion

**Alternative:** Mark as "Future Enhancement" or "Out of Scope"

**Recommended Replacement:**
```markdown
### FR-1.2: Supported File Formats

**In-Scope (Phase 1-3):**
- Images: .jpg, .jpeg, .png, .tiff, .bmp
- PDFs: .pdf (all types: image-only, born-digital, hybrid)

**Out-of-Scope (Future Consideration):**
- Office: .doc, .docx, .xls, .xlsx
- Other: .odt, .rtf, .epub

**Rationale:**
Office formats require specialized parsers (python-docx, openpyxl) and
have different processing requirements. May be added in Phase 5
(Continuous Improvement) if demand exists.
```

**Action Items:**
- [ ] Remove Office formats from FR-1.2
- [ ] Add to "Future Enhancements" section
- [ ] Document as explicit scope limitation

---

### 13. PDF Portfolio Detection (functional_requirements.md FR-2.2)

**Discard or Defer** - Rare edge case, minimal value.

**PR Text:**
```
FR-2.2: Identify PDF Portfolio files and flag as "Portfolio"
```

**Rationale:**
- PDF Portfolios are rare in modern workflows
- Adobe deprecated this format
- Low ROI for implementation effort

**Recommended Action:**
```markdown
### FR-2.2: PDF Portfolio Handling (Out of Scope)

**Status:** Deferred to Phase 5 (if needed)

**Rationale:**
PDF Portfolios (collection of embedded files) are deprecated by Adobe
and rarely encountered in production RAG workflows. If encountered,
the tool shall return an error: "PDF Portfolio format not supported."

**Future Implementation:**
If demand exists, add portfolio detection using PyMuPDF's
`doc.is_pdf` and `doc.embfile_count()` checks.
```

**Action Items:**
- [ ] Move FR-2.2 to "Out of Scope" section
- [ ] Add error handling for portfolio detection

---

### 14. Adaptive Thresholding Requirement (functional_requirements.md FR-3.7)

**Discard or Revise** - Too prescriptive, conflicts with ML approach.

**PR Text:**
```
FR-3.7: Apply adaptive thresholding (cv2.adaptiveThreshold)
to create clean, binarized image for layout analysis.
```

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
```

**Action Items:**
- [ ] Revise FR-3.7 to be less prescriptive
- [ ] Remove specific cv2 function names from requirements

---

### 15. Column Count Detection (functional_requirements.md FR-4.4)

**Discard** - Redundant with layout detection.

**PR Text:**
```
FR-4.4: Provide column_count (e.g., 1 or 2) by analyzing
spatial relationship of detected Text blocks.
```

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
```

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

4. **Update Functional Requirements Document**
   - Fix bounding box format (CRITICAL: [x,y,w,h] not [x1,y1,x2,y2])
   - Update performance targets (GPU/CPU split)
   - Update correction thresholds (2° with guardrails)
   - Remove Office format support (out of scope)
   - **Files:** Create `docs/requirements/functional_requirements_v2.md`
   - **Deadline:** Next week

5. **Add Missing Features to PROJECT_PLAN**
   - Add PDF type classification (Phase 2)
   - Add language detection details (Phase 2)
   - Add DQS routing logic (Phase 4)
   - **Files:** PROJECT_PLAN.md
   - **Deadline:** Next week

### Phase 3: Schema Updates (Week After)

**Goal:** Extend schema to support new features

6. **Update schema.py**
   - Add pdf_type field: Literal["image_only", "born_digital", "hybrid"]
   - Add languages: List[str] field
   - Add has_non_latin: bool field
   - Add dqs field: Dict with degradation_score, structural_score
   - **Files:** src/image_preprocessing_detector/schema.py
   - **Deadline:** 2 weeks

7. **Create Implementation Tasks**
   - Create src/ingestion/pdf_classifier.py (PDF type detection)
   - Create src/detection/language_detector.py (language detection)
   - Create src/scoring/dqs_calculator.py (DQS computation)
   - **Deadline:** Phase 2 planning

### Phase 4: Documentation Cleanup (Ongoing)

**Goal:** Maintain consistent documentation

8. **Archive PR Documents**
   - Move PRs 14-15 documents to `docs/archive/planning/`
   - Add "SUPERSEDED" header to each document
   - Reference updated versions
   - **Deadline:** After Phase 1-3 complete

9. **Update CHANGELOG**
   - Document what was extracted from PRs 14-15
   - Note what was discarded and why
   - **Deadline:** After all updates complete

---

## 🎯 SUCCESS CRITERIA

**This reconciliation is complete when:**

- [x] ADR-0028 (DQS) created and merged
- [ ] PROJECT_PLAN updated with strategic context from project_mandate.md
- [ ] Research content extracted to docs/research/
- [ ] Functional requirements v2 created with all updates:
  - [ ] COCO bounding box format corrected
  - [ ] Performance targets aligned (GPU/CPU)
  - [ ] Correction thresholds updated (2° with guardrails)
  - [ ] Office formats removed (out of scope)
- [ ] Schema updated with new fields (pdf_type, languages, dqs)
- [ ] PRs 14-15 documents archived with "SUPERSEDED" notice
- [ ] No conflicting documentation exists

---

## 📞 QUESTIONS FOR PROJECT OWNER

Before proceeding with full reconciliation, clarify:

1. **Project Name:**
   - Keep "Image Preprocessing Detector" (current) OR
   - Change to "RAG Triage Tool" (PRs 14-15)?

2. **Office Format Support:**
   - Permanently out of scope OR
   - Defer to Phase 5 (future enhancement)?

3. **PDF Portfolio Handling:**
   - Ignore completely OR
   - Add basic error detection?

4. **DQS Framework:**
   - Implement in Phase 4 (recommended) OR
   - Defer to Phase 5?

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
**Last Updated:** 2025-11-11
**Status:** Ready for Implementation
